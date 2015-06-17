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


def parse_old_format_data(reading, ip_map):
    measuring_role = ip_map[reading['receiver']]
    sending_role = ip_map[reading['sender']]
    actual_measurer = reading['actual_sender'].split(':')[-1] # Extract Ipv4 from ipv6
    if actual_measurer != reading['receiver']:
        print('Was TURNed through AWS!', file=sys.stderr)
    bytes_received = int(reading['data']['video']['bytesReceived'])
    return sending_role, measuring_role, bytes_received


def parse_new_format_line(reading, ip_map):
    measuring_address = reading['connection']['local']['ipAddress']
    measuring_ip = measuring_address.split(':')[0] # Strip port
    measuring_role = ip_map[measuring_ip]
    sending_address = reading['connection']['remote']['ipAddress']
    sending_ip = sending_address.split(':')[0]
    sending_role = ip_map[sending_ip]
    actual_measurer = reading['actual_sender'].split(':')[-1] # Extract Ipv4 from ipv6
    if actual_measurer != measuring_ip:
        print('Was TURNed through AWS!', file=sys.stderr)
    bytes_received = int(reading['video']['incoming']['bytesReceived'])
    return sending_role, measuring_role, bytes_received


def get_readings(input_file, ip_map, field, start_time):
    readings = collections.defaultdict(lambda: collections.defaultdict(list))
    last_read_time = collections.defaultdict(lambda: collections.defaultdict(int))
    last_byte_count = collections.defaultdict(lambda: collections.defaultdict(int))
    with open(input_file) as fh:
        for line in fh:
            reading = json.loads(line.strip())
            new_format = 'timestamp' in reading
            # Skip if measurement was done before start time
            read_time = int(reading['timestamp'] if new_format else reading['data']['timestamp'])/1000
            if start_time and read_time < start_time:
                continue
            if new_format:
                sender, receiver, bytes_received = parse_new_format_line(reading, ip_map)
            else:
                sender, receiver, bytes_received = parse_old_format_data(reading, ip_map)
            if not last_read_time[sender][receiver]:
                last_read_time[sender][receiver] = read_time
                last_byte_count[sender][receiver] = bytes_received
                continue
            bytes_per_s = float(bytes_received - last_byte_count[sender][receiver])/(read_time - last_read_time[sender][receiver])
            bits_per_s = bytes_per_s*8
            readings[sender][receiver].append(bits_per_s)
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
            mean, stdev = stats[receiver].get(sender, (0, 0))
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
