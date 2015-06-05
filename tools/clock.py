import time
import sys
import subprocess

def print_clock_offset():
    ntpdate_output = subprocess.check_output([
        'ntpdate',
        '-q',
        'ntp.ntnu.no',
        ]).strip().split('\n')
    offset_start = ntpdate_output[-1].find('offset')
    return ntpdate_output[-1][offset_start:]

def now():
    return time.time()

def start_printing_time():
    while True:
        try:
            t = now()
            print '%4.3f' % (t % 60),
            sys.stdout.flush()
            time.sleep(0.002)
            print '\r',
        except KeyboardInterrupt:
            break


if __name__ == '__main__':
    print print_clock_offset()
    start_printing_time()
