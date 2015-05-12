import argparse

def main(slots=None, number_of_edges=4):
    if slots is None:
        for slot in range(1, 31):
            get_edges(slot, number_of_edges)
    else:
        get_edges(slots, number_of_edges)

def get_edges(slots, number_of_edges=4):
    cutoffs = get_cutoffs(number_of_edges)
    print '%d slots:' % slots,
    edges = [] # (slots, treshold, cost) tuples
    utilization = 0.0
    utilization_step = 1.0/slots
    slots_in_edge = 0
    # TODO: Instead of iterating up, simply find the number of slots in each edge by size_of_segment/step_size
    for slot in range(slots):
        utilization += utilization_step
        slots_in_edge += 1
        for cutoff_number, cutoff in enumerate(cutoffs):
            if utilization + utilization_step > cutoff:
                if len(edges) + 1 < number_of_edges - cutoff_number:
                    edges.append((slots_in_edge, utilization, cost(utilization)))
                    slots_in_edge = 0
                    break
    if edges[-1][1] < 1:
        edges.append((slots_in_edge, utilization, cost(utilization)))
    print ', '.join('(s=%d, u=%.3f, c=%.3f)' % (s, u, c) for s, u, c in edges)
    # print ', '.join(str(k[0]) for k in edges if k != (0, 0, 0))

def cost(utilization):
    return 1.0/(1-0.9*utilization)


def get_cutoffs(partitions=4):
    segments = sum(2**i for i in range(partitions)) # Exponentially smaller
    segment_size = 1.0/segments
    segs = [segment_size*2**i for i in range(partitions)]
    cutoffs = [sum(segs[-1:-1-i:-1]) for i in range(1, partitions)]
    return list(reversed(cutoffs))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--slots', type=int)
    parser.add_argument('-e', '--edges', type=int, default=4)
    args = parser.parse_args()
    main(slots=args.slots, number_of_edges=args.edges)
