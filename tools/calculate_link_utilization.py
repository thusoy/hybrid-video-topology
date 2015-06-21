#!/usr/bin/env python

"""
    Using cases.yml (with the limits), uses a file like

        \addplot+[error bars/.cd,y dir=both, y explicit]
        coordinates{
            (A,0) +- (0.0, 0)
            (B,448388.10704107524) +- (0.0, 14768.58419020849)
            (C,1919158.2973459633) +- (0.0, 57964.53320482376)};

        \addplot+[error bars/.cd,y dir=both, y explicit]
        coordinates{
            (A,573908.3598606641) +- (0.0, 27672.874503205858)
            (B,0) +- (0.0, 0)
            (C,87273.74871534701) +- (0.0, 37120.53082400897)};

        \addplot+[error bars/.cd,y dir=both, y explicit]
        coordinates{
            (A,2038854.5694618924) +- (0.0, 34228.91094452904)
            (B,421286.00651905156) +- (0.0, 10677.063917160945)
            (C,0) +- (0.0, 0)};

        \legend{A, B, C}

    to extract the mean utilization of up and down for the nodes in the case.

"""

import argparse
import os
import collections
import sys
import yaml

def main(tex_file, case):
    bandwidth_limits = load_bandwidth_limits(case)
    bandwidth_usage = load_bandwidth_usage(tex_file)
    utilization = get_utilization(bandwidth_limits, bandwidth_usage)
    print_utilization(utilization)


def load_bandwidth_limits(case_name):
    cases_filename = os.path.join(os.path.dirname(__file__), 'cases.yml')
    with open(cases_filename) as fh:
        case_specs = yaml.load(fh)
    case_spec = case_specs[case_name]

    case = {}
    for node_name, node_spec in case_spec['nodes'].items():
        down, up = node_spec['downlink'], node_spec['uplink']
        case[node_name] = (int(down.strip('Mbit'))*10**6, int(up.strip('Mbit'))*10**6)
    return case


def load_bandwidth_usage(tex_file):
    nodes = 'ABCDEFG'
    receiving_usage = collections.defaultdict(int)
    sending_usage = collections.defaultdict(int)
    sending_node_index = -1
    with open(tex_file) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith('\\addplot'):
                sending_node_index += 1
                continue
            if line.startswith('coordinates') or line.startswith('%'):
                continue
            if line.startswith('\\legend'):
                break
            receiving_node = line[line.find('(') + 1]
            if not receiving_node in nodes:
                raise ValueError('Sending node not in nodes, was "{}"'.format(receiving_node))
            mean_bandwidth = float(line[line.find(',') + 1:line.find(')')])
            sending_usage[nodes[sending_node_index]] += mean_bandwidth
            receiving_usage[receiving_node] += mean_bandwidth

    usage = {}
    for node, downlink_usage in receiving_usage.items():
        uplink_usage = sending_usage[node]
        usage[node] = (downlink_usage, uplink_usage)
    return usage


def get_utilization(limits, usage):
    utilization = {}
    for node, (down_limit, up_limit) in limits.items():
        down_usage, up_usage = usage[node]
        utilization[node] = (min(down_usage/down_limit, 1), min(up_usage/up_limit, 1))
    return utilization


def print_utilization(utilization):
    for node, (down_util, up_util) in sorted(utilization.items()):
        print '%s & %.0f & %.0f \\\\' % (node, down_util*100, up_util*100)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('tex_file')
    parser.add_argument('-c', '--case', default='traveller')
    args = parser.parse_args()
    main(args.tex_file, args.case)
