#!/usr/bin/env python

import argparse
import requests
import socket
import os
import re
from subprocess import call as _call, check_output


TC=["sudo", "tc"]


cases = {
    'asia': {
        '1': {
            'downlink': '10Mbit',
            'uplink': '5Mbit',
            '2': '125ms 7ms',  # netem-compatible delay spec
            '3': '3ms 1ms'
        },
        '2': {
            'downlink': '2Mbit',
            'uplink': '1Mbit',
            '1': '125ms 7ms',
            '3': '130ms 10ms'
        },
        '3': {
            'downlink': '10Mbit',
            'uplink': '8Mbit',
            '1': '3ms 1ms',
            '2': '130ms 10ms',
        }
    },
    'standup': {
        '1': {
            'downlink': '10Mbit',
            'uplink': '10Mbit',
            '2': '5ms 2ms',
            '3': '7ms 2ms',
            '4': '47ms 3ms'
        },
        '2': {
            'downlink': '10Mbit',
            'uplink': '10Mbit',
            '1': '5ms 1ms',
            '3': '7ms 2ms',
            '4': '50ms 5ms',
        },
        '3': {
            'downlink': '5Mbit',
            'uplink': '2Mbit',
            '1': '7ms 2ms',
            '2': '7ms 1ms',
            '4': '40ms 5ms',
        },
        '4': {
            'downlink': '1Mbit',
            'uplink': '512kbit',
            '1': '50ms 3ms',
            '2': '50ms 5ms',
            '3': '40ms 5ms',
        }
    },
    'sitdown': {
        '1': {
            'downlink': '10Mbit',
            'uplink': '10Mbit',
            '2': '8ms 3ms',
            '3': '10ms 2ms',
            '4': '9ms 2ms',
        },
        '2': {
            'downlink': '3Mbit',
            'uplink': '2Mbit',
            '1': '7ms 2ms',
            '3': '9ms 2ms',
            '4': '7ms 2ms',
        },
        '3': {
            'downlink': '5Mbit',
            'uplink': '2Mbit',
            '1': '10ms 2ms',
            '2': '9ms 2ms',
            '4': '10ms 2ms',
        },
        '4': {
            'downlink': '2Mbit',
            'uplink': '1Mbit',
            '1': '9ms 2ms',
            '2': '8ms 2ms',
            '3': '10ms 2ms',
        }
    },
    'friends': {
        # Add this later
    }
}

default_rolemap = {
    '1': 'a.cluster.thusoy.com',
    '2': 'b.cluster.thusoy.com',
    '3': 'c.cluster.thusoy.com',
#    '4': 'd.cluster.thusoy.com',
}


def main():
    parser = argparse.ArgumentParser(prog='case-asia')
    parser.add_argument('-m', '--role-map', help='A mapping of roles to ip addresses',
        default=default_rolemap)
    parser.add_argument('-r', '--role', help='Which role should be activated. Defaults to'
        'checking whether any role is associated with your IP address')
    parser.add_argument('-c', '--case', help='Which case to load', default='asia', choices=cases.keys())
    parser.add_argument('-C', '--clear', action='store_true',
        help="Clear all existing rules without applying a new case")
    args = parser.parse_args()
    if args.clear:
        print('Clearing any existing rules...')
        clear_all_rules()
        return
    case = cases[args.case]
    role_map = args.role_map
    ipify_role_map(role_map)
    role = args.role or get_role_from_ip(args.role_map)
    activate_role(role, args.role_map, case)


def clear_all_rules():
    device = get_interface_device()
    call(TC + ['qdisc', 'del', 'dev', device, 'ingress'], silent=True)
    call(TC + ['qdisc', 'del', 'dev', device, 'root'], silent=True)


def ipify_role_map(role_map):
    """ Needed since a DNS lookup usually will only return IPv4 addresses, while the WebRTC-discovery
    protocol will also find the nodes IPv6 addresses. We thus SSH to each node and query its interface
    list for all IPs it'll answer on.
    """
    ip_regex = re.compile(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}')
    for role, hostname_or_ip in role_map.items():
        if not ip_regex.match(hostname_or_ip):
            # Not an IP in the role map, let's find the IPs
            ips = []
            ipv4_addr_out = check_output([
                'ssh',
                '-o StrictHostKeyChecking=no',
                hostname_or_ip,
                "ifconfig | grep -o 'inet addr:[^ ]*' | cut -d: -f2 | grep -v 127.0.0.1"])
            ips += ipv4_addr_out.strip().split('\n')
            ipv6_out = check_output([
                'ssh',
                '-o StrictHostKeyChecking=no',
                hostname_or_ip,
                "ifconfig | grep -o \"inet6 addr: [^ ]*\" | cut -d' ' -f3 | grep -v '^fe80' | grep -v '^::1'"])
            ips += ipv6_out.strip().split('\n')
            # Probably a hostname, resolve it and use the IP in the role map
            role_map[role] = ips


