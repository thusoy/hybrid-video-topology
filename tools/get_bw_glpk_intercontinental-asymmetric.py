from collections import namedtuple
from itertools import chain, product
from pdb import set_trace as trace
from pulp import LpMinimize, LpMaximize, LpProblem, LpVariable, LpInteger, LpSenses, GLPK, value
import argparse
import logging
import os
import sys
import yaml

logger = logging.getLogger('hytop')
case = None
constraints = []


class Commodity(int):
    def set_pair(self, sender, receiver):
        self.sender = sender
        self.receiver = receiver


def load_cases(case_file):
    with open(case_file) as fh:
        return yaml.load(fh)

Edge = namedtuple('Edge', ['slots', 'threshold', 'cost'])


def main():
    global case
    default_case_file = os.path.join(os.path.dirname(__file__), 'cases.yml')
    cases = load_cases(default_case_file)
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', help='Logs all constraints added',
        action='store_true', default=False)
    parser.add_argument('-d', '--debug', help='Print debug information',
        action='store_true', default=False)
    parser.add_argument('-s', '--slot-size', help='Set slot size to this size', default='512kbps')
    parser.add_argument('-e', '--edges', default=4, type=int,
        help='How many parallell edges to add between each pair of nodes')
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
    text = '%s constraint' % label if label else 'Constraint'
    logger.info('%s: %s', text, constraint)
    constraints.append(constraint)


_debug_vars = []
_debug_index = 0
def debug():
    global _debug_index
    _debug_index += 1
    _debug_vars.append(LpVariable('x%d' % _debug_index, lowBound=0))
    _debug_vars.append(LpVariable('y%d' % _debug_index, lowBound=0))
    return _debug_vars[-1] - _debug_vars[-2]

def dump_nonzero_variables(prob):
    print '\n'.join('%s = %s' % (v.name, v.varValue) for v in prob.variables() if v.varValue)


def get_edge_latency(node, other_node):
    """ Get latency of edge between node and other_node. If that is not specified in the case spec,
    latency from other_node to node will be returned if present.
    """
    if node.startswith('rep'):
        other_actual_node = other_node[0]
        edge_latency = int(case['repeaters'][node][other_actual_node].split()[0].strip('ms'))
    elif other_node.startswith('rep'):
        other_actual_node = node[0]
        edge_latency = int(case['repeaters'][other_node][other_actual_node].split()[0].strip('ms'))
    elif 'proxy' in node and 'proxy' in other_node:
        try:
            edge_latency = int(case['nodes'][node[0]][other_node[0]].split()[0].strip('ms'))
        except:
            # A -> B not defined, lookup B -> A
            edge_latency = int(case['nodes'][other_node[0]][node[0]].split()[0].strip('ms'))
    else:
        # TODO: Add edge cost for parallell edges between proxies and their nodes
        edge_latency = 0
    return edge_latency


def get_objective(variables, number_of_edges):
    objective = 0
    for node, other_node in node_pairs():
        commodity = commodity_from_nodes(node, other_node)
        other_proxy = other_node + 'proxy'
        for edge in range(number_of_edges):
            # Add bandwidth-gains to objective
            objective += 10*case['nodes'][other_node]['gain'] * variables[other_proxy][other_node][commodity][edge]
            # TODO: Subtract incoming flow to the source node from objective?


    for commodity, (node, other_node) in product(commodities(), edges()):
        # Subtract edge cost from objective
        edge_latency = get_edge_latency(node, other_node)
        for edge in variables[node][other_node][commodity]:
            objective -= edge_latency*edge

    return objective


def initialize_variables(number_of_edges):
    variables = {}
    # Initialize all edge variables
    for (node, other_node), commodity in product(edges(), commodities()):
        bandwidth_limited = ('proxy' in node and node[0] == other_node) or ('proxy' in other_node and other_node[0] == node)
        parallell_edges = number_of_edges if bandwidth_limited else 1
        for edge in range(parallell_edges):
            # Assume nothing exceeds gigabit speeds, not even backbone links
            if edge == 0:
                variables.setdefault(node, {}).setdefault(other_node, []).append([])
            variables[node][other_node][-1].append(LpVariable('%sto%sK%dC%d' % (node, other_node, commodity, edge),
                lowBound=0, upBound=1000, cat=LpInteger))
    return variables

def add_bandwidth_conservation(variables):
    # Stay below bandwidth (capacities)
    for node in nodes():
        downlink_capacity = int(case['nodes'][node]['downlink'].strip('Mbit'))
        add_constraint(sum(sum(variables[node+'proxy'][node][commodity]) for commodity in commodities()) <= downlink_capacity)
        uplink_capacity = int(case['nodes'][node]['uplink'].strip('Mbit'))
        add_constraint(sum(sum(variables[node][node+'proxy'][commodity]) for commodity in commodities()) <= uplink_capacity)


