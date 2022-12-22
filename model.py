from gurobi import *
from util import to_range

# supplier -> RDC / CS -> AA
model = Model('Disaster relief logistic model')
model.ModelSense = GRB.MINIMIZE

W1 = 0.4  # weight of objective 1 (total cost)
M = float('inf')  # a large number
EPSILON = 1  # a limit on the number of CS

# the deviation (δ) is indicating an increased commodity inventory penalized
# by the last term of the first objective function
DELTA = []

# sets / indices
SET = dict(
    I=[],  # set of suppliers (i)
    J=[],  # candidates of RDC or CS (j)
    K=[],  # set of AA (k)
    Kh=[],  # set of high-risk AA (`Kh` is a subset of `K`) (k′)
    # S=[], # set of possible scenarios (s)
    C=[]  # set of commodities (c)
)

# parameters
PARAMETER = dict(
    # p=[0.2, 0.3, 0,5], # occurrence probability of scenario `s`
    CAP_SIZE_r=1,  # capacity limit for an RDC
    CAP_SIZE_c=1,  # capacity limit for an CS
    CAP_SIZE_a=1,  # capacity limit for an AA
    Fr=1,  # fixed setup cost for an RDC
    Fc=1,  # fixed setup cost fo an CS
    C=[],  # transportation cost from supplier `i` to RDC / CS `j` for commodity `c`
    h=[],  # inventory holding cost for commodity `c` at AA `k`
    PI=[],  # inventory shortage cost for commodity `c`
    v=[],  # required unit space for commodity `c`
    D=[],  # amount of demand for commodity `c` at AA `k`
    S=[],  # amount of commodity `c` that could be supplied from supplier `i`
    RHOj=1,  # fraction of stocked material of commodity `c` remains usable at RDC / CS `j` (0 <= RHOj <= 1)
    RHOi=1  # fraction of stocked material of commodity `c` remains usable at supplier `i` (0 <= RHOi <= 1)
)

# variables
i, j, k, k_prime, c = [len(idx) for idx in SET.values()]
J_prime = []  # j′ is a subset of `J`

Q = model.addVars(i, j, c, lb=0, vtype=GRB.CONTINUOUS, name='Q')
X = model.addVars(i, j, c, lb=0, vtype=GRB.CONTINUOUS, name='X')
Y = model.addVars(j, k, c, lb=0, vtype=GRB.CONTINUOUS, name='Y')
Y_prime = model.addVars(len(J_prime), j, c, lb=0, vtype=GRB.CONTINUOUS, name='Y')
I = model.addVars(k, c, lb=0, vtype=GRB.CONTINUOUS, name='I')
b = model.addVars(k, c, lb=0, vtype=GRB.CONTINUOUS, name='b')
alpha = model.addVars(j, vtype=GRB.BINARY, name='alpha')  # if j is an RDC
beta = model.addVars(j, vtype=GRB.BINARY, name='beta')  # if j is a CS
model.update()

# defined for the convenience of formulation
SC = quicksum(PARAMETER['Fr'] * alpha[j] + PARAMETER['Fc'] * beta[j] for j in to_range(SET['J']))
TC = quicksum(PARAMETER['C'][i][j][c] * Q[i, j, c]
              for i in to_range(SET['I']) for j in to_range(SET['J']) for c in to_range(SET['C']))
TCs = quicksum(PARAMETER['C'][i][j][c] * X[i, j, c]
               for i in to_range(SET['I']) for j in to_range(SET['J']) for c in to_range(SET['C']))
TCRCs = quicksum(PARAMETER['C'][j][k][c] * Y[j, k, c]
                 for j in to_range(SET['J']) for k in to_range(SET['K']) for c in to_range(SET['C']))
ICs = quicksum(PARAMETER['h'][k][c] * I[k, c] for k in to_range(SET['K']) for c in to_range(SET['C']))
SCs = quicksum(PARAMETER['PI'][c] * b[k, c] for k in to_range(SET['K']) for c in to_range(SET['C']))

# objective function
model.setObjectiveN(SC + TC + TCs + TCRCs + ICs + SCs, index=0, weight=W1, name='Cost')
model.setObjectiveN(quicksum(max_(b[k, c] for k in to_range(SET['K'])) for c in to_range(SET['C'])),
                    index=1, weight=1 - W1, name='Satisfaction measure')

# constraints
# structure reference: https://or.stackexchange.com/questions/1508/common-structures-in-gurobi-python
model.addConstrs((
    quicksum(X[i, j, c] for i in to_range(SET['I'])) +
    PARAMETER['RHOj'] * quicksum(Q[i, j, c] for i in to_range(SET['I'])) +
    quicksum(Y_prime[j, j_prime, c] * alpha[j_prime] * alpha[j] for j_prime in to_range(J_prime) if j_prime != j) -  # puzzled: Y or Y′
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
