# Program the M12.5 K26 bitstream once and capture all directed multi-tick cases.
if {$argc != 5} {
    error "usage: capture_m12_5_characterization.tcl <bitstream> <ltx> <hardware_cases.tsv> <output_dir> <cycle_tsv>"
}
set bitstream [file normalize [lindex $argv 0]]
set probes    [file normalize [lindex $argv 1]]
set metadata  [file normalize [lindex $argv 2]]
set output_dir [file normalize [lindex $argv 3]]
set cycle_tsv [file normalize [lindex $argv 4]]
file mkdir $output_dir
file mkdir [file dirname $cycle_tsv]
set cycle_fh [open $cycle_tsv w]
puts $cycle_fh "case_id\tcase_name\ttick\tcycles\texternal_events\trecurrent_events\trouted_events"
foreach path [list $bitstream $probes $metadata] {
    if {![file exists $path]} {
        error "Required M12.5 hardware artifact does not exist: $path"
    }
}

set meta_fh [open $metadata r]
set meta_text [string trim [read $meta_fh]]
close $meta_fh
set meta_lines [split $meta_text "\n"]
if {[llength $meta_lines] < 2 || [lindex $meta_lines 0] ne "case_id\tcase_name\tsource_kind\tseed\tconfiguration_sha256\tneuron_count\taxon_count\tsynapse_count\troute_count\ttick_count"} {
    error "M12.5 hardware case metadata has an invalid header"
}
set case_lines [lrange $meta_lines 1 end]

proc find_one_probe {vio needle} {
    set matches {}
    foreach probe [get_hw_probes -quiet -of_objects $vio] {
        set name [get_property NAME $probe]
        set leaf [lindex [split $name "/"] end]
        if {$leaf eq $needle} {
            lappend matches $probe
        }
    }
    if {[llength $matches] != 1} {
        set available {}
        foreach probe [get_hw_probes -quiet -of_objects $vio] {
            lappend available [get_property NAME $probe]
        }
        error "Expected exactly one VIO probe named '$needle'; matches=$matches available=$available"
    }
    return [lindex $matches 0]
}

proc probe_uint {probe} {
    set raw [get_property INPUT_VALUE $probe]
    if {[string match "0x*" $raw] || [string match "0X*" $raw]} {
        return [expr {$raw}]
    }
    set value 0
    if {[scan $raw %x value] != 1} {
        error "Could not parse VIO probe value '$raw' for [get_property NAME $probe]"
    }
    return $value
}

proc set_probe_uint {probe value} {
    set current [get_property OUTPUT_VALUE $probe]
    set digits [string length $current]
    if {$digits < 1} {
        error "Could not determine HEX output width for [get_property NAME $probe]"
    }
    set encoded [format "%0*x" $digits $value]
    if {[string length $encoded] != $digits} {
        error "VIO value does not fit probe width: probe=[get_property NAME $probe] value=$value digits=$digits"
    }
    set_property OUTPUT_VALUE $encoded $probe
    commit_hw_vio $probe
}

proc pulse_probe {probe} {
    set_probe_uint $probe 1
    after 2
    set_probe_uint $probe 0
    after 2
}

proc bool_json {value} {
    if {$value == 0} { return "false" }
    return "true"
}

proc json_quote {value} {
    return "\"[string map [list \\ \\\\ \" \\\"] $value]\""
}

proc u64_hex {value} {
    return [format "0x%016x" $value]
}

proc u64_to_i64 {value} {
    if {$value >= 9223372036854775808} {
        return [expr {$value - 18446744073709551616}]
    }
    return $value
}

proc json_int_list {values} {
    return [format {[%s]} [join $values {, }]]
}

proc json_bool_list {values} {
    set out {}
    foreach value $values { lappend out [bool_json $value] }
    return [format {[%s]} [join $out {, }]]
}

proc json_u64_list {values} {
    set out {}
    foreach value $values { lappend out [json_quote [u64_hex $value]] }
    return [format {[%s]} [join $out {, }]]
}

proc wait_for_input {vio probe expected attempts delay_ms description} {
    for {set attempt 0} {$attempt < $attempts} {incr attempt} {
        refresh_hw_vio $vio
        if {[probe_uint $probe] == $expected} {
            return
        }
        after $delay_ms
    }
    refresh_hw_vio $vio
    error "Timed out waiting for $description: expected=$expected actual=[probe_uint $probe]"
}

