from gurobi import *
from util import to_range

# supplier -> RDC / CS -> AA
model = Model('Disaster relief logistic model')
# model.ScenarioNumber = 3
model.ModelSense = GRB.MINIMIZE

W1 = 0.4  # weight of objective 1 (total cost)
M = float('inf')  # a large number
DELTA = 1

# sets / indices
SET = dict(
    I=[],  # set of suppliers (i)
    J=[],  # candidates of RDC or CS (j)
    K=[],  # set of AA (k)
    Kh=[],  # set of high-risk AA (`Kh` is a subset of `K`) (k')
    # S=[], # set of possible scenarios (s)
    C=[]  # set of commodities (c)
)

# parameters
PARAMETER = dict(
    # p=[0.2, 0.3, 0,5], # occurrence probability of scenario `s`
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
J_prime = []  # j' is a subset of `J`

Q = model.addVars(i, j, c, vtype=GRB.CONTINUOUS, name='Q')
X = model.addVars(i, j, c, vtype=GRB.CONTINUOUS, name='X')
Y = model.addVars(j, k, c, vtype=GRB.CONTINUOUS, name='Y')
Y_prime = model.addVars(j, len(J_prime), c, vtype=GRB.CONTINUOUS, name='Y')
I = model.addVars(k, c, vtype=GRB.CONTINUOUS, name='I')
b = model.addVars(k, c, vtype=GRB.CONTINUOUS, name='b')
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
model.addConstr(
    quicksum(X[i, j, c] for i in to_range(SET['I']) for j in to_range(SET['J']) for c in to_range(SET['C'])) +
    PARAMETER['RHOj'] * quicksum(
        Q[i, j, c] for i in to_range(SET['I']) for j in to_range(SET['J']) for c in to_range(SET['C'])
    ) +
    quicksum(
        Y_prime[j, j_prime, c] * alpha[j_prime] * alpha[j]
        for j in to_range(SET['J']) for j_prime in to_range(J_prime) for c in to_range(SET['C'])
    ) -
    quicksum(
        Y[j, k, c] * (alpha[j] + beta[j])
        for j in to_range(SET['J']) for k in to_range(SET['K']) for c in to_range(SET['C'])
    ) -
    quicksum(DELTA[j][c] for j in to_range(SET['J']) for c in to_range(SET['C']))
    == 0
)
