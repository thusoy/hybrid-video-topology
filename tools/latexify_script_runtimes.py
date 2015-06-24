#!/usr/bin/env python3

import statistics
import sys

first = True
value_sets = []
for line in sys.stdin:
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
    mean = statistics.mean(value_set)
    stdev = statistics.pstdev(value_set, mean)
    header = headers[value_num]
    print('{}: {} +- {}'.format(header, mean, stdev))
