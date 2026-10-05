# P05 one-engine / three-context physical conformance over Hardware Manager + VIO.
if {$argc != 5} {
    error "usage: p05_physical_conformance.tcl <bit> <ltx> <vectors.tcl> <result.txt> <hw_server_url>"
}

set bit_file [file normalize [lindex $argv 0]]
set ltx_file [file normalize [lindex $argv 1]]
set vector_file [file normalize [lindex $argv 2]]
set result_file [file normalize [lindex $argv 3]]
set hw_server_url [lindex $argv 4]
foreach path [list $bit_file $ltx_file $vector_file] {
    if {![file exists $path]} { error "P05 physical input missing: $path" }
}
source $vector_file

proc p05_parse_value {raw} {
    set text [string trim $raw]
    regsub -all {_} $text "" text
    if {[regexp -nocase {^0x([0-9a-f]+)$} $text -> digits]} {
        return [expr "0x$digits"]
    }
    if {[regexp -nocase {^[0-9a-f]+$} $text]} {
        return [expr "0x$text"]
    }
    error "P05 cannot parse VIO value '$raw'"
}

proc p05_probe {direction port} {
    global P05_VIO
    set wanted [string tolower $direction]
    foreach probe [get_hw_probes -of_objects $P05_VIO] {
        set type [string tolower [get_property TYPE $probe]]
        set probe_port [get_property PROBE_PORT $probe]
        if {$type eq $wanted && $probe_port == $port} { return $probe }
    }
    puts "P05 available VIO probes:"
    foreach probe [get_hw_probes -of_objects $P05_VIO] {
        puts "  name=[get_property NAME $probe] type=[get_property TYPE $probe] port=[get_property PROBE_PORT $probe] bits=[get_property PROBE_PORT_BIT_COUNT $probe]"
    }
    error "P05 VIO probe not found: direction=$direction port=$port"
}

proc p05_format_output_value {probe value} {
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
        error "P05 cannot format VIO output value '$value'"
    }
    if {$numeric < 0 || $numeric >= (1 << $bits)} {
        error "P05 VIO output value out of range: value=$value bits=$bits port=[get_property PROBE_PORT $probe]"
    }
    if {[string length $digits] > $chars} {
        error "P05 VIO output value too wide: value=$value bits=$bits"
    }
    return "[string repeat 0 [expr {$chars - [string length $digits]}]]$digits"
}

proc p05_commit {settings} {
    global P05_VIO
    foreach {port value} $settings {
        set probe [p05_probe vio_output $port]
        set_property OUTPUT_VALUE [p05_format_output_value $probe $value] $probe
    }
    commit_hw_vio $P05_VIO
}

proc p05_refresh {} {
    global P05_VIO
    refresh_hw_vio $P05_VIO
}

proc p05_input {port} {
    p05_refresh
    return [p05_parse_value [get_property INPUT_VALUE [p05_probe vio_input $port]]]
}

proc p05_wait_input {port expected timeout_ms label} {
    set deadline [expr {[clock milliseconds] + $timeout_ms}]
    while {[clock milliseconds] <= $deadline} {
        set actual [p05_input $port]
        if {$actual == $expected} { return $actual }
        after 10
    }
    error "P05 timeout waiting for $label: expected=$expected actual=[p05_input $port]"
}

proc p05_expect {label actual expected} {
    if {$actual != $expected} {
        error "P05 mismatch $label: actual=0x[format %X $actual] expected=0x[format %X $expected]"
    }
}

proc p05_expect_list_unordered {label actual expected} {
    set actual_sorted [lsort -integer $actual]
    set expected_sorted [lsort -integer $expected]
    if {$actual_sorted ne $expected_sorted} {
        error "P05 mismatch $label: actual=$actual_sorted expected=$expected_sorted"
    }
}

proc p05_field {value offset width} {
    return [expr {($value >> $offset) & ((1 << $width) - 1)}]
}

# VIO outputs: 6=req 7=write 8=context slot 9=bank 10=addr 11=wdata.
# VIO inputs: 29=ack 30=rvalid 31=error 32=rdata.
proc p05_host_write {slot bank addr value} {
    p05_commit [list 6 0x0 7 0x1 8 $slot 9 $bank 10 $addr 11 $value]
    p05_commit [list 6 0x1]
    p05_wait_input 29 1 2000 "host write ack slot=$slot bank=$bank addr=$addr"
    set err [p05_input 31]
    p05_commit [list 6 0x0]
    if {$err != 0} { error "P05 host write failed: slot=$slot bank=$bank addr=$addr" }
}

