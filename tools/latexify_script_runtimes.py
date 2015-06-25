#!/usr/bin/env python3

import statistics
import sys
import os
import collections

mem_only = len(sys.argv) == 2 and sys.argv[1] == 'mem'

case_results = collections.defaultdict(list)
for case in os.listdir(os.path.join('data', 'script-runtimes')):
    if not case[-4:] == '.csv':
        continue
    case_file = os.path.join('data', 'script-runtimes', case)
    first = True
    value_sets = []
    with open(case_file) as fh:
        for line in fh:
            if first:
                headers = line.strip().split(',')
                first = False
                for header in headers:
                    value_sets.append([])
                continue
            values = line.split(',')
            for value_num, value in enumerate(values):
                value_sets[value_num].append(float(value))


    for value_num, value_set in enumerate(value_sets):
        header = headers[value_num]
        mean = statistics.mean(value_set)
        stdev = statistics.pstdev(value_set, mean)
        case_name = case[:-4]
        case_results[header].append((case_name, mean))

if mem_only:
    values =  case_results['Memory usage']
    print('\\addplot coordinates{{{}}};'.format(' '.join('({},{})'.format(case, int(mean)/10**6) for case, mean in sorted(values))))
    # print('\\addlegendentry{{{}}}'.format(header))

else:
    for header, values in case_results.items():
        if header != 'Memory usage' and header != 'Retrace time':
            print('\\addplot coordinates{{{}}};'.format(' '.join('({},{})'.format(case, mean) for case, mean in sorted(values))))
            print('\\addlegendentry{{{}}}'.format(header))
