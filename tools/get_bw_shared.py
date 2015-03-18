#/usr/bin/env python

import sys

def main():
    raw_hosts = sys.argv[1:]

    hosts = [tuple(map(int, host.split(':'))) for host in raw_hosts]


    # Allocate an in and an out node for each host, plus two rows for the supersink and the supersource
    matrix = []

    for node, (down, up) in enumerate(hosts):
        node_bws = []
        for other_node, (other_down, other_up) in enumerate(hosts):
            if node == other_node:
                node_bws.append(0)
                continue
            send_cap = up/(len(hosts)-1)
            recv_cap = other_down/(len(hosts)-1)
            bw = min(send_cap, recv_cap)
            node_bws.append(bw)
        matrix.append(node_bws)

    print('Capacities:')
    print_matrix(matrix)


def print_matrix(m):
    print
    print ' '*2  +  ' '.join(str(n).center(3) for n in range(1, len(m) + 1))
    even = True
    for node_num, line in enumerate(m):
        print
        node = node_num
        node_text = '%d ' % node
        print node_text + ' '.join(str(s).center(3) for s in line)


if __name__ == '__main__':
    main()
