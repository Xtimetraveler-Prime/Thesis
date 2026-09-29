# P03 physical one-core conformance over Vivado Hardware Manager + VIO.
if {$argc != 5} {
    error "usage: p03_physical_conformance.tcl <bit> <ltx> <vectors.tcl> <result.txt> <hw_server_url>"
}

set bit_file [file normalize [lindex $argv 0]]
set ltx_file [file normalize [lindex $argv 1]]
set vector_file [file normalize [lindex $argv 2]]
set result_file [file normalize [lindex $argv 3]]
set hw_server_url [lindex $argv 4]

foreach path [list $bit_file $ltx_file $vector_file] {
    if {![file exists $path]} { error "P03 physical input missing: $path" }
}
source $vector_file

proc p03_parse_value {raw} {
    set text [string trim $raw]
    regsub -all {_} $text "" text
    if {[regexp -nocase {^0x([0-9a-f]+)$} $text -> digits]} {
        return [expr "0x$digits"]
    }
    if {[regexp -nocase {^[0-9a-f]+$} $text]} {
        return [expr "0x$text"]
    }
    error "Cannot parse VIO value '$raw'"
}

proc p03_probe {direction port} {
    global P03_VIO
    set wanted [string tolower $direction]
    foreach probe [get_hw_probes -of_objects $P03_VIO] {
        set type [string tolower [get_property TYPE $probe]]
        set probe_port [get_property PROBE_PORT $probe]
        if {$type eq $wanted && $probe_port == $port} {
            return $probe
        }
    }
    puts "P03 available VIO probes:"
    foreach probe [get_hw_probes -of_objects $P03_VIO] {
        puts "  name=[get_property NAME $probe] type=[get_property TYPE $probe] port=[get_property PROBE_PORT $probe] bits=[get_property PROBE_PORT_BIT_COUNT $probe]"
    }
    error "P03 VIO probe not found: direction=$direction port=$port"
}

proc p03_commit {settings} {
    global P03_VIO
    foreach {port value} $settings {
        set probe [p03_probe vio_output $port]
        set_property OUTPUT_VALUE $value $probe
    }
    commit_hw_vio $P03_VIO
}

proc p03_refresh {} {
    global P03_VIO
    refresh_hw_vio $P03_VIO
}

proc p03_input {port} {
    p03_refresh
    return [p03_parse_value [get_property INPUT_VALUE [p03_probe vio_input $port]]]
}

proc p03_wait_input {port expected timeout_ms label} {
    set deadline [expr {[clock milliseconds] + $timeout_ms}]
    while {[clock milliseconds] <= $deadline} {
        set actual [p03_input $port]
        if {$actual == $expected} { return $actual }
        after 10
    }
    error "P03 timeout waiting for $label: expected=$expected actual=[p03_input $port]"
}

proc p03_host_write {bank addr value} {
    # out7=req out8=write out9=bank out10=addr out11=wdata
    p03_commit [list 7 0x0 8 0x1 9 $bank 10 $addr 11 $value]
    p03_commit [list 7 0x1]
    p03_wait_input 11 1 2000 "host write ack bank=$bank addr=$addr"
    set err [p03_input 13]
    p03_commit [list 7 0x0]
    if {$err != 0} { error "P03 host write failed: bank=$bank addr=$addr" }
}

proc p03_host_read {bank addr} {
    p03_commit [list 7 0x0 8 0x0 9 $bank 10 $addr 11 0x0]
    p03_commit [list 7 0x1]
    p03_wait_input 11 1 2000 "host read ack bank=$bank addr=$addr"
    set valid [p03_input 12]
    set err [p03_input 13]
    set value [p03_input 14]
    p03_commit [list 7 0x0]
    if {$err != 0 || $valid != 1} {
        error "P03 host read failed: bank=$bank addr=$addr valid=$valid error=$err"
    }
    return $value
}

