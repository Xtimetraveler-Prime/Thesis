# Program the accepted P03.2 shell and issue one pre-run PL reset pulse.
if {$argc < 2 || $argc > 3} {
    error "usage: p03_2c_program_bitstream.tcl <bit> <ltx> ?<hw_server_url>?"
}

set bit_file [file normalize [lindex $argv 0]]
set ltx_file [file normalize [lindex $argv 1]]
set server_url "localhost:3121"
if {$argc == 3} { set server_url [lindex $argv 2] }

foreach path [list $bit_file $ltx_file] {
    if {![file exists $path]} { error "P03.2c programming input missing: $path" }
}

proc p03_probe {vio direction port} {
    set wanted [string tolower $direction]
    set matches {}
    foreach probe [get_hw_probes -of_objects $vio] {
        if {[string tolower [get_property TYPE $probe]] eq $wanted &&
            [get_property PROBE_PORT $probe] == $port} {
            lappend matches $probe
        }
    }
    if {[llength $matches] != 1} {
        error "P03.2c probe lookup failed direction=$direction port=$port matches=[llength $matches]"
    }
    return [lindex $matches 0]
}

open_hw_manager
connect_hw_server -url $server_url
open_hw_target

set device ""
foreach candidate [get_hw_devices] {
    set name [string tolower [get_property NAME $candidate]]
    set part ""
    catch {set part [string tolower [get_property PART $candidate]]}
    if {[string match "*xck26*" $name] || [string match "*xczu5*" $name] ||
        [string match "*xck26*" $part] || [string match "*xczu5*" $part]} {
        set device $candidate
        break
    }
}
if {$device eq ""} { error "P03.2c could not identify K26 device" }

current_hw_device $device
refresh_hw_device $device
set_property PROGRAM.FILE $bit_file $device
set_property PROBES.FILE $ltx_file $device
catch {set_property FULL_PROBES.FILE $ltx_file $device}
program_hw_devices $device
refresh_hw_device $device

set vio ""
foreach candidate [get_hw_vios -of_objects $device] {
    set cell ""
    set name ""
    catch {set cell [get_property CELL_NAME $candidate]}
    catch {set name [get_property NAME $candidate]}
    if {[string match "*vio_p08*" $cell] || [string match "*vio_p08*" $name]} {
        set vio $candidate
        break
    }
}
if {$vio eq ""} { error "P03.2c could not find reset/observation VIO" }

foreach probe [get_hw_probes -of_objects $vio] {
    set type [string tolower [get_property TYPE $probe]]
    if {$type eq "vio_input" || $type eq "vio_output"} {
        set_property [expr {$type eq "vio_input" ? "INPUT_VALUE_RADIX" : "OUTPUT_VALUE_RADIX"}] HEX $probe
    }
}

reset_hw_vio_outputs $vio
refresh_hw_vio -update_output_values $vio

set reset_probe [p03_probe $vio vio_output 1]
set_property OUTPUT_VALUE 1 $reset_probe
commit_hw_vio $vio
after 20
set_property OUTPUT_VALUE 0 $reset_probe
commit_hw_vio $vio
after 20

refresh_hw_vio $vio
set resetn [get_property INPUT_VALUE [p03_probe $vio vio_input 28]]
if {[expr "0x[string trim $resetn]"] != 1} {
    error "P03.2c PL reset did not release: resetn=$resetn"
}

puts "PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released"
close_hw_manager
