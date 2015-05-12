import argparse

def main(slots=None):
    if slots is None:
        for slot in range(1, 31):
            get_edges(slot)
    else:
        get_edges(slots)

def get_edges(slots):
    cutoffs = (0.933, 0.8, 0.533)
    print '%d slots:' % slots,
    edges = [(0, 0.0, 0.0)] # (slots, treshold, cost) tuples
    utilization = 0.0
    utilization_step = 1.0/slots
    slots_in_edge = 0
    for slot in range(1, slots + 1):
        utilization += utilization_step
        slots_in_edge += 1
        edges[-1] = (slots_in_edge, utilization, cost(utilization))
        for cutoff_number, cutoff in enumerate(cutoffs):
            if utilization + utilization_step > cutoff:
                if len(edges) < len(cutoffs) + 1 - cutoff_number:
                    edges.append((0, 0.0, 0.0))
                    slots_in_edge = 0
                    break
    print ', '.join('(s=%d, u=%.3f, c=%.3f)' % (s, u, c) for s, u, c in edges if (s, u, c) != (0, 0, 0))
    # print ', '.join(str(k[0]) for k in edges if k != (0, 0, 0))

def cost(utilization):
    return 1.0/(1-0.9*utilization)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--slots', type=int)
    args = parser.parse_args()
    main(args.slots)
