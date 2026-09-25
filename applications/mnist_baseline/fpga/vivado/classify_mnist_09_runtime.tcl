# Classify one host-supplied MNIST event schedule with the reusable MNIST-09 bitstream.
if {$argc != 7} {
    error "usage: classify_mnist_09_runtime.tcl <bit> <ltx> <profile_id> <profile_name> <mnist_index> <events_tsv> <output_json>"
}
set bitstream   [file normalize [lindex $argv 0]]
set probes      [file normalize [lindex $argv 1]]
set profile_id  [lindex $argv 2]
set profile_name [lindex $argv 3]
set mnist_index [lindex $argv 4]
set events_path [file normalize [lindex $argv 5]]
set output_json [file normalize [lindex $argv 6]]

foreach path [list $bitstream $probes $events_path] {
    if {![file exists $path]} { error "MNIST-09 required runtime input missing: $path" }
}
if {![string is integer -strict $profile_id] || $profile_id < 0 || $profile_id > 1} {
    error "profile_id must be 0 or 1"
}

set fh [open $events_path r]
set lines [split [string trimright [read $fh] "\n"] "\n"]
close $fh
if {[llength $lines] != 17 || [lindex $lines 0] ne "tick\tevents"} {
    error "MNIST-09 runtime event TSV must contain header plus exactly 16 ticks"
}
set schedules {}
set total_events 0
for {set tick 0} {$tick < 16} {incr tick} {
    set fields [split [lindex $lines [expr {$tick + 1}]] "\t"]
    if {[llength $fields] < 1 || [lindex $fields 0] != $tick} {
        error "MNIST-09 event TSV tick mismatch at $tick"
    }
    set events {}
    if {[llength $fields] >= 2 && [string length [lindex $fields 1]] > 0} {
        foreach token [split [lindex $fields 1] ","] {
            if {![string is integer -strict $token] || $token < 0 || $token > 1023} {
                error "invalid runtime axon id '$token' at tick $tick"
            }
            lappend events $token
        }
    }
    incr total_events [llength $events]
    lappend schedules $events
}

proc find_one_probe {vio needle} {
    set matches {}
    foreach probe [get_hw_probes -quiet -of_objects $vio] {
        set leaf [lindex [split [get_property NAME $probe] "/"] end]
        if {$leaf eq $needle} { lappend matches $probe }
    }
    if {[llength $matches] != 1} { error "Expected one VIO probe '$needle'; got $matches" }
    return [lindex $matches 0]
}
proc probe_uint {probe} {
    set raw [get_property INPUT_VALUE $probe]
    if {[string match "0x*" $raw] || [string match "0X*" $raw]} { return [expr {$raw}] }
    set value 0
    if {[scan $raw %x value] != 1} { error "Could not parse VIO value '$raw'" }
    return $value
}
proc set_probe_uint {probe value} {
    set current [get_property OUTPUT_VALUE $probe]
    set digits [string length $current]
    set encoded [format "%0*x" $digits $value]
    if {[string length $encoded] != $digits} { error "VIO value does not fit probe" }
    set_property OUTPUT_VALUE $encoded $probe
    commit_hw_vio $probe
}
proc pulse_probe {probe} {
    set_probe_uint $probe 1
    after 1
    set_probe_uint $probe 0
    after 1
}
proc wait_input {vio probe expected description} {
    for {set i 0} {$i < 2000} {incr i} {
        refresh_hw_vio $vio
        if {[probe_uint $probe] == $expected} { return }
        after 1
    }
    error "Timed out waiting for $description; expected=$expected actual=[probe_uint $probe]"
}
proc trace_read_word {vio p_ready p_seq p_rsp_space p_rsp_addr p_rsp_data p_rsp_error p_req p_space p_addr space addr} {
    # Runtime event appends deliberately leave trace_read_space at 7, for which
    # the RTL advertises trace_read_ready=0. Select the requested normal trace
    # space/address first, then wait for readiness before issuing the request.
    set_probe_uint $p_space $space
    set_probe_uint $p_addr $addr
    set ready 0
    for {set i 0} {$i < 200} {incr i} {
        refresh_hw_vio $vio
        if {[probe_uint $p_ready] == 1} {
            set ready 1
            break
        }
        after 1
    }
    if {!$ready} { error "trace bridge not ready for space=$space addr=$addr" }
    set old_seq [probe_uint $p_seq]
    pulse_probe $p_req
    for {set i 0} {$i < 200} {incr i} {
        refresh_hw_vio $vio
        if {[probe_uint $p_seq] != $old_seq} { break }
        after 1
    }
    refresh_hw_vio $vio
    if {[probe_uint $p_seq] == $old_seq} { error "trace read response timeout" }
    if {[probe_uint $p_rsp_space] != $space || [probe_uint $p_rsp_addr] != $addr || [probe_uint $p_rsp_error] != 0} {
        error "trace read response mismatch/error"
    }
    return [probe_uint $p_rsp_data]
}
proc json_quote {value} { return "\"[string map [list \\ \\\\ \" \\\"] $value]\"" }

open_hw_manager
connect_hw_server
open_hw_target
set candidates [get_hw_devices -quiet *xck26*]
if {[llength $candidates] == 0} { set candidates [get_hw_devices -quiet] }
if {[llength $candidates] != 1} { error "MNIST-09 expected exactly one hardware device; found $candidates" }
set dev [lindex $candidates 0]
current_hw_device $dev
set device_name [get_property NAME $dev]
set_property PROGRAM.FILE $bitstream $dev
set_property PROBES.FILE $probes $dev
program_hw_devices $dev
refresh_hw_device $dev
puts "MNIST-09 bitstream programmed successfully."

set vios [get_hw_vios -quiet]
if {[llength $vios] != 1} { error "MNIST-09 expected one VIO; found $vios" }
set vio [lindex $vios 0]

