# P08.4.3b representative host-paged physical conformance on the routed P08 shell.
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

proc p08_parse_value {raw} {
    set text [string trim $raw]
    regsub -all {_} $text "" text
    if {[regexp -nocase {^0x([0-9a-f]+)$} $text -> digits]} {
        return [expr "0x$digits"]
    }
    if {[regexp -nocase {^[0-9a-f]+$} $text]} {
        return [expr "0x$text"]
    }
    error "P08.4.3b cannot parse VIO value '$raw'"
}

proc p08_probe {direction port} {
    global P08_VIO
    set wanted [string tolower $direction]
    foreach probe [get_hw_probes -of_objects $P08_VIO] {
        if {[string tolower [get_property TYPE $probe]] eq $wanted &&
            [get_property PROBE_PORT $probe] == $port} {
            return $probe
        }
    }
    error "P08.4.3b VIO probe not found: direction=$direction port=$port"
}

proc p08_format_output_value {probe value} {
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

proc p08_commit {settings} {
    global P08_VIO
    foreach {port value} $settings {
        set probe [p08_probe vio_output $port]
        set_property OUTPUT_VALUE [p08_format_output_value $probe $value] $probe
    }
    commit_hw_vio $P08_VIO
}

proc p08_input {port} {
    global P08_VIO
    refresh_hw_vio $P08_VIO
    return [p08_parse_value [get_property INPUT_VALUE [p08_probe vio_input $port]]]
}

proc p08_wait_input {port expected timeout_ms label} {
    set deadline [expr {[clock milliseconds] + $timeout_ms}]
    while {[clock milliseconds] <= $deadline} {
        set actual [p08_input $port]
        if {$actual == $expected} { return $actual }
        after 10
    }
    error "P08.4.3b timeout waiting for $label: expected=$expected actual=[p08_input $port]"
}

proc p08_expect {label actual expected} {
    if {$actual != $expected} {
        error "P08.4.3b mismatch $label: actual=0x[format %X $actual] expected=0x[format %X $expected]"
    }
}

proc p08_expect_list_unordered {label actual expected} {
    set actual_sorted [lsort -integer $actual]
    set expected_sorted [lsort -integer $expected]
    if {$actual_sorted ne $expected_sorted} {
        error "P08.4.3b mismatch $label: actual=$actual_sorted expected=$expected_sorted"
    }
}

proc p08_signed {value bits} {
    set mask [expr {(1 << $bits) - 1}]
    set raw [expr {$value & $mask}]
    set sign [expr {1 << ($bits - 1)}]
    if {$raw & $sign} {
        return [expr {$raw - (1 << $bits)}]
    }
    return $raw
}

proc p08_find_context {wanted} {
    global P08_CONTEXTS
    foreach context $P08_CONTEXTS {
        if {[dict get $context name] eq $wanted} { return $context }
    }
    error "P08.4.3b context '$wanted' not found in generated corpus"
}

# P08 VIO host path: outputs 6=req, 7=write, 8=slot, 9=bank,
# 10=address, 11=write data; inputs 20..24 return host status/data.
proc p08_host_write {slot bank addr value} {
    p08_commit [list 6 0 7 1 8 $slot 9 $bank 10 $addr 11 $value]
    p08_commit [list 6 1]
    p08_wait_input 21 1 5000 "host write ack slot=$slot bank=$bank addr=$addr"
    set err [p08_input 23]
    p08_commit [list 6 0]
    if {$err != 0} { error "P08.4.3b host write failed: slot=$slot bank=$bank addr=$addr" }
}

proc p08_host_read {slot bank addr} {
    p08_commit [list 6 0 7 0 8 $slot 9 $bank 10 $addr 11 0]
    p08_commit [list 6 1]
    p08_wait_input 21 1 5000 "host read ack slot=$slot bank=$bank addr=$addr"
    set valid [p08_input 22]
    set err [p08_input 23]
    set value [p08_input 24]
    p08_commit [list 6 0]
    if {$err != 0 || $valid != 1} {
        error "P08.4.3b host read failed: slot=$slot bank=$bank addr=$addr valid=$valid error=$err"
    }
    return $value
}

proc p08_load_pairs {slot bank seeds} {
    foreach seed $seeds {
        lassign $seed addr value
        p08_host_write $slot $bank $addr $value
    }
}

proc p08_load_context {context} {
    set slot [dict get $context slot]
    set compartment_count [dict get $context compartment_count]

    # Dense static/state tables overwrite all addresses used by the new context.
    p08_load_pairs $slot 0 [dict get $context config_seeds]
    p08_load_pairs $slot 1 [dict get $context state_seeds]
    p08_load_pairs $slot 2 [dict get $context axon_seeds]
    p08_load_pairs $slot 3 [dict get $context synapse_seeds]

    # Route descriptors are sparse. Clear every live compartment first so an
    # evicted context cannot leave a stale route on a newly loaded compartment.
    for {set addr 0} {$addr < $compartment_count} {incr addr} {
        p08_host_write $slot 4 $addr 0
    }
    p08_load_pairs $slot 4 [dict get $context route_desc_seeds]
    p08_load_pairs $slot 5 [dict get $context route_seeds]

    # All representative dispatches use event bank 0. Only event_count entries
    # are consumed by HLS, so overwriting those entries is sufficient.
    set addr 0
    foreach axon [dict get $context events] {
        p08_host_write $slot 6 $addr $axon
        incr addr
    }

    # A few direct readbacks establish that the replacement reached the selected
    # physical slot before compute begins. Full correctness is checked after the
    # dispatch by exact state/trace/packet comparison.
    if {$compartment_count > 0} {
        set first_config [p08_parse_value [lindex [lindex [dict get $context config_seeds] 0] 1]]
        p08_expect "loaded first config" [p08_host_read $slot 0 0] $first_config
        set first_state [p08_parse_value [lindex [lindex [dict get $context state_seeds] 0] 1]]
        p08_expect "loaded first state" [p08_host_read $slot 1 0] $first_state
    }
}

proc p08_check_errors {label} {
    foreach port {11 12 13 23 26 27} {
        set value [p08_input $port]
        if {$value != 0} { error "P08.4.3b $label error probe=$port value=$value" }
    }
    p08_expect "$label controller status" [p08_input 7] 0
    p08_expect "$label HLS status" [p08_input 19] 0
}

proc p08_verify_context {context} {
    set name [dict get $context name]
    set slot [dict get $context slot]
    set logical_id [dict get $context logical_core_id]
    set compartment_count [dict get $context compartment_count]
    set expected_states [dict get $context expected_states]
    set expected_traces [dict get $context expected_traces]

    for {set i 0} {$i < $compartment_count} {incr i} {
        p08_expect "$name logical$logical_id state($i)" \
            [p08_host_read $slot 1 $i] \
            [p08_parse_value [lindex $expected_states $i]]
        p08_expect "$name logical$logical_id trace($i)" \
            [p08_host_read $slot 7 $i] \
            [p08_parse_value [lindex $expected_traces $i]]
    }

    set actual_packets {}
    for {set i 0} {$i < [dict get $context expected_packet_count]} {incr i} {
        lappend actual_packets [p08_host_read $slot 8 $i]
    }
    set expected_packets {}
    foreach word [dict get $context expected_packets] {
        lappend expected_packets [p08_parse_value $word]
    }
    p08_expect_list_unordered "$name logical$logical_id packets" $actual_packets $expected_packets
}

proc p08_read_evidence {context} {
    global P08_EVIDENCE_COMPARTMENTS
    set slot [dict get $context slot]
    set evidence {}
    foreach compartment $P08_EVIDENCE_COMPARTMENTS {
        set state_word [p08_host_read $slot 1 $compartment]
        set voltage_bits [expr {($state_word >> 24) & 0xFFFFFF}]
        lappend evidence [p08_signed $voltage_bits 24]
    }
    return $evidence
}

proc p08_argmax_lowest {values} {
    if {[llength $values] == 0} { error "P08.4.3b argmax received empty list" }
    set best_index 0
    set best_value [lindex $values 0]
    for {set i 1} {$i < [llength $values]} {incr i} {
        set value [lindex $values $i]
        if {$value > $best_value} {
            set best_value $value
            set best_index $i
        }
    }
    return $best_index
}

open_hw_manager
connect_hw_server -url $hw_server_url
set targets [get_hw_targets]
if {[llength $targets] == 0} { error "P08.4.3b no hardware targets found" }
current_hw_target [lindex $targets 0]
open_hw_target

set P08_DEVICE ""
foreach device [get_hw_devices] {
    set name [get_property NAME $device]
    if {[regexp -nocase {(xczu|xck26)} $name]} {
        set P08_DEVICE $device
        break
    }
}
if {$P08_DEVICE eq ""} { error "P08.4.3b could not identify the K26 device" }
current_hw_device $P08_DEVICE
refresh_hw_device -update_hw_probes false $P08_DEVICE
set_property PROGRAM.FILE $bit_file $P08_DEVICE
if {[lsearch -exact [list_property $P08_DEVICE] PROBES.FILE] >= 0} {
    set_property PROBES.FILE $ltx_file $P08_DEVICE
}
if {[lsearch -exact [list_property $P08_DEVICE] FULL_PROBES.FILE] >= 0} {
    set_property FULL_PROBES.FILE $ltx_file $P08_DEVICE
}
program_hw_devices $P08_DEVICE
refresh_hw_device $P08_DEVICE

set P08_VIO ""
set vios [get_hw_vios -of_objects $P08_DEVICE]
foreach vio $vios {
    set cell ""
    catch {set cell [get_property CELL_NAME $vio]}
    if {[string match "*vio_p08*" $cell]} {
        set P08_VIO $vio
        break
    }
}
if {$P08_VIO eq "" && [llength $vios] == 1} { set P08_VIO [lindex $vios 0] }
if {$P08_VIO eq ""} { error "P08.4.3b could not find the P08 VIO core" }
puts "P08.4.3b hardware device: [get_property NAME $P08_DEVICE]"
puts "P08.4.3b VIO core: $P08_VIO"

foreach probe [get_hw_probes -of_objects $P08_VIO] {
    set type [string tolower [get_property TYPE $probe]]
    if {$type eq "vio_input"} { catch {set_property INPUT_VALUE_RADIX HEX $probe} }
    if {$type eq "vio_output"} { catch {set_property OUTPUT_VALUE_RADIX HEX $probe} }
}
reset_hw_vio_outputs $P08_VIO
refresh_hw_vio -update_output_values $P08_VIO

# Explicit reset after programming, then verify both reset release and PL clock.
p08_commit [list 1 1]
after 20
p08_commit [list 1 0]
p08_wait_input 28 1 2000 "reset release"
set heartbeat_before [p08_input 25]
after 20
set heartbeat_after [p08_input 25]
if {$heartbeat_before == $heartbeat_after} {
    error "P08.4.3b control fabric heartbeat did not advance"
}
puts "P08.4.3b reset release verified: heartbeat $heartbeat_before -> $heartbeat_after"

set result [open $result_file w]
puts $result "schema=p08-4-3b-physical-conformance-v1"
puts $result "device=[get_property NAME $P08_DEVICE]"
puts $result "parameter_fingerprint=$P08_PARAMETER_FINGERPRINT"
puts $result "network_fingerprint=$P08_NETWORK_FINGERPRINT"
puts $result "compiled_fingerprint=$P08_COMPILED_FINGERPRINT"
puts $result "p08_4_2_manifest_fingerprint=$P08_P08_4_2_MANIFEST_FINGERPRINT"
puts $result "normalized_trace_fingerprint=$P08_NORMALIZED_TRACE_FINGERPRINT"
puts $result "test_index=$P08_TEST_INDEX"
puts $result "label=$P08_LABEL"
puts $result "timestep=$P08_TIMESTEP"
puts $result "physical_slot=$P08_RESIDENT_SLOT"
puts $result "resident_contexts=3"
puts $result "physical_engines=1"
puts $result "logical_cores=5"
puts $result "page_replacements=2"
puts $result "reload_exercised=1"
puts $result "official_test_used_for_physical_conformance=1"
puts $result "model_or_conversion_selection_after_test=0"

set previous_name ""
set dispatch_index 0
set final_evidence {}
set final_prediction -1
foreach context_name $P08_SEQUENCE {
    set context [p08_find_context $context_name]
    set slot [dict get $context slot]
    set logical_id [dict get $context logical_core_id]
    set timestep [dict get $context timestep]
    set metadata [dict get $context metadata]

    if {[p08_input 1] != 0 || [p08_input 20] != 0} {
        error "P08.4.3b shell was busy before loading context $context_name"
    }
    p08_load_context $context

    set target_dispatches [expr {[p08_input 8] + 1}]
    p08_commit [list 2 $slot 3 $metadata 4 $timestep 5 0 0 0]
    p08_commit [list 0 1]
    after 1
    p08_commit [list 0 0]
    p08_wait_input 8 $target_dispatches 20000 "dispatch completion $context_name"

    p08_check_errors "dispatch=$context_name"
    p08_expect "$context_name active slot" [p08_input 3] $slot
    p08_expect "$context_name logical identity" [p08_input 4] $logical_id
    p08_expect "$context_name event bank" [p08_input 5] 0
    p08_expect "$context_name packet count latched" [p08_input 6] [dict get $context expected_packet_count]
    p08_expect "$context_name HLS packet count" [p08_input 18] [dict get $context expected_packet_count]
    p08_expect "$context_name HLS spike count" [p08_input 17] [dict get $context expected_spike_count]
    set cycles [p08_input 10]
    if {$cycles <= 0} { error "P08.4.3b $context_name reported zero dispatch cycles" }

    p08_verify_context $context

    if {$context_name eq "output_core4_t99"} {
        set final_evidence [p08_read_evidence $context]
        if {$final_evidence ne $P08_EXPECTED_EVIDENCE} {
            error "P08.4.3b final evidence mismatch: actual=$final_evidence expected=$P08_EXPECTED_EVIDENCE"
        }
        set final_prediction [p08_argmax_lowest $final_evidence]
        p08_expect "final prediction" $final_prediction $P08_EXPECTED_PREDICTION
        puts "PASS: P08.4.3b physical final evidence prediction=$final_prediction evidence=$final_evidence exact_match=true"
    }

    set replacement [expr {$previous_name ne "" && $previous_name ne $context_name ? 1 : 0}]
    puts $result "dispatch=$dispatch_index context=$context_name logical_core=$logical_id slot=$slot timestep=$timestep cycles=$cycles replacement=$replacement"
    puts "PASS: P08.4.3b physical dispatch index=$dispatch_index context=$context_name logical_core=$logical_id slot=$slot cycles=$cycles exact_state_trace_packets=true"
    set previous_name $context_name
    incr dispatch_index
}

if {$dispatch_index != 3} { error "P08.4.3b expected exactly three physical dispatches" }
if {$final_evidence eq "" || $final_prediction != $P08_EXPECTED_PREDICTION} {
    error "P08.4.3b output-context evidence was not verified"
}

puts $result "prediction=$final_prediction"
puts $result "evidence=$final_evidence"
puts $result "context_reload_exact=1"
puts $result "result=PASS"
close $result

puts "PASS: P08.4.3b physical paging sequence=$P08_SEQUENCE replacements=2 reload_exact=true"
puts "PASS: P08.4.3b physical identities parameters=$P08_PARAMETER_FINGERPRINT network=$P08_NETWORK_FINGERPRINT compiled=$P08_COMPILED_FINGERPRINT"
puts "PASS: P08.4.3b physical test-use boundary official_test_used_for_physical_conformance=true model_or_conversion_selection_after_test=false"
puts "P08.4.3b representative K26 physical conformance completed successfully."
