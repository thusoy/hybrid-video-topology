from pulp import *

prob = LpProblem("interkontinental-symmetric", LpMaximize)

# Variables
abs = LpVariable("abs", lowBound=0, cat=LpInteger)
abl = LpVariable("abl", lowBound=0, cat=LpInteger)
acs = LpVariable("acs", lowBound=0, cat=LpInteger)
acl = LpVariable('acl', lowBound=0, cat=LpInteger)
bcs = LpVariable("bcs", lowBound=0, cat=LpInteger)
bcl = LpVariable('bcl', lowBound=0, cat=LpInteger)

# Objective
prob += 10*(4*(acs + acl + abs + abl) + 3*(abs + abl + bcs + bcl) + 2*(acs + acl + bcs + bcl)) \
    - (7*(abs + acl + bcl) + 260*(bcs + acl + abl) + 250*(acs + bcl + abl))

# Constraints
prob += abs + abl + acs + acl <= 10
prob += abs + abl + bcs + bcl <= 7
prob += acs + acl + bcs + bcl <= 2
prob += abs + acl + bcl <= 50
prob += bcs + abl + acl <= 20
prob += acs + abl + bcl <= 20
prob += abs + abl >= 1
prob += acs + acl >= 1
prob += bcs + bcl >= 1
prob += abs >= 0
prob += abl >= 0
prob += acs >= 0
prob += acl >= 0
prob += bcs >= 0
prob += bcl >= 0

GLPK().solve(prob)

# Solution
for v in prob.variables():
    print v.name, "=", v.varValue

print "objective=", value(prob.objective)
