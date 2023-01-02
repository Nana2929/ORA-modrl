## ORA Term Project 2022
### Disaster Relief Logistics with Contactless Delivery Policy
### 2022 Fall

Team B

資訊所一 楊晴雯 P76114511

資訊所一 許智豪 P76114503


---

## Table of Contents
1. [Introduction](#Introduction)
    1.1 [Background: Disaster Relief Logistics](#Background:-Disaster-Relief-Logistics)
    1.2 [Motivation](#Motivation)


## Introduction
### Background: Disaster Relief Logistics

Our project is inspired by "A multi-objective robust stochastic programming model for disaster relief logistics under uncertainty" by Ali bozorgi-Amiri et al, published on *OR Spectrum* in year 2011. Their model is a multi-objective model that aims to minimizes the total cost and its variance (as the first objective), and maximizes the satisfaction level of the least satisfied affected area (as the second objective). Since the disaster scale is stochastic, their model proposes to use discrete scenario analysis to include the stochastic factors.



### Abbreviations

RDC: Resource Distribution Center
CS: Contactless Station
AA: Affected Area


### Motivation
As Covid-19 threats gradually becomes a normality, it is a must to consider how to respond to a disaster under the pandemic. An imaginary scenario is that an earthquake damages a hospital that quarantines many Covid-19 confirmed cases, and now the resources need to be sent to this hospital without further human contacts. In this case, some contactless stations (CSs) need to be set up in place of the Amiri's proposed RDCs.
CSs send resources via self-driving cars, therefore avoid the risk brought by frequent human mobility in between. They also reduces the transportation costs because no drivers are needed. We imagine that CSs should have higher setup cost an dbetter capacity than RDCs.
The below compares the original paper setting and our proposed setting.
#### Amiri's Paper Setting
![alt text](./figures/schemas/amiri_general_schema_of_rd_chain.png)

#### Our Setting
![alt text](./figures/schemas/general_schema_of_rd_chain_revised.png)


### Problem Definition
Amiri's paper models disaster planning and response capturing the inherent uncertainty in demand, supply, and cost resulting from the disaster. The model consists of 3 stages and 2 kinds of pair-wise transportation (Supplier-RDC, RDC-AA). Given constraints on transportation and the capacity limits in the 3 sets of nodes, the goal is to select optimum number of commodities in delivery from node to node, locations to set up RDCs, and capacitiy levels if an RDC is to be set up, while minimizing the total cost and the least satisified area's shortage cost. Amiri's paper goes further to wrap the objective functions with a robust optimization framework to guarantee small variance and model feasibility; we would like to skip the part as it makes the model too complicated.
In brief, we would like to mainly follow Amiri's paper formulation and multi-objective (bi-objective) setting, but with the following modifications:
1. Separating RDCs into standard RDCs (denoted RDC) and CSs (denoted CS).
2. Separating affected areas into high-risk and low-risk AAs, where high-risk AAs only receive resources from CSs, and low-risk AAs could receive from both.
3. Simplifying the constraints by removing the procure costs of commodities, and fixing the setup cost and capacity size for RDC (Amiri's paper has 3 setup costs with 3 sizes), and handcrafting a setup cost and a capacity size for CS.
4. Simplifying the objectives by removing the robust optimization framework described in the paper section 3 formula (13), and keeping only the naive $\xi$ for both objectives.

## Methodology

### Formulation

- Sets and Indices

    - $I$: Suppliers
    - $J$: Candidate points for RDCs and CCs
    - $K$: Affected Areas
    - $I$, For each $j \in J$, it is could be an RDC, or a CS, or none of the above, just an empty point.
    - $K'$: High-risk Affected Areas; Affected Areas that only receive commodities transported by CSs.
    - $K/K'$: Low-risk Affected Areas; Affected Areas that only receive commodities transported by RDCs.
    - $C$: Commodity Types.
    - $S$: Possible scenarios (discrete).



- Parameters

    (Deterministic Parameters)

    - $F^R$: fixed setup cost for RDCs.
    - $F^C$: fixed setup cost for CSs.
    - $C_{ijc}$: transportation cost from supplier $i$ to candidate point $j$ with commodity $c$.
    - $h_{kc}$: inventory holding cost for commodity $c$ at AA $k$.
    - $\pi_{c}$: inventory shortage cost for commdotiy $c$.
    - $v_{c}$: required unit space for commodity $c$.
    - $S_ic$: amount of commodity $c$ supplied by supplier $i$.
    - M: a large number

    (Stochastic Parameters)

    - $p_s$: occurrence of probability of scenario $s \ in S$.
    - $C_{ijcs}$: transportation cost from supplier $i$ to candidate point $j$ with commodity $c$ under scenario $s$.
    - $C_{jkcs}$: transportation cost from candidate point $j$ to AA $k$ with commodity $c$ under scenario $s$.
    - $D_{kcs}$: amount of demand of commodity $c$ under scenario $s$.
    - $\rho_{jcs}$: fraction of stocked materials of commodity $c$ remains usable at candidate point $j$ under scenario $s$ ($$0 \leq \rho_{jcs} \leq 1$$)
    - $\rho_{ics}$: fraction of stokced materials of commodity $c$ remains usdables at supplier $i$ under scenario $s$ ($$0 \leq \rho_{ics} \leq 1$$)

- Decision Variables

    - $Q_{ijc}$: amount of commodity $c$ supplied by supplier $i$, stored at candidate point $j$.
    - $X_{ijcs}$: amount of commodity $c$ transferred from supplier $i$ to candidate point $j$ under scenario $s$. If $X_{ijcs} > 0, j$ must be either an RDC or a CS.
    - $Y_{jkcs}$: amount of commodity $c$ transferred from candidate point $j$ to AA $k$ under scenario $s$. If $Y_{jkcs} > 0, j$ must be either an RDC or a CS.
    <!-- - $Y'_{j'jcs}$: amount of commodity $c$ transferred from candidate point $j'$ to another candidate point $j$ under scenario $s$. If $j' = j$, then $Y'_{j'jcs} = 0$. -->
    - $I_{kcs}$: amount of inventory of commodity $c$ held at AA $k$ under scenario $s$.
    - $b_{kcs}$: amount of shortage of commodity $c$ at AA $k$ under scenario $s$.
    - $\alpha_i$: if candidate point $j$ is an RDC, $\alpha_j = 1$; otherwise $=0$.
    - $\beta_j$: if candidate point $j$ is a CS, $\beta_j = 1$; otherwise $=0$.

- Mathematical Formulations

    These are defined for convenience and the simplicity in objective functions.

    - $\Sigma_{j \in J}(F^R\alpha_j + F^C\beta_j)$: (SC) Setup Cost for RDCs and CSs
    - $\Sigma_{i\in I}\Sigma_{j \in J}\Sigma_{c \in C}C_{ijc}Q_{ijc}$: Transportation Cost from suppliers to RDCs and CSs (preparedness phase).
    - $\Sigma_{i\in I}\Sigma_{j \in J}\Sigma_{c \in C}C_{ijcs}X_{ijcs}$:(TC-pre) Transportation Cost from suppliers to RDCs and CSs under a scenario (response phase).
    - $\Sigma_{i\in I}\Sigma_{k \in K}\Sigma_{c \in C}C_{jkcs}Y_{jkcs}$:(TC-post)Transportation Cost from RDCs and CSs to AAs under a scenario (response phase).
    - $\Sigma_{k \in k}\Sigma_{c \in C}h_{kc}I_{kcs}$:(IC) Inventory holding costs at AAs under a scenario (response phase).
    - $\Sigma_{k \in K}\Sigma_{c \in C}\pi_{c}b_{kcs}$:(SHC) Shortage costs at AAs under a scenario (response phase).


- Constraints
    The green parts are highlighted to indicate the revised parts from Amiri's paper.

    (1) **Control Balance Equation**: The amount of commodities sent from suppliers and other RDC/CS $j'$ to $j$ $-$ the amount $j$ sending out to other AA roughly equals to the amount of commodities transferred to AAs from the RDC $j$. If LHS is greater than the RHS, this inventory surplus is penalized by the first objective.
    <!-- (24) -->

    $$\Sigma_{i \in I} X_{ijcs} + \rho\Sigma_{i \in I}Q_{ijc} + {\color{green}\Sigma_{j' \neq j}{Y_{jj'cs}}\alpha_{j'}\beta_{j'}} - \Sigma_{k \in K}Y_{jkcs}(\alpha_j + \beta_j) = \delta_{jcs} \\ \forall j \in J, \forall c \in C, \forall s \in S$$

    (2) **Inventory Equality Constraint**: The amount of commodites from RDC/CS $j$ to AA $k -$ AA $k$'s demand should equal to $k$'s invnentory $- k$'s shortage. The revised part is the special case when $k$ is a special AA that could only receive commodites sent by a CS.

    <!-- (25)- -->
    <!-- 從rdc j 送到AA k 的貨 = k's inventory - k's shortage -->
    $$(\Sigma_{j \in J}Y_{jkcs} (\alpha_j + \beta_j)) -  D_{kcs} = I_{kcs} - b_{kcs} \\ \forall k \in K/K' \forall c \in C, \forall s \in S$$
    <!-- 從cs j 送special AA k' 的貨 = k' 's inventory - k' 's shortage -->
    $$\color{green} (\Sigma_{j \in J}Y_{jk'cs} (\alpha_j + \beta_j)) -  D_{k'cs} = I_{k'cs} - b_{k'cs} \\ \forall k' \in K' \forall c \in C, \forall s \in S$$


    (3) **RDC/CS Transferability**: RDC/CS could transfer commodity to other nodes only if there exists another RDC/CS/AA.
    <!-- (26) -->
    <!-- j is a RDC or a CS and k is a low-risk AA <=> j can send stuffs to k -->
    $$Y_{jkcs} \leq M(\alpha_j + \beta_j)D_{kcs}c \\ \forall j \in J, \forall k \in K/K', \forall c \in C, \forall s \in S$$
    <!-- j is a cs and k' is a high-risk AA <=> j can send commods to k'-->
    $$\color{green} Y_{jk'cs} \leq M\beta_jD_{k'cs} \forall j \in J, \\ \forall k' \in K', \forall c \in C, \forall s \in S$$
    <!-- (28) -->

    $$\Sigma_{i \in I} {X_{ijcs} \leq M(\alpha_j + \beta_j)} \\ \forall j \in J, \forall c \in C, \forall s \in S$$

    (5) **RDC Capacity Constraint**: the amount of commodities sent from supplier $i$ to RDC $j$ should not exceed the capacity of the RDC. Similarly, the amount of commodities sent from supplier $i$ to CS $j$ should not exceed the capacity of the CS.
    <!-- (30) -->

    $$\Sigma_{i \in I}\Sigma_{c \in C} v_cQ_{ijc} \leq CapSize^R \cdot \alpha_j \forall j \in J\\
    \Sigma_{i \in I}\Sigma_{c \in C} v_cQ_{ijc} \leq CapSize^C \cdot \beta_j \forall j \in J$$

    (6) **Supplier Capacity Constraint (in preparedness phase):** The amount of commodities a supplier sends out to other places should not exceed the supplier's own capacity (before the disaster).
     <!-- (32) -->
    $$\Sigma_{j \in J} Q_{ijc} \leq S_{ic} \;\forall i \in I, \forall c \in C$$

    (7) **Supplier Capacity Constraint (in response phase):** The amount of commodities a supplier sends out to other places should not exceed the supplier's own capacity (after the disaster, under all scenarios).
     <!-- (33) -->
     $$\Sigma_{j \in J} X_{ijcs} \leq \rho_{ics} S_{ic} \;\forall i \in I, \forall c \in C, \forall s \in S$$

    (8) **RDC/CS Identity Constraint:** A node in set $J$ could only be (1) none (2) RDC (3) CS, but not RDC and CS simultaneously.
    <!-- (34) -->
    $$\alpha_j + \beta_j \leq 1 \;\forall j \in J$$

    (9) **CS Number Constraint:** $\epsilon$ is the maximum number of CSs allowed in the network.
    $$
    \color{green} \Sigma_{j \in J} \beta_j \leq \epsilon
    $$
- Objectives

    - Objective 1: minimize the total costs
    $SC + TC_{pre} + TC_{post}+ IC + SHC$
    - Objective 2: maximize the total satisfaction; i.e., minimize the shortage costs of the least satisfied AA under all scenarios.
    $\Sigma_{s \in S}p_s(\Sigma_{c \in C}\max_{k \in K}{b_{cks}})$


### Multi-Objective Optimization


 There are several methods to solve a multi-objective problem, as can be found in past literatures (Mahjoob, M. and Abbasian, P., 2018; Kong, Z. Y., How, B. S., Mahmoud, A., & Sunarso, J., 2022; Yang, Z. et al., 2014). We employ the following 2 methods to combine our 2 objectives together, and solve the problem as a single-objective problem.

#### Weighted-Sum Method
Both objectives are assigned a positive weight ($w$ for $Obj_1$, $0 \leq w \leq 1$) and the goal is to minimize the weighted sum of both objective functions. An issue is that $Obj_1$ involves $Obj_2$, so it must be numerically greater than the latter, therefore assigning a small enough $w$ is important to avoid the dominance of the total cost over AA satisfaction.
$$\min w * Obj_1 + (1 - w) * Obj_2$$


#### Lp-Metric Method
The Lp-metric method aims to reduce the digression btween objective functions and their ideal solution obtained by indiviually optimizing them. In order to obtain the $Obj^*$, we need to solve the problem with only one objective at a time (optimize twice) and then plug in the $Obj^*$ values, so there's 3 times of optimization in total.

$$\min w * \frac{Obj_1 - Obj_1^*}{Obj_1^*} + (1 - w) * \frac{Obj_2 - Obj_2^*}{Obj_2^*}$$




## Data Collection and Analysis Result

### Data Collection
We use the data in case study from Amiri's paper. The scene is set at a well-populated region of Iran located near sourthern Central Alborz, with several active faults surrounding (hence the disaster is imagined to be an earthquake). We consider
1. $I$ contains 5 suppliers, including Sari, Qazvin, Tehran, Arak and Isfahan.
2. $J$ contains 15 candidate points, including Gorgan, Semnan, Sari, Rasht, Qazvin, Karaj, Tehran, Varamin, Roibatkarim, Islamshahr, Shahriar, Gom, Arak, Isfahan and Kashan. Their pair-wise distance statistics are shown in figure 3. The setup costs of an RDC and a CS are shown in figure 3.
3. $K$ contains 15 demand points (AAs) which are the same as $J$. The first 8 nodes are low-risk AAs while the later 7 are high-risk ones (the former is denoted $K/K'$ while the latter is denoted $K'$). Their demands under all scenarios ($D_{kcs}$) are shown in figure 4.
4. $C$ is the set of commodities, here we use water, food, and shelter.
5. $S$ is the set of scenarios with probabilites $p_s = [0.45, 0.3, 0.1, 0.15]$.

Note that $I$ is a subset of $J$, and $J = K$. Although it could seem unreasonable that the resource sources and the demand points are the same nodes in calculation, we assume that the affected area and the center building are located in different geographical locations; they are simply within the same city. Same reasoning goes for the subset condition of $I \subseteq J$.

<figure>
  <img
  src="./figures/data/distance.png"
  alt="distance matrix">
  <figcaption>Figure 1. Distance matrix</figcaption>
</figure>


<figure>
  <img
  src="./figures/data/supplier_capacity.png">
  <figcaption>Figure 2. Supplier and their capacity with respect to commodity type</figcaption>
</figure>
  <img
  src="./figures/data/rho_remains_usable.png">

  Figure 5. $\rho_{jcs}$ and $\rho_{ics}$; the fraction of stocked materials that remain usable (unit: %).


<figure>
  <img width=200
  src="./figures/data/setup_cost.png">
  <figcaption>Figure 3. Setup cost for RDC and CS</figcaption>
</figure>

<figure>
  <img
  src="./figures/data/demand_under_scenario.png">
  <figcaption>Figure 4. Demands of each AA under different scenarios.</figcaption>
</figure>


## Result Analysis

### Modeling
We start simple and build a **deterministic model** first. This model assumes in the response phase, we have perfect knowledge of which scenario would happen, so the *demand, transportation cost, and the fraction of stocked materials that remain usable* are pre-determined. In the following experiemnts, we choose to use the scenario $s1$. We do not extensively discuss on this model but record its statistics for reference.
Our final model is the stochastic model that considers 4 scenarios, representing different epicenters and potential earthquake intensity.


### Implementation Details
We decide to solve the problem using Gurobi Optimization solver with the academic license. The environment is Gurobi 10.0.0 with Python 3.7.12 under the *Linux x86_64 system with 12th Gen Intel(R) Core(TM) i7-12700*.
In Gurobi implementation, we use the `setObjectiveN()`  that defaults to weighted-sum method according to the official documentation ([gurobi doc 9.1: Working with Multiple Objective](https://www.gurobi.com/documentation/9.1/refman/working_with_multiple_obje.html)) for both weighted-sum and Lp-metric strategies.

### Solution

```
model type: stochastic
weight: 0.3
optimization metod: Lp-metric
```



### Weight Analysis
| | Lp-metric  &nbsp; &nbsp;| Weighted-sum &nbsp; &nbsp;
| :------------ | :-------------------------:| -------------:|
Deterministic |![](./figures/dm_lp-metric.png)  |  ![](./figures/dm_weighted-sum.png)
Stochastic |![](./figures/sp_lp-metric.png)  |  ![](./figures/sp_weighted-sum.png)

Before analysis, it should be first noted that the numeric scales for both objectives are different; Objective 1 accumulates all costs so it is at around $10^4$, while Objective 2 is around $10^3$ (5 times smaller). Therefore, the Lp-metric which aims to minimize the digression between the objectives and their ideal solution is more suitable for this problem.

In terms of the modeling method, the stochastic model gives more flunctuating line than the deterministic one. With single-objective optimization, we can minimize the total costs to $11,950$ ($10^6\$$) and the maximum shortage costs to $1364$ ($10^6\$$).




## References

- Mahjoob, M. (2018). Designing a cost-time-quality-efficient grinding process using MODM methods. arXiv preprint arXiv:1804.10710. [link](https://arxiv.org/abs/1804.10710)
- Blank, J., & Deb, K. (2020). Pymoo: Multi-objective optimization in python. IEEE Access, 8, 89497-89509. [link](https://ieeexplore.ieee.org/document/8950979)
- Kong, Z. Y., How, B. S., Mahmoud, A., & Sunarso, J. (2022). Multi-objective Optimisation Using Fuzzy and Weighted Sum Approach for Natural Gas Dehydration with Consideration of Regional Climate. Process Integration and Optimization for Sustainability, 1-18. [link](https://doi.org/10.1007/s41616-021-00195-9)
- Yang, Z., Cai, X., & Fan, Z. (2014, July). Epsilon constrained method for constrained multiobjective optimization problems: some preliminary results. In Proceedings of the companion publication of the 2014 annual conference on genetic and evolutionary computation (pp. 1181-1186).