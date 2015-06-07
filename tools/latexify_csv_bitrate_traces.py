#!/usr/bin/env python3

import argparse
import csv
import statistics
import sys
import os
import socket
import yaml
from collections import defaultdict, namedtuple

def main(data_files, cutoff=0):
    role_map = load_role_map()
    ip_map = create_ip_to_role_map(role_map)
    results = read_data_sets(data_files, cutoff, ip_map)
    properties = summarize_results(results)
    latexify_properties(properties)


def load_role_map():
    rolemap = os.path.join(os.path.dirname(__file__), 'rolemap.yml')
    with open(rolemap) as fh:
        return yaml.load(fh)


def create_ip_to_role_map(role_map):
    ips = {}
    for role, hostname in role_map.items():
        ips[socket.gethostbyname(hostname)] = role
    return ips


def read_data_sets(data_files, cutoff, ip_map):
    results = defaultdict(lambda: defaultdict(list))
    for data_file in data_files:
        with open(data_file) as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                if float(row['Interval start']) < cutoff:
                    continue
                for column_name, value in row.items():
                    if column_name == 'Interval start':
                        continue
                    ip = column_name.split('==')[1]
                    role = ip_map[ip]
                    filename = os.path.basename(data_file)
                    sending_role = filename[0].upper()
                    results[sending_role][role].append(float(value)*8)
    return results


def summarize_results(results):
    properties = defaultdict(lambda: defaultdict(lambda: BitrateProperties(0, 0)))
    for sender in sorted(results):
        BitrateProperties = namedtuple('BitrateProperties', ['mean', 'stdev'])
        for receiver in sorted(results):
            values = results[sender][receiver]
            stdev = statistics.pstdev(values) if values else 0
            mean = statistics.mean(values) if values else 0
            if sender != receiver:
                print('Num measurements {} -> {}: {}'.format(sender, receiver, len(values)))
            properties[receiver][sender] = BitrateProperties(mean, stdev)
    return properties


def latexify_properties(properties):
    indent_unit = ' '*4
    indent_level = 3
    indent = indent_unit*indent_level
    for receiver in sorted(properties):
        print('{}%% Traffic received by {}'.format(indent, receiver))
        print('{0}\\addplot+[error bars/.cd,y dir=both, y explicit]\n{0}coordinates{{'.format(indent),
            end='')
        for sender in sorted(properties[receiver]):
            prop = properties[receiver][sender]
            print('\n{indent}({sender},{value:.0f}) +- (0.0, {stdev:.0f})'.format(**{'sender': sender,
                'value': prop.mean, 'stdev': prop.stdev, 'indent': indent_unit*(indent_level+1)}),
                end='')

        print('};\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='+')
    parser.add_argument('-c', '--cutoff', default=60, type=int,
        help='Limit the statistics to only from this time and outwards')
    args = parser.parse_args()
    main(args.files, args.cutoff)
