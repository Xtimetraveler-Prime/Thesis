# P04 physical two-core conformance over Vivado Hardware Manager + VIO.
if {$argc != 5} {
    error "usage: p04_physical_conformance.tcl <bit> <ltx> <vectors.tcl> <result.txt> <hw_server_url>"
}

set bit_file [file normalize [lindex $argv 0]]
set ltx_file [file normalize [lindex $argv 1]]
set vector_file [file normalize [lindex $argv 2]]
set result_file [file normalize [lindex $argv 3]]
set hw_server_url [lindex $argv 4]
foreach path [list $bit_file $ltx_file $vector_file] {
    if {![file exists $path]} { error "P04 physical input missing: $path" }
}
source $vector_file

proc p04_parse_value {raw} {
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

proc p04_probe {direction port} {
    global P04_VIO
    set wanted [string tolower $direction]
    foreach probe [get_hw_probes -of_objects $P04_VIO] {
        set type [string tolower [get_property TYPE $probe]]
        set probe_port [get_property PROBE_PORT $probe]
        if {$type eq $wanted && $probe_port == $port} { return $probe }
    }
    puts "P04 available VIO probes:"
    foreach probe [get_hw_probes -of_objects $P04_VIO] {
        puts "  name=[get_property NAME $probe] type=[get_property TYPE $probe] port=[get_property PROBE_PORT $probe] bits=[get_property PROBE_PORT_BIT_COUNT $probe]"
    }
    error "P04 VIO probe not found: direction=$direction port=$port"
}

proc p04_format_output_value {probe value} {
    set bits [get_property PROBE_PORT_BIT_COUNT $probe]
    set chars [expr {($bits + 3) / 4}]
    set text [string trim $value]
    regsub -all {_} $text "" text
    if {[regexp -nocase {^0x([0-9a-f]+)$} $text -> digits]} {
        set digits [string toupper $digits]
        set numeric [expr "0x$digits"]
    } elseif {[regexp {^[0-9]+$} $text]} {
        set numeric [expr {$text + 0}]
        set digits [format %X $numeric]
    } else {
        error "P04 cannot format VIO output value '$value'"
    }
    if {$numeric < 0 || $numeric >= (1 << $bits)} {
        error "P04 VIO output value out of range: value=$value bits=$bits port=[get_property PROBE_PORT $probe]"
    }
    if {[string length $digits] > $chars} {
        error "P04 VIO output value too wide: value=$value bits=$bits"
    }
    return "[string repeat 0 [expr {$chars - [string length $digits]}]]$digits"
}

proc p04_commit {settings} {
    global P04_VIO
    foreach {port value} $settings {
        set probe [p04_probe vio_output $port]
        set_property OUTPUT_VALUE [p04_format_output_value $probe $value] $probe
    }
    commit_hw_vio $P04_VIO
}

proc p04_refresh {} {
    global P04_VIO
    refresh_hw_vio $P04_VIO
}

proc p04_input {port} {
    p04_refresh
    return [p04_parse_value [get_property INPUT_VALUE [p04_probe vio_input $port]]]
}

proc p04_wait_input {port expected timeout_ms label} {
    set deadline [expr {[clock milliseconds] + $timeout_ms}]
    while {[clock milliseconds] <= $deadline} {
        set actual [p04_input $port]
        if {$actual == $expected} { return $actual }
        after 10
    }
    error "P04 timeout waiting for $label: expected=$expected actual=[p04_input $port]"
}

proc p04_expect {label actual expected} {
    if {$actual != $expected} {
        error "P04 mismatch $label: actual=0x[format %X $actual] expected=0x[format %X $expected]"
    }
}

proc p04_expect_list_unordered {label actual expected} {
    set actual_sorted [lsort -integer $actual]
    set expected_sorted [lsort -integer $expected]
    if {$actual_sorted ne $expected_sorted} {
        error "P04 mismatch $label: actual=$actual_sorted expected=$expected_sorted"
    }
}

# VIO outputs: 13=req 14=write 15=core 16=bank 17=addr 18=wdata.
# VIO inputs: 34=ack 35=rvalid 36=error 37=rdata.
proc p04_host_write {core bank addr value} {
    p04_commit [list 13 0x0 14 0x1 15 $core 16 $bank 17 $addr 18 $value]
    p04_commit [list 13 0x1]
    p04_wait_input 34 1 2000 "host write ack core=$core bank=$bank addr=$addr"
    set err [p04_input 36]
    p04_commit [list 13 0x0]
    if {$err != 0} { error "P04 host write failed: core=$core bank=$bank addr=$addr" }
}

proc p04_host_read {core bank addr} {
    p04_commit [list 13 0x0 14 0x0 15 $core 16 $bank 17 $addr 18 0x0]
    p04_commit [list 13 0x1]
    p04_wait_input 34 1 2000 "host read ack core=$core bank=$bank addr=$addr"
    set valid [p04_input 35]
    set err [p04_input 36]
    set value [p04_input 37]
    p04_commit [list 13 0x0]
    if {$err != 0 || $valid != 1} {
        error "P04 host read failed: core=$core bank=$bank addr=$addr valid=$valid error=$err"
    }
    return $value
}

proc p04_host_expect_error {core bank addr} {
    p04_commit [list 13 0x0 14 0x0 15 $core 16 $bank 17 $addr 18 0x0]
    p04_commit [list 13 0x1]
    p04_wait_input 34 1 2000 "expected host error core=$core bank=$bank addr=$addr"
    set err [p04_input 36]
    p04_commit [list 13 0x0]
    if {$err != 1} {
        error "P04 expected physical-allocation host rejection: core=$core bank=$bank addr=$addr"
    }
}

proc p04_load_seeds {core bank seeds} {
    foreach seed $seeds {
        lassign $seed addr value
        p04_host_write $core $bank $addr $value
    }
}

proc p04_clear_route_descriptors {core count} {
    for {set addr 0} {$addr < $count} {incr addr} {
        p04_host_write $core 4 $addr 0x0
    }
}

proc p04_load_core_image {core image physical_compartments} {
    # A route descriptor can remain architecturally visible even when the next
    # scenario has no output routes. Clear the small physical descriptor bank
    # before loading sparse descriptors so scenario order cannot leak state.
    p04_clear_route_descriptors $core $physical_compartments
    p04_load_seeds $core 0 [dict get $image config_seeds]
    p04_load_seeds $core 1 [dict get $image state_seeds]
    p04_load_seeds $core 2 [dict get $image axon_seeds]
    p04_load_seeds $core 3 [dict get $image synapse_seeds]
    p04_load_seeds $core 4 [dict get $image route_desc_seeds]
    p04_load_seeds $core 5 [dict get $image route_seeds]
}

proc p04_load_initial_events {core events} {
    set addr 0
    foreach axon $events {
        p04_host_write $core 6 $addr $axon
        incr addr
    }
}

proc p04_check_error_inputs {label} {
    # Controller/router/memory sticky error inputs 16..26 must all be zero.
    for {set port 16} {$port <= 26} {incr port} {
        set value [p04_input $port]
        if {$value != 0} { error "P04 $label error input port=$port value=$value" }
    }
    # Per-core HLS status flags are inputs 29 and 32.
    p04_expect "$label core0 status" [p04_input 29] 0
    p04_expect "$label core1 status" [p04_input 32] 0
}

open_hw_manager
connect_hw_server -url $hw_server_url
set targets [get_hw_targets]
if {[llength $targets] == 0} { error "P04 no hardware targets found" }
current_hw_target [lindex $targets 0]
open_hw_target

set P04_DEVICE ""
foreach device [get_hw_devices] {
    set name [get_property NAME $device]
    if {[regexp -nocase {(xczu|xck26)} $name]} {
        set P04_DEVICE $device
        break
    }
}
if {$P04_DEVICE eq ""} {
    set devices [get_hw_devices]
    if {[llength $devices] == 1} {
        set P04_DEVICE [lindex $devices 0]
    } else {
        puts "P04 hardware devices: $devices"
        error "P04 could not identify the K26/UltraScale+ hardware device"
    }
}
current_hw_device $P04_DEVICE
refresh_hw_device -update_hw_probes false $P04_DEVICE
set_property PROGRAM.FILE $bit_file $P04_DEVICE
if {[lsearch -exact [list_property $P04_DEVICE] PROBES.FILE] >= 0} {
    set_property PROBES.FILE $ltx_file $P04_DEVICE
}
if {[lsearch -exact [list_property $P04_DEVICE] FULL_PROBES.FILE] >= 0} {
    set_property FULL_PROBES.FILE $ltx_file $P04_DEVICE
}
program_hw_devices $P04_DEVICE
refresh_hw_device $P04_DEVICE

set P04_VIO ""
set vios [get_hw_vios -of_objects $P04_DEVICE]
foreach vio $vios {
    set cell ""
    catch {set cell [get_property CELL_NAME $vio]}
    if {[string match "*vio_p04*" $cell]} {
        set P04_VIO $vio
        break
    }
}
if {$P04_VIO eq "" && [llength $vios] == 1} { set P04_VIO [lindex $vios 0] }
if {$P04_VIO eq ""} {
    puts "P04 discovered VIO cores: $vios"
    error "P04 VIO core was not found after programming"
}
puts "P04 hardware device: [get_property NAME $P04_DEVICE]"
puts "P04 VIO core: $P04_VIO"

foreach probe [get_hw_probes -of_objects $P04_VIO] {
    set type [string tolower [get_property TYPE $probe]]
    if {$type eq "vio_input"} { catch {set_property INPUT_VALUE_RADIX HEX $probe} }
    if {$type eq "vio_output"} { catch {set_property OUTPUT_VALUE_RADIX HEX $probe} }
}
reset_hw_vio_outputs $P04_VIO
refresh_hw_vio -update_output_values $P04_VIO

# out2 drives the active-low proc_sys_reset external reset.
p04_commit [list 2 0x0]
after 20
p04_commit [list 2 0x1]
after 20
set heartbeat_before [p04_input 38]
after 20
set heartbeat_after [p04_input 38]
if {$heartbeat_before == $heartbeat_after} {
    error "P04 control fabric did not leave reset: heartbeat remained $heartbeat_after"
}
puts "P04 reset release verified: heartbeat $heartbeat_before -> $heartbeat_after"

# Verify both endpoint Port-B paths at the final valid physical address of every
# bank. This proves the resource-scaled allocation is retained and separately
# host-addressable without claiming those depths are logical Loihi capacities.
set bank_preflight [list \
    [list 0 [expr {$P04_PHYSICAL_COMPARTMENTS - 1}] 0x0123456789ABCDEFFEDCBA9876543210] \
    [list 1 [expr {$P04_PHYSICAL_COMPARTMENTS - 1}] 0x0123456789ABCDEF] \
    [list 2 [expr {$P04_PHYSICAL_AXONS - 1}] 0x1122334455667788] \
    [list 3 [expr {$P04_PHYSICAL_SYNAPSES - 1}] 0x8877665544332211] \
    [list 4 [expr {$P04_PHYSICAL_COMPARTMENTS - 1}] 0x89ABCDEF] \
    [list 5 [expr {$P04_PHYSICAL_ROUTES - 1}] 0x13579BDF] \
    [list 6 [expr {$P04_PHYSICAL_EVENTS - 1}] 0x2468ACE0] \
    [list 7 [expr {$P04_PHYSICAL_COMPARTMENTS - 1}] 0x00112233445566778899AABBCCDDEEFFFFEEDDCCBBAA99887766554433221100] \
    [list 8 [expr {$P04_PHYSICAL_PACKETS - 1}] 0x0F1E2D3C4B5A6978]]
foreach core {0 1} {
    foreach item $bank_preflight {
        lassign $item bank addr value
        p04_host_write $core $bank $addr $value
        p04_expect "core $core bank $bank preflight" \
            [p04_host_read $core $bank $addr] [p04_parse_value $value]
    }
    # One address beyond the physical fixture must be rejected, proving that
    # high logical addresses cannot alias into the small validation memories.
    p04_host_expect_error $core 0 $P04_PHYSICAL_COMPARTMENTS
}
puts "P04 physical memory preflight passed for both endpoint fabrics"

set result [open $result_file w]
puts $result "schema=p04-physical-conformance-v1"
puts $result "device=[get_property NAME $P04_DEVICE]"
puts $result "scenarios=[llength $P04_SCENARIOS]"
puts $result "physical_fixture_compartments=$P04_PHYSICAL_COMPARTMENTS"
puts $result "physical_fixture_axons=$P04_PHYSICAL_AXONS"
puts $result "physical_fixture_synapses=$P04_PHYSICAL_SYNAPSES"
puts $result "physical_fixture_routes=$P04_PHYSICAL_ROUTES"
puts $result "logical_capacity_changed=0"

foreach scenario $P04_SCENARIOS {
    set name [dict get $scenario name]
    set core0_image [dict get $scenario core0]
    set core1_image [dict get $scenario core1]
    set initial_events0 [dict get $scenario initial_events0]
    set initial_events1 [dict get $scenario initial_events1]
    set ticks [dict get $scenario ticks]

    foreach reverse {0 1} {
        p04_load_core_image 0 $core0_image $P04_PHYSICAL_COMPARTMENTS
        p04_load_core_image 1 $core1_image $P04_PHYSICAL_COMPARTMENTS
        p04_load_initial_events 0 $initial_events0
        p04_load_initial_events 1 $initial_events1

        # out3=service_reverse, out4=timestep, out5/6=initial event counts,
        # out7..12=per-core active compartment/synapse/route counts.
        p04_commit [list \
            3 $reverse \
            4 0 \
            5 [llength $initial_events0] \
            6 [llength $initial_events1] \
            7 [dict get $core0_image compartment_count] \
            8 [dict get $core0_image synapse_count] \
            9 [dict get $core0_image route_count] \
            10 [dict get $core1_image compartment_count] \
            11 [dict get $core1_image synapse_count] \
            12 [dict get $core1_image route_count] \
            0 0x0 \
            1 0x0]

        # Pulse epoch_load to bind the just-loaded initial event memories to
        # algorithmic timestep zero.
        p04_commit [list 0 0x1]
        after 1
        p04_commit [list 0 0x0]
        p04_wait_input 3 1 2000 "epoch loaded scenario=$name reverse=$reverse"
        p04_expect "scenario $name initial timestep" [p04_input 4] 0
        p04_expect "scenario $name initial event count core0" [p04_input 5] [llength $initial_events0]
        p04_expect "scenario $name initial event count core1" [p04_input 6] [llength $initial_events1]

        set tick_index 0
        foreach tick $ticks {
            set timestep [dict get $tick timestep]
            set expected0 [dict get $tick core0]
            set expected1 [dict get $tick core1]
            set next_events0 [dict get $tick next_events0]
            set next_events1 [dict get $tick next_events1]
            set expected_local [dict get $tick local_packets]
            set expected_remote [dict get $tick remote_packets]

            set before_runs [p04_input 14]
            set target_runs [expr {$before_runs + 1}]
            p04_commit [list 1 0x1]
            after 1
            p04_commit [list 1 0x0]
            p04_wait_input 14 $target_runs 10000 "completed tick scenario=$name reverse=$reverse timestep=$timestep"

            p04_check_error_inputs "scenario=$name reverse=$reverse timestep=$timestep"
            p04_expect "$name t$timestep current timestep" [p04_input 4] [expr {$timestep + 1}]
            p04_expect "$name t$timestep current events core0" [p04_input 5] [llength $next_events0]
            p04_expect "$name t$timestep current events core1" [p04_input 6] [llength $next_events1]
            p04_expect "$name t$timestep local packets" [p04_input 12] $expected_local
            p04_expect "$name t$timestep remote packets" [p04_input 13] $expected_remote
            p04_expect "$name t$timestep spike count core0" [p04_input 27] [dict get $expected0 spike_count]
            p04_expect "$name t$timestep packet count core0" [p04_input 28] [dict get $expected0 packet_count]
            p04_expect "$name t$timestep spike count core1" [p04_input 30] [dict get $expected1 spike_count]
            p04_expect "$name t$timestep packet count core1" [p04_input 31] [dict get $expected1 packet_count]
            set cycles [p04_input 15]
            if {$cycles <= 0} { error "P04 $name t$timestep reported zero physical cycles" }

            foreach core {0 1} expected [list $expected0 $expected1] image [list $core0_image $core1_image] {
                set compartment_count [dict get $image compartment_count]
                set states [dict get $expected states]
                set traces [dict get $expected traces]
                for {set i 0} {$i < $compartment_count} {incr i} {
                    p04_expect "$name t$timestep core$core state($i)" \
                        [p04_host_read $core 1 $i] [p04_parse_value [lindex $states $i]]
                    p04_expect "$name t$timestep core$core trace($i)" \
                        [p04_host_read $core 7 $i] [p04_parse_value [lindex $traces $i]]
                }

                set packet_count [dict get $expected packet_count]
                set actual_packets {}
                for {set i 0} {$i < $packet_count} {incr i} {
                    lappend actual_packets [p04_host_read $core 8 $i]
                }
                set expected_packets {}
                foreach word [dict get $expected packets] {
                    lappend expected_packets [p04_parse_value $word]
                }
                p04_expect_list_unordered "$name t$timestep core$core packets" $actual_packets $expected_packets
            }

            set actual_events0 {}
            for {set i 0} {$i < [llength $next_events0]} {incr i} {
                lappend actual_events0 [p04_host_read 0 6 $i]
            }
            set actual_events1 {}
            for {set i 0} {$i < [llength $next_events1]} {incr i} {
                lappend actual_events1 [p04_host_read 1 6 $i]
            }
            p04_expect_list_unordered "$name t$timestep next events core0" $actual_events0 $next_events0
            p04_expect_list_unordered "$name t$timestep next events core1" $actual_events1 $next_events1

            puts $result "scenario=$name reverse=$reverse tick=$tick_index timestep=$timestep cycles=$cycles local=$expected_local remote=$expected_remote"
            puts "P04 physical tick PASS: scenario=$name reverse=$reverse timestep=$timestep cycles=$cycles local=$expected_local remote=$expected_remote"
            incr tick_index
        }
    }
}

puts $result "result=PASS"
close $result
puts "P04 physical Python/FPGA conformance PASS: result=$result_file"
close_hw_manager