proc p03_expect {label actual expected} {
    if {$actual != $expected} {
        error "P03 mismatch $label: actual=0x[format %X $actual] expected=0x[format %X $expected]"
    }
}

proc p03_load_seeds {bank seeds} {
    foreach seed $seeds {
        lassign $seed addr value
        p03_host_write $bank $addr $value
    }
}

open_hw_manager
connect_hw_server -url $hw_server_url
set targets [get_hw_targets]
if {[llength $targets] == 0} { error "P03 no hardware targets found" }
current_hw_target [lindex $targets 0]
open_hw_target

set P03_DEVICE ""
foreach device [get_hw_devices] {
    set name [get_property NAME $device]
    if {[regexp -nocase {(xczu|xck26)} $name]} {
        set P03_DEVICE $device
        break
    }
}
if {$P03_DEVICE eq ""} {
    set devices [get_hw_devices]
    if {[llength $devices] == 1} {
        set P03_DEVICE [lindex $devices 0]
    } else {
        puts "P03 hardware devices: $devices"
        error "P03 could not identify the K26/UltraScale+ hardware device"
    }
}
current_hw_device $P03_DEVICE
refresh_hw_device -update_hw_probes false $P03_DEVICE
set_property PROGRAM.FILE $bit_file $P03_DEVICE
if {[lsearch -exact [list_property $P03_DEVICE] PROBES.FILE] >= 0} {
    set_property PROBES.FILE $ltx_file $P03_DEVICE
}
if {[lsearch -exact [list_property $P03_DEVICE] FULL_PROBES.FILE] >= 0} {
    set_property FULL_PROBES.FILE $ltx_file $P03_DEVICE
}
program_hw_devices $P03_DEVICE
refresh_hw_device $P03_DEVICE

set P03_VIO ""
set vios [get_hw_vios -of_objects $P03_DEVICE]
foreach vio $vios {
    set cell ""
    catch {set cell [get_property CELL_NAME $vio]}
    if {[string match "*vio_p03*" $cell]} {
        set P03_VIO $vio
        break
    }
}
if {$P03_VIO eq "" && [llength $vios] == 1} {
    set P03_VIO [lindex $vios 0]
}
if {$P03_VIO eq ""} {
    puts "P03 discovered VIO cores: $vios"
    error "P03 VIO core was not found after programming"
}
puts "P03 hardware device: [get_property NAME $P03_DEVICE]"
puts "P03 VIO core: $P03_VIO"

# Force numeric VIO probes to hexadecimal so INPUT_VALUE/OUTPUT_VALUE parsing is
# deterministic for vectors up to the 256-bit trace width.
foreach probe [get_hw_probes -of_objects $P03_VIO] {
    set type [string tolower [get_property TYPE $probe]]
    if {$type eq "vio_input"} { catch {set_property INPUT_VALUE_RADIX HEX $probe} }
    if {$type eq "vio_output"} { catch {set_property OUTPUT_VALUE_RADIX HEX $probe} }
}
reset_hw_vio_outputs $P03_VIO
refresh_hw_vio -update_output_values $P03_VIO

# out1 is the active-high external reset command.
p03_commit [list 1 0x1]
after 20
p03_commit [list 1 0x0]
after 20

# Physical Port-B preflight: write/read one unused high address in every bank.
# This proves the VIO bridge reaches every retained XPM bank before model data is
# loaded. Values are width-limited to the corresponding bank.
set bank_preflight {
    {0 1023 0x0123456789ABCDEFFEDCBA9876543210}
    {1 1023 0x0123456789ABCDEF}
    {2 4095 0x1122334455667788}
    {3 32767 0x8877665544332211}
    {4 1023 0x89ABCDEF}
    {5 4095 0x13579BDF}
    {6 4095 0x2468ACE0}
    {7 1023 0x00112233445566778899AABBCCDDEEFFFFEEDDCCBBAA99887766554433221100}
    {8 4095 0x0F1E2D3C4B5A6978}
}
foreach item $bank_preflight {
    lassign $item bank addr value
    p03_host_write $bank $addr $value
    p03_expect "bank $bank preflight" [p03_host_read $bank $addr] [p03_parse_value $value]
}
puts "P03 physical memory preflight passed for all 9 banks"

