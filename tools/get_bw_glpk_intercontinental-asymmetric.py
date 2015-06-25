"""
    Find optimal video routing for a given case.

    :copyright: (c) 2015 by Tarjei Husøy
    :license: MIT, see http://opensource.org/licenses/MIT
"""

from collections import defaultdict, namedtuple
from itertools import chain, product
from pdb import set_trace as trace
from pulp import (LpMinimize, LpMaximize, LpProblem, LpVariable, LpInteger,
    LpSenses, GLPK, value)
import argparse
import io
import logging
import os
import sys
import time
import yaml

logger = logging.getLogger('hytop')
case = None
constraints = []

device_gain = {
    'desktop': 4,
    'laptop': 3,
    'tablet': 2,
    'mobile': 1,
}

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
    parser.add_argument('-s', '--slot-size', default='512kbps',
        help='Set slot size to this size')
    parser.add_argument('-e', '--edges', default=4, type=int,
        help='How many parallell edges to add between each pair of nodes')
    parser.add_argument('-c', '--case', choices=cases.keys(),
        default='traveller')
    args = parser.parse_args()
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, stream=sys.stdout)
    case = cases[args.case]
    solve_case(args, number_of_edges=args.edges)


def all_edges(include_self=False):
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
    utilized_slots = sum(edge.slots for edge in edges)
    edges.append(Edge(number_of_slots - utilized_slots, 1, cost(1)))
    edges = [edge for edge in edges if edge.slots]
    return edges

def cost(utilization, punishment_factor=0.9):
     # The closer the punishment_factor is to 1, the heavier the punishment
     # for saturating links (balance against cost factor of delay)
    return 1/(1-punishment_factor*utilization)

def get_cutoffs(partitions=4):
    """ Find the cut-off points for partitioning something where each part is
    twice as large as the previous.

    >>> get_cutoffs(2)
    [0.66]
    """
    number_of_segments = sum(2**i for i in range(partitions))
    segment_size = 1.0/number_of_segments

    # Create an array like [0.066667, 0.1333, 0.26667, 0.53] for partitions=4
    segs = [segment_size*2**i for i in range(partitions)]

    # Reverse the array and make each element a cumulative sum
    cutoffs = [sum(segs[-1:-1-i:-1]) for i in range(1, partitions)]
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
    _debug_vars.append(LpVariable('__debug__x%d' % _debug_index, lowBound=0))
    _debug_vars.append(LpVariable('__debug__y%d' % _debug_index, lowBound=0))
    return _debug_vars[-1] - _debug_vars[-2]

def dump_nonzero_variables(prob):
    print '\n'.join('%s = %s' % (v.name, v.varValue) for v in prob.variables()
        if v.varValue)


def get_edge_latency(node, other_node):
    """ Get latency of edge between node and other_node. If that is not
    specified in the case spec, latency from other_node to node will be
    returned if present.
    """
    if node.startswith('rep'):
        edge_latency = case['repeaters'][node][other_node[0]].split()[0]
    elif other_node.startswith('rep'):
        edge_latency = case['repeaters'][other_node][node[0]].split()[0]
    elif 'proxy' in node and 'proxy' in other_node:
        try:
            edge_latency = case['nodes'][node[0]][other_node[0]].split()[0]
        except:
            # A -> B not defined, lookup B -> A
            edge_latency = case['nodes'][other_node[0]][node[0]].split()[0]
    else:
        # TODO: Add edge cost for parallell edges between proxies and their nodes
        edge_latency = '0ms'
    return int(edge_latency.strip('ms'))


def get_objective(variables, number_of_edges):
    objective = 0
    for node, other_node in node_pairs():
        commodity = commodity_from_nodes(node, other_node)
        other_proxy = other_node + 'proxy'
        edges = get_edges(number_of_edges)
        for edge_number, edge in enumerate(edges):
            # Add bandwidth-gains to objective
            device_class = case['nodes'][other_node]['class']
            gain = device_gain[device_class]
            edge_var = variables[other_proxy][other_node][commodity][edge_number]
            gainconst = 10
            objective += gainconst * gain * edge_var
            # objective -= edge.cost * edge_var
            # TODO: Subtract incoming flow to the source node from objective?


    for commodity, (node, other_node) in product(commodities(), all_edges()):
        # Subtract edge cost from objective
        edge_latency = get_edge_latency(node, other_node)
        for edge in variables[node][other_node][commodity]:
            objective -= edge_latency*edge

    return objective


