# P08.4.3b representative MNIST physical dispatch on the accepted host-paged shell.
if {$argc != 5} {
    error "usage: p08_4_3b_physical_conformance.tcl <bit> <ltx> <vectors.tcl> <result.txt> <hw_server_url>"
}

set bit_file [file normalize [lindex $argv 0]]
set ltx_file [file normalize [lindex $argv 1]]
set vector_file [file normalize [lindex $argv 2]]
set result_file [file normalize [lindex $argv 3]]
set hw_server_url [lindex $argv 4]
foreach path [list $bit_file $ltx_file $vector_file] {
    if {![file exists $path]} { error "P08.4.3b physical input missing: $path" }
}
source $vector_file

proc p08b_parse_value {raw} {
    set text [string trim $raw]
    regsub -all {_} $text "" text
    if {[regexp -nocase {^0x([0-9a-f]+)$} $text -> digits]} { return [expr "0x$digits"] }
    if {[regexp -nocase {^[0-9a-f]+$} $text]} { return [expr "0x$text"] }
    error "P08.4.3b cannot parse VIO value '$raw'"
}

proc p08b_probe {direction port} {
    global P08B_VIO
    set wanted [string tolower $direction]
    foreach probe [get_hw_probes -of_objects $P08B_VIO] {
        if {[string tolower [get_property TYPE $probe]] eq $wanted && [get_property PROBE_PORT $probe] == $port} {
            return $probe
        }
    }
    error "P08.4.3b VIO probe not found: direction=$direction port=$port"
}

proc p08b_format_output_value {probe value} {
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
        error "P08.4.3b cannot format VIO output value '$value'"
    }
    if {$numeric < 0 || $numeric >= (1 << $bits)} {
        error "P08.4.3b VIO output value out of range: value=$value bits=$bits"
    }
    return "[string repeat 0 [expr {$chars - [string length $digits]}]]$digits"
}

proc p08b_commit {settings} {
    global P08B_VIO
    foreach {port value} $settings {
        set probe [p08b_probe vio_output $port]
        set_property OUTPUT_VALUE [p08b_format_output_value $probe $value] $probe
    }
    commit_hw_vio $P08B_VIO
}

proc p08b_input {port} {
    global P08B_VIO
    refresh_hw_vio $P08B_VIO
    return [p08b_parse_value [get_property INPUT_VALUE [p08b_probe vio_input $port]]]
}

proc p08b_wait_input {port expected timeout_ms label} {
    set deadline [expr {[clock milliseconds] + $timeout_ms}]
    set actual -1
    while {[clock milliseconds] <= $deadline} {
        set actual [p08b_input $port]
        if {$actual == $expected} { return $actual }
        after 10
    }
    error "P08.4.3b timeout waiting for $label: expected=$expected actual=$actual"
}

proc p08b_expect {label actual expected} {
    if {$actual != $expected} {
        error "P08.4.3b mismatch $label: actual=0x[format %X $actual] expected=0x[format %X $expected]"
    }
}

proc p08b_host_write {slot bank addr value} {
    p08b_commit [list 6 0 7 1 8 $slot 9 $bank 10 $addr 11 $value]
    p08b_commit [list 6 1]
    p08b_wait_input 21 1 2000 "host write ack slot=$slot bank=$bank addr=$addr"
    set err [p08b_input 23]
    p08b_commit [list 6 0]
    if {$err != 0} { error "P08.4.3b host write failed: slot=$slot bank=$bank addr=$addr" }
}

proc p08b_host_read {slot bank addr} {
    p08b_commit [list 6 0 7 0 8 $slot 9 $bank 10 $addr 11 0]
    p08b_commit [list 6 1]
    p08b_wait_input 21 1 2000 "host read ack slot=$slot bank=$bank addr=$addr"
    set valid [p08b_input 22]
    set err [p08b_input 23]
    set value [p08b_input 24]
    p08b_commit [list 6 0]
    if {$err != 0 || $valid != 1} {
        error "P08.4.3b host read failed: slot=$slot bank=$bank addr=$addr valid=$valid error=$err"
    }
    return $value
}

proc p08b_load_pairs {slot bank entries} {
    foreach entry $entries {
        lassign $entry addr value
        p08b_host_write $slot $bank $addr $value
    }
}

proc p08b_clear_runtime_banks {slot compartment_count} {
    for {set addr 0} {$addr < $compartment_count} {incr addr} {
        p08b_host_write $slot 7 $addr 0
    }
    for {set addr 0} {$addr < 32} {incr addr} {
        p08b_host_write $slot 8 $addr 0
    }
}

