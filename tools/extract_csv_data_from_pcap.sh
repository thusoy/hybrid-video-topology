#!/bin/bash

# Convert a pcap dump (stored in dropbox) to a csv which can be stored in the
# repo for further processing

filters=$(python -c "import sys; print ','.join(sys.argv[2:])" $@)

tshark -r $1 -qz io,stat,1,$filters | sed "1,/0 <>/d" | tr -d "|" | python -c "
import sys
num_filters = len(sys.argv[2:])
field_numbers = [0] + range(6,6+num_filters*2, 2)
print 'Interval start,' + ','.join(sys.argv[2:])
for line in sys.stdin:
    if line.startswith('===='):
        sys.exit()
    fields = line.split()
    saved_fields = []
    for num in field_numbers:
        saved_fields.append(fields[num])
    print ','.join(saved_fields)
" $@
