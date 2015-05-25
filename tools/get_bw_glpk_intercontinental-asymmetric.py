from pulp import *
from pdb import set_trace as trace
from collections import namedtuple
import sys
import argparse
from itertools import chain
import logging

logger = logging.getLogger('hytop')
case = None
prob = None



class Commodity(int):
    def set_pair(self, sender, receiver):
        self.sender = sender
        self.receiver = receiver


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
        'nodes': {
            'A': {
                'downlink': '10Mbit',
                'uplink': '10Mbit',
                'gain': 4,
                'B': '5ms 2ms',
                'C': '7ms 2ms',
                'D': '47ms 3ms'
            },
            'B': {
                'downlink': '10Mbit',
                'uplink': '10Mbit',
                'gain': 4,
                'A': '5ms 1ms',
                'C': '7ms 2ms',
                'D': '50ms 5ms',
            },
            'C': {
                'downlink': '5Mbit',
                'uplink': '2Mbit',
                'gain': 3,
                'A': '7ms 2ms',
                'B': '7ms 1ms',
                'D': '40ms 5ms',
            },
            'D': {
                'downlink': '1Mbit',
                'uplink': '1Mbit',
                'gain': 2,
                'A': '50ms 3ms',
                'B': '50ms 5ms',
                'C': '40ms 5ms',
            }
        },
        'repeaters': {
            'rep_eu': {
                'A': '25ms 2ms',
                'B': '20ms 1ms',
                'C': '40ms 2ms',
                'D': '60ms 4ms',
                #'rep_eu': '130ms 2ms', # High-quality SLA-backed connection, how to specify?
                #'cost': '$.01/GB', # Roughly the cost pr GB at DigitalOcean
            },
        }
    },
}

Edge = namedtuple('Edge', ['slots', 'threshold', 'cost'])


def main():
    global case
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', help='Logs all constraints added',
        action='store_true', default=False)
    parser.add_argument('-d', '--debug', help='Print debug information',
        action='store_true', default=False)
    parser.add_argument('-s', '--slot-size', help='Set slot size to this size', default='512kbps')
    parser.add_argument('-e', '--edges', help='How many parallell edges to add between each pair of nodes', default=4, type=int)
    parser.add_argument('-c', '--case', choices=cases.keys(), default='asia')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, stream=sys.stdout)
    case = cases[args.case]
    solve_case(args, number_of_edges=args.edges)


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

def get_edges(number_of_slots, number_of_edges=4):
    cutoffs = get_cutoffs(number_of_edges)
    print '%d slots:' % number_of_slots,
    edges = [] # (slots, treshold, cost) tuples
    utilization = 0.0
    utilization_step = 1.0/number_of_slots
    for cutoff in cutoffs:
        slots = int(number_of_slots*(cutoff - utilization))
        utilization += utilization_step*slots
        edges.append(Edge(slots, utilization, cost(utilization)))
    edges.append((number_of_slots-sum(edge.slots for edge in edges), 1, cost(1)))
    edges = [edge for edge in edges if edge.slots]
    return edges

def cost(utilization, punishment_factor=0.9):
     # The closer the punishment_factor is to 1, the heavier the punishment
     # for saturating links (balance against cost factor of delay)
    return 1/(1-punishment_factor*utilization)

def get_cutoffs(partitions=4):
    segments = sum(2**i for i in range(partitions)) # Exponentially smaller
    segment_size = 1.0/segments
    segs = [segment_size*2**i for i in range(partitions)] # Gives an array like [0.066667, 0.1333, 0.26667, 0.53] for partitions=4
    cutoffs = [sum(segs[-1:-1-i:-1]) for i in range(1, partitions)] # Reverse the array and make each element a cumulative sum of foregoing elements
    return cutoffs

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
                commodity = Commodity(commodity_number)
                commodity.set_pair(node, other_node)
                yield commodity
                commodity_number += 1


def commodity_from_nodes(sender, receiver):
    number = 0
    for node in nodes():
        for other_node in nodes():
            if node != other_node:
                if node == sender and other_node == receiver:
                    commodity = Commodity(number)
                    commodity.set_pair(node, other_node)
                    return commodity
                number += 1


def proxies():
    for node in nodes():
        yield node + 'proxy'


def repeaters():
    for repeater in case.get('repeaters', {}):
        yield repeater

def add_constraint(constraint, label=None):
    global prob
    text = '%s constraint' % label if label else 'Constraint'
    logger.info('%s: %s', text, constraint)
    prob += constraint


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

def dump_variables(prob):
    print '\n'.join('%s = %s' % (v.name, v.varValue) for v in prob.variables() if v.varValue)