proc p05_host_read {slot bank addr} {
    p05_commit [list 6 0x0 7 0x0 8 $slot 9 $bank 10 $addr 11 0x0]
    p05_commit [list 6 0x1]
    p05_wait_input 29 1 2000 "host read ack slot=$slot bank=$bank addr=$addr"
    set valid [p05_input 30]
    set err [p05_input 31]
    set value [p05_input 32]
    p05_commit [list 6 0x0]
    if {$err != 0 || $valid != 1} {
        error "P05 host read failed: slot=$slot bank=$bank addr=$addr valid=$valid error=$err"
    }
    return $value
}

proc p05_host_expect_error {slot bank addr} {
    p05_commit [list 6 0x0 7 0x0 8 $slot 9 $bank 10 $addr 11 0x0]
    p05_commit [list 6 0x1]
    p05_wait_input 29 1 2000 "expected host error slot=$slot bank=$bank addr=$addr"
    set err [p05_input 31]
    p05_commit [list 6 0x0]
    if {$err != 1} {
        error "P05 expected host rejection: slot=$slot bank=$bank addr=$addr"
    }
}

proc p05_load_seeds {slot bank seeds} {
    foreach seed $seeds {
        lassign $seed addr value
        p05_host_write $slot $bank $addr $value
    }
}

proc p05_clear_small_runtime_region {slot} {
    # The directed corpus uses one compartment and only a handful of events.
    # Clear the visible low runtime region so repeated scenarios cannot inherit
    # stale sparse route descriptors or event records.
    p05_host_write $slot 4 0 0x0
    for {set addr 0} {$addr < 8} {incr addr} {
        p05_host_write $slot 6 $addr 0x0
        p05_host_write $slot 9 $addr 0x0
    }
}

proc p05_load_context_image {context} {
    set slot [dict get $context slot]
    p05_clear_small_runtime_region $slot
    p05_load_seeds $slot 0 [dict get $context config_seeds]
    p05_load_seeds $slot 1 [dict get $context state_seeds]
    p05_load_seeds $slot 2 [dict get $context axon_seeds]
    p05_load_seeds $slot 3 [dict get $context synapse_seeds]
    p05_load_seeds $slot 4 [dict get $context route_desc_seeds]
    p05_load_seeds $slot 5 [dict get $context route_seeds]
}

proc p05_load_initial_events {slot events} {
    set addr 0
    foreach axon $events {
        p05_host_write $slot 6 $addr $axon
        incr addr
    }
}

proc p05_check_error_inputs {label} {
    # Controller sticky errors are inputs 13..18.
    for {set port 13} {$port <= 18} {incr port} {
        set value [p05_input $port]
        if {$value != 0} { error "P05 $label controller error port=$port value=$value" }
    }
    # Shared memory HLS/integration guards are inputs 34 and 35.
    p05_expect "$label hls address error" [p05_input 34] 0
    p05_expect "$label integration address error" [p05_input 35] 0
    # The currently exposed HLS status belongs to the final serviced context.
    p05_expect "$label final HLS status" [p05_input 27] 0
}

open_hw_manager
connect_hw_server -url $hw_server_url
set targets [get_hw_targets]
if {[llength $targets] == 0} { error "P05 no hardware targets found" }
current_hw_target [lindex $targets 0]
open_hw_target

set P05_DEVICE ""
foreach device [get_hw_devices] {
    set name [get_property NAME $device]
    if {[regexp -nocase {(xczu|xck26)} $name]} {
        set P05_DEVICE $device
        break
    }
}
if {$P05_DEVICE eq ""} {
    set devices [get_hw_devices]
    if {[llength $devices] == 1} {
        set P05_DEVICE [lindex $devices 0]
    } else {
        puts "P05 hardware devices: $devices"
        error "P05 could not identify the K26/UltraScale+ hardware device"
    }
}
current_hw_device $P05_DEVICE
refresh_hw_device -update_hw_probes false $P05_DEVICE
set_property PROGRAM.FILE $bit_file $P05_DEVICE
if {[lsearch -exact [list_property $P05_DEVICE] PROBES.FILE] >= 0} {
    set_property PROBES.FILE $ltx_file $P05_DEVICE
}
if {[lsearch -exact [list_property $P05_DEVICE] FULL_PROBES.FILE] >= 0} {
    set_property FULL_PROBES.FILE $ltx_file $P05_DEVICE
}
program_hw_devices $P05_DEVICE
refresh_hw_device $P05_DEVICE

set P05_VIO ""
set vios [get_hw_vios -of_objects $P05_DEVICE]
foreach vio $vios {
    set cell ""
    catch {set cell [get_property CELL_NAME $vio]}
    if {[string match "*vio_p05*" $cell]} {
        set P05_VIO $vio
        break
    }
}
if {$P05_VIO eq "" && [llength $vios] == 1} { set P05_VIO [lindex $vios 0] }
if {$P05_VIO eq ""} {
    puts "P05 discovered VIO cores: $vios"
    error "P05 VIO core was not found after programming"
}
puts "P05 hardware device: [get_property NAME $P05_DEVICE]"
puts "P05 VIO core: $P05_VIO"

