# Diagnose P04 PL clock and proc_sys_reset behavior over Hardware Manager/VIO.
if {$argc != 3} {
    error "usage: p04_reset_diagnostic.tcl <bit> <ltx> <hw_server_url>"
}
set bit_file [file normalize [lindex $argv 0]]
set ltx_file [file normalize [lindex $argv 1]]
set hw_server_url [lindex $argv 2]
foreach path [list $bit_file $ltx_file] {
    if {![file exists $path]} { error "P04 reset diagnostic input missing: $path" }
}

proc p04d_parse {raw} {
    set text [string trim $raw]
    regsub -all {_} $text "" text
    if {[regexp -nocase {^0x([0-9a-f]+)$} $text -> digits]} { return [expr "0x$digits"] }
    if {[regexp -nocase {^[0-9a-f]+$} $text]} { return [expr "0x$text"] }
    error "P04 reset diagnostic cannot parse '$raw'"
}
proc p04d_probe {direction port} {
    global P04D_VIO
    set wanted [string tolower $direction]
    foreach probe [get_hw_probes -of_objects $P04D_VIO] {
        if {[string tolower [get_property TYPE $probe]] eq $wanted &&
            [get_property PROBE_PORT $probe] == $port} { return $probe }
    }
    error "P04 reset diagnostic probe not found: direction=$direction port=$port"
}
proc p04d_input {port} {
    global P04D_VIO
    refresh_hw_vio $P04D_VIO
    return [p04d_parse [get_property INPUT_VALUE [p04d_probe vio_input $port]]]
}
proc p04d_set_output {port value} {
    global P04D_VIO
    set probe [p04d_probe vio_output $port]
    set bits [get_property PROBE_PORT_BIT_COUNT $probe]
    set chars [expr {($bits + 3) / 4}]
    set formatted [format %0*X $chars $value]
    set_property OUTPUT_VALUE $formatted $probe
    commit_hw_vio $P04D_VIO
}
proc p04d_snapshot {label} {
    set heartbeat [p04d_input 38]
    set ready0 [p04d_input 39]
    set ready1 [p04d_input 40]
    set idle0 [p04d_input 41]
    set idle1 [p04d_input 42]
    set rawclk [p04d_input 45]
    set resetn [p04d_input 46]
    puts "P04 RESET DIAG $label raw_clock_count=$rawclk peripheral_aresetn=$resetn heartbeat=$heartbeat core_ready=$ready0,$ready1 core_idle=$idle0,$idle1"
    return [list $rawclk $resetn $heartbeat]
}

open_hw_manager
connect_hw_server -url $hw_server_url
set targets [get_hw_targets]
if {[llength $targets] == 0} { error "P04 reset diagnostic found no hardware targets" }
current_hw_target [lindex $targets 0]
open_hw_target

set P04D_DEVICE ""
foreach device [get_hw_devices] {
    if {[regexp -nocase {(xczu|xck26)} [get_property NAME $device]]} {
        set P04D_DEVICE $device
        break
    }
}
if {$P04D_DEVICE eq ""} { error "P04 reset diagnostic could not identify K26 device" }
current_hw_device $P04D_DEVICE
refresh_hw_device -update_hw_probes false $P04D_DEVICE
set_property PROGRAM.FILE $bit_file $P04D_DEVICE
if {[lsearch -exact [list_property $P04D_DEVICE] PROBES.FILE] >= 0} {
    set_property PROBES.FILE $ltx_file $P04D_DEVICE
}
if {[lsearch -exact [list_property $P04D_DEVICE] FULL_PROBES.FILE] >= 0} {
    set_property FULL_PROBES.FILE $ltx_file $P04D_DEVICE
}
program_hw_devices $P04D_DEVICE
refresh_hw_device $P04D_DEVICE

set vios [get_hw_vios -of_objects $P04D_DEVICE]
if {[llength $vios] != 1} { error "P04 reset diagnostic expected one VIO, got $vios" }
set P04D_VIO [lindex $vios 0]
foreach probe [get_hw_probes -of_objects $P04D_VIO] {
    set type [string tolower [get_property TYPE $probe]]
    if {$type eq "vio_input"} { catch {set_property INPUT_VALUE_RADIX HEX $probe} }
    if {$type eq "vio_output"} { catch {set_property OUTPUT_VALUE_RADIX HEX $probe} }
}
reset_hw_vio_outputs $P04D_VIO
refresh_hw_vio -update_output_values $P04D_VIO

set s0 [p04d_snapshot initial_a]
after 20
set s1 [p04d_snapshot initial_b]

# Assert active-high external reset.
p04d_set_output 2 1
after 20
set sr [p04d_snapshot reset_asserted]

# Release external reset and observe the synchronized reset output twice.
p04d_set_output 2 0
after 20
set s2 [p04d_snapshot released_a]
after 20
set s3 [p04d_snapshot released_b]

set raw0 [lindex $s2 0]
set raw1 [lindex $s3 0]
set resetn [lindex $s3 1]
set hb0 [lindex $s2 2]
set hb1 [lindex $s3 2]

puts "P04 RESET DIAG SUMMARY raw_clock_changed=[expr {$raw0 != $raw1}] peripheral_aresetn=$resetn heartbeat_changed=[expr {$hb0 != $hb1}]"
if {$raw0 == $raw1} {
    puts "P04 RESET DIAG RESULT=PL_CLOCK_NOT_TOGGLING"
} elseif {$resetn != 1} {
    puts "P04 RESET DIAG RESULT=PROC_SYS_RESET_STILL_ASSERTED"
} elseif {$hb0 == $hb1} {
    puts "P04 RESET DIAG RESULT=HEARTBEAT_PATH_FAULT"
} else {
    puts "P04 RESET DIAG RESULT=CLOCK_AND_RESET_GOOD"
}
close_hw_manager