def solve_case(args, number_of_edges):
    global prob
    # Initialize variables
    variables = {}
    # Initialize all edge variables
    for node, other_node in edges():
        for commodity in commodities():
            bandwidth_limited = ('proxy' in node and node[0] == other_node) or ('proxy' in other_node and other_node[0] == node)
            parallell_edges = number_of_edges if bandwidth_limited else 1
            for edge in range(parallell_edges):
                # Assume nothing exceeds gigabit speeds, not even backbone links
                if edge == 0:
                    variables.setdefault(node, {}).setdefault(other_node, []).append([])
                variables[node][other_node][-1].append(LpVariable('%sto%sK%dC%d' % (node, other_node, commodity, edge),
                    lowBound=0, upBound=1000, cat=LpInteger))


    objective = 0
    for node, other_node in node_pairs():
        commodity = commodity_from_nodes(node, other_node)
        other_proxy = other_node + 'proxy'
        for edge in range(number_of_edges):
            # Add bandwidth-gains to objective
            objective += 10*case['nodes'][other_node]['gain'] * variables[other_proxy][other_node][commodity][edge]
            # TODO: Subtract incoming flow to the source node from objective?


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
                # TODO: Add edge cost for parallell edges between proxies and their nodes
                edge_latency = 0
            for edge in variables[node][other_node][commodity]:
                objective -= edge_latency*edge

    # TODO: Subtract repeater/re-encoder costs
    # TODO: Subtract CPU costs


    prob_type = LpMinimize if args.debug else LpMaximize
    prob = LpProblem("interkontinental-asymmetric", prob_type)

    # Objective
    if args.debug:
        prob += sum(_debug_vars)
    else:
        prob += objective
    logger.info('Objective: %s %s', LpSenses[prob.sense], objective)

    # Stay below bandwidth (capacities)
    for node in nodes():
        downlink_capacity = int(case['nodes'][node]['downlink'].strip('Mbit'))
        add_constraint(sum(sum(variables[node+'proxy'][node][commodity]) for commodity in commodities()) <= downlink_capacity)
        uplink_capacity = int(case['nodes'][node]['uplink'].strip('Mbit'))
        add_constraint(sum(sum(variables[node][node+'proxy'][commodity]) for commodity in commodities()) <= uplink_capacity)

    # All commodities must be sent by the correct parties
    # Note: Node should not need to send a commodity if a repeater does, and the
    # repeater receives another commodity from this node
    for commodity in commodities():
        proxy = commodity.sender + 'proxy'
        commodity_sources = sum(variables[commodity.sender][proxy][commodity])
        for repeater in repeaters():
            for proxy in proxies():
                commodity_sources += sum(variables[repeater][proxy][commodity])
        add_constraint(commodity_sources >= 1)
        add_constraint(sum(variables[commodity.receiver + 'proxy'][commodity.receiver][commodity]) >= 1)

    for commodity in commodities():

        # Constraints
        # Add flow conservation for proxies, as per an all-to-all topology
        for node in nodes():
            proxy = node + 'proxy'
            in_to_proxy = 0
            out_of_proxy = 0
            for other_node in chain(proxies(), repeaters()):
                if proxy == other_node:
                    continue
                in_to_proxy += sum(variables[other_node][proxy][commodity])
                out_of_proxy += sum(variables[proxy][other_node][commodity])
            logger.info('Flow conservation: %s == %s', in_to_proxy, variables[proxy][node][commodity])
            logger.info('Flow conservation: %s == %s', out_of_proxy, variables[node][proxy][commodity])
            prob += in_to_proxy == variables[proxy][node][commodity]
            prob += out_of_proxy == variables[node][proxy][commodity]

        # Add flow conservation for nodes, make sure they can only be origin for their own commodity,
        # and does not terminate their own commodities
        # TODO: Does not allow nodes to re-encode data for now
        for node in nodes():
            proxy = node + 'proxy'
            if node != commodity.sender and node != commodity.receiver:
                add_constraint(sum(variables[node][proxy][commodity]) == sum(variables[proxy][node][commodity]), 'Node')
            elif node == commodity.sender:
                add_constraint(sum(variables[proxy][node][commodity]) == 0, 'Node')

    # Repeaters repeat incoming commodities out to all proxies, converted to their desired commodity
    for repeater in repeaters():
        for node in nodes():
            proxy = node + 'proxy'
            left_side = 0
            right_side = []
            for commodity in commodities():
                if commodity.sender == node:
                    left_side += variables[proxy][repeater][commodity][0]
                    right_side.append(variables[repeater][commodity.receiver + 'proxy'][commodity][0])
            for outgoing in right_side:
                add_constraint(left_side == outgoing, 'Repeaterflow')

        # Never send traffic back to source (hopefully not needed)
        proxy_of_sending_node = commodity.sender + 'proxy'
        add_constraint(variables[repeater][proxy_of_sending_node][commodity][0] == 0, 'Repeater flow')

        # for proxy in proxies():
        #     if proxy != proxy_of_sending_node:
        #         # Send as much to each other proxy as you receive from the sender
        #         target_commodity = commodity_from_nodes(commodity.sender, proxy[0])
        #         constraint = variables[proxy_of_sending_node][repeater][commodity] == variables[repeater][proxy][target_commodity]
        #         logger.info('Repeater flow constraint: %s', constraint)
        #         prob += constraint

        #         # Don't send any of the other commodities from that node through this link.
        #         # This prevents stuff from going B -> repeater -> C -> A, but that shouldn't be necessary,
        #         # as the provider should have a backbone capable of B -> repeater -> A without the extra cost through C
        #         for other_commodity in commodities():
        #             if commodity != other_commodity and other_commodity.receiver != proxy[0]:
        #                 constraint = variables[repeater][proxy][other_commodity] == 0
        #                 logger.info('Repeater flow constraint: %s', constraint)
        #                 prob += constraint

        #                 # Make sure something is sent if something is received from a node

        #                 # Send on all edges if a commodity is received?



    if args.debug:
        for key in prob.constraints:
            prob.constraints[key] += debug()

    res = GLPK(echo_proc=args.verbose).solve(prob)


    for commodity in commodities():
        print 'K%d: %s -> %s' % (commodity, commodity.sender, commodity.receiver)

    if res < 0:
        print 'Unsolvable!'
        sys.exit(1)
    else:
        if args.debug:
            print 'Problem constraints:'
            for v in prob.variables():
                if v.varValue != 0.0 and (v.name.startswith('x') or v.name.startswith('y')):
                    print '\n'.join('\t' + str(c) for c in prob.constraints.values() if ' %s ' % (v.name,) in str(c))


        dump_variables(prob)
        print

        # Print the solution
        for node, other_node in node_pairs():
            commodity = commodity_from_nodes(node, other_node)
            proxy = node + 'proxy'
            other_proxy = other_node + 'proxy'
            path = [other_proxy]
            other_proxy = other_node + 'proxy'
            while path[-1] != proxy:
                incoming_paths = []
                for search_node, variable in variables.iteritems():
                    if path[-1] in variable and any(edge.varValue for edge in variable[path[-1]][commodity]):
                        # search_node has a path to the last node we found
                        incoming_paths.append(search_node)
                # Check for cycle
                for incoming_path in incoming_paths:
                    # Do we send to that node as well as receive -> cycle.
                    if any(edge.varValue for edge in variables[path[-1]][incoming_path][commodity]):
                        path.append(incoming_path)
                        path.append(path[-2])

                # Add non-cycle path
                for incoming_path in incoming_paths:
                    if incoming_path not in path:
                        # The other non-cycle path
                        path.append(incoming_path)

                if not incoming_paths:
                    if not path[-1].startswith('rep'):
                        print 'Commodity K%d not found in to %s' % (commodity, path[-1])
                        break
                    # Trace a repeater changing commodity type
                    all_node_commodities = [c for c in commodities() if c.sender == node and c != commodity]
                    origin_commodity = None
                    for c in all_node_commodities:
                        for sending_node, variable in variables.iteritems():
                            if path[-1] in variable and any(edge.varValue for edge in variable[path[-1]][c]):
                                origin_commodity = c
                                break
                    if origin_commodity is None:
                        print path
                    assert origin_commodity is not None, "Didn't find mangled commodity"
                    while path[-1] != proxy:
                        for search_node, variable in variables.iteritems():
                            if path[-1] in variable and any(edge.varValue for edge in variable[path[-1]][origin_commodity]):
                                path.append(search_node)
                                break
                        else:
                            print 'No path found after repeater change, path: %s' % path
                            break

                    if path[-1] != proxy:
                        break
            else:
                # Found path between nodes
                print '%s til %s (K%d):' % (node, other_node, commodity),
                cost = 0
                path = list(reversed(path))
                print ' -> '.join(p for p  in path), ',',
                for index, edge in enumerate(path[1:], 1):
                    flow = sum(edge.varValue for edge in variables[path[index-1]][path[index]][commodity])
                    if 'proxy' in path[index] and 'proxy' in path[index-1]:
                        # It's an edge between two proxies, ie. it has a latency cost
                        # which can be found from the case
                        cost += int(case['nodes'][path[index-1][0]][path[index][0]].split()[0].strip('ms'))
                    elif 'rep' in path[index] and 'proxy' in path[index-1]:
                        cost += int(case['repeaters'][path[index]][path[index-1][0]].split()[0].strip('ms'))
                    elif 'proxy' in path[index] and 'rep' in path[index-1]:
                        cost += int(case['repeaters'][path[index-1]][path[index][0]].split()[0].strip('ms'))
                print 'Flow: %s, cost: %dms' % (flow, cost)

        for node in nodes():
            downlink_total = int(case['nodes'][node]['downlink'].strip('Mbit'))
            uplink_total = int(case['nodes'][node]['uplink'].strip('Mbit'))
            proxy = node + 'proxy'
            downlink_usage = sum(sum(edge.varValue for edge in variables[proxy][node][commodity]) for commodity in commodities())
            uplink_usage = sum(sum(edge.varValue for edge in variables[node][proxy][commodity]) for commodity in commodities())
            print '%s downlink: %.1f, uplink: %.1f' % (node, float(downlink_usage)/downlink_total, float(uplink_usage)/uplink_total)

        print "Score =", value(prob.objective)


if __name__ == '__main__':
    main()
