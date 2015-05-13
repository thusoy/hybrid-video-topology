import argparse

def main(slots=None, number_of_edges=4):
    if slots is None:
        for slot in range(1, 31):
            get_edges(slot, number_of_edges)
    else:
        get_edges(slots, number_of_edges)


def get_edges(number_of_slots, number_of_edges=4):
    cutoffs = get_cutoffs(number_of_edges)
    print '%d slots:' % number_of_slots,
    edges = [] # (slots, treshold, cost) tuples
    utilization = 0.0
    utilization_step = 1.0/number_of_slots
    for cutoff in cutoffs:
        slots = int(number_of_slots*(cutoff - utilization))
        utilization += utilization_step*slots
        edges.append((slots, utilization, cost(utilization)))
    edges.append((number_of_slots-sum(edge[0] for edge in edges), 1, cost(1)))
    edges = [edge for edge in edges if edge[0]]
    print ', '.join('(s=%d, u=%.3f, c=%.3f)' % (s, u, c) for s, u, c in edges)
    # print ', '.join(str(k[0]) for k in edges if k != (0, 0, 0))


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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--slots', type=int)
    parser.add_argument('-e', '--edges', type=int, default=4)
    args = parser.parse_args()
    main(slots=args.slots, number_of_edges=args.edges)