def initialize_variables(number_of_edges):
    variables = defaultdict(lambda: defaultdict(list))
    # Initialize all edge variables
    for (node, other_node), commodity in product(all_edges(), commodities()):
        bandwidth_limited = ('proxy' in node and node[0] == other_node) or (
            'proxy' in other_node and other_node[0] == node)
        parallell_edges = number_of_edges if bandwidth_limited else 1
        for edge in range(parallell_edges):
            # Assume nothing exceeds gigabit speeds, not even backbone links
            if edge == 0:
                variables[node][other_node].append([])
            variables[node][other_node][-1].append(LpVariable('%sto%sK%dC%d' %
                (node, other_node, commodity, edge), lowBound=0, upBound=1000,
                cat=LpInteger))
    return variables

def parse_bandwidth_into_slots(bandwidth):
    slot_size = 400000
    bandwidth = bandwidth.strip('bit')
    unit = bandwidth[-1]
    multipliers = {
        'G': 10**9,
        'M': 10**6,
        'k': 10**3,
    }
    multiplier = multipliers[unit]
    return int(bandwidth[:-1])*multiplier/slot_size


def add_bandwidth_conservation(variables):
    # Stay below bandwidth (capacities)
    for node in nodes():
        downlink_raw = case['nodes'][node]['downlink']
        downlink_capacity = parse_bandwidth_into_slots(downlink_raw)
        add_constraint(sum(sum(variables[node+'proxy'][node][commodity]) for
            commodity in commodities()) <= downlink_capacity)
        uplink_raw = case['nodes'][node]['uplink']
        uplink_capacity = parse_bandwidth_into_slots(uplink_raw)
        add_constraint(sum(sum(variables[node][node+'proxy'][commodity]) for
            commodity in commodities()) <= uplink_capacity)


def add_all_commodities_must_be_sent_and_received_constraint(variables):
    # All commodities must be sent by the correct parties
    # Note: Node should not need to send a commodity if a repeater does, and
    # the repeater receives another commodity from this node
    for commodity in commodities():
        proxy = commodity.sender + 'proxy'
        commodity_sources = sum(variables[commodity.sender][proxy][commodity])
        for repeater, proxy in product(repeaters(), proxies()):
            commodity_sources += sum(variables[repeater][proxy][commodity])
        add_constraint(commodity_sources >= 1)
        node_ext = commodity.receiver + 'proxy'
        node = commodity.receiver
        all_incoming_edges = variables[node_ext][node][commodity]
        add_constraint(sum(all_incoming_edges) >= 1)


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
        # Add flow conservation for nodes, make sure they can only be origin
        # for their own commodity, and does not terminate their own
        # commodities
        # TODO: Does not allow nodes to re-encode data for now
        proxy = node + 'proxy'
        if node == commodity.sender:
            received = sum(variables[proxy][node][commodity])
            add_constraint(received == 0, 'Node')
        elif node != commodity.receiver:
            sent = sum(variables[node][proxy][commodity])
            received = sum(variables[proxy][node][commodity])
            add_constraint(sent == received, 'Node')

def add_repeater_flow_conservation(variables):
    # Repeaters repeat incoming commodities out to all proxies, mangled to
    # their desired commodity
    for repeater, node in product(repeaters(), nodes()):
        proxy = node + 'proxy'
        left_side = 0
        right_side = []
        for commodity in commodities():
            if commodity.sender == node:
                left_side += variables[proxy][repeater][commodity][0]
                node_ext = commodity.receiver + 'proxy'
                right_side.append(variables[repeater][node_ext][commodity][0])

                # Never send traffic back to source (hopefully not needed)
                sender_ext = commodity.sender + 'proxy'
                edge_var = variables[repeater][sender_ext][commodity][0]
                add_constraint(edge_var == 0, 'Repeater flow')

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
        if v.varValue and v.name.startswith('__debug__'):
            for c in prob.constraints.values():
                if ' %s ' % (v.name,) in str(c):
                    print '\t%s' % c

def find_path_between_nodes(variables, node, other_node):
    commodity = commodity_from_nodes(node, other_node)
    destination = node + 'proxy'
    path = [other_node + 'proxy']
    while path[-1] != destination:
        # print path
        path_hops, commodity = find_next_path_hops_and_commodity(variables,
            path[-1], destination, commodity)
        path.extend(path_hops)
    else:
        # Found path between nodes
        path = list(reversed(path))
        return path

def find_next_path_hops_and_commodity(variables, origin, destination,
    commodity):
    incoming_paths = find_nodes_who_sends_commodity(variables, origin,
        commodity)
    if len(incoming_paths) == 2:
        # There's a cycle (we go through another node), add the cycle and
        # the actual exit to the path
        return get_exit_path_from_proxy(variables, origin,
            incoming_paths, commodity), commodity
    elif len(incoming_paths) == 1:
        return incoming_paths, commodity

    else:
        if not origin.startswith('rep'):
            raise ValueError('Commodity K%d not found in to %s' % (commodity,
                destination))
        # Trace a repeater changing commodity type
        commodity = find_mangled_commodity(variables, destination,
            commodity.sender)
        return find_path(variables, origin, destination, commodity), commodity

