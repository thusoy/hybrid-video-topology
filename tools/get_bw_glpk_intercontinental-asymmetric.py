from pulp import *

cases = {
    'asia': {
        0: {
            'gain': 4, # Max quality percievable by this unit. 4=big monitor desktop, 3=laptop, 2=phone
            'downlink': '10Mbit',
            'uplink': '5Mbit',
            1: '125ms 7ms',  # netem-compatible delay spec
            2: '3ms 1ms'
        },
        1: {
            'gain': 2,
            'downlink': '2Mbit',
            'uplink': '2Mbit',
            0: '125ms 7ms',
            2: '130ms 10ms'
        },
        2: {
            'gain': 3,
            'downlink': '10Mbit',
            'uplink': '8Mbit',
            0: '3ms 1ms',
            1: '130ms 10ms',
        }
    }
}
case = cases['asia']

prob = LpProblem("interkontinental-asymmetric", LpMaximize)

def edges(include_self=False):
    for node in sorted(case.keys()):
        for other_node in sorted(case.keys()):
            if other_node != node or include_self:
                yield (node, other_node)

def nodes():
    names = {0: 'EN', 1: 'TO', 2: 'TRE'}
    for node in [names[n] for n in sorted(case.keys())] + ['%sproxy' % names[n] for n in case]:
        yield node

def commodities():
    commodity_number = 0
    for node in sorted(case.keys()):
        for other_node in sorted(case.keys()):
            if node != other_node:
                yield commodity_number
                commodity_number += 1


def commodity_name(commodity_number):
    number = 0
    for node in sorted(case.keys()):
        for other_node in sorted(case.keys()):
            if node != other_node:
                if number == commodity_number:
                    return 'K(%s-%s)' % (node, other_node)
                number += 1


num_nodes = len(case)

# Initialize variables
variables = []
for node in nodes():
    variables.append([])
    for other_node in nodes():
        variables[-1].append([])
        for commodity in commodities():
            # Assume nothing exceeds gigabit speeds, not even backbone links
            variables[-1][-1].append(LpVariable('%sto%sK%d' % (node, other_node, commodity),
                lowBound=0, upBound=1000, cat=LpInteger))


objective = 0
for commodity in commodities():
    # Add bandwidth-gains to objective
    for node, other_node in edges():
        objective += 10*case[node]['gain'] * variables[other_node][node][commodity]


    # Subtract edge cost from objective
    for node, other_node in edges():
        objective -= int(case[node][other_node].split()[0].strip('ms')) * variables[node+num_nodes][other_node+num_nodes][commodity]

print 'Objective: Maximize', objective

# Objective
prob += objective

# Stay below bandwidth
for node in case:
    constraint = sum(variables[node+num_nodes][node]) <= int(case[node]['downlink'].strip('Mbit'))
    print 'Constraint:', constraint
    prob += constraint
    constraint = sum(variables[node][node+num_nodes]) <= int(case[node]['uplink'].strip('Mbit'))
    print 'Constraint:', constraint
    prob += constraint

for commodity in commodities():

    # Constraints
    # Every edge must be positive
    for node, other_node in edges(include_self=True):
        constraint = variables[node][other_node][commodity] >= 0
        print 'Constraint:', constraint
        prob += constraint

    # All pairs must exchange traffic
    for node, other_node in edges():
        constraint = variables[node][other_node][commodity] >= 1
        print 'Constraint:', constraint
        prob += constraint

    # Any single commodity must not exceed bandwidth
    for node in case:
        constraint = variables[node+num_nodes][node][commodity] <= int(case[node]['downlink'].strip('Mbit'))
        print 'Constraint:', constraint
        prob += constraint
        constraint = variables[node][node+num_nodes][commodity] <= int(case[node]['uplink'].strip('Mbit'))
        print 'Constraint:', constraint
        prob += constraint

    # Add flow conservation, as per an all-to-all topology
    for node in case:
        proxy = node + num_nodes
        in_to_proxy = 0
        out_of_proxy = 0
        for other_node in case:
            if node == other_node:
                continue
            other_proxy = other_node + num_nodes
            in_to_proxy += variables[other_proxy][proxy][commodity]
            out_of_proxy += variables[proxy][other_proxy][commodity]
        print 'Flow conservation: ', in_to_proxy, '==', variables[node][proxy][commodity]
        print 'Flow conservation: ', out_of_proxy, '==', variables[proxy][node][commodity]
        prob += in_to_proxy == variables[node][proxy][commodity]
        prob += out_of_proxy == variables[proxy][node][commodity]

    # Add end-to-end sums
    for node, other_node in edges():
        proxy, other_proxy = node + num_nodes, other_node + num_nodes
        constraint = variables[node][other_node][commodity] == (variables[node][proxy][commodity] +
            variables[proxy][other_proxy][commodity] + variables[other_proxy][other_node][commodity])
        print 'Constraint:', constraint
        prob += constraint


GLPK().solve(prob)

# Solution
for v in prob.variables():
    print v.name, "=", v.varValue

print "objective=", value(prob.objective)
