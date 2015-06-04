#!/usr/bin/env python3

"""
    Transform timestamp,a,b,c,d,e,f csv file to
    timestamp,a->b,a->c,a->d,... pairs, compute median and stdev,
    output to latex.
"""
import statistics
import csv
import sys
from collections import defaultdict


def main(input_file):
    latencies = get_latencies(input_file)
    statistical_properties = get_statistical_properties(latencies)
    latexify_properties(statistical_properties)

def get_latencies(input_file):
    # {
    #     'A': {
    #         'B': [
    #             (timestamp, latency_on_video_from_b_to_a)
    #         ]
    #     }
    # }
    latencies = defaultdict(lambda: defaultdict(list))
    with open(input_file) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            timestamp = row.pop('Timestamp')
            local_time = float(row.pop('Local time'))
            receiver_max = '0'
            receiver = None
            for role, value in row.items():
                if value > receiver_max:
                    receiver = role
                    receiver_max = value
                if float(value) > (local_time if local_time > 1 else local_time + 60):
                    print('OBS: Possible erroneous reading at {}, local time was {:.3f}, measured value {:.3f}'.format(timestamp, local_time, float(value)))
            row.pop(receiver)
            for sender, value in row.items():
                if value:
                    latency = int(1000*(float(receiver_max) - float(value)))
                    latencies[receiver][sender].append((timestamp, latency))
    return latencies


def get_statistical_properties(latencies):
    # creates a dict like {
    #     'A': {
    #         'B': (mean, stdev),
    #     }
    # }
    properties = defaultdict(dict)
    for receiver, sender_dict in latencies.items():
        for sender, measurements in sender_dict.items():
            values = [t[1] for t in measurements]
            mean = statistics.mean(values)
            stdev = statistics.pstdev(values)
            if any(value for value in values if abs(value - mean) > stdev):
                print('OBS: Large offset at {}'.format(str([(timestamp, value) for timestamp, value in measurements if abs(value - mean) > stdev])))
            properties[receiver][sender] = (mean, stdev)
    return properties


def latexify_properties(properties):
    for receiver in sorted(properties):
        print('\\addplot+[error bars/.cd,y dir=both, y explicit]\ncoordinates{', end='')
        for sender in sorted(properties[receiver]):
            mean, stdev = properties[receiver][sender]
            print('\n    ({sender},{value:.0f}) +- (0.0, {stdev:.0f})'.format(**{'sender': sender,
                'value': mean, 'stdev': stdev}), end='')

        print('};\n')


if __name__ == '__main__':
    main(sys.argv[1])
