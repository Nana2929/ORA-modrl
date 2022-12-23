import pandas as pd
from gurobi import *
from util import to_range, EXP_PATH, DATA_PATH

PATH_PREFIX = 'MoDRL_'
df_supplier = pd.read_csv(DATA_PATH + f'/{PATH_PREFIX}supplier.csv').drop('Suppliers', axis=1)
df_commodity = pd.read_csv(DATA_PATH + f'/{PATH_PREFIX}commodity.csv')
df_setup_cost = pd.read_csv(DATA_PATH + f'/{PATH_PREFIX}setup_cost.csv')
df_demand = pd.read_csv(DATA_PATH + f'/{PATH_PREFIX}demand.csv').drop('DP', axis=1)
df_remains_usable = pd.read_csv(DATA_PATH + f'/{PATH_PREFIX}remains_usable.csv').drop('Node', axis=1)

# supplier -> RDC / CS -> AA
model = Model('Disaster relief logistic model')
model.ModelSense = GRB.MINIMIZE

W1 = 0.4  # weight of objective 1 (total cost)
M = 10**1e1  # a large number
EPSILON = (df_demand.shape[1] // 2 // 2) + 1  # a limit on the number of CS

# sets / indices
SET = dict(
    I=[i for i in range(df_supplier.shape[0])],  # set of suppliers (i)
    J=[j for j in range(df_demand.shape[1] // 2)],  # candidates of RDC or CS (j)
    K=[k for k in range(df_demand.shape[1] // 2 + 1)],  # set of AA (k)
    Kh=[k for k in range(df_demand.shape[1] // 2 // 2)],  # set of high-risk AA (`Kh` is a subset of `K`) (k′)
    # S=[], # set of possible scenarios (s)
    C=[c for c in range(df_supplier.shape[1])]  # set of commodities (c)
)

# the deviation (δ) is indicating an increased commodity inventory penalized
# by the last term of the first objective function
DELTA = [[0 for j in to_range(SET['C'])] for c in to_range(SET['J'])]

# parameters
PARAMETER = dict(
    # p=[0.2, 0.3, 0,5], # occurrence probability of scenario `s`
    CAP_SIZE_r=df_setup_cost.iloc[0, 2],  # capacity limit for an RDC
    CAP_SIZE_c=df_setup_cost.iloc[2, 2],  # capacity limit for an CS
    CAP_SIZE_a=df_setup_cost.iloc[1, 2],  # capacity limit for an AA
    Fr=df_setup_cost.iloc[0, 1],  # fixed setup cost for an RDC
    Fc=df_setup_cost.iloc[2, 1],  # fixed setup cost fo an CS
    Ci=[[tuple(df_commodity['transport'].tolist()) for _ in to_range(SET['J'])] for _ in range(df_supplier.shape[0])],  # transportation cost from supplier `i` to RDC / CS `j` for commodity `c`
    Cj=[[tuple(df_commodity['transport'].tolist()) for _ in to_range(SET['K'])] for _ in to_range(SET['J'])],  # transportation cost from RDC / CS `j` to AA `k` for commodity `c`
    h=[tuple(round(df_commodity['procure'] * 0.3, 3)) for _ in to_range(SET['K'])],  # inventory holding cost for commodity `c` at AA `k`
    PI=tuple(round(df_commodity['procure'] * 0.6, 3)),  # inventory shortage cost for commodity `c`
    v=df_commodity['volume'].tolist(),  # required unit space for commodity `c`
    D=[(tuple(map(int, d.split(', ')))) for d in df_demand.iloc[0, 1:]],  # amount of demand for commodity `c` at AA `k`
    S=list(df_supplier.itertuples(index=False, name=None)),  # amount of commodity `c` that could be supplied from supplier `i`
    RHOj=0.26,  # fraction of stocked material of commodity `c` remains usable at RDC / CS `j` (0 <= RHOj <= 1)
    RHOi=0.26  # fraction of stocked material of commodity `c` remains usable at supplier `i` (0 <= RHOi <= 1)
)

# variables
i, j, k, k_prime, c = [len(idx) for idx in SET.values()]
J_prime = [j_prime for j_prime in to_range(SET['J'])]  # j′ is a subset of `J`

Q = model.addVars(i, j, c, lb=0, vtype=GRB.CONTINUOUS, name='Q')
X = model.addVars(i, j, c, lb=0, vtype=GRB.CONTINUOUS, name='X')
Y = model.addVars(j, k, c, lb=0, vtype=GRB.CONTINUOUS, name='Y')
Y_prime = model.addVars(len(J_prime), j, c, lb=0, vtype=GRB.CONTINUOUS, name='Y')
I = model.addVars(k, c, lb=0, vtype=GRB.CONTINUOUS, name='I')
b = model.addVars(k, c, lb=0, vtype=GRB.CONTINUOUS, name='b')
alpha = model.addVars(j, vtype=GRB.BINARY, name='alpha')  # if j is an RDC
beta = model.addVars(j, vtype=GRB.BINARY, name='beta')  # if j is a CS

# defined for linearize or Gurobi limited
# reference: https://support.gurobi.com/hc/en-us/community/posts/4408734183185-TypeError-unsupported-operand-type-s-for-int-and-GenExpr-
b_linearize = model.addVars(c, lb=0, vtype=GRB.CONTINUOUS, name='b_linearize')
# reference: https://support.gurobi.com/hc/en-us/community/posts/360056771292-Invalid-argument-to-QuadExpr-multiplication-Error-
j_disjoint = model.addVars(j, len(J_prime), lb=0, vtype=GRB.CONTINUOUS, name='j_disjoint')
model.update()

# defined for the convenience of formulation
SC = quicksum(PARAMETER['Fr'] * alpha[j] + PARAMETER['Fc'] * beta[j] for j in to_range(SET['J']))
TC = quicksum(PARAMETER['Ci'][i][j][c] * Q[i, j, c]
              for i in to_range(SET['I']) for j in to_range(SET['J']) for c in to_range(SET['C']))
TCs = quicksum(PARAMETER['Ci'][i][j][c] * X[i, j, c]
               for i in to_range(SET['I']) for j in to_range(SET['J']) for c in to_range(SET['C']))
TCRCs = quicksum(PARAMETER['Cj'][j][k][c] * Y[j, k, c]
                 for j in to_range(SET['J']) for k in to_range(SET['K']) for c in to_range(SET['C']))
ICs = quicksum(PARAMETER['h'][k][c] * I[k, c] for k in to_range(SET['K']) for c in to_range(SET['C']))
SCs = quicksum(PARAMETER['PI'][c] * b[k, c] for k in to_range(SET['K']) for c in to_range(SET['C']))

# objective function
model.setObjectiveN(SC + TC + TCs + TCRCs + ICs + SCs, index=0, weight=W1, name='Cost')
model.setObjectiveN(quicksum(b_linearize),
                    index=1, weight=1 - W1, name='Satisfaction measure')

# constraints
# structure reference: https://or.stackexchange.com/questions/1508/common-structures-in-gurobi-python
model.addConstrs((
    quicksum(X[i, j, c] for i in to_range(SET['I'])) +
    PARAMETER['RHOj'] * quicksum(Q[i, j, c] for i in to_range(SET['I'])) +
    quicksum(Y_prime[j, j_prime, c] * j_disjoint[j, j_prime] for j_prime in to_range(J_prime) if j_prime != j) -  # puzzled: Y or Y′
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
    Y_prime[j, j, c] == 0
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