foreach probe [get_hw_probes -of_objects $P05_VIO] {
    set type [string tolower [get_property TYPE $probe]]
    if {$type eq "vio_input"} { catch {set_property INPUT_VALUE_RADIX HEX $probe} }
    if {$type eq "vio_output"} { catch {set_property OUTPUT_VALUE_RADIX HEX $probe} }
}
reset_hw_vio_outputs $P05_VIO
refresh_hw_vio -update_output_values $P05_VIO

# Reuse the P04-proven source-controlled active-high reset command.
p05_commit [list 2 0x1]
after 20
p05_commit [list 2 0x0]
after 20
set heartbeat_before [p05_input 33]
after 20
set heartbeat_after [p05_input 33]
if {$heartbeat_before == $heartbeat_after} {
    error "P05 control fabric did not leave reset: heartbeat remained $heartbeat_after"
}
puts "P05 reset release verified: heartbeat $heartbeat_before -> $heartbeat_after"

# Exercise the final address of every full logical bank in every retained
# context. This is deliberately different from P04: these are full P03 logical
# depths physically retained for all three contexts.
set bank_preflight [list \
    [list 0 1023 0x0123456789ABCDEFFEDCBA9876543210] \
    [list 1 1023 0x0123456789ABCDEF] \
    [list 2 4095 0x1122334455667788] \
    [list 3 32767 0x8877665544332211] \
    [list 4 1023 0x89ABCDEF] \
    [list 5 4095 0x13579BDF] \
    [list 6 4095 0x2468ACE0] \
    [list 7 1023 0x00112233445566778899AABBCCDDEEFFFFEEDDCCBBAA99887766554433221100] \
    [list 8 4095 0x0F1E2D3C4B5A6978] \
    [list 9 4095 0x55AA55AA]]
foreach slot {0 1 2} {
    foreach item $bank_preflight {
        lassign $item bank addr value
        p05_host_write $slot $bank $addr $value
        p05_expect "slot $slot bank $bank preflight" \
            [p05_host_read $slot $bank $addr] [p05_parse_value $value]
    }
    p05_host_expect_error $slot 0 1024
}
# Context slot 3 is representable by the host selector but is not retained.
p05_host_expect_error 3 0 0
puts "P05 full-context memory preflight passed for all three retained contexts"

set result [open $result_file w]
puts $result "schema=p05-physical-conformance-v1"
puts $result "device=[get_property NAME $P05_DEVICE]"
puts $result "logical_contexts=$P05_CONTEXTS"
puts $result "physical_engines=$P05_PHYSICAL_ENGINES"
puts $result "virtualization_ratio=3.0"
puts $result "full_logical_context_depths=1"
puts $result "double_buffered_events=1"
puts $result "logical_capacity_changed=0"
puts $result "scenarios=[llength $P05_SCENARIOS]"

