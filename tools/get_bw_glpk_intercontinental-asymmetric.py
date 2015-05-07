from pulp import *
import sys
import argparse
from itertools import chain
import logging

logger = logging.getLogger('hytop')
parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', help='Logs all constraints added',
    action='store_true', default=False)
parser.add_argument('-d', '--debug', help='Print debug information',
    action='store_true', default=False)
args = parser.parse_args()
logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, stream=sys.stdout)

cases = {
    'asia': {
        'nodes': {
            'A': {
                'gain': 4, # Max quality percievable by this unit. 4=big monitor desktop, 3=laptop, 2=phone
                'downlink': '10Mbit',
                'uplink': '5Mbit',
                'B': '125ms 7ms',  # netem-compatible delay spec
                'C': '3ms 1ms'
            },
            'B': {
                'gain': 2,
                'downlink': '2Mbit',
                'uplink': '1Mbit',
                'A': '125ms 7ms',
                'C': '130ms 10ms'
            },
            'C': {
                'gain': 3,
                'downlink': '10Mbit',
                'uplink': '8Mbit',
                'A': '3ms 1ms',
                'B': '130ms 10ms',
            },
        },
        'repeaters': {
            'rep_asia': {
                'A': '130ms 5ms',
                'B': '20ms 2ms',
                'C': '110ms 4ms',
                'rep_eu': '130ms 2ms', # High-quality SLA-backed connection, how to specify?
                #'cost': '$.01/GB', # Roughly the cost pr GB at DigitalOcean
            },
#            'rep_eu': {
#                'A': '15ms 1ms',
#                'B': '2000ms 150ms',
#                'C': '10ms 1ms',
#                'rep_asia': '130ms 2ms', # High-quality SLA-backed connection, how to specify?
#            }
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


def edges(include_self=False):
    for node in nodes():
        for other_node in nodes():
            if other_node != node or include_self:
                yield (node + 'proxy', other_node + 'proxy')
        yield (node, node + 'proxy')
        yield (node + 'proxy', node)
    for proxy in proxies():
        for repeater in repeaters():
            yield (proxy, repeater)
            yield (repeater, proxy)


def node_pairs():
    for node in nodes():
        for other_node in nodes():
            if node != other_node:
                yield (node, other_node)


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


def commodity_from_nodes(sender, receiver):
    number = 0
    for node in nodes():
        for other_node in nodes():
            if node != other_node:
                if node == sender and other_node == receiver:
                    return number
                number += 1

def proxies():
    for node in nodes():
        yield node + 'proxy'

def repeaters():
    for repeater in case.get('repeaters', {}):
        yield repeater


_debug_vars = []
_debug_index = 0
def debug():
    global _debug_index
    if not args.debug:
        return 0
    _debug_index += 1
    _debug_vars.append(LpVariable('x%d' % _debug_index, lowBound=0))
    _debug_vars.append(LpVariable('y%d' % _debug_index, lowBound=0))
    return _debug_vars[-1] - _debug_vars[-2]


# Initialize variables
variables = {}
# Initialize all edge variables
for node, other_node in edges():
    for commodity in commodities():
        # Assume nothing exceeds gigabit speeds, not even backbone links
        variables.setdefault(node, {}).setdefault(other_node, []).append(LpVariable('%sto%sK%d' % (node, other_node, commodity),
            lowBound=0, upBound=1000, cat=LpInteger))


objective = 0
for node in nodes():
    commodity_list = list(commodities())
    for other_node in nodes():
        if node != other_node:
            commodity = commodity_from_nodes(node, other_node)
            other_proxy = other_node + 'proxy'
            # Add bandwidth-gains to objective
            objective += 10*case['nodes'][node]['gain'] * variables[other_proxy][other_node][commodity]


for commodity in commodities():
    # Subtract edge cost from objective
    for node, other_node in edges():
        if node.startswith('rep') or other_node.startswith('rep'):
            if node.startswith('rep'):
                other_actual_node = other_node[0]
                edge_latency = int(case['repeaters'][node][other_actual_node].split()[0].strip('ms'))
            else:
                other_actual_node = node[0]
                edge_latency = int(case['repeaters'][other_node][other_actual_node].split()[0].strip('ms'))
        elif 'proxy' in node and 'proxy' in other_node:
            edge_latency = int(case['nodes'][node[0]][other_node[0]].split()[0].strip('ms'))
        else:
            edge_latency = 0
        objective -= edge_latency * variables[node][other_node][commodity]

# TODO: Subtract repeater/re-encoder costs
# TODO: Subtract CPU costs

logger.info('Objective: Maximize %s', objective)

prob = LpProblem("interkontinental-asymmetric")

# Objective
#prob += objective
prob += sum(_debug_vars)

# Stay below bandwidth
for node in nodes():
    constraint = sum(variables[node+'proxy'][node]) <= int(case['nodes'][node]['downlink'].strip('Mbit'))
    logger.info('Constraint: %s', constraint)
    prob += constraint
    constraint = sum(variables[node][node+'proxy']) <= int(case['nodes'][node]['uplink'].strip('Mbit'))
    logger.info('Constraint: %s', constraint)
    prob += constraint

# All commodities must be sent and received by the correct parties
for node, other_node in node_pairs():
    commodity = commodity_from_nodes(node, other_node)
    proxy = node + 'proxy'
    constraint = variables[node][proxy][commodity] >= 1
    logger.info('Constraint: %s', constraint)
    prob += constraint

    other_proxy = other_node + 'proxy'
    constraint = variables[other_proxy][other_node][commodity] >= 1
    logger.info('Constraint: %s', constraint)
    prob += constraint

for commodity in commodities():

    # Constraints
    # Every edge must be positive
    for node, other_node in edges():
        constraint = variables[node][other_node][commodity] >= 0
        logger.info('Constraint: %s', constraint)
        prob += constraint


    # Any single commodity must not exceed bandwidth
    for node in nodes():
        constraint = variables[node+'proxy'][node][commodity] <= int(case['nodes'][node]['downlink'].strip('Mbit'))
        logger.info('Constraint: %s', constraint)
        prob += constraint
        constraint = variables[node][node+'proxy'][commodity] <= int(case['nodes'][node]['uplink'].strip('Mbit'))
        logger.info('Constraint: %s', constraint)
        prob += constraint

    # Add flow conservation, as per an all-to-all topology
    for node in nodes():
        proxy = node + 'proxy'
        in_to_proxy = 0
        out_of_proxy = 0
        for other_node in chain(proxies(), repeaters()):
            if proxy == other_node:
                continue
            in_to_proxy += variables[other_node][proxy][commodity]
            out_of_proxy += variables[proxy][other_node][commodity]
        logger.info('Flow conservation: %s == %s', in_to_proxy, variables[proxy][node][commodity])
        logger.info('Flow conservation: %s == %s', out_of_proxy, variables[node][proxy][commodity])
        prob += in_to_proxy == variables[proxy][node][commodity]
        prob += out_of_proxy == variables[node][proxy][commodity]

    # Repeaters can repeat arbitrary many copies of input data
    # TODO: Make repeaters able to change commodity type, or somehow make it possible to exceed the bandwidth limitation to the proxy
    # when sending through a repeater
    for repeater in repeaters():
        for proxy in proxies():
            constraint = variables[proxy][repeater][commodity] <= sum(variables[repeater][p][commodity] for p in proxies() if proxy != p)
            logger.info('Repeater flow constraint: %s', constraint)
            prob += constraint
            M = 1001
            for other_proxy in proxies():
                rep_binary = LpVariable('%s_%s_%s_K%d_bin' % (repeater, proxy, other_proxy, commodity), cat=LpBinary)
                if proxy != other_proxy:
                    constraint = variables[proxy][repeater][commodity] - (1-rep_binary)*M == variables[repeater][other_proxy][commodity]
                    #logger.info('Repeater flow constraint: %s', constraint)
                    #prob += constraint
                    constraint = variables[proxy][repeater][commodity] >= variables[repeater][other_proxy][commodity]
                    #logger.info('Repeater flow constraint: %s', constraint)
                    #prob += constraint
                    constraint = variables[repeater][proxy][commodity] <= rep_binary*M
                    #logger.info('Repeater flow constraint: %s', constraint)
                    #prob += constraint


    # Add end-to-end sums
#    for node, other_node in edges():
#        proxy, other_proxy = node +'proxy', other_node +'proxy'
#        constraint = variables[node][other_node][commodity] == (variables[node][proxy][commodity] +
#            variables[proxy][other_proxy][commodity] + variables[other_proxy][other_node][commodity])
#        logger.info('Constraint: %s', constraint)
#        prob += constraint

    # Add relaying servers that do not need to be flow constrained (in some way, anyway) for 'standup'
    # to be feasible

if args.debug:
    for key in prob.constraints:
        prob.constraints[key] += debug()

res = GLPK(echo_proc=args.verbose).solve(prob)

for node, other_node in node_pairs():
    commodity = commodity_from_nodes(node, other_node)
    print 'K%d: %s -> %s' % (commodity, node, other_node)

if res < 0:
    print 'Unsolvable!'
else:
    if args.debug:
        print 'Problem constraints:'
        for v in prob.variables():
            if v.varValue != 0.0 and (v.name.startswith('x') or v.name.startswith('y')):
                print '\n'.join('\t' + str(c) for c in prob.constraints.values() if ' %s ' % (v.name,) in str(c))

    # Print the solution
    for node, other_node in node_pairs():
        commodity = commodity_from_nodes(node, other_node)
        proxy = node + 'proxy'
        path = [proxy]
        other_proxy = other_node + 'proxy'
        while path[-1] != other_node:
            for edge, variable in variables[path[-1]].iteritems():
                if variable[commodity].varValue:
                    path.append(edge)
                    break
            else:
                print 'No path found from %s to %s' % (node, other_node)
                break
        else:
            # Found path between nodes
            print '%s til %s (K%d):' % (node, other_node, commodity),
            cost = 0
            for index, edge in enumerate(path[1:], 1):
                var = variables[path[index-1]][path[index]][commodity]
                print var.name, '->',
                if 'proxy' in path[index] and 'proxy' in path[index-1]:
                    # It's an edge between two proxies, ie. it has a latency cost
                    # which can be found from the case
                    cost += int(case['nodes'][path[index-1][0]][path[index][0]].split()[0].strip('ms'))
            print 'Flow: %s, cost: %dms' % (var.varValue, cost)

    for node in nodes():
        downlink_total = int(case['nodes'][node]['downlink'].strip('Mbit'))
        uplink_total = int(case['nodes'][node]['uplink'].strip('Mbit'))
        proxy = node + 'proxy'
        downlink_usage = sum(v.varValue for v in variables[proxy][node])
        uplink_usage = sum(v.varValue for v in variables[node][proxy])
        print '%s downlink: %.1f, uplink: %.1f' % (node, float(downlink_usage)/downlink_total, float(uplink_usage)/uplink_total)

    print "Score =", value(prob.objective)
