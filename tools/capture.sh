#!/bin/bash

# Starts the actual capture of screenshots, and prints the current time offset and local clock
session_id=$(hostname)-$(date +"%s")

# Print which role we're configured as
grep $(hostname) apply-case.py

# Start sniffing traffic to reconstruct bandwidth usage between peers, excluding some common spammy services (ssh, spotify, name lookups, ssdp)
sudo tcpdump -nNqtts68 "port not 3271 and port not 17500 and port not 137 and port not 138 and port not 1900 and (udp or tcp)" -w /tmp/$session-id.pcap &
tcpdump_pid=$!

python clock.py &
clock_pid=$!
trap cleanup INT

function cleanup () {
    echo -e "\nStopping children..."
    kill -INT $clock_pid
    kill -INT $tcpdump_pid
    exit $?
}

while :; do
    gm import -window root /tmp/screen-$session_id-$(date +"%s").png
    sleep 10
done