foreach scenario $P05_SCENARIOS {
    set name [dict get $scenario name]
    set contexts [dict get $scenario contexts]
    set metadata [dict get $scenario context_metadata]
    set initial_events0 [dict get $scenario initial_events0]
    set initial_events1 [dict get $scenario initial_events1]
    set initial_events2 [dict get $scenario initial_events2]
    set ticks [dict get $scenario ticks]

    foreach reverse {0 1} {
        foreach context $contexts { p05_load_context_image $context }
        p05_load_initial_events 0 $initial_events0
        p05_load_initial_events 1 $initial_events1
        p05_load_initial_events 2 $initial_events2

        # out3=service_reverse, out4=epoch_timestep, out5=three packed metadata records.
        p05_commit [list 3 $reverse 4 0 5 $metadata 0 0x0 1 0x0]
        p05_commit [list 0 0x1]
        after 1
        p05_commit [list 0 0x0]
        p05_wait_input 3 1 2000 "epoch loaded scenario=$name reverse=$reverse"
        p05_expect "$name initial timestep" [p05_input 4] 0
        p05_expect "$name initial read bank" [p05_input 21] 0

        set current_counts [p05_input 5]
        p05_expect "$name initial events slot0" [p05_field $current_counts 0 13] [llength $initial_events0]
        p05_expect "$name initial events slot1" [p05_field $current_counts 13 13] [llength $initial_events1]
        p05_expect "$name initial events slot2" [p05_field $current_counts 26 13] [llength $initial_events2]

        set tick_index 0
        foreach tick $ticks {
            set timestep [dict get $tick timestep]
            set expected_contexts [dict get $tick contexts]
            set next_events0 [dict get $tick next_events0]
            set next_events1 [dict get $tick next_events1]
            set next_events2 [dict get $tick next_events2]
            set expected_local [dict get $tick local_packets]
            set expected_remote [dict get $tick remote_packets]

            set before_runs [p05_input 11]
            set target_runs [expr {$before_runs + 1}]
            p05_commit [list 1 0x1]
            after 1
            p05_commit [list 1 0x0]
            p05_wait_input 11 $target_runs 15000 "completed tick scenario=$name reverse=$reverse timestep=$timestep"

            p05_check_error_inputs "scenario=$name reverse=$reverse timestep=$timestep"
            p05_expect "$name t$timestep start blocked" [p05_input 2] 0
            p05_expect "$name t$timestep current timestep" [p05_input 4] [expr {$timestep + 1}]
            p05_expect "$name t$timestep barrier completed" [p05_input 7] 7
            p05_expect "$name t$timestep local packets" [p05_input 9] $expected_local
            p05_expect "$name t$timestep remote packets" [p05_input 10] $expected_remote

            set counts [p05_input 5]
            p05_expect "$name t$timestep current events slot0" [p05_field $counts 0 13] [llength $next_events0]
            p05_expect "$name t$timestep current events slot1" [p05_field $counts 13 13] [llength $next_events1]
            p05_expect "$name t$timestep current events slot2" [p05_field $counts 26 13] [llength $next_events2]

            set expected_bank [expr {($timestep + 1) & 1}]
            p05_expect "$name t$timestep event read bank" [p05_input 21] $expected_bank
            set event_host_bank [expr {$expected_bank ? 9 : 6}]

            set cycles [p05_input 12]
            if {$cycles <= 0} { error "P05 $name t$timestep reported zero physical cycles" }

            # The final serviced context is a useful physical confirmation that
            # service_reverse really selected opposite legal schedules.
            set final_slot [expr {$reverse ? 0 : 2}]
            p05_expect "$name t$timestep final context slot" [p05_input 19] $final_slot
            set final_expected [lindex $expected_contexts $final_slot]
            p05_expect "$name t$timestep final logical core" [p05_input 20] [dict get $final_expected logical_core_id]
            p05_expect "$name t$timestep final spike count" [p05_input 25] [dict get $final_expected spike_count]
            p05_expect "$name t$timestep final packet count" [p05_input 26] [dict get $final_expected packet_count]

            foreach expected $expected_contexts context $contexts {
                set slot [dict get $expected slot]
                set logical_id [dict get $expected logical_core_id]
                p05_expect "$name t$timestep context slot identity" $slot [dict get $context slot]
                p05_expect "$name t$timestep logical identity" $logical_id [dict get $context logical_core_id]

                set compartment_count [dict get $context compartment_count]
                set states [dict get $expected states]
                set traces [dict get $expected traces]
                for {set i 0} {$i < $compartment_count} {incr i} {
                    p05_expect "$name t$timestep logical$logical_id state($i)" \
                        [p05_host_read $slot 1 $i] [p05_parse_value [lindex $states $i]]
                    p05_expect "$name t$timestep logical$logical_id trace($i)" \
                        [p05_host_read $slot 7 $i] [p05_parse_value [lindex $traces $i]]
                }

                set packet_count [dict get $expected packet_count]
                set actual_packets {}
                for {set i 0} {$i < $packet_count} {incr i} {
                    lappend actual_packets [p05_host_read $slot 8 $i]
                }
                set expected_packets {}
                foreach word [dict get $expected packets] {
                    lappend expected_packets [p05_parse_value $word]
                }
                p05_expect_list_unordered "$name t$timestep logical$logical_id packets" $actual_packets $expected_packets
            }

            foreach slot {0 1 2} expected_events [list $next_events0 $next_events1 $next_events2] {
                set actual_events {}
                for {set i 0} {$i < [llength $expected_events]} {incr i} {
                    lappend actual_events [p05_host_read $slot $event_host_bank $i]
                }
                p05_expect_list_unordered "$name t$timestep slot$slot next events" $actual_events $expected_events
            }

            puts $result "scenario=$name reverse=$reverse tick=$tick_index timestep=$timestep cycles=$cycles local=$expected_local remote=$expected_remote"
            puts "P05 physical tick PASS: scenario=$name reverse=$reverse timestep=$timestep cycles=$cycles local=$expected_local remote=$expected_remote"
            incr tick_index
        }
    }
}

puts $result "result=PASS"
close $result
puts "P05 physical virtualization conformance PASS: result=$result_file"
close_hw_manager
