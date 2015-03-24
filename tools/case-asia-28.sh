#!/bin/bash

set -eu

I=eth1
UPLINK=5Mbit
DOWNLINK=10Mbit

# Clear all existing rules
sudo tc qdisc del dev $I ingress || echo "Couldn't clear ingress, skipping..."
sudo tc qdisc del dev $I root || echo "Nothing to clear, skipping..."

# Add root nodes
sudo tc qdisc add dev $I root handle 1: htb
sudo tc class add dev $I parent 1: classid 1:1 htb rate 100Mbit
sudo tc qdisc add dev $I handle ffff: ingress

# This effectively limits UDP to the given downlink bandwidth, but TCP will have lower performance, because of negative effects of the window
# size and the large delays. This doens't matter in this case, as our traffic is UDP-based, but it's worth to keep it mind.
sudo tc filter add dev $I parent ffff: protocol ip prio 50 u32 match ip src 0.0.0.0/0 police rate $DOWNLINK burst $DOWNLINK flowid :1

# Add classes for each of the nodes in the conversation
sudo tc class add dev $I parent 1:1 classid 1:30 htb rate $UPLINK
sudo tc class add dev $I parent 1:1 classid 1:27 htb rate $UPLINK

# Set class delays
sudo tc qdisc add dev $I parent 1:30 handle 301: netem delay 12ms 1ms
sudo tc qdisc add dev $I parent 1:27 handle 271: netem delay 4ms 1ms

# Add traffic to filters
sudo tc filter add dev $I protocol ip parent 1:0 prio 3 u32 match ip dst 129.241.209.30 flowid 1:30
sudo tc filter add dev $I protocol ip parent 1:0 prio 3 u32 match ip dst 129.241.209.27 flowid 1:27
