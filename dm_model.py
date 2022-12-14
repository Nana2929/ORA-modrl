#%%

import pandas as pd
from gurobipy import *
from util import to_range, DATA_PATH, FIG_PATH, RESULT_PATH, getSupplierAADistance, OptimizationMethod
from typing import List
import matplotlib.pyplot as plt

PATH_PREFIX = 'MoDRL_'
df_supplier = pd.read_csv(DATA_PATH + f'/{PATH_PREFIX}supplier.csv').drop('Suppliers', axis=1)
df_commodity = pd.read_csv(DATA_PATH + f'/{PATH_PREFIX}commodity.csv')
df_setup_cost = pd.read_csv(DATA_PATH + f'/{PATH_PREFIX}setup_cost.csv')
df_demand = pd.read_csv(DATA_PATH + f'/{PATH_PREFIX}demand.csv').drop('DP', axis=1)
df_remains_usable = pd.read_csv(DATA_PATH + f'/{PATH_PREFIX}remains_usable.csv').drop('Node', axis=1)
df_distance = pd.read_csv(DATA_PATH + f'/{PATH_PREFIX}distance.csv')
assert df_remains_usable.shape[1] == df_distance.shape[0]

M = 10 ** 1e1  # a large number
EPSILON = (df_demand.shape[1] // 2) + 1  # a limit on the number of CS

# sets / indices
# Here J, K are the same point sets
SET = dict(
    I=[i for i in range(df_supplier.shape[0])],  # set of suppliers (i)
    J=[j for j in range(df_demand.shape[1])],  # candidates of RDC or CS (j)
    K=[k for k in range(df_demand.shape[1])],  # set of AA (k)
    Kh=[k for k in range(df_demand.shape[1] // 2 + 1)],  # set of high-risk AA (`Kh` is a subset of `K`) (k′)
    # S=[], # set of possible scenarios (s)
    C=[c for c in range(df_supplier.shape[1])]  # set of commodities (c)
)

# the deviation (δ) indicates an increased commodity inventory penalized
# by the last term of the first objective function (the robust-optimization framework specified in paper p.7 section 3)
DELTA = [[0 for j in to_range(SET['C'])] for c in to_range(SET['J'])]

# parameters
PARAMETER = dict(
    # p=[0.2, 0.3, 0,5], # occurrence probability of scenario `s`
    CAP_SIZE_r=df_setup_cost.iloc[0, 2],  # capacity limit for an RDC
    CAP_SIZE_c=df_setup_cost.iloc[2, 2],  # capacity limit for an CS
    CAP_SIZE_a=df_setup_cost.iloc[1, 2],  # capacity limit for an AA
    Fr=df_setup_cost.iloc[0, 1],          # fixed setup cost for an RDC
    Fc=df_setup_cost.iloc[2, 1],          # fixed setup cost fo an CS
    AADist=df_distance.to_numpy(),        # distance between nodes
    SupAADist=getSupplierAADistance(
        distance_info_path=DATA_PATH + f'/{PATH_PREFIX}distance.csv',
        supplier_info_path=DATA_PATH + f'/{PATH_PREFIX}supplier.csv',
    ),
    Ci=[[tuple(df_commodity['transport'].tolist()) for _ in to_range(SET['J'])] for _ in
        range(df_supplier.shape[0])],
    # transportation cost from supplier `i` to RDC / CS `j` for commodity `c`
    Cj=[[tuple(df_commodity['transport'].tolist()) for _ in to_range(SET['K'])] for _ in to_range(SET['J'])],
    # transportation cost from RDC / CS `j` to AA `k` for commodity `c`
    h=[tuple(round(df_commodity['procure'] * 0.3, 3)) for _ in to_range(SET['K'])],
    # inventory holding cost for commodity `c` at AA `k`
    PI=tuple(round(df_commodity['procure'] * 0.6, 3)),  # inventory shortage cost for commodity `c`
    v=df_commodity['volume'].tolist(),  # required unit space for commodity `c`
    D=[(tuple(map(int, d.split(', ')))) for d in df_demand.iloc[0, :]],
    # amount of demand for commodity `c` at AA `k`
    S=list(df_supplier.itertuples(index=False, name=None)),
    # amount of commodity `c` that could be supplied from supplier `i`
    RHOj=0.26,  # fraction of stocked material of commodity `c` remains usable at RDC / CS `j` (0 <= RHOj <= 1)
    RHOi=0.26   # fraction of stocked material of commodity `c` remains usable at supplier `i` (0 <= RHOi <= 1)
)

# =====================================================

def solve(weight=0.01,
        opt_method=OptimizationMethod.WEIGHTED_SUM,
        single_objval:List[float]=[0,0],
        GAMMA = 100 ,
        delta_term = True):

    # supplier -> RDC / CS -> AA
    model = Model('Disaster relief logistic model: Deterministic')
    model.ModelSense = GRB.MINIMIZE
    model.setParam('NonConvex', 2)
    W1 = weight  # weight of objective 1 (total cost)

    # variables
    i, j, k, k_prime, c = [len(idx) for idx in SET.values()]
    J_prime = [j_prime for j_prime in to_range(SET['J'])]  # j′ is a subset of `J`

    # Qijc: Amount of commodity c supplied by supplier i to RDC / CS j
    Q = model.addVars(i, j, c, lb=0, vtype=GRB.CONTINUOUS, name='Q')
    # Xijcs: Amount of c transferred from Suppkier i to RDC / CS j under scenario s
    X = model.addVars(i, j, c, lb=0, vtype=GRB.CONTINUOUS, name='X')
    # Yjkcs: Amount of c transferred from RDC / CS j to AA k under scenario s
    Y = model.addVars(j, k, c, lb=0, vtype=GRB.CONTINUOUS, name='Y')
    # Y'_jj'cs: Amount of c transferred from RDC / CS j to RDC / CS j under scenario s
    # Y_prime = model.addVars(len(J_prime), j, c, lb=0, vtype=GRB.CONTINUOUS, name='Y')
    # Ikcs: Amount of inventory c held at AA k under scenario s
    I = model.addVars(k, c, lb=0, vtype=GRB.CONTINUOUS, name='I')
    # bkcs: Amount of shortage of c at AA k under scenario s
    b = model.addVars(k, c, lb=0, vtype=GRB.CONTINUOUS, name='b')
    # if j is an RDC
    alpha = model.addVars(j, vtype=GRB.BINARY, name='alpha')
    # if j is a CS
    beta = model.addVars(j, vtype=GRB.BINARY, name='beta')

    delta = model.addVars(j, c, vtype=GRB.CONTINUOUS, name='delta')


    # defined for linearize or Gurobi limited
    # reference: https://support.gurobi.com/hc/en-us/community/posts/4408734183185-TypeError-unsupported-operand-type-s-for-int-and-GenExpr-
    b_linearize = model.addVars(c, lb=0, vtype=GRB.CONTINUOUS, name='b_linearize')
    # reference: https://support.gurobi.com/hc/en-us/community/posts/360056771292-Invalid-argument-to-QuadExpr-multiplication-Error-
    j_disjoint = model.addVars(j, len(J_prime), lb=0, vtype=GRB.CONTINUOUS, name='j_disjoint')
    model.update()

    # defined for the convenience of formulation
    SC = quicksum(PARAMETER['Fr'] * alpha[j] + PARAMETER['Fc'] * beta[j] for j in to_range(SET['J']))
    # transportation cost (preparedness phase) from supplier i to RDC / CS j
    TC = quicksum(PARAMETER['Ci'][i][j][c] * Q[i, j, c] * PARAMETER['SupAADist'][i][j]
                  for i in to_range(SET['I']) for j in to_range(SET['J']) for c in to_range(SET['C']))
    # transportation cost (response phase) from supplier i to RDC / CS j
    TCs = quicksum(PARAMETER['Ci'][i][j][c] * X[i, j, c] * PARAMETER['SupAADist'][i][j]
                   for i in to_range(SET['I']) for j in to_range(SET['J']) for c in to_range(SET['C']))

    # transportation cost from RDC / CS j to AA k
    TCRCs = quicksum(PARAMETER['Cj'][j][k][c] * Y[j, k, c] * PARAMETER['AADist'][j][k]
                     for j in to_range(SET['J']) for k in to_range(SET['K']) for c in to_range(SET['C']))

    # inventory cost at AA k
    ICs = quicksum(PARAMETER['h'][k][c] * I[k, c] for k in to_range(SET['K']) for c in to_range(SET['C']))
    # shortage cost at AA k
    SCs = quicksum(PARAMETER['PI'][c] * b[k, c] for k in to_range(SET['K']) for c in to_range(SET['C']))

    # objective function
    # single objective 1 -> 9631.5
    # single objective 2 -> 567631.946 (setObjectiveN -> model.objVal) or 586.3 (best value)
    obj1 = SC + TC + TCs + TCRCs + ICs + SCs
    if delta_term:
        obj1_delta_term = GAMMA * quicksum(delta[j, c] for j in to_range(SET['J'])
                                           for c in to_range(SET['C']))
        obj1 = obj1 + obj1_delta_term
    obj2 = quicksum(b_linearize)
    if opt_method == OptimizationMethod.WEIGHTED_SUM:
        model.setObjectiveN(obj1, index=0, weight=W1, name='Cost')
        model.setObjectiveN(obj2, index=1, weight=1 - W1, name='Satisfaction measure')
    elif opt_method == OptimizationMethod.LP_METRIC:
        model.setObjectiveN(((obj1 - single_objval[0]) / single_objval[0]), index=0, weight=W1, name='Cost')
        model.setObjectiveN(((obj2 - single_objval[1]) / single_objval[1]), index=1, weight=1 - W1,
                            name='Satisfaction measure')

        # combined_obj = (W1 * ((obj1 - single_objval[0]) / single_objval[0])) + \
        #                ((1 - W1) * ((obj2 - single_objval[1]) / single_objval[1]))
        #
        # model.setObjective(combined_obj)

    # constraints
    # structure reference: https://or.stackexchange.com/questions/1508/common-structures-in-gurobi-python
    model.addConstrs((
        quicksum(X[i, j, c] for i in to_range(SET['I'])) +
        PARAMETER['RHOj'] * quicksum(Q[i, j, c] for i in to_range(SET['I'])) +
        quicksum(Y[j, j_prime, c] * j_disjoint[j, j_prime] for j_prime in to_range(J_prime) if j_prime != j) -
        quicksum(Y[j, k, c] for k in to_range(SET['K'])) * (alpha[j] + beta[j])
        == DELTA[j][c] for j in to_range(SET['J']) for c in to_range(SET['C'])
    ), 'c-24')

    model.addConstrs((
        quicksum(Y[j, k, c] * (alpha[j] + beta[j]) for j in to_range(SET['J'])) - PARAMETER['D'][k][c]
        == I[k, c] - b[k, c] for k in to_range(SET['K']) for c in to_range(SET['C'])
    ), 'c-25-1')

    model.addConstrs((
        quicksum(Y[j, k_prime, c] * beta[j] for j in to_range(SET['J'])) - PARAMETER['D'][k_prime][c]
        == I[k_prime, c] - b[k_prime, c] for k_prime in to_range(SET['Kh']) for c in to_range(SET['C'])
    ), 'c-25-2')

    model.addConstrs((
        Y[j, k, c] <= M * (alpha[j] + beta[j]) * PARAMETER['D'][k][c]
        for j in to_range(SET['J']) for k in to_range(SET['K']) for c in to_range(SET['C'])
    ), 'c-26-1')

    model.addConstrs((
        Y[j, k_prime, c] <= M * beta[j] * PARAMETER['D'][k_prime][c]
        for j in to_range(SET['J']) for k_prime in to_range(SET['Kh']) for c in to_range(SET['C'])
    ), 'c-26-2')

    model.addConstrs((
        Y[j, j, c] == 0
        for j in to_range(SET['J']) for c in to_range(SET['C'])
    ), 'c-27')

    model.addConstrs((
        quicksum(X[i, j, c] for i in to_range(SET['I']))
        <= M * (alpha[j] + beta[j]) for j in to_range(SET['J']) for c in to_range(SET['C'])
    ), 'c-28')

    model.addConstrs((
        quicksum(PARAMETER['v'][c] * Q[i, j, c] for i in to_range(SET['I']) for c in to_range(SET['C']))
        <= PARAMETER['CAP_SIZE_r'] * alpha[j] for j in to_range(SET['J'])
    ), 'c-30-1')

    model.addConstrs((
        quicksum(PARAMETER['v'][c] * Q[i, j, c] for i in to_range(SET['I']) for c in to_range(SET['C']))
        <= PARAMETER['CAP_SIZE_c'] * beta[j] for j in to_range(SET['J'])
    ), 'c-30-2')

    model.addConstrs((
        quicksum(PARAMETER['v'][c] * I[k, c] for c in to_range(SET['C']))
        <= PARAMETER['CAP_SIZE_a'] for k in to_range(SET['K'])
    ), 'c-31')

    model.addConstrs((
        quicksum(Q[i, j, c] for j in to_range(SET['J']))
        <= PARAMETER['S'][i][c] for i in to_range(SET['I']) for c in to_range(SET['C'])
    ), 'c-32')

    model.addConstrs((
        quicksum(X[i, j, c] for j in to_range(SET['J']))
        <= PARAMETER['RHOi'] * PARAMETER['S'][i][c] for i in to_range(SET['I']) for c in to_range(SET['C'])
    ), 'c-33')

    model.addConstrs((
        alpha[j] + beta[j] <= 1 for j in to_range(SET['J'])
    ), 'c-34')

    model.addConstr(quicksum(beta[j] for j in to_range(SET['J'])) <= EPSILON, 'c-number_of_CS')

    model.addConstrs((
        b_linearize[c] == max_(b[k, c] for k in to_range(SET['K'])) for c in to_range(SET['C'])
    ), 'c-b_linearize')

    model.addConstrs((
        j_disjoint[j, j_prime] == alpha[j_prime] * alpha[j]
        for j in to_range(J_prime) for j_prime in to_range(J_prime) if j_prime != j
    ), 'c-j_disjoint')

    model.optimize()

    print(f'Objective value: {model.objVal}')
    print(f'Objective 1 value: {obj1.getValue()}')
    print(f'Objective 2 value: {obj2.getValue()}')
    return model, obj1, obj2

#%%

def draw(optimize_method: str):

    # weight range
    weights = [0.1 * i for i in range(11)]
    # matplotlib settings
    ax1_color = 'dodgerblue'
    ax1_color2 = 'steelblue'
    ax2_color = "tab:green"
    msize = 12
    title = f'Deterministic model\'s objective value under different weight ({optimize_method})'
    figname =  f'/dm_{optimize_method}.png'
    statname = f'/statistics/dm_{optimize_method}.csv'
    if optimize_method == 'weighted-sum':
        solvers = [solve(w, OptimizationMethod.WEIGHTED_SUM) for w in weights]
        # weighted Objs
        wObjs = [weights[i] * solvers[i][1].getValue()
        + (1-weights[i]) * solvers[i][2].getValue() for i in to_range(weights)]

    elif optimize_method == 'lp-metric':
        m, obj1, obj2 = solve(1, OptimizationMethod.WEIGHTED_SUM)
        obj1_star = obj1.getValue()
        m, obj1, obj2 = solve(0, OptimizationMethod.WEIGHTED_SUM)
        obj2_star = obj2.getValue()
        objstars = [obj1_star, obj2_star]

        solvers = [solve(w, OptimizationMethod.LP_METRIC,
                    objstars) for w in weights]
        # note that in lp-metrics, we need (Obj - Obj*) / Obj* instead of native Obj
        Obj1_s = [(s[1].getValue()  - obj1_star) / obj1_star for s in solvers]
        Obj2_s = [(s[2].getValue() - obj2_star) / obj2_star for s in solvers]
        # lp-metric Objs
        wObjs = [weights[i] * Obj1_s[i] + (1-weights[i]) * Obj2_s[i] for i in to_range(weights)]

    Obj1s = [s[1].getValue() for s in solvers]
    Obj2s = [s[2].getValue() for s in solvers]
    # 1/2 subplots, double y-axis
    fig, ax1 = plt.subplots()
    # drawing the obj1, obj2 in ax1 (greater numeric scale)
    obj1_line = ax1.plot(weights, Obj1s,
            linestyle='-', linewidth='2',
            markersize=msize, marker='.',
            label="Obj1", color=ax1_color)
    obj2_line = ax1.plot(weights, Obj2s,
            linestyle='-', linewidth='2',
            markersize=msize, marker='.',
            label="Obj2", color=ax1_color2)
    ax1.set_ylabel('Single Obj Value', color=ax1_color)
    ax1.tick_params(axis='y', labelcolor=ax1_color)

    # drawing lp=metric obj in ax2 (smaller scale)
    ax2 = ax1.twinx()
    obj3_line = ax2.plot(weights, wObjs,
            linestyle='-', linewidth='2',
            markersize= msize, marker='.',
            color = ax2_color, label=optimize_method)
    ax2.set_ylabel(f'{optimize_method} Obj Value', color=ax2_color)
    ax2.tick_params(axis='y', labelcolor=ax2_color)

    # setting unified legend
    lns = obj1_line + obj2_line + obj3_line
    labs = [l.get_label() for l in lns]
    plt.legend(lns, labs, loc=0)

    plt.xlabel('weight')
    plt.title(title)
    plt.savefig(FIG_PATH + figname)
    plt.show()
     # saving stats
    columns = ['w', 'Obj1', 'Obj2', optimize_method]
    rows = {}
    if optimize_method == 'lp-metric':
       rows['*'] = [obj1_star, obj2_star, '', '']
    for wid, w in enumerate(weights):
        o1 = round(Obj1s[wid], 4)
        o2 = round(Obj2s[wid], 4)
        o3 = round(wObjs[wid], 4)
        # message = f'w: {w}, Obj1: {o1}, Obj2: {o2}, {optimize_method}: {o3} \n'
        row = [w, o1, o2, o3]
        rows[wid] = row
    sp_table = pd.DataFrame.from_dict(rows,
                orient='index',
                columns=columns)
    sp_table.to_csv(RESULT_PATH + statname)

#%%
draw('lp-metric')
#%%
draw('weighted-sum')

# %%