proc trace_read_word {vio p_ready p_seq p_rsp_space p_rsp_addr p_rsp_data p_rsp_error p_req p_space p_addr space addr} {
    refresh_hw_vio $vio
    if {[probe_uint $p_ready] != 1} {
        error "Trace bridge is not ready before request: space=$space addr=$addr"
    }
    set old_seq [probe_uint $p_seq]
    set_probe_uint $p_space $space
    set_probe_uint $p_addr $addr
    set_probe_uint $p_req 1
    after 2
    set_probe_uint $p_req 0

    set changed 0
    for {set attempt 0} {$attempt < 100} {incr attempt} {
        refresh_hw_vio $vio
        if {[probe_uint $p_seq] != $old_seq} {
            set changed 1
            break
        }
        after 2
    }
    if {!$changed} {
        error "Timed out waiting for trace response: space=$space addr=$addr seq=$old_seq"
    }
    set rsp_space [probe_uint $p_rsp_space]
    set rsp_addr [probe_uint $p_rsp_addr]
    set rsp_error [probe_uint $p_rsp_error]
    if {$rsp_space != $space || $rsp_addr != $addr} {
        error "Trace response tag mismatch: requested space=$space addr=$addr got space=$rsp_space addr=$rsp_addr"
    }
    if {$rsp_error != 0} {
        error "Trace bridge returned error: space=$space addr=$addr"
    }
    return [probe_uint $p_rsp_data]
}

open_hw_manager
connect_hw_server
open_hw_target

set candidates [get_hw_devices -quiet *xck26*]
if {[llength $candidates] == 0} {
    set candidates [get_hw_devices -quiet]
}
if {[llength $candidates] != 1} {
    error "M12.5 expected exactly one target hardware device; found: $candidates"
}
set dev [lindex $candidates 0]
current_hw_device $dev
set device_name [get_property NAME $dev]
puts "M12.5 hardware device: $device_name"

set_property PROGRAM.FILE $bitstream $dev
set_property PROBES.FILE $probes $dev
program_hw_devices $dev
refresh_hw_device $dev
puts "M12.5 bitstream programmed successfully."

set vios [get_hw_vios -quiet]
if {[llength $vios] != 1} {
    error "M12.5 expected exactly one VIO core after programming; found: $vios"
}
set vio [lindex $vios 0]

set p_heartbeat [find_one_probe $vio clock_heartbeat]
set p_start_seen [find_one_probe $vio start_seen]
set p_reset_released [find_one_probe $vio reset_released]
set p_busy [find_one_probe $vio capture_busy]
set p_step_ready [find_one_probe $vio step_ready]
set p_window [find_one_probe $vio trace_window_open]
set p_done [find_one_probe $vio capture_done]
set p_capture_fault [find_one_probe $vio capture_fault]
set p_capture_fault_code [find_one_probe $vio capture_fault_code]
set p_phase [find_one_probe $vio capture_phase]
set p_tick [find_one_probe $vio observed_tick]
set p_core_fault [find_one_probe $vio observed_core_fault]
set p_core_fault_code [find_one_probe $vio observed_core_fault_code]
set p_bank [find_one_probe $vio observed_recurrent_bank]
set p_current_count [find_one_probe $vio observed_recurrent_count]
set p_bank0_count [find_one_probe $vio observed_recurrent_bank0_count]
set p_bank1_count [find_one_probe $vio observed_recurrent_bank1_count]
set p_consumed_count [find_one_probe $vio observed_consumed_recurrent_count]
set p_routed_count [find_one_probe $vio observed_routed_recurrent_count]
set p_external_count [find_one_probe $vio observed_external_event_count]
set p_tick_cycles [find_one_probe $vio observed_last_tick_cycles]
set p_trace_ready [find_one_probe $vio trace_read_ready]
set p_rsp_seq [find_one_probe $vio trace_response_seq]
set p_rsp_space [find_one_probe $vio trace_response_space]
set p_rsp_addr [find_one_probe $vio trace_response_addr]
set p_rsp_data [find_one_probe $vio trace_response_data]
set p_rsp_error [find_one_probe $vio trace_response_error]
set p_route_write_seen [find_one_probe $vio observed_route_target_write_seen]
set p_route_write_addr [find_one_probe $vio observed_route_target_write_addr]
set p_route_write_data [find_one_probe $vio observed_route_target_write_data]
set p_route_read_addr [find_one_probe $vio observed_route_target_read_addr]
set p_route_read_data [find_one_probe $vio observed_route_target_read_data]
set p_bank_write_seen [find_one_probe $vio observed_recurrent_bank_write_seen]
set p_bank_write_bank [find_one_probe $vio observed_recurrent_bank_write_bank]
set p_bank_write_addr [find_one_probe $vio observed_recurrent_bank_write_addr]
set p_bank_write_data [find_one_probe $vio observed_recurrent_bank_write_data]