def get_exit_path_from_proxy(variables, origin, incoming_paths, commodity):
    path = []
    # Check for cycle
    for incoming_path in incoming_paths:
        if incoming_path == origin:
            continue
        # Do we send to that node as well as receive -> cycle.
        if any(edge.varValue for edge in
            variables[origin][incoming_path][commodity]):
                path.append(incoming_path)
                path.append(origin)
                break

    # Add non-cycle path
    for incoming_path in incoming_paths:
        if incoming_path not in path:
            # The other non-cycle path
            path.append(incoming_path)
            break
    return path


def find_mangled_commodity(variables, repeater, sender):
    all_node_commodities = [c for c in commodities() if c.sender == sender]
    for c in all_node_commodities:
        for sending_node, variable in variables.iteritems():
            if repeater in variable and any(edge.varValue for edge in \
                                            variable[repeater][c]):
                return c
    raise ValueError('Mangled commodity not found.')


def find_path(variables, origin, destination, commodity):
    path = []
    last_node_found = origin
    while last_node_found != destination:
        sending_nodes = find_nodes_who_sends_commodity(variables,
            last_node_found, commodity)
        if sending_nodes:
            last_node_found = sending_nodes[0]
        else:
            raise ValueError('No path found after repeater change, '
                'path: %s, origin: %s, dest: %s, c: %s' % (path, origin,
                destination, commodity))
        path.append(last_node_found)
    return path

def find_nodes_who_sends_commodity(variables, destination, commodity):
    sending_nodes = []
    for search_node, variable in variables.iteritems():
        if destination in variable:
            edges = variable[destination][commodity]
            any_traffic = any(edge.varValue for edge in edges)
            if any_traffic:
                sending_nodes.append(search_node)
    return sending_nodes


def get_path_cost(variables, path, commodity):
    cost = 0
    for index, edge in enumerate(path[1:], 1):
        sender, receiver = path[index-1], path[index]
        cost += get_edge_latency(sender, receiver)
    return cost

def print_solution(variables):
    # Print the solution
    for node, other_node in node_pairs():
        commodity = commodity_from_nodes(node, other_node)
        path = find_path_between_nodes(variables, node, other_node)
        cost = get_path_cost(variables, path, commodity)
        flow = sum(edge.varValue for edge in
            variables[path[-2]][path[-1]][commodity])
        path_as_str = ' -> '.join(path)
        print '%s til %s (K%d): %s, flow: %d, cost: %dms' % (node, other_node,
            commodity, path_as_str, flow, cost)

def print_bandwidth_usage(variables):
    for node in nodes():
        downlink_raw = case['nodes'][node]['downlink']
        downlink_capacity = parse_bandwidth_into_slots(downlink_raw)
        uplink_raw = case['nodes'][node]['uplink']
        uplink_capacity = parse_bandwidth_into_slots(uplink_raw)
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
    global_start_time = time.time()
    variables = initialize_variables(number_of_edges)

    # TODO: Subtract repeater/re-encoder costs

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

    starttime = time.time()
    pipe = io.StringIO()
    res = GLPK(pipe=pipe).solve(prob)
    endtime = time.time()

    output = pipe.getvalue()
    memstart = output.find('Memory used')


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
        print 'Found solution in %.3fs' % (endtime - starttime)
        with open('results.csv', 'a') as fh:
            memory_segment = ''.join(output[memstart:memstart+20])
            memory_used = float(memory_segment.split()[2])*10**6
            solve_time = endtime - starttime
            build_time = starttime - global_start_time
            retrace_time = time.time() - endtime
            fh.write('%.3f,%.3f,%.3f,%d' % (solve_time, build_time, retrace_time, memory_used) + '\n')


import unittest
class VideoSolverTestCase(unittest.TestCase):

    def test_get_exit_path_from_node_with_cycle(self):
        graph = {
            'Aext': {
                'Bext': [1]
            },
            'Bext': {
                'B': [1],
                'Cext': [1]
            },
            'B': {
                'Bext': [1],
            },
            'Cext': {}
        }
        expected_path = ['Cext', 'Bext', 'B', 'Bext', 'Aext']
        commodity = 0
        path = get_exit_path_from_proxy(graph, 'Bext', ['Aext', 'B'], commodity)
        self.assertEqual(path, expected_path)


    def test_bandwidth_parsing(self):
        test_values = {
            '10Mbit': 10000000,
            '3kbit': 3000,
            '14Gbit': 14000000000,
        }
        for bw, expected in test_values.items():
            self.assertEqual(parse_bandwidth_into_slots(bw), expected)


if __name__ == '__main__':
    main()
