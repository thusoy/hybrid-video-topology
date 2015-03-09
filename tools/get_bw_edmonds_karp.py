#/usr/bin/env python

# We define a topology as a matrix with (latency, upload bandwidth) between hosts in the conversation,
# and each host also has a upper limit on upload and download.
# First line is
# <EOF 20/5 13/2 0.5/0.5
# - 5/4,5 75/0.5
# 4/1.7 - 80/0.4
# 77/.5 85/.05 -
# EOF

import sys

def main():
    raw_hosts = sys.argv[1:]

    hosts = [tuple(map(int, host.split(':'))) for host in raw_hosts]
    # Allocate an in and an out node for each host, plus two rows for the supersink and the supersource
    matrix = [None]*(len(hosts)*2+2)

    print hosts
#    print_matrix(matrix)

    supersource = len(matrix) - 2
    supersink = len(matrix) - 1
    matrix[supersource] = [0]*len(matrix)

    for node_num, (down, up) in enumerate(hosts):
        n_in = node_num*2
        n_out = node_num*2 + 1
        matrix[n_in] = [0]*(len(matrix) - 1) + [up]
        out_cap = [up, 0]*(len(matrix)/2)
        out_cap[-2:] = [0]*2
        out_cap[n_in] = 0
        out_cap[n_out] = 0
        matrix[n_out] = out_cap
        matrix[supersource][n_out] = down
    matrix[supersink] = [0] * len(matrix)

    print('Capacities:')
    print_matrix(matrix)

    print('Flow:')
    print_matrix(edmonds_karp(matrix, supersource, supersink))
    print 'Flow:', max_flow(matrix, supersource, supersink)


# Arguments are the hosts bandwidth
def max_flow(C, source, sink):
    F = edmonds_karp(C, source, sink)
    return sum(F[source][i] for i in xrange(len(C)))


def edmonds_karp(C, source, sink):
    n = len(C) # C is the capacity matrix
    F = [[0] * n for i in xrange(n)]
    # residual capacity from u to v is C[u][v] - F[u][v]

    while True:
        path = bfs(C, F, source, sink)
        if not path:
            break
        # traverse path to find smallest capacity
        flow = min(C[u][v] - F[u][v] for u,v in path)
        # traverse path to update flow
        for u,v in path:
            F[u][v] += flow
            F[v][u] -= flow
    return F


def bfs(C, F, source, sink):
    queue = [source]
    paths = {source: []}
    while queue:
        u = queue.pop(0)
        for v in xrange(len(C)):
            if C[u][v] - F[u][v] > 0 and v not in paths:
                paths[v] = paths[u] + [(u,v)]
                if v == sink:
                    return paths[v]
                queue.append(v)
    return None


def print_matrix(m):
    print
    print ' '*4  +  ' '.join('%sin %sou' % (n, n) for n in range(1, int(len(m)/2))) + '  s   t '
    even = True
    for node_num, line in enumerate(m):
        print
        node = node_num/2 + 1
        node_text = '%d%s ' % (node, 'in' if even else 'ou')
        if node_num == len(m) - 2:
            node_text = ' s  '
        elif node_num == len(m) -1:
            node_text = ' t  '

        print node_text + ' '.join(str(s).center(3) for s in line)
        even = not even


if __name__ == '__main__':
    main()
