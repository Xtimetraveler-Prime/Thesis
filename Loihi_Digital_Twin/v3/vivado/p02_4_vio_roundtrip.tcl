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

proc p02_dump_probe_inventory {vio} {
    puts "P02.4 VIO probe inventory:"
    foreach probe [get_hw_probes -of_objects $vio] {
        set name [get_property NAME $probe]
        set type [string tolower [get_property TYPE $probe]]
        set port [get_property PROBE_PORT $probe]
        set width [get_property PROBE_PORT_BIT_COUNT $probe]
        puts "  name=$name type=$type port=$port width=$width"
    }
}

proc p02_find_probe_by_port {vio expected_type expected_port expected_width} {
    set matches {}
    foreach probe [get_hw_probes -of_objects $vio] {
        set type [string tolower [get_property TYPE $probe]]
        set port [get_property PROBE_PORT $probe]
        if {$type eq $expected_type && $port == $expected_port} {
            lappend matches $probe
        }
    }
    if {[llength $matches] != 1} {
        p02_dump_probe_inventory $vio
        error "P02.4 expected exactly one $expected_type probe at port $expected_port, found [llength $matches]"
    }
    set probe [lindex $matches 0]
    set width [get_property PROBE_PORT_BIT_COUNT $probe]
    if {$width != $expected_width} {
        p02_dump_probe_inventory $vio
        error "P02.4 $expected_type port $expected_port width=$width expected=$expected_width"
    }
    return $probe
}

proc p02_input_int {vio probe} {
    refresh_hw_vio $vio
    set raw [get_property INPUT_VALUE $probe]
    return [expr {wide($raw)}]
}

proc p02_commit_page_outputs {vio probe_array_name page_out mutable_only slot record_base start_value} {
    upvar 1 $probe_array_name p
    set_property OUTPUT_VALUE $start_value $p(out0)
    set_property OUTPUT_VALUE $page_out $p(out1)
    set_property OUTPUT_VALUE $mutable_only $p(out2)
    set_property OUTPUT_VALUE $slot $p(out3)
    set_property OUTPUT_VALUE $record_base $p(out4)
    commit_hw_vio $vio
}

proc p02_page_command {vio probe_array_name label page_out mutable_only slot record_base expected_bytes} {
    # Keep the hw_probe Tcl objects in the caller's array.  Serializing them
    # through "array get" converts Vivado object handles into plain path strings
    # that get_property/set_property reject as hardware objects.
    upvar 1 $probe_array_name p

    set completed_before [p02_input_int $vio $p(in4)]
    set read_before [p02_input_int $vio $p(in9)]
    set write_before [p02_input_int $vio $p(in10)]
    set axi_before [p02_input_int $vio $p(in11)]

    p02_commit_page_outputs $vio p $page_out $mutable_only $slot $record_base 0
    p02_commit_page_outputs $vio p $page_out $mutable_only $slot $record_base 1
    after 10
    p02_commit_page_outputs $vio p $page_out $mutable_only $slot $record_base 0

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

set devices [get_hw_devices]
if {[llength $devices] == 1} {
    set device [lindex $devices 0]
} else {
    set device ""
    foreach candidate $devices {
        set part ""
        set name ""
        catch {set part [string tolower [get_property PART $candidate]]}
        catch {set name [string tolower [get_property NAME $candidate]]}
        if {
            [string match "*xck26*" $part] ||
            [string match "*xczu5*" $part] ||
            [string match "*xck26*" $name] ||
            [string match "*xczu5*" $name]
        } {
            set device $candidate
            break
        }
    }
}
if {$device eq ""} {
    error "P02.4 could not uniquely identify the connected K26/xczu5 hardware device"
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
    set name ""
    catch {set cell [get_property CELL_NAME $candidate]}
    catch {set name [get_property NAME $candidate]}
    if {
        [string match "*vio_p02_page*" $cell] ||
        [string match "*vio_p02_page*" $name]
    } {
        set page_vio $candidate
        break
    }
}
if {$page_vio eq ""} {
    error "P02.4 paging VIO (vio_p02_page) was not found after programming"
}

p02_dump_probe_inventory $page_vio

array set p {}
set out_widths {1 1 1 2 64}
set in_widths {1 1 1 32 32 64 1 1 1 32 32 64 1 1 9}

for {set i 0} {$i < [llength $out_widths]} {incr i} {
    set width [lindex $out_widths $i]
    set p(out$i) [p02_find_probe_by_port $page_vio vio_output $i $width]
    set_property OUTPUT_VALUE_RADIX UNSIGNED $p(out$i)
}
for {set i 0} {$i < [llength $in_widths]} {incr i} {
    set width [lindex $in_widths $i]
    set p(in$i) [p02_find_probe_by_port $page_vio vio_input $i $width]
    set_property INPUT_VALUE_RADIX UNSIGNED $p(in$i)
}
puts "PASS: P02.4 paging VIO probes bound by TYPE/PROBE_PORT metadata"

# Fresh programming resets all page/AXI observability counters. Pass the array
# name so Vivado hw_probe objects remain live Tcl objects instead of strings.
p02_page_command $page_vio p PAGE_IN_FULL 0 0 0 0x40000000 438272
p02_page_command $page_vio p PAGE_OUT_FULL 1 0 0 0x43F00000 438272
p02_page_command $page_vio p PAGE_OUT_MUTABLE 1 1 0 0x43F80000 106496

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