# Load the same packed image used by the Python/HLS differential corpus.
p03_load_seeds 0 $P03_CONFIG_SEEDS
p03_load_seeds 1 $P03_STATE_SEEDS
p03_load_seeds 2 $P03_AXON_SEEDS
p03_load_seeds 3 $P03_SYNAPSE_SEEDS
p03_load_seeds 4 $P03_ROUTE_DESC_SEEDS
p03_load_seeds 5 $P03_ROUTE_SEEDS

set result [open $result_file w]
puts $result "schema=p03-physical-conformance-v1"
puts $result "device=[get_property NAME $P03_DEVICE]"
puts $result "ticks=[llength $P03_TICKS]"
puts $result "compartments=$P03_COMPARTMENT_COUNT"
puts $result "synapses=$P03_SYNAPSE_COUNT"
puts $result "routes=$P03_ROUTE_COUNT"

set tick_index 0
foreach tick $P03_TICKS {
    set timestep [dict get $tick timestep]
    set events [dict get $tick events]
    set expected_spikes [dict get $tick spike_count]
    set expected_states [dict get $tick states]
    set expected_traces [dict get $tick traces]
    set expected_packets [dict get $tick packets]

    set event_addr 0
    foreach axon $events {
        p03_host_write 6 $event_addr $axon
        incr event_addr
    }

    # out2=compartments out3=events out4=synapses out5=routes out6=timestep
    p03_commit [list \
        2 $P03_COMPARTMENT_COUNT \
        3 [llength $events] \
        4 $P03_SYNAPSE_COUNT \
        5 $P03_ROUTE_COUNT \
        6 $timestep \
        0 0x0]

    set before_runs [p03_input 16]
    set target_runs [expr {$before_runs + 1}]
    p03_commit [list 0 0x1]
    after 1
    p03_commit [list 0 0x0]
    p03_wait_input 16 $target_runs 10000 "completed run counter for timestep $timestep"

    set blocked [p03_input 15]
    set status [p03_input 5]
    set spikes [p03_input 3]
    set packets [p03_input 4]
    set cycles [p03_input 8]
    if {$blocked != 0} { error "P03 timestep $timestep start was blocked" }
    p03_expect "timestep $timestep status" $status 0
    p03_expect "timestep $timestep spike_count" $spikes $expected_spikes
    p03_expect "timestep $timestep packet_count" $packets [llength $expected_packets]
    if {$cycles <= 0} { error "P03 timestep $timestep reported zero physical cycles" }

    for {set i 0} {$i < $P03_COMPARTMENT_COUNT} {incr i} {
        p03_expect "timestep $timestep state($i)" \
            [p03_host_read 1 $i] [p03_parse_value [lindex $expected_states $i]]
        p03_expect "timestep $timestep trace($i)" \
            [p03_host_read 7 $i] [p03_parse_value [lindex $expected_traces $i]]
    }
    for {set i 0} {$i < [llength $expected_packets]} {incr i} {
        p03_expect "timestep $timestep packet($i)" \
            [p03_host_read 8 $i] [p03_parse_value [lindex $expected_packets $i]]
    }

    puts $result "tick=$tick_index timestep=$timestep cycles=$cycles spikes=$spikes packets=$packets status=$status"
    puts "P03 physical tick PASS: index=$tick_index timestep=$timestep cycles=$cycles spikes=$spikes packets=$packets"
    incr tick_index
}

puts $result "result=PASS"
close $result
puts "P03 physical Python/FPGA conformance PASS: ticks=$tick_index result=$result_file"
close_hw_manager