set p_heartbeat [find_one_probe $vio clock_heartbeat]
set p_reset_released [find_one_probe $vio reset_released]
set p_step_ready [find_one_probe $vio step_ready]
set p_window [find_one_probe $vio trace_window_open]
set p_done [find_one_probe $vio capture_done]
set p_capture_fault [find_one_probe $vio capture_fault]
set p_capture_fault_code [find_one_probe $vio capture_fault_code]
set p_tick [find_one_probe $vio observed_tick]
set p_core_fault [find_one_probe $vio observed_core_fault]
set p_core_fault_code [find_one_probe $vio observed_core_fault_code]
set p_external_count [find_one_probe $vio observed_external_event_count]
set p_trace_ready [find_one_probe $vio trace_read_ready]
set p_rsp_seq [find_one_probe $vio trace_response_seq]
set p_rsp_space [find_one_probe $vio trace_response_space]
set p_rsp_addr [find_one_probe $vio trace_response_addr]
set p_rsp_data [find_one_probe $vio trace_response_data]
set p_rsp_error [find_one_probe $vio trace_response_error]
set p_start [find_one_probe $vio capture_start]
set p_step [find_one_probe $vio capture_step]
set p_trace_req [find_one_probe $vio trace_read_req]
set p_trace_space [find_one_probe $vio trace_read_space]
set p_trace_addr [find_one_probe $vio trace_read_addr]
set p_resetn [find_one_probe $vio capture_resetn]

refresh_hw_vio -update_output_values $vio
foreach probe [list $p_start $p_step $p_trace_req $p_trace_space $p_trace_addr $p_resetn] { set_probe_uint $probe 0 }
set before [probe_uint $p_heartbeat]
after 50
refresh_hw_vio $vio
set after_hb [probe_uint $p_heartbeat]
if {$before == $after_hb} { error "MNIST-09 PL heartbeat did not advance" }
set_probe_uint $p_resetn 1
after 20
wait_input $vio $p_reset_released 1 "runtime reset release"

# Session start: profile ID is carried in trace_read_addr exactly as M12.3 carried case ID.
set_probe_uint $p_trace_addr $profile_id
pulse_probe $p_start
wait_input $vio $p_step_ready 1 "runtime profile preload/reset"
refresh_hw_vio $vio
if {[probe_uint $p_tick] != 0 || [probe_uint $p_capture_fault] != 0} {
    error "MNIST-09 session did not start cleanly"
}

set spike_counts {0 0 0 0 0 0 0 0 0 0}
for {set tick 0} {$tick < 16} {incr tick} {
    set events [lindex $schedules $tick]
    foreach axon $events {
        set_probe_uint $p_trace_space 7
        set_probe_uint $p_trace_addr $axon
        pulse_probe $p_trace_req
        refresh_hw_vio $vio
        if {[probe_uint $p_capture_fault] != 0} {
            error "MNIST-09 append fault at tick=$tick axon=$axon code=[probe_uint $p_capture_fault_code]"
        }
    }

    pulse_probe $p_step
    set expected_tick [expr {$tick + 1}]
    for {set i 0} {$i < 5000} {incr i} {
        refresh_hw_vio $vio
        if {[probe_uint $p_capture_fault] != 0 || [probe_uint $p_core_fault] != 0} {
            error "MNIST-09 tick fault tick=$expected_tick shell=[probe_uint $p_capture_fault_code] core=[probe_uint $p_core_fault_code]"
        }
        if {[probe_uint $p_window] == 1 && [probe_uint $p_tick] == $expected_tick} { break }
        after 1
    }
    refresh_hw_vio $vio
    if {[probe_uint $p_window] != 1 || [probe_uint $p_tick] != $expected_tick} {
        error "MNIST-09 tick completion timeout at tick=$expected_tick"
    }
    if {[probe_uint $p_external_count] != [llength $events]} {
        error "MNIST-09 external-event count mismatch tick=$expected_tick expected=[llength $events] actual=[probe_uint $p_external_count]"
    }

    for {set neuron 0} {$neuron < 10} {incr neuron} {
        set spike [trace_read_word $vio $p_trace_ready $p_rsp_seq $p_rsp_space $p_rsp_addr $p_rsp_data $p_rsp_error $p_trace_req $p_trace_space $p_trace_addr 3 $neuron]
        if {$spike & 1} {
            lset spike_counts $neuron [expr {[lindex $spike_counts $neuron] + 1}]
        }
    }
}
refresh_hw_vio $vio
if {[probe_uint $p_done] != 1} { error "MNIST-09 runtime did not assert done after 16 ticks" }

set prediction 0
set best [lindex $spike_counts 0]
for {set neuron 1} {$neuron < 10} {incr neuron} {
    set value [lindex $spike_counts $neuron]
    if {$value > $best} { set best $value; set prediction $neuron }
}

file mkdir [file dirname $output_json]
set out [open $output_json w]
puts $out "\{"
puts $out "  \"schema\": \"neuromorphic-twin-mnist-runtime-result-v1\","
puts $out "  \"profile\": [json_quote $profile_name],"
puts $out "  \"profile_id\": $profile_id,"
puts $out "  \"mnist_test_index\": $mnist_index,"
puts $out "  \"device\": [json_quote $device_name],"
puts $out "  \"ticks\": 16,"
puts $out "  \"total_events\": $total_events,"
puts $out "  \"spike_counts\": \[[join $spike_counts {, }]\],"
puts $out "  \"prediction\": $prediction"
puts $out "\}"
close $out
puts "MNIST-09 runtime classification complete: profile=$profile_name index=$mnist_index prediction=$prediction spikes=$spike_counts events=$total_events"
close_hw_manager