def get_role_from_ip(rolemap):
    my_ip = get_my_ip()
    for role, ips in rolemap.items():
        if my_ip in ips:
            return role
    raise ValueError("Role not found for ip %s" % my_ip)


def get_my_ip():
    """ Get the IP of the box running this code. """
    # This function is memoizable
    return requests.get('http://httpbin.org/ip').json()['origin']


def activate_role(role, role_map, case):
    print 'Activating role %s' % role
    clear_all_rules()
    uplink = case[role]['uplink']
    downlink = case[role]['downlink']
    add_roots(downlink, uplink)
    add_role_rules(role, role_map, case)


def add_roots(downlink, uplink):
    device = get_interface_device()
    call(TC + ['qdisc', 'add', 'dev', device, 'root', 'handle', '1:', 'htb'])
    call(TC + ['class', 'add', 'dev', device, 'parent', '1:', 'classid', '1:1', 'htb', 'rate', '100Mbit'])
    call(TC + ['class', 'add', 'dev', device, 'parent', '1:1', 'classid', '1:2', 'htb', 'rate', uplink])
    call(TC + ['qdisc', 'add', 'dev', device, 'handle', 'ffff:', 'ingress'])
    # This effectively limits UDP to the given downlink bandwidth, but TCP will have lower performance, because of negative effects of the window
    # size and the large delays. This doesn't matter in this case, as our traffic is UDP-based, but it's worth to keep it mind.
    call(TC + ['filter', 'add', 'dev', device, 'parent', 'ffff:', 'protocol', 'ip', 'prio', '50', 'u32', 'match', 'ip', 'src', '0.0.0.0/0', 'police', 'rate', downlink, 'burst', downlink, 'flowid', ':1'])


def add_role_rules(role, role_map, case):
    device = get_interface_device()
    ipv4_regex = re.compile(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}')
    for other_role, delay_config in case[role].items():
        if other_role in ('uplink', 'downlink'):
            continue
        class_id = int(other_role)*10
        handle_id = str(class_id) + '1'
        delay_config_as_list = delay_config.split()
        if not other_role in role_map:
            raise ValueError('Role does not have a specified target in the role_map: %s' % other_role)
        call(TC + ['class', 'add', 'dev', device, 'parent', '1:2', 'classid', '1:%d' % class_id, 'htb', 'rate', case[role]['uplink']])
        call(TC + ['qdisc', 'add', 'dev', device, 'parent', '1:%d' % class_id, 'handle', '%s:' % handle_id, 'netem', 'delay'] + delay_config_as_list)
        for ip in role_map[other_role]:
            if ipv4_regex.match(ip):
                call(TC + ['filter', 'add', 'dev', device, 'protocol', 'ip',
                    'parent', '1:0', 'prio', '3', 'u32', 'match', 'ip', 'dst',
                    ip, 'flowid', '1:%d' % class_id])
            else:
                call(TC + ['filter', 'add', 'dev', device, 'protocol', 'ipv6',
                    'parent', '1:0', 'prio', '4', 'u32', 'match', 'ip6',
                    'dst', ip, 'flowid', '1:%d' % class_id])


def get_interface_device():
    # This function is memoizable
    my_ip = get_my_ip()
    all_interfaces = []
    ip_links_output = check_output(['ip', 'link', 'list'])
    for line in ip_links_output.split('\n'):
        if not line.startswith('%s:' % (len(all_interfaces) + 1)):
            continue
        interface = line.split(':')[1].strip()
        all_interfaces.append(interface)
    for interface in all_interfaces:
        ip_addr_output = check_output(['ip', 'addr', 'show', 'dev', interface])
        if my_ip in ip_addr_output:
            return interface
    raise ValueError('Failed to find correct interface to use!')


def call(args, silent=False, **kwargs):
    devnull = open(os.devnull, 'wb')
    if silent:
        kwargs['stdout'] = devnull
        kwargs['stderr'] = devnull
    else:
        print 'Running cmd: %s' % ' '.join(args)
    _call(args, **kwargs)


if __name__ == '__main__':
    main()
