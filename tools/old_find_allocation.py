from pulp import *
from pdb import set_trace as trace
import sys
import argparse
from itertools import chain
import logging
import yaml

logger = logging.getLogger('hytop')
case = None
prob = None

class Commodity(int):
    def set_pair(self, sender, receiver):
        self.sender = sender
        self.receiver = receiver

device_gain = {
    'desktop': 4,
    'laptop': 3,
    'tablet': 2,
    'mobile': 1,
}

def load_cases(case_file):
    with open(case_file) as fh:
        return yaml.load(fh)

def parse_bandwidth_into_slots(bandwidth):
    slot_size = 600000
    bandwidth = bandwidth.strip('bit')
    unit = bandwidth[-1]
    multipliers = {
        'G': 10**9,
        'M': 10**6,
        'k': 10**3,
    }
    multiplier = multipliers[unit]
    return int(bandwidth[:-1])*multiplier/slot_size


def main():
    global case
    parser = argparse.ArgumentParser()
    default_case_file = os.path.join(os.path.dirname(__file__), 'cases.yml')
    cases = load_cases(default_case_file)
    parser.add_argument('-v', '--verbose', help='Logs all constraints added',
        action='store_true', default=False)
    parser.add_argument('-d', '--debug', help='Print debug information',
        action='store_true', default=False)
    parser.add_argument('-c', '--case', choices=cases.keys(), default='traveller')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, stream=sys.stdout)
    case = cases[args.case]
    solve_case(args)


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

def solve_case(args):
    global prob
    # Initialize variables
    variables = {}
    # Initialize all edge variables
    for node, other_node in edges():
        for commodity in commodities():
            # Assume nothing exceeds gigabit speeds, not even backbone links
            variables.setdefault(node, {}).setdefault(other_node, []).append(LpVariable('%sto%sK%d' % (node, other_node, commodity),
                lowBound=0, upBound=1000, cat=LpInteger))


    objective = 0
    for node, other_node in node_pairs():
        commodity = commodity_from_nodes(node, other_node)
        other_proxy = other_node + 'proxy'
        # Add bandwidth-gains to objective
        gain = device_gain[case['nodes'][other_node]['class']]
        objective += 10*gain*variables[other_proxy][other_node][commodity]
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
                edge_latency = 0
            objective -= edge_latency * variables[node][other_node][commodity]

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
        downlink_capacity = parse_bandwidth_into_slots(case['nodes'][node]['downlink'])
        constraint = sum(variables[node+'proxy'][node]) <= downlink_capacity
        logger.info('Constraint: %s', constraint)
        prob += constraint
        uplink_capacity = parse_bandwidth_into_slots(case['nodes'][node]['uplink'])
        constraint = sum(variables[node][node+'proxy']) <= uplink_capacity
        logger.info('Constraint: %s', constraint)
        prob += constraint

    # Don't exceed the bandwidth saturation point
    saturation_point = '2Mbit'
    slots = parse_bandwidth_into_slots(saturation_point)
    for commodity in commodities():
        proxy = commodity.receiver + 'proxy'
        constraint = variables[proxy][commodity.receiver][commodity] <= slots
        add_constraint(constraint, 'Prevent saturation')

    # All commodities must be sent by the correct parties
    # Note: Node should not need to send a commodity if a repeater does, and the
    # repeater receives another commodity from this node
    for commodity in commodities():
        proxy = commodity.sender + 'proxy'
        commodity_sources = variables[commodity.sender][proxy][commodity]
        for repeater in repeaters():
            for proxy in proxies():
                commodity_sources += variables[repeater][proxy][commodity]
        add_constraint(commodity_sources >= 1)
        add_constraint(variables[commodity.receiver + 'proxy'][commodity.receiver][commodity] >= 1)

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
                in_to_proxy += variables[other_node][proxy][commodity]
                out_of_proxy += variables[proxy][other_node][commodity]
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
                add_constraint(variables[node][proxy][commodity] == variables[proxy][node][commodity], 'Node')
            elif node == commodity.sender:
                add_constraint(variables[proxy][node][commodity] == 0, 'Node')

    # Repeaters repeat incoming commodities out to all proxies, converted to their desired commodity
    for repeater in repeaters():
        for node in nodes():
            proxy = node + 'proxy'
            left_side = 0
            right_side = []
            for commodity in commodities():
                if commodity.sender == node:
                    left_side += variables[proxy][repeater][commodity]
                    right_side.append(variables[repeater][commodity.receiver + 'proxy'][commodity])
            for outgoing in right_side:
                add_constraint(left_side == outgoing, 'Repeaterflow')

        # Never send traffic back to source (hopefully not needed)
        proxy_of_sending_node = commodity.sender + 'proxy'
        add_constraint(variables[repeater][proxy_of_sending_node][commodity] == 0, 'Repeater flow')

    if args.debug:
        for key in prob.constraints:
            prob.constraints[key] += debug()

    res = GLPK().solve(prob)


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
                    if path[-1] in variable and variable[path[-1]][commodity].varValue:
                        # search_node has a path to the last node we found
                        incoming_paths.append(search_node)
                # Check for cycle
                for incoming_path in incoming_paths:
                    # Do we send to that node as well as receive -> cycle.
                    if variables[path[-1]][incoming_path][commodity].varValue:
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
                            if path[-1] in variable and variable[path[-1]][c].varValue:
                                origin_commodity = c
                                break
                    if origin_commodity is None:
                        print path
                    assert origin_commodity is not None, "Didn't find mangled commodity"
                    while path[-1] != proxy:
                        for search_node, variable in variables.iteritems():
                            if path[-1] in variable and variable[path[-1]][origin_commodity].varValue:
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
                print ' -> '.join(variables[path[index-1]][path[index]][commodity].name for index, _ in enumerate(path[1:], 1)), ',',
                for index, edge in enumerate(path[1:], 1):
                    var = variables[path[index-1]][path[index]][commodity]
                    if 'proxy' in path[index] and 'proxy' in path[index-1]:
                        # It's an edge between two proxies, ie. it has a latency cost
                        # which can be found from the case
                        cost += int(case['nodes'][path[index-1][0]][path[index][0]].split()[0].strip('ms'))
                    elif 'rep' in path[index] and 'proxy' in path[index-1]:
                        cost += int(case['repeaters'][path[index]][path[index-1][0]].split()[0].strip('ms'))
                    elif 'proxy' in path[index] and 'rep' in path[index-1]:
                        cost += int(case['repeaters'][path[index-1]][path[index][0]].split()[0].strip('ms'))
                print 'Flow: %s, cost: %dms' % (var.varValue, cost)

        for node in nodes():
            downlink_total = parse_bandwidth_into_slots(case['nodes'][node]['downlink'])
            uplink_total = parse_bandwidth_into_slots(case['nodes'][node]['uplink'])
            proxy = node + 'proxy'
            downlink_usage = sum(v.varValue for v in variables[proxy][node])
            uplink_usage = sum(v.varValue for v in variables[node][proxy])
            print '%s downlink: %.1f, uplink: %.1f' % (node, float(downlink_usage)/downlink_total, float(uplink_usage)/uplink_total)

        print "Score =", value(prob.objective)


if __name__ == '__main__':
    main()