def add_all_commodities_must_be_sent_and_received_constraint(variables):
    # All commodities must be sent by the correct parties
    # Note: Node should not need to send a commodity if a repeater does, and the
    # repeater receives another commodity from this node
    for commodity in commodities():
        proxy = commodity.sender + 'proxy'
        commodity_sources = sum(variables[commodity.sender][proxy][commodity])
        for repeater, proxy in product(repeaters(), proxies()):
            commodity_sources += sum(variables[repeater][proxy][commodity])
        add_constraint(commodity_sources >= 1)
        add_constraint(sum(variables[commodity.receiver + 'proxy'][commodity.receiver][commodity]) >= 1)


def add_proxy_flow_conservation(variables):
    for commodity, node in product(commodities(), nodes()):
        # Add flow conservation for proxies, as per an all-to-all topology
        proxy = node + 'proxy'
        in_to_proxy = 0
        out_of_proxy = 0
        for other_node in chain(proxies(), repeaters()):
            if proxy == other_node:
                continue
            in_to_proxy += sum(variables[other_node][proxy][commodity])
            out_of_proxy += sum(variables[proxy][other_node][commodity])
        add_constraint(in_to_proxy == variables[proxy][node][commodity])
        add_constraint(out_of_proxy == variables[node][proxy][commodity])


def add_node_flow_conservation(variables):
    for commodity, node in product(commodities(), nodes()):
        # Add flow conservation for nodes, make sure they can only be origin for their own commodity,
        # and does not terminate their own commodities
        # TODO: Does not allow nodes to re-encode data for now
        proxy = node + 'proxy'
        if node != commodity.sender and node != commodity.receiver:
            add_constraint(sum(variables[node][proxy][commodity]) == sum(variables[proxy][node][commodity]), 'Node')
        elif node == commodity.sender:
            add_constraint(sum(variables[proxy][node][commodity]) == 0, 'Node')

def add_repeater_flow_conservation(variables):
    # Repeaters repeat incoming commodities out to all proxies, converted to their desired commodity
    for repeater, node in product(repeaters(), nodes()):
        proxy = node + 'proxy'
        left_side = 0
        right_side = []
        for commodity in commodities():
            if commodity.sender == node:
                left_side += variables[proxy][repeater][commodity][0]
                right_side.append(variables[repeater][commodity.receiver + 'proxy'][commodity][0])

                # Never send traffic back to source (hopefully not needed)
                proxy_of_sending_node = commodity.sender + 'proxy'
                add_constraint(variables[repeater][proxy_of_sending_node][commodity][0] == 0, 'Repeater flow')

        for outgoing in right_side:
            add_constraint(left_side == outgoing, 'Repeaterflow')



def get_constraints(variables):
    constaint_sources = (
        add_bandwidth_conservation,
        add_all_commodities_must_be_sent_and_received_constraint,
        add_proxy_flow_conservation,
        add_node_flow_conservation,
        add_repeater_flow_conservation,
    )
    for source in constaint_sources:
        source(variables)
    return constraints

def print_problem_constraints(prob):
    print 'Problem constraints:'
    for v in prob.variables():
        if v.varValue != 0.0 and (v.name.startswith('x') or v.name.startswith('y')):
                print '\n'.join('\t' + str(c) for c in prob.constraints.values() if ' %s ' % (v.name,) in str(c))


def print_solution(variables):
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
                sender, receiver = path[index-1], path[index]
                cost += get_edge_latency(sender, receiver)
            print 'Flow: %s, cost: %dms' % (flow, cost)


def print_bandwidth_usage(variables):
    for node in nodes():
        downlink_capacity = int(case['nodes'][node]['downlink'].strip('Mbit'))
        uplink_capacity = int(case['nodes'][node]['uplink'].strip('Mbit'))
        proxy = node + 'proxy'
        downlink_used = sum(sum(edge.varValue for edge in
            variables[proxy][node][commodity]) for commodity in commodities())
        uplink_used = sum(sum(edge.varValue for edge in
            variables[node][proxy][commodity]) for commodity in commodities())
        downlink_percentage = float(downlink_used)/downlink_capacity
        uplink_percentage = float(uplink_used)/uplink_capacity
        print '%s downlink: %.1f, uplink: %.1f' % (node, downlink_percentage,
            uplink_percentage)

def solve_case(args, number_of_edges):
    variables = initialize_variables(number_of_edges)

    # TODO: Subtract repeater/re-encoder costs
    # TODO: Subtract CPU costs

    constraints = get_constraints(variables)

    if args.debug:
        for i in range(len(constraints)):
            constraints[i] += debug()

    prob_type = LpMinimize if args.debug else LpMaximize
    prob = LpProblem("interkontinental-asymmetric", prob_type)
    objective = get_objective(variables, number_of_edges) if not args.debug \
        else sum(_debug_vars)
    logger.info('Objective: %s %s', LpSenses[prob.sense], objective)
    prob += objective

    for constraint in constraints:
        prob += constraint


    res = GLPK(echo_proc=args.verbose).solve(prob)


    for commodity in commodities():
        print 'K%d: %s -> %s' % (commodity, commodity.sender,
            commodity.receiver)

    if res < 0:
        print 'Unsolvable!'
        sys.exit(1)
    else:
        if args.debug:
            print_problem_constraints(prob)

        dump_nonzero_variables(prob)
        print

        print_solution(variables)
        print_bandwidth_usage(variables)

        print "Score =", value(prob.objective)


if __name__ == '__main__':
    main()
