set ns [new Simulator]

set nf [open out.nam w]
$ns namtrace-all $nf

proc finish {} {
    global ns nf
    $ns flush-trace
    close $nf
    exec nam out.nam &
    exit 0
}

$ns at 5.0 "finish"


##################################
# Start actual code and topo setup
##################################


# Create two nodes
set n0 [$ns node]
set n1 [$ns node]

# Link them
$ns duplex-link $n0 $n1 1Mb 10ms DropTail

# Create an agent at each node
set udp0 [new Agent/UDP]
$ns attach-agent $n0 $udp0

# Create a constant bitrate traffic-generator at ns0
set cbr0 [new Application/Traffic/CBR]
$cbr0 set packetSize_ 500
$cbr0 set interval_ 0.005
$cbr0 attach-agent $udp0

# Create a traffic sink at ns1
set null0 [new Agent/Null]
$ns attach-agent $n1 $null0

# Link the agents
$ns connect $udp0 $null0

$ns at 0.5 "$cbr0 start"
$ns at 4.8 "$cbr0 stop"


######################
# Start the simulation
######################


$ns run