proc p08b_signed24 {value} {
    set value [expr {$value & 0xFFFFFF}]
    if {$value & 0x800000} { return [expr {$value - 0x1000000}] }
    return $value
}

open_hw_manager
connect_hw_server -url $hw_server_url
set targets [get_hw_targets]
if {[llength $targets] == 0} { error "P08.4.3b no hardware targets found" }
current_hw_target [lindex $targets 0]
open_hw_target

set P08B_DEVICE ""
foreach device [get_hw_devices] {
    set name [get_property NAME $device]
    if {[regexp -nocase {(xczu|xck26)} $name]} {
        set P08B_DEVICE $device
        break
    }
}
if {$P08B_DEVICE eq ""} { error "P08.4.3b could not identify the K26 device" }
current_hw_device $P08B_DEVICE
refresh_hw_device -update_hw_probes false $P08B_DEVICE
set_property PROGRAM.FILE $bit_file $P08B_DEVICE
if {[lsearch -exact [list_property $P08B_DEVICE] PROBES.FILE] >= 0} { set_property PROBES.FILE $ltx_file $P08B_DEVICE }
if {[lsearch -exact [list_property $P08B_DEVICE] FULL_PROBES.FILE] >= 0} { set_property FULL_PROBES.FILE $ltx_file $P08B_DEVICE }
program_hw_devices $P08B_DEVICE
refresh_hw_device $P08B_DEVICE

set P08B_VIO ""
foreach vio [get_hw_vios -of_objects $P08B_DEVICE] {
    set cell ""
    catch {set cell [get_property CELL_NAME $vio]}
    if {[string match "*vio_p08*" $cell]} {
        set P08B_VIO $vio
        break
    }
}
if {$P08B_VIO eq ""} { error "P08.4.3b could not find vio_p08" }
foreach probe [get_hw_probes -of_objects $P08B_VIO] {
    set type [string tolower [get_property TYPE $probe]]
    if {$type eq "vio_input"} { catch {set_property INPUT_VALUE_RADIX HEX $probe} }
    if {$type eq "vio_output"} { catch {set_property OUTPUT_VALUE_RADIX HEX $probe} }
}
reset_hw_vio_outputs $P08B_VIO
refresh_hw_vio -update_output_values $P08B_VIO

p08b_commit [list 1 1]
after 20
p08b_commit [list 1 0]
after 20
p08b_expect "resetn released" [p08b_input 28] 1
set heartbeat_before [p08b_input 25]
after 20
set heartbeat_after [p08b_input 25]
if {$heartbeat_before == $heartbeat_after} { error "P08.4.3b heartbeat did not advance" }
puts "PASS: P08.4.3b K26 reset/clock heartbeat $heartbeat_before->$heartbeat_after"

set slot $P08B_SLOT
set target $P08B_TARGET_CONTEXT

p08b_host_write $slot 1 0 $P08B_DECOY_MARKER
p08b_expect "decoy marker readback" [p08b_host_read $slot 1 0] [p08b_parse_value $P08B_DECOY_MARKER]
puts "PASS: P08.4.3b decoy residency logical_core=$P08B_DECOY_LOGICAL_CORE slot=$slot marker_verified=true"

p08b_load_pairs $slot 0 [dict get $target config_seeds]
p08b_load_pairs $slot 1 [dict get $target state_seeds]
p08b_load_pairs $slot 2 [dict get $target axon_seeds]
p08b_load_pairs $slot 3 [dict get $target synapse_seeds]
p08b_load_pairs $slot 4 [dict get $target route_desc_seeds]
p08b_load_pairs $slot 5 [dict get $target route_seeds]
p08b_clear_runtime_banks $slot [dict get $target compartment_count]

set event_bank [expr {$P08B_EVENT_READ_BANK ? 9 : 6}]
set event_addr 0
foreach axon $P08B_INPUT_EVENTS {
    p08b_host_write $slot $event_bank $event_addr $axon
    incr event_addr
}

set first_target_state [lindex [dict get $target state_seeds] 0]
lassign $first_target_state first_addr first_word
p08b_expect "target state replacement readback" [p08b_host_read $slot 1 $first_addr] [p08b_parse_value $first_word]
puts "PASS: P08.4.3b page replacement slot=$slot evicted_logical_core=$P08B_DECOY_LOGICAL_CORE loaded_logical_core=$P08B_TARGET_LOGICAL_CORE"

