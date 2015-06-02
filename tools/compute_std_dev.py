#!/usr/bin/env python3

import csv
import statistics
import sys
from collections import defaultdict, namedtuple


def main(data_file, cutoff=0):
    results = defaultdict(list)
    with open(data_file) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if float(row['Interval start']) < cutoff:
                continue
            for column_name, value in row.items():
                if column_name == 'Interval start':
                    continue
                results[column_name].append(float(value)*8)
    properties = {}
    BitrateProperties = namedtuple('BitrateProperties', ['mean', 'stdev'])
    for row, values in results.items():
        stdev = statistics.pstdev(values)
        mean = statistics.mean(values)
        properties[row] = BitrateProperties(mean, stdev)

    for set_name, bitrate_properties in sorted(properties.items()):
        print('{:s}: mean={:.2f} Mbit, stdev={:.1f} kbit'.format(set_name,
            bitrate_properties.mean/10**6, bitrate_properties.stdev/10**3))


if __name__ == '__main__':
    main(sys.argv[1], 60)
