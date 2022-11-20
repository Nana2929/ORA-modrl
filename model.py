from gurobi import *

model = Model()
model.ScenarioNumber = 3
model.ModelSense = GRB.MINIMIZE

I = []
J = []
K = []
L = []
S = []
C = []
F = []
omega = []
h = []
pi = []

# variables
Q = model.addVar(vtype=GRB.CONTINUOUS, name='Q_i_j_c')
X = model.addVar(vtype=GRB.CONTINUOUS, name='X_i_j_c_s')
Y = model.addVar(vtype=GRB.CONTINUOUS, name='Y_j_k_c_s')
I = model.addVar(vtype=GRB.CONTINUOUS, name='I_k_c_s')
b = model.addVar(vtype=GRB.CONTINUOUS, name='b_k_c_s')
Z = model.addVar(vtype=GRB.BINARY, name='Z_j_l')
model.update()

SC = quicksum(F[j, l] * Z[j, l] for j in J for l in L)
TC = quicksum(c[i, j, c] * Q[i, j, c] for i in I for j in J for c in C)
PC = quicksum(omega[i, c, s] * Q[i, j, c, s] for i in I for j in J for c in C)
PCs = quicksum(omega[i, c, s] * X[i, j, c, s] for i in I for j in J for c in C)
TCSs = quicksum(c[i, j, c] * X[i, j, c] for i in I for j in J for c in C)
TCRCs = quicksum(c[j, k, c, s] * Y[j, k, c, s] for j in J for k in K for c in C)
ICs = quicksum(h[k, c] * I[k, c, s] for k in K for c in C)
SCs = quicksum(pi[c] * b[k, c, s] for k in K for c in C)
# objective function
model.setObjectiveN(SC + PC + TC + quicksum(p[s] * (PCs + TCSs + TCRCs + ICs + SCs) for s in S) +
                    _lambda[0] * quicksum(
                            p[s] * ((PCs + TCSs + TCRCs + ICs + SCs) -
                                    quicksum(p[s] * (PCs + TCSs + TCRCs + ICs + SCs) for s in S)
                            ) + 2*theta[0][s] for s in S) + gamma * quicksum(p[s] * delta[j][c][s] for j in J for c in C for s in S), 0, 1)
model.setObjectiveN(quicksum(p[s] * quicksum(for c in C) for s in S), 1, 0)
# constraints
model.addConstr()