set p_start [find_one_probe $vio capture_start]
set p_step [find_one_probe $vio capture_step]
set p_trace_req [find_one_probe $vio trace_read_req]
set p_trace_space [find_one_probe $vio trace_read_space]
set p_trace_addr [find_one_probe $vio trace_read_addr]
set p_resetn [find_one_probe $vio capture_resetn]

# Initialize commands low and assert the local capture reset before heartbeat test.
refresh_hw_vio -update_output_values $vio
foreach probe [list $p_start $p_step $p_trace_req $p_trace_space $p_trace_addr $p_resetn] {
    set_probe_uint $probe 0
}
refresh_hw_vio $vio
if {[probe_uint $p_reset_released] != 0} {
    error "M12.5 synchronized reset was not asserted before heartbeat test"
}
set heartbeat_before [probe_uint $p_heartbeat]
after 100
refresh_hw_vio $vio
set heartbeat_after [probe_uint $p_heartbeat]
if {$heartbeat_before == $heartbeat_after} {
    error "M12.5 PL clock heartbeat did not advance: value=$heartbeat_before"
}
puts "M12.5 PL clock heartbeat advanced: $heartbeat_before -> $heartbeat_after"

set_probe_uint $p_resetn 1
after 20
refresh_hw_vio $vio
if {[probe_uint $p_reset_released] != 1} {
    error "M12.5 proc_sys_reset did not release the capture domain"
}
puts "M12.5 local capture reset released through VIO."

