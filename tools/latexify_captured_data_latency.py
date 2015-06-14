#!/usr/bin/env python3

import argparse
import collections
import json
import os
import socket
import statistics
import sys
import yaml


def main(input_file, field, limit, start_time):
    role_map = load_role_map()
    ip_map = create_ip_to_role_map(role_map)
    readings = get_readings(input_file, ip_map, field, start_time)
    stats = get_statistics_from_reading(readings, limit)
    print_latexified_stats(stats)

def get_readings(input_file, ip_map, field, start_time):
    readings = collections.defaultdict(lambda: collections.defaultdict(list))
    with open(input_file) as fh:
        for line in fh:
            reading = json.loads(line.strip())
            read_time = int(reading['data']['timestamp'])/1000
            if start_time and read_time < start_time:
                continue
            measuring_role = ip_map[reading['receiver']]
            sending_role = ip_map[reading['sender']]
            actual_measurer = reading['actual_sender'].split(':')[-1] # Extract Ipv4 from ipv6
            if actual_measurer != reading['receiver']:
                print('Was TURNed through AWS!', file=sys.stderr)
            delay_components = (
                int(reading['data']['video']['currentDelayMs']),
                max(
                    int(reading['data']['video']['minPlayoutDelayMs']),
                    (
                        int(reading['data']['video']['decodeMs']) +
                        int(reading['data']['video']['renderDelayMs']) +
                        int(reading['data']['video']['jitterBufferMs'])
                    )
                )
            )
            total_delay = sum(delay_components)

            readings[sending_role][measuring_role].append(total_delay)
    return readings

def get_statistics_from_reading(readings, limit):
    stats = collections.defaultdict(dict)
    for sender, receivers in readings.items():
        for receiver, values in receivers.items():
            values = values[-limit:]
            print('{} -> {} computed over {} values'.format(
                sender, receiver, len(values)), file=sys.stderr)
            mean = statistics.mean(values)
            stdev = statistics.stdev(values, xbar=mean)
            stats[sender][receiver] = (mean, stdev)
    return stats


def print_latexified_stats(stats):
    indent_unit = ' '*4
    for receiver in sorted(stats):
        print('\\addplot+[error bars/.cd,y dir=both, y explicit]\ncoordinates{', end='')
        for sender in sorted(stats):
            mean, stdev = stats[sender].get(receiver, (0, 0))
            print('\n{}({},{}) +- (0.0, {})'.format(
                indent_unit, sender, mean, stdev), end='')
        print('};\n')
    print('\\legend{{{}}}'.format(', '.join(sorted(stats))))


def load_role_map():
    rolemap = os.path.join(os.path.dirname(__file__), 'rolemap.yml')
    with open(rolemap) as fh:
        return yaml.load(fh)


def create_ip_to_role_map(role_map):
    ips = {}
    for role, hostname in role_map.items():
        ips[socket.gethostbyname(hostname)] = role
    return ips

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file')
    parser.add_argument('-f', '--field', default='currentDelayMs')
    parser.add_argument('-s', '--start-time', type=int)
    parser.add_argument('-n', '--limit', default=120, type=int)
    args = parser.parse_args()
    main(args.input_file, args.field, args.limit, args.start_time)
