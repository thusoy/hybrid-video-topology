from pulp import *
import argparse
import logging

logger = logging.getLogger('hytop')
parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', help='Logs all constraints added',
    action='store_true', default=False)
args = parser.parse_args()
logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)

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
    },
    'standup': {
        0: {
            'downlink': '10Mbit',
            'uplink': '10Mbit',
            'gain': 4,
            1: '5ms 2ms',
            2: '7ms 2ms',
            3: '47ms 3ms'
        },
        1: {
            'downlink': '10Mbit',
            'uplink': '10Mbit',
            'gain': 4,
            0: '5ms 1ms',
            2: '7ms 2ms',
            3: '50ms 5ms',
        },
        2: {
            'downlink': '5Mbit',
            'uplink': '2Mbit',
            'gain': 3,
            0: '7ms 2ms',
            1: '7ms 1ms',
            3: '40ms 5ms',
        },
        3: {
            'downlink': '1Mbit',
            'uplink': '1Mbit',
            'gain': 2,
            0: '50ms 3ms',
            1: '50ms 5ms',
            2: '40ms 5ms',
        }
    },
}
case = cases['standup']

prob = LpProblem("interkontinental-asymmetric", LpMaximize)

def edges(include_self=False):
    for node in sorted(case.keys()):
        for other_node in sorted(case.keys()):
            if other_node != node or include_self:
                yield (node, other_node)

names = {0: 'EN', 1: 'TO', 2: 'TRE', 3: 'FI'}
def nodes():
    for node in [names[n] for n in sorted(case.keys())] + ['%sproxy' % names[n] for n in case]:
        yield node

def commodities():
    commodity_number = 0
    for node in sorted(case.keys()):
        for other_node in sorted(case.keys()):
            if node != other_node:
                yield commodity_number
                commodity_number += 1


def commodity_from_number(commodity_number):
    number = 0
    for node in sorted(case.keys()):
        for other_node in sorted(case.keys()):
            if node != other_node:
                if number == commodity_number:
                    return '%s->%s' % (names[node], names[other_node])
                number += 1

def commodity_from_nodes(sender, receiver):
    number = 0
    for node in sorted(case.keys()):
        for other_node in sorted(case.keys()):
            if node != other_node:
                if node == sender and other_node == receiver:
                    return number
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
for node in case:
    commodity_list = list(commodities())
    for other_node in case:
        if node != other_node:
            commodity = commodity_from_nodes(node, other_node)
            other_proxy = other_node + num_nodes
            # Add bandwidth-gains to objective
            objective += 10*case[node]['gain'] * variables[other_proxy][other_node][commodity]


for commodity in commodities():
    # Subtract edge cost from objective
    for node, other_node in edges():
        objective -= int(case[node][other_node].split()[0].strip('ms')) * variables[node+num_nodes][other_node+num_nodes][commodity]

logger.info('Objective: Maximize %s', objective)

# Objective
prob += objective

# Stay below bandwidth
for node in case:
    constraint = sum(variables[node+num_nodes][node]) <= int(case[node]['downlink'].strip('Mbit'))
    logger.info('Constraint: %s', constraint)
    prob += constraint
    constraint = sum(variables[node][node+num_nodes]) <= int(case[node]['uplink'].strip('Mbit'))
    logger.info('Constraint: %s', constraint)
    prob += constraint

# All commodities must be sent and received by the correct parties
for node in case:
    for other_node in case:
        if node != other_node:
            commodity = commodity_from_nodes(node, other_node)
            proxy = node + num_nodes
            constraint = variables[node][proxy][commodity] >= 1
            logger.info('Constraint: %s', constraint)
            prob += constraint

            other_proxy = other_node + num_nodes
            constraint = variables[other_proxy][other_node][commodity] >= 1
            logger.info('Constraint: %s', constraint)
            prob += constraint

for commodity in commodities():

    # Constraints
    # Every edge must be positive
    for node, other_node in edges(include_self=True):
        constraint = variables[node][other_node][commodity] >= 0
        logger.info('Constraint: %s', constraint)
        prob += constraint


    # Any single commodity must not exceed bandwidth
    for node in case:
        constraint = variables[node+num_nodes][node][commodity] <= int(case[node]['downlink'].strip('Mbit'))
        logger.info('Constraint: %s', constraint)
        prob += constraint
        constraint = variables[node][node+num_nodes][commodity] <= int(case[node]['uplink'].strip('Mbit'))
        logger.info('Constraint: %s', constraint)
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
        logger.info('Flow conservation: %s == %s', in_to_proxy, variables[proxy][node][commodity])
        logger.info('Flow conservation: %s == %s', out_of_proxy, variables[node][proxy][commodity])
        prob += in_to_proxy == variables[proxy][node][commodity]
        prob += out_of_proxy == variables[node][proxy][commodity]

        # Nodes can only be sinks to commodities destined for them

    # Add end-to-end sums
#    for node, other_node in edges():
#        proxy, other_proxy = node + num_nodes, other_node + num_nodes
#        constraint = variables[node][other_node][commodity] == (variables[node][proxy][commodity] +
#            variables[proxy][other_proxy][commodity] + variables[other_proxy][other_node][commodity])
#        logger.info('Constraint: %s', constraint)
#        prob += constraint

    # Add relaying servers that do not need to be flow constrained (in some way, anyway) for 'standup'
    # to be feasible


GLPK().solve(prob)

# Solution
for v in prob.variables():
    print v.name, "=", v.varValue

for commodity in commodities():
    name = commodity_from_number(commodity)
    print 'K%d: %s' % (commodity, name)

print "objective=", value(prob.objective)
