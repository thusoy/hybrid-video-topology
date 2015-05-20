#!/bin/bash

# Starts the actual capture of screenshots, and prints the current time offset and local clock

grep $(hostname) apply-case.py

python clock.py &
clock_pid=$!
trap cleanup INT

function cleanup () {
    kill -9 $clock_pid
    echo -e "\n"
    exit $?
}

while :; do
    gm import -window root /tmp/screen-$(hostname)-$(date +"%s").png
    sleep 10
done