set captured_cases 0
set captured_ticks 0
foreach record $case_lines {
    if {[string trim $record] eq ""} { continue }
    set fields [split $record "\t"]
    if {[llength $fields] != 10} {
        error "Invalid M12.5 hardware metadata row: $record"
    }
    set case_id [lindex $fields 0]
    set case_name [lindex $fields 1]
    set source_kind [lindex $fields 2]
    set seed [lindex $fields 3]
    set configuration_sha256 [lindex $fields 4]
    set neuron_count [lindex $fields 5]
    set tick_count [lindex $fields 9]
    if {
        ![string is integer -strict $case_id] ||
        ![string is integer -strict $neuron_count] ||
        ![string is integer -strict $tick_count] ||
        $tick_count < 1
    } {
        error "Invalid integer M12.5 metadata row: $record"
    }

    # Before capture_start, trace_read_addr is the case selector. The RTL
    # latches its low 8 bits and then returns the probe to trace-address duty.
    set_probe_uint $p_trace_addr $case_id
    pulse_probe $p_start
    wait_for_input $vio $p_step_ready 1 1000 2 "M12.5 case preload/reset"
    refresh_hw_vio $vio
    set phase [probe_uint $p_phase]
    set selected_case $phase
    if {$selected_case != $case_id} {
        error "M12.5 case-select witness mismatch: requested=$case_id observed=$selected_case phase=$phase"
    }
    if {[probe_uint $p_tick] != 0 || [probe_uint $p_capture_fault] != 0} {
        error "M12.5 case $case_id did not reach clean tick zero: tick=[probe_uint $p_tick] capture_fault=[probe_uint $p_capture_fault] code=[probe_uint $p_capture_fault_code] phase=$phase"
    }
    puts "M12.5 case $case_id selected and reset: name=$case_name kind=$source_kind seed=$seed config=$configuration_sha256 neurons=$neuron_count ticks=$tick_count"

    set output_json [file join $output_dir [format "%02d-%s.physical.json" $case_id $case_name]]
    set fh [open $output_json w]
    # Literal JSON braces are escaped because this foreach body is a braced Tcl word.
    puts $fh "\{"
    puts $fh "  \"schema\": \"neuromorphic-twin-physical-fpga-trace-v1\","
    puts $fh "  \"scenario_id\": [json_quote $case_name],"
    puts $fh "  \"transport\": \"jtag-vio\","
    puts $fh "  \"device\": [json_quote $device_name],"
    puts $fh "  \"ticks\": \["

    for {set expected_tick 1} {$expected_tick <= $tick_count} {incr expected_tick} {
        pulse_probe $p_step
        set reached 0
        for {set attempt 0} {$attempt < 1000} {incr attempt} {
            refresh_hw_vio $vio
            if {[probe_uint $p_capture_fault] != 0} {
                close $fh
                error "M12.5 capture shell fault for case $case_id tick=$expected_tick: code=[probe_uint $p_capture_fault_code] phase=[probe_uint $p_phase] core_fault=[probe_uint $p_core_fault_code]"
            }
            if {[probe_uint $p_window] == 1 && [probe_uint $p_tick] == $expected_tick} {
                set reached 1
                break
            }
            after 2
        }
        if {!$reached} {
            close $fh
            error "Timed out waiting for M12.5 post-commit trace window: case=$case_id expected_tick=$expected_tick observed_tick=[probe_uint $p_tick] phase=[probe_uint $p_phase]"
        }

        refresh_hw_vio $vio
        set expected_done [expr {$expected_tick == $tick_count ? 1 : 0}]
        if {[probe_uint $p_done] != $expected_done} {
            close $fh
            error "M12.5 capture_done mismatch: case=$case_id tick=$expected_tick expected=$expected_done actual=[probe_uint $p_done]"
        }

        set core_fault [probe_uint $p_core_fault]
        set core_fault_code [probe_uint $p_core_fault_code]
        set current_bank [probe_uint $p_bank]
        set current_count [probe_uint $p_current_count]
        set bank0_count [probe_uint $p_bank0_count]
        set bank1_count [probe_uint $p_bank1_count]
        set consumed_count [probe_uint $p_consumed_count]
        set routed_count [probe_uint $p_routed_count]
        set external_count [probe_uint $p_external_count]
        set tick_cycles [probe_uint $p_tick_cycles]
        if {$tick_cycles <= 0} {
            close $fh
            close $cycle_fh
            error "M12.5 invalid tick-cycle measurement: case=$case_id tick=$expected_tick cycles=$tick_cycles"
        }
        set route_write_seen [probe_uint $p_route_write_seen]
        set route_write_addr [probe_uint $p_route_write_addr]
        set route_write_data [probe_uint $p_route_write_data]
        set route_read_addr [probe_uint $p_route_read_addr]
        set route_read_data [probe_uint $p_route_read_data]
        set bank_write_seen [probe_uint $p_bank_write_seen]
        set bank_write_bank [probe_uint $p_bank_write_bank]
        set bank_write_addr [probe_uint $p_bank_write_addr]
        set bank_write_data [probe_uint $p_bank_write_data]
        puts "M12.5 route witness case $case_id tick $expected_tick: target_write_seen=$route_write_seen target_write_addr=$route_write_addr target_write_data=$route_write_data target_read_addr=$route_read_addr target_read_data=$route_read_data bank_write_seen=$bank_write_seen bank_write_bank=$bank_write_bank bank_write_addr=$bank_write_addr bank_write_data=$bank_write_data"

        set state_before {}
        set state_after {}
        set synaptic_input {}
        set spikes {}
        for {set neuron 0} {$neuron < $neuron_count} {incr neuron} {
            lappend state_before [trace_read_word $vio $p_trace_ready $p_rsp_seq $p_rsp_space $p_rsp_addr $p_rsp_data $p_rsp_error $p_trace_req $p_trace_space $p_trace_addr 0 $neuron]
            lappend state_after [trace_read_word $vio $p_trace_ready $p_rsp_seq $p_rsp_space $p_rsp_addr $p_rsp_data $p_rsp_error $p_trace_req $p_trace_space $p_trace_addr 1 $neuron]
            set syn_u64 [trace_read_word $vio $p_trace_ready $p_rsp_seq $p_rsp_space $p_rsp_addr $p_rsp_data $p_rsp_error $p_trace_req $p_trace_space $p_trace_addr 2 $neuron]
            lappend synaptic_input [u64_to_i64 $syn_u64]
            lappend spikes [trace_read_word $vio $p_trace_ready $p_rsp_seq $p_rsp_space $p_rsp_addr $p_rsp_data $p_rsp_error $p_trace_req $p_trace_space $p_trace_addr 3 $neuron]
        }

        set external_events {}
        for {set idx 0} {$idx < $external_count} {incr idx} {
            lappend external_events [trace_read_word $vio $p_trace_ready $p_rsp_seq $p_rsp_space $p_rsp_addr $p_rsp_data $p_rsp_error $p_trace_req $p_trace_space $p_trace_addr 4 $idx]
        }

        # After Phase F the current bank contains the newly routed outputs. The
        # opposite bank retains the just-consumed prefix for trace purposes.
        if {$current_bank == 0} {
            set routed_space 5
            set consumed_space 6
        } else {
            set routed_space 6
            set consumed_space 5
        }
        set recurrent_inputs {}
        for {set idx 0} {$idx < $consumed_count} {incr idx} {
            lappend recurrent_inputs [trace_read_word $vio $p_trace_ready $p_rsp_seq $p_rsp_space $p_rsp_addr $p_rsp_data $p_rsp_error $p_trace_req $p_trace_space $p_trace_addr $consumed_space $idx]
        }
        set routed_outputs {}
        for {set idx 0} {$idx < $routed_count} {incr idx} {
            lappend routed_outputs [trace_read_word $vio $p_trace_ready $p_rsp_seq $p_rsp_space $p_rsp_addr $p_rsp_data $p_rsp_error $p_trace_req $p_trace_space $p_trace_addr $routed_space $idx]
        }

        puts $fh "    \{"
        puts $fh "      \"committed_tick\": $expected_tick,"
        puts $fh "      \"core_fault\": [bool_json $core_fault],"
        puts $fh "      \"core_fault_code\": $core_fault_code,"
        puts $fh "      \"external_event_count\": $external_count,"
        puts $fh "      \"consumed_recurrent_count\": $consumed_count,"
        puts $fh "      \"routed_recurrent_count\": $routed_count,"
        puts $fh "      \"recurrent_current_bank\": $current_bank,"
        puts $fh "      \"recurrent_current_count\": $current_count,"
        puts $fh "      \"recurrent_bank0_count\": $bank0_count,"
        puts $fh "      \"recurrent_bank1_count\": $bank1_count,"
        puts $fh "      \"external_input_axons\": [json_int_list $external_events],"
        puts $fh "      \"recurrent_input_axons\": [json_int_list $recurrent_inputs],"
        puts $fh "      \"routed_output_axons\": [json_int_list $routed_outputs],"
        puts $fh "      \"synaptic_input\": [json_int_list $synaptic_input],"
        puts $fh "      \"state_before_words\": [json_u64_list $state_before],"
        puts $fh "      \"state_after_words\": [json_u64_list $state_after],"
        puts $fh "      \"spikes\": [json_bool_list $spikes]"
        if {$expected_tick < $tick_count} {
            puts $fh "    \},"
        } else {
            puts $fh "    \}"
        }

        puts $cycle_fh "$case_id\t$case_name\t$expected_tick\t$tick_cycles\t$external_count\t$consumed_count\t$routed_count"
        incr captured_ticks
        puts "M12.5 captured physical case $case_id tick $expected_tick/$tick_count: external=$external_count consumed=$consumed_count routed=$routed_count bank=$current_bank"
    }

    puts $fh "  \]"
    puts $fh "\}"
    close $fh
    incr captured_cases
    puts "M12.5 captured physical case $case_id complete: name=$case_name ticks=$tick_count output=$output_json"
}

if {$captured_cases != [llength $case_lines]} {
    error "M12.5 captured case count mismatch: captured=$captured_cases metadata=[llength $case_lines]"
}
puts "M12.5 physical characterization capture completed successfully: cases=$captured_cases ticks=$captured_ticks cycles=$cycle_tsv output=$output_dir"
close $cycle_fh
close_hw_manager
