# P02.4 physical page-in/page-out acceptance through the existing paging VIO.
if {$argc < 2 || $argc > 3} {
    error "usage: p02_4_vio_roundtrip.tcl <bit_file> <ltx_file> ?<vivado_hw_server_url>?"
}

set bit_file [file normalize [lindex $argv 0]]
set ltx_file [file normalize [lindex $argv 1]]
set server_url "localhost:3121"
if {$argc == 3} { set server_url [lindex $argv 2] }

foreach f [list $bit_file $ltx_file] {
    if {![file exists $f]} { error "P02.4 hardware artifact missing: $f" }
}

proc p02_find_probe {vio suffix} {
    foreach probe [get_hw_probes -of_objects $vio] {
        set name [get_property NAME $probe]
        if {[string match "*${suffix}" $name]} {
            return $probe
        }
    }
    error "P02.4 VIO probe not found: $suffix"
}

proc p02_input_int {vio probe} {
    refresh_hw_vio $vio
    set raw [get_property INPUT_VALUE $probe]
    return [expr {wide($raw)}]
}

proc p02_commit_outputs {vio assignments} {
    foreach {probe value} $assignments {
        set_property OUTPUT_VALUE $value $probe
    }
    commit_hw_vio $vio
}

proc p02_page_command {vio probes label page_out mutable_only slot record_base expected_bytes} {
    array set p $probes

    set completed_before [p02_input_int $vio $p(in4)]
    set read_before [p02_input_int $vio $p(in9)]
    set write_before [p02_input_int $vio $p(in10)]
    set axi_before [p02_input_int $vio $p(in11)]

    p02_commit_outputs $vio [list         $p(out0) 0         $p(out1) $page_out         $p(out2) $mutable_only         $p(out3) $slot         $p(out4) $record_base]
    p02_commit_outputs $vio [list $p(out0) 1]
    after 10
    p02_commit_outputs $vio [list $p(out0) 0]

    set complete 0
    for {set poll 0} {$poll < 3000} {incr poll} {
        refresh_hw_vio $vio
        foreach err_name {in6 in7 in8 in12 in13} {
            if {[expr {wide([get_property INPUT_VALUE $p($err_name)])}] != 0} {
                error "P02.4 $label reported error probe $err_name"
            }
        }
        if {[expr {wide([get_property INPUT_VALUE $p(in2)])}] != 0} {
            error "P02.4 $label was blocked at command start"
        }
        set completed_now [expr {wide([get_property INPUT_VALUE $p(in4)])}]
        if {$completed_now > $completed_before} {
            set complete 1
            break
        }
        after 10
    }
    if {!$complete} {
        error "P02.4 $label timed out waiting for completed_transfers"
    }

    refresh_hw_vio $vio
    set bytes [expr {wide([get_property INPUT_VALUE $p(in3)])}]
    set cycles [expr {wide([get_property INPUT_VALUE $p(in5)])}]
    set read_after [expr {wide([get_property INPUT_VALUE $p(in9)])}]
    set write_after [expr {wide([get_property INPUT_VALUE $p(in10)])}]
    set axi_after [expr {wide([get_property INPUT_VALUE $p(in11)])}]

    if {$bytes != $expected_bytes} {
        error "P02.4 $label moved $bytes semantic bytes; expected $expected_bytes"
    }

    puts "P02_4_${label}_CYCLES=$cycles"
    puts "P02_4_${label}_READ_BURSTS=[expr {$read_after - $read_before}]"
    puts "P02_4_${label}_WRITE_BURSTS=[expr {$write_after - $write_before}]"
    puts "P02_4_${label}_AXI_BYTES=[expr {$axi_after - $axi_before}]"
    puts "PASS: P02.4 $label transfer completed bytes=$bytes cycles=$cycles"
}

open_hw_manager
connect_hw_server -url $server_url
open_hw_target

set device ""
foreach candidate [get_hw_devices] {
    set part ""
    catch {set part [get_property PART $candidate]}
    if {[string match "xck26*" [string tolower $part]]} {
        set device $candidate
        break
    }
}
if {$device eq ""} {
    error "P02.4 could not find a connected xck26 hardware device"
}
current_hw_device $device
refresh_hw_device $device

set_property PROGRAM.FILE $bit_file $device
set_property PROBES.FILE $ltx_file $device
catch {set_property FULL_PROBES.FILE $ltx_file $device}
program_hw_devices $device
refresh_hw_device $device

set page_vio ""
foreach candidate [get_hw_vios -of_objects $device] {
    set cell ""
    catch {set cell [get_property CELL_NAME $candidate]}
    if {[string match "*vio_p02_page*" $cell]} {
        set page_vio $candidate
        break
    }
}
if {$page_vio eq ""} {
    error "P02.4 paging VIO (vio_p02_page) was not found after programming"
}

array set p {}
for {set i 0} {$i <= 4} {incr i} {
    set p(out$i) [p02_find_probe $page_vio probe_out$i]
}
for {set i 0} {$i <= 14} {incr i} {
    set p(in$i) [p02_find_probe $page_vio probe_in$i]
}
set probes [array get p]

# Fresh programming resets all page/AXI observability counters.
p02_page_command $page_vio $probes PAGE_IN_FULL 0 0 0 0x40000000 438272
p02_page_command $page_vio $probes PAGE_OUT_FULL 1 0 0 0x43F00000 438272
p02_page_command $page_vio $probes PAGE_OUT_MUTABLE 1 1 0 0x43F80000 106496

refresh_hw_vio $page_vio
set completed [expr {wide([get_property INPUT_VALUE $p(in4)])}]
set read_bursts [expr {wide([get_property INPUT_VALUE $p(in9)])}]
set write_bursts [expr {wide([get_property INPUT_VALUE $p(in10)])}]
set axi_bytes [expr {wide([get_property INPUT_VALUE $p(in11)])}]
set pending [expr {wide([get_property INPUT_VALUE $p(in14)])}]

if {$completed != 3} { error "P02.4 expected 3 completed transfers, got $completed" }
if {$read_bursts != 1712} { error "P02.4 expected 1712 read bursts, got $read_bursts" }
if {$write_bursts != 2128} { error "P02.4 expected 2128 write bursts, got $write_bursts" }
if {$axi_bytes != 983040} { error "P02.4 expected 983040 AXI bytes, got $axi_bytes" }
if {$pending != 0} { error "P02.4 write coalescer still has $pending pending bytes" }

puts "P02_4_COMPLETED_TRANSFERS=$completed"
puts "P02_4_READ_BURSTS=$read_bursts"
puts "P02_4_WRITE_BURSTS=$write_bursts"
puts "P02_4_AXI_BYTES=$axi_bytes"
puts "PASS: P02.4 VIO physical paging sequence completed successfully"

close_hw_manager
