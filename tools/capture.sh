#!/bin/bash

# Starts the actual capture of screenshots, and prints the current time offset and local clock

grep $(hostname) apply-case.py

ntpdate -q no.pool.ntp.org | tail -1 | grep -o "offset.*"
python clock.py &
clock_pid=$!
trap cleanup INT

function cleanup () {
	kill -9 $clock_pid
	echo -e "\n"
	exit $?
}

while :; do
	xwd -root | gzip > /tmp/screen-$(hostname)-$(date +"%s").xwd.gz
	sleep 10
done