set dispatch_before [p08b_input 8]
p08b_commit [list 2 $slot 3 $P08B_METADATA 4 $P08B_TIMESTEP 5 $P08B_EVENT_READ_BANK 0 0]
p08b_commit [list 0 1]
after 1
p08b_commit [list 0 0]
p08b_wait_input 8 [expr {$dispatch_before + 1}] 30000 "completed physical MNIST dispatch"

p08b_expect "active resident slot" [p08b_input 3] $slot
p08b_expect "active logical core" [p08b_input 4] $P08B_TARGET_LOGICAL_CORE
p08b_expect "event read bank" [p08b_input 5] $P08B_EVENT_READ_BANK
p08b_expect "latched HLS status" [p08b_input 7] 0
p08b_expect "raw HLS status" [p08b_input 19] 0
foreach port {11 12 13 26 27} {
    p08b_expect "hardware error port $port" [p08b_input $port] 0
}
p08b_expect "spike count" [p08b_input 17] $P08B_EXPECTED_SPIKE_COUNT
p08b_expect "latched packet count" [p08b_input 6] [llength $P08B_EXPECTED_PACKETS]
p08b_expect "raw packet count" [p08b_input 18] [llength $P08B_EXPECTED_PACKETS]
set dispatch_cycles [p08b_input 10]
if {$dispatch_cycles <= 0} { error "P08.4.3b dispatch reported zero cycles" }
puts "PASS: P08.4.3b physical dispatch logical_core=$P08B_TARGET_LOGICAL_CORE timestep=$P08B_TIMESTEP cycles=$dispatch_cycles spikes=$P08B_EXPECTED_SPIKE_COUNT packets=[llength $P08B_EXPECTED_PACKETS]"

set state_index 0
foreach expected $P08B_EXPECTED_STATES {
    p08b_expect "state($state_index)" [p08b_host_read $slot 1 $state_index] [p08b_parse_value $expected]
    incr state_index
}
set trace_index 0
foreach expected $P08B_EXPECTED_TRACES {
    p08b_expect "trace($trace_index)" [p08b_host_read $slot 7 $trace_index] [p08b_parse_value $expected]
    incr trace_index
}
puts "PASS: P08.4.3b exact state/trace compartments=$state_index"

set actual_packets {}
for {set addr 0} {$addr < [llength $P08B_EXPECTED_PACKETS]} {incr addr} {
    lappend actual_packets [p08b_host_read $slot 8 $addr]
}
set expected_packets {}
foreach word $P08B_EXPECTED_PACKETS { lappend expected_packets [p08b_parse_value $word] }
if {[lsort -integer $actual_packets] ne [lsort -integer $expected_packets]} {
    error "P08.4.3b packet image mismatch"
}
puts "PASS: P08.4.3b exact packet image count=[llength $actual_packets]"

set actual_evidence {}
foreach compartment $P08B_EVIDENCE_COMPARTMENTS {
    set state [p08b_host_read $slot 1 $compartment]
    lappend actual_evidence [p08b_signed24 [expr {$state >> 24}]]
}
if {$actual_evidence ne $P08B_EXPECTED_EVIDENCE} {
    error "P08.4.3b output evidence mismatch: actual=$actual_evidence expected=$P08B_EXPECTED_EVIDENCE"
}
puts "PASS: P08.4.3b physical MNIST evidence=$actual_evidence exact_match=true"

set result [open $result_file w]
puts $result "schema=p08-4-3b-physical-mnist-conformance-v1"
puts $result "device=[get_property NAME $P08B_DEVICE]"
puts $result "compiled_fingerprint=$P08B_COMPILED_FINGERPRINT"
puts $result "test_index=$P08B_TEST_INDEX"
puts $result "label=$P08B_LABEL"
puts $result "timestep=$P08B_TIMESTEP"
puts $result "resident_slot=$slot"
puts $result "evicted_logical_core=$P08B_DECOY_LOGICAL_CORE"
puts $result "loaded_logical_core=$P08B_TARGET_LOGICAL_CORE"
puts $result "dispatch_cycles=$dispatch_cycles"
puts $result "spike_count=$P08B_EXPECTED_SPIKE_COUNT"
puts $result "packet_count=[llength $P08B_EXPECTED_PACKETS]"
puts $result "evidence=$actual_evidence"
puts $result "state_trace_exact_match=1"
puts $result "packet_exact_match=1"
puts $result "evidence_exact_match=1"
puts $result "model_or_conversion_selection_after_test=0"
puts $result "result=PASS"
close $result

puts "PASS: P08.4.3b test-use boundary official_test_used_for_physical_conformance=true model_or_conversion_selection_after_test=false"
puts "P08.4.3b physical MNIST conformance completed successfully."
