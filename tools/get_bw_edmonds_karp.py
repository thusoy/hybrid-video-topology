#/usr/bin/env python

# We define a topology as a matrix with (latency, upload bandwidth) between hosts in the conversation,
# and each host also has a upper limit on upload and download.
# First line is
# <EOF 20/5 13/2 0.5/0.5
# - 5/4,5 75/0.5
# 4/1.7 - 80/0.4
# 77/.5 85/.05 -
# EOF

one_mobile = """20/5 13/2 0.5/0.5
- 5/4.5 75/0.5
4/1.7 - 80/0.4
77/.5 85/.5 -""".split('\n')

scenario = one_mobile

import sys
from collections import namedtuple

Node = namedtuple('Node', ['down', 'up'])
#Link = namedtuple('Link', ['latency', 'bandwidth'])
class Link(object):
    slot_size = 250

    def __init__(self, latency, bandwidth):
        self.latency = latency
        self.bandwidth = bandwidth
        self.slots = (bandwidth*(2**10)) // Link.slot_size
      #  print 'Link with bw=%.2f initialized with %d slots' % (self.bandwidth, self.slots)
        self.utilized_slots = 0


    def cost(self):
        if self.slots:
            return self.latency**(float(self.utilized_slots)/self.slots + 1)
        else:
            return float('Inf')


    def __repr__(self):
        return 'Link(lat=%d, slots=%d)' % (self.latency, self.slots)


def main():
    nodes = parse_nodes(scenario[0])
    graph = parse_graph(scenario[1:])
    #print_matrix(graph)
    costs, predecessors = floyd_warshall(graph)
    print_paths(predecessors, costs)
    print
    print_link_utilization(graph)

def print_paths(predecessors, costs):
    for source, targets in predecessors.items():
        for target, predecessor in enumerate(targets):
            if source == target:
                continue
            path = [source]
            current_node = source
            while current_node != predecessor:
                current_node = predecessors[predecessor][target]
                path.append(current_node)
            path.append(target)
            print 'Path from %d to %d (%3dms): %s' % (source, target, costs[source][target], ' -> '.join(str(n) for n in path))


def print_link_utilization(graph):
    for node, links in enumerate(graph):
        for link in links:
            if link:
                print '%.2f' % (float(link.utilized_slots) / link.slots),
            else:
                print '----',
        print


def parse_nodes(node_line):
    nodes = []
    raw_nodes = node_line.split()
    for raw_node in raw_nodes:
     #   print('Parsing node %s' % raw_node)
        down, up = raw_node.split('/')
        nodes.append(Node(up, down))
    return nodes


def floyd_warshall(graph):
    costs = {}
    predecessor = {}
    # Initialize costs and predecessors
    for i in range(len(graph)):
        costs[i] = [float('Inf') for j in range(len(graph))]
        predecessor[i] = [-1 for j in range(len(graph))]
        costs[i][i] = 0
        for neighbor in range(len(graph)):
            if i == neighbor:
                continue
            link = graph[i][neighbor]
            costs[i][neighbor] = link.cost()
            predecessor[i][neighbor] = i


    # Run the algorithm
    found_new_path = True
    while found_new_path:
        found_new_path = False
        for third_party in range(len(graph)):
            for sender in range(len(graph)):
                for receiver in range(len(graph)):
                    new_cost = costs[sender][third_party] + costs[third_party][receiver]
                    if new_cost < costs[sender][receiver]:
                        found_new_path = True
                        first_link = graph[sender][third_party]
                        first_link.utilized_slots += 1
                        second_link = graph[third_party][receiver]
                        second_link.utilized_slots += 1
                        costs[sender][receiver] = new_cost

                        # This will probably not work, as the assumption here is that the shortest
                        # route seen so far between the third_party and the receiver will always
                        # be the cheapest route, but as our routes change cost the more nodes use
                        # it, this assumption won't hold
                        predecessor[sender][receiver] = predecessor[third_party][receiver]

    return costs, predecessor


def parse_graph(graph_lines):
    num_nodes = len(graph_lines)
    graph = []
    for node_num, line in enumerate(graph_lines):
        node_links = line.split()
        graph.append([])
        for other_node_num, node_link in enumerate(node_links):
            if node_num == other_node_num:
                graph[-1].append(None)
                continue
            latency, bandwidth = node_link.split('/')
            graph[-1].append(Link(int(latency), float(bandwidth)))
    return graph


# Arguments are the hosts bandwidth
def max_flow(C, source, sink):
    F = edmonds_karp(C, source, sink)
    return sum(F[source][i] for i in xrange(len(C)))


def print_matrix(m):
    print
#    print ' '*4  +  ' '.join('%sin %sou' % (n, n) for n in range(1, int(len(m)/2))) + '  s   t '
    print m
    cell_width = 9
    for node_num, line in enumerate(m):
        print
        print ' '.join(('%d/%.1f' % (l.latency, l.bandwidth)).center(cell_width) if l else '-'.center(cell_width) for l in line)


if __name__ == '__main__':
    main()
