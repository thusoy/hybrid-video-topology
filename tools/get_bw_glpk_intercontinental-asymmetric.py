from pulp import *

cases = {
    'asia': {
        '1': {
            'gain': 4, # Max quality percievable by this unit. 4=big monitor desktop, 3=laptop, 2=phone
            'downlink': '10Mbit',
            'uplink': '5Mbit',
            '2': '125ms 7ms',  # netem-compatible delay spec
            '3': '3ms 1ms'
        },
        '2': {
            'gain': 2,
            'downlink': '2Mbit',
            'uplink': '2Mbit',
            '1': '125ms 7ms',
            '3': '130ms 10ms'
        },
        '3': {
            'gain': 3,
            'downlink': '10Mbit',
            'uplink': '8Mbit',
            '1': '3ms 1ms',
            '2': '130ms 10ms',
        }
    }
}
case = cases['asia']

prob = LpProblem("interkontinental-asymmetric", LpMaximize)

def edges(include_self=False):
    for node in case:
        for other_node in case:
            if other_node != node or include_self:
                yield (node, other_node)

def nodes():
    for node in [names[n] for n in sorted(case.keys())] + ['%sproxy' % names[n] for n in case]:
        yield node

names = {'1': 'EN', '2': 'TO', '3': 'TRE'}

# Initialize variables
variables = []
for node in nodes():
    variables.append([])
    for other_node in nodes():
        variables[-1].append(LpVariable('%sto%s' % (node, other_node), lowBound=0, cat=LpInteger))

for array in variables:
    for var in array:
        print str(var).ljust(12),
    print

# Add bandwidth-gains to objective
objective = 0
for node, other_node in edges():
    objective += 10*case[node]['gain'] * variables[int(other_node)-1][int(node)-1]

num_nodes = len(case)

# Subtract edge cost from objective
for node, other_node in edges():
    objective -= int(case[node][other_node].split()[0].strip('ms')) * variables[int(node)-1+num_nodes][int(other_node)-1+num_nodes]

print 'Objective:', objective

# Objective
prob += objective

# Constraints
# Every edge must be positive
for node, other_node in edges(include_self=True):
    print 'Constraint: %s >= 0' % variables[int(node)-1][int(other_node)-1]
    prob += variables[int(node)-1][int(other_node)-1] >= 0

# All pairs must exchange traffic
for node, other_node in edges():
    print 'Constraint: %s >= 1' % variables[int(node)-1][int(other_node)-1]
    prob += variables[int(node)-1][int(other_node)-1] >= 1

# Stay below bandwidth
for node in case:
    print 'Constraint: %s <= %s' % (variables[int(node)-1+num_nodes][int(node)-1], int(case[node]['downlink'].strip('Mbit')))
    prob += variables[int(node)-1+num_nodes][int(node)-1] <= int(case[node]['downlink'].strip('Mbit'))
    print 'Constraint: %s <= %s' % (variables[int(node)-1][int(node)-1+num_nodes], int(case[node]['uplink'].strip('Mbit')))
    prob += variables[int(node)-1][int(node)-1+num_nodes] <= int(case[node]['uplink'].strip('Mbit'))

# Add flow conservation!!

GLPK().solve(prob)

# Solution
for v in prob.variables():
    print v.name, "=", v.varValue

print "objective=", value(prob.objective)
