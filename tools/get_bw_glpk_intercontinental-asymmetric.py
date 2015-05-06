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
        'nodes': {
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
case = cases['asia']

prob = LpProblem("interkontinental-asymmetric", LpMaximize)

def edges(include_self=False):
    for node in nodes():
        for other_node in nodes():
            if other_node != node or include_self:
                yield (node, other_node)

names = {0: 'EN', 1: 'TO', 2: 'TRE', 3: 'FI'}
def all_node_names():
    for node in [names[n] for n in nodes()] + ['%sproxy' % names[n] for n in case['nodes']]:
        yield node

def nodes():
    for node in sorted(case['nodes'].keys()):
        yield node

def commodities():
    commodity_number = 0
    for node in nodes():
        for other_node in nodes():
            if node != other_node:
                yield commodity_number
                commodity_number += 1


def commodity_from_number(commodity_number):
    number = 0
    for node in nodes():
        for other_node in nodes():
            if node != other_node:
                if number == commodity_number:
                    return '%s->%s' % (names[node], names[other_node])
                number += 1

def commodity_from_nodes(sender, receiver):
    number = 0
    for node in nodes():
        for other_node in nodes():
            if node != other_node:
                if node == sender and other_node == receiver:
                    return number
                number += 1


num_nodes = len(case['nodes'])

# Initialize variables
variables = []
for node in all_node_names():
    variables.append([])
    for other_node in all_node_names():
        variables[-1].append([])
        for commodity in commodities():
            # Assume nothing exceeds gigabit speeds, not even backbone links
            variables[-1][-1].append(LpVariable('%sto%sK%d' % (node, other_node, commodity),
                lowBound=0, upBound=1000, cat=LpInteger))


objective = 0
for node in nodes():
    commodity_list = list(commodities())
    for other_node in nodes():
        if node != other_node:
            commodity = commodity_from_nodes(node, other_node)
            other_proxy = other_node + num_nodes
            # Add bandwidth-gains to objective
            objective += 10*case['nodes'][node]['gain'] * variables[other_proxy][other_node][commodity]


for commodity in commodities():
    # Subtract edge cost from objective
    for node, other_node in edges():
        objective -= int(case['nodes'][node][other_node].split()[0].strip('ms')) * variables[node+num_nodes][other_node+num_nodes][commodity]

logger.info('Objective: Maximize %s', objective)

# Objective
prob += objective

# Stay below bandwidth
for node in nodes():
    constraint = sum(variables[node+num_nodes][node]) <= int(case['nodes'][node]['downlink'].strip('Mbit'))
    logger.info('Constraint: %s', constraint)
    prob += constraint
    constraint = sum(variables[node][node+num_nodes]) <= int(case['nodes'][node]['uplink'].strip('Mbit'))
    logger.info('Constraint: %s', constraint)
    prob += constraint

# All commodities must be sent and received by the correct parties
for node in nodes():
    for other_node in nodes():
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
    for node in nodes():
        constraint = variables[node+num_nodes][node][commodity] <= int(case['nodes'][node]['downlink'].strip('Mbit'))
        logger.info('Constraint: %s', constraint)
        prob += constraint
        constraint = variables[node][node+num_nodes][commodity] <= int(case['nodes'][node]['uplink'].strip('Mbit'))
        logger.info('Constraint: %s', constraint)
        prob += constraint

    # Add flow conservation, as per an all-to-all topology
    for node in nodes():
        proxy = node + num_nodes
        in_to_proxy = 0
        out_of_proxy = 0
        for other_node in nodes():
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


res = GLPK().solve(prob)
if res < 0:
    print 'Unsolvable!'
else:
    # Print the solution
    for node, other_node in edges():
        commodity = commodity_from_nodes(node, other_node)
        proxy = node + num_nodes
        path = [proxy]
        other_proxy = other_node + num_nodes
        while path[-1] != other_node:
            for edge, variable in enumerate(variables[path[-1]]):
                if variable[commodity].varValue:
                    path.append(edge)
        print '%s til %s (K%d):' % (names[node], names[other_node], commodity),
        cost = 0
        for index, edge in enumerate(path[1:], 1):
            var = variables[path[index-1]][path[index]][commodity]
            print var.name, '->',
            if path[index] >= num_nodes and path[index-1] >= num_nodes:
                # It's an edge between two proxies, ie. it has a latency cost
                cost += int(case['nodes'][path[index-1]-num_nodes][path[index]-num_nodes].split()[0].strip('ms'))
        print 'Flow: %s, cost: %dms' % (var.varValue, cost)

    for node in nodes():
        downlink_total = int(case['nodes'][node]['downlink'].strip('Mbit'))
        uplink_total = int(case['nodes'][node]['uplink'].strip('Mbit'))
        proxy = node + num_nodes
        downlink_usage = sum(v.varValue for v in variables[proxy][node])
        uplink_usage = sum(v.varValue for v in variables[node][proxy])
        print '%s downlink: %.1f, uplink: %.1f' % (names[node], float(downlink_usage)/downlink_total, float(uplink_usage)/uplink_total)

    print "Score =", value(prob.objective)
