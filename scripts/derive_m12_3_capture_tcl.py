from pathlib import Path

root = Path('Neuromorphic Digital Twin/rtl/core_v1')
src = root / 'vivado' / 'capture_m12_2_single_tick.tcl'
dst = root / 'vivado' / 'capture_m12_3_multitick.tcl'
text = src.read_text(encoding='utf-8')
text = text.replace(
    '# Program the M12.2 K26 bitstream once and capture all directed single-tick cases.',
    '# Program the M12.3 K26 bitstream once and capture all directed multi-tick cases.',
)
text = text.replace('M12.2', 'M12.3')
text = text.replace('capture_m12_2_single_tick.tcl', 'capture_m12_3_multitick.tcl')
text = text.replace(
    'case_id\\tcase_name\\tneuron_count"',
    'case_id\\tcase_name\\tneuron_count\\ttick_count"',
    1,
)

prefix = text[: text.index('set captured_cases 0')]

tail = r'''set captured_cases 0
set captured_ticks 0
foreach record $case_lines {
    if {[string trim $record] eq ""} { continue }
    set fields [split $record "\t"]
    if {[llength $fields] != 4} {
        error "Invalid M12.3 hardware metadata row: $record"
    }
    set case_id [lindex $fields 0]
    set case_name [lindex $fields 1]
    set neuron_count [lindex $fields 2]
    set tick_count [lindex $fields 3]
    if {
        ![string is integer -strict $case_id] ||
        ![string is integer -strict $neuron_count] ||
        ![string is integer -strict $tick_count] ||
        $tick_count < 1
    } {
        error "Invalid integer M12.3 metadata row: $record"
    }

    # Before capture_start, trace_read_addr is the case selector. The RTL
    # latches its low 8 bits and then returns the probe to trace-address duty.
    set_probe_uint $p_trace_addr $case_id
    pulse_probe $p_start
    wait_for_input $vio $p_step_ready 1 1000 2 "M12.3 case preload/reset"
    refresh_hw_vio $vio
    set phase [probe_uint $p_phase]
    set selected_case [expr {($phase >> 4) & 0xF}]
    if {$selected_case != $case_id} {
        error "M12.3 case-select witness mismatch: requested=$case_id observed=$selected_case phase=$phase"
    }
    if {[probe_uint $p_tick] != 0 || [probe_uint $p_capture_fault] != 0} {
        error "M12.3 case $case_id did not reach clean tick zero: tick=[probe_uint $p_tick] capture_fault=[probe_uint $p_capture_fault] code=[probe_uint $p_capture_fault_code] phase=$phase"
    }
    puts "M12.3 case $case_id selected and reset: name=$case_name neurons=$neuron_count ticks=$tick_count"

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
                error "M12.3 capture shell fault for case $case_id tick=$expected_tick: code=[probe_uint $p_capture_fault_code] phase=[probe_uint $p_phase] core_fault=[probe_uint $p_core_fault_code]"
            }
            if {[probe_uint $p_window] == 1 && [probe_uint $p_tick] == $expected_tick} {
                set reached 1
                break
            }
            after 2
        }
        if {!$reached} {
            close $fh
            error "Timed out waiting for M12.3 post-commit trace window: case=$case_id expected_tick=$expected_tick observed_tick=[probe_uint $p_tick] phase=[probe_uint $p_phase]"
        }

        refresh_hw_vio $vio
        set expected_done [expr {$expected_tick == $tick_count ? 1 : 0}]
        if {[probe_uint $p_done] != $expected_done} {
            close $fh
            error "M12.3 capture_done mismatch: case=$case_id tick=$expected_tick expected=$expected_done actual=[probe_uint $p_done]"
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
        set route_write_seen [probe_uint $p_route_write_seen]
        set route_write_addr [probe_uint $p_route_write_addr]
        set route_write_data [probe_uint $p_route_write_data]
        set route_read_addr [probe_uint $p_route_read_addr]
        set route_read_data [probe_uint $p_route_read_data]
        set bank_write_seen [probe_uint $p_bank_write_seen]
        set bank_write_bank [probe_uint $p_bank_write_bank]
        set bank_write_addr [probe_uint $p_bank_write_addr]
        set bank_write_data [probe_uint $p_bank_write_data]
        puts "M12.3 route witness case $case_id tick $expected_tick: target_write_seen=$route_write_seen target_write_addr=$route_write_addr target_write_data=$route_write_data target_read_addr=$route_read_addr target_read_data=$route_read_data bank_write_seen=$bank_write_seen bank_write_bank=$bank_write_bank bank_write_addr=$bank_write_addr bank_write_data=$bank_write_data"

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

        incr captured_ticks
        puts "M12.3 captured physical case $case_id tick $expected_tick/$tick_count: external=$external_count consumed=$consumed_count routed=$routed_count bank=$current_bank"
    }

    puts $fh "  \]"
    puts $fh "\}"
    close $fh
    incr captured_cases
    puts "M12.3 captured physical case $case_id complete: name=$case_name ticks=$tick_count output=$output_json"
}

if {$captured_cases != [llength $case_lines]} {
    error "M12.3 captured case count mismatch: captured=$captured_cases metadata=[llength $case_lines]"
}
puts "M12.3 physical directed multi-tick suite capture completed successfully: cases=$captured_cases ticks=$captured_ticks output=$output_dir"
close_hw_manager
'''

dst.write_text(prefix + tail, encoding='utf-8')
print(dst)
