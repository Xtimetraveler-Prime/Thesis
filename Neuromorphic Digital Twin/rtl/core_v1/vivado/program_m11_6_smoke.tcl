# Program the M11.6 K26 bitstream and execute the autonomous VIO/JTAG smoke.
if {$argc != 2} {
    error "usage: program_m11_6_smoke.tcl <bitstream> <ltx>"
}
set bitstream [file normalize [lindex $argv 0]]
set probes    [file normalize [lindex $argv 1]]
foreach path [list $bitstream $probes] {
    if {![file exists $path]} {
        error "Required M11.6 hardware artifact does not exist: $path"
    }
}

proc find_one_probe {vio needle} {
    set matches {}
    foreach probe [get_hw_probes -quiet -of_objects $vio] {
        set name [get_property NAME $probe]
        if {[string match "*${needle}*" $name]} {
            lappend matches $probe
        }
    }
    if {[llength $matches] != 1} {
        set available {}
        foreach probe [get_hw_probes -quiet -of_objects $vio] {
            lappend available [get_property NAME $probe]
        }
        error "Expected exactly one VIO probe matching '$needle'; matches=$matches available=$available"
    }
    return [lindex $matches 0]
}

open_hw_manager
connect_hw_server
open_hw_target

set candidates [get_hw_devices -quiet *xck26*]
if {[llength $candidates] == 0} {
    # Some cable/server combinations use a generic device name. Fall back to a
    # single discovered device rather than guessing when multiple devices exist.
    set candidates [get_hw_devices -quiet]
}
if {[llength $candidates] != 1} {
    error "M11.6 expected exactly one target hardware device; found: $candidates"
}
set dev [lindex $candidates 0]
current_hw_device $dev
puts "M11.6 hardware device: [get_property NAME $dev]"

set_property PROGRAM.FILE $bitstream $dev
set_property PROBES.FILE $probes $dev
program_hw_devices $dev
refresh_hw_device $dev
puts "M11.6 bitstream programmed successfully."

set vios [get_hw_vios -quiet]
if {[llength $vios] != 1} {
    error "M11.6 expected exactly one VIO core after programming; found: $vios"
}
set vio [lindex $vios 0]
puts "M11.6 VIO core: [get_property NAME $vio]"

set p_start     [find_one_probe $vio smoke_start]
set p_resetn    [find_one_probe $vio smoke_resetn]
set p_heartbeat [find_one_probe $vio clock_heartbeat]
set p_busy  [find_one_probe $vio smoke_busy]
set p_done  [find_one_probe $vio smoke_done]
set p_pass  [find_one_probe $vio smoke_pass]
set p_fail  [find_one_probe $vio smoke_fail_code]
set p_phase [find_one_probe $vio smoke_phase]
set p_tick  [find_one_probe $vio observed_tick]
set p_fault [find_one_probe $vio observed_core_fault_code]
set p_s0    [find_one_probe $vio observed_state0]
set p_s1    [find_one_probe $vio observed_state1]
set p_s2    [find_one_probe $vio observed_state2]
set p_spike [find_one_probe $vio observed_spikes]
set p_bank  [find_one_probe $vio observed_recurrent_bank]
set p_count [find_one_probe $vio observed_recurrent_count]

# Synchronize Tcl-side values with the freshly programmed VIO. Both command
# outputs initialize low: smoke_start=0 and smoke_resetn=0. Before releasing the
# reset, prove that the reset-independent heartbeat advances on the physical PL0
# clock. This distinguishes clock failure from reset/datapath failure.
refresh_hw_vio -update_output_values $vio
set_property OUTPUT_VALUE 0 $p_start
commit_hw_vio $p_start
set_property OUTPUT_VALUE 0 $p_resetn
commit_hw_vio $p_resetn
refresh_hw_vio $vio
set heartbeat_before [get_property INPUT_VALUE $p_heartbeat]
after 100
refresh_hw_vio $vio
set heartbeat_after [get_property INPUT_VALUE $p_heartbeat]
if {$heartbeat_before eq $heartbeat_after} {
    error "M11.6 PL clock heartbeat did not advance: value=$heartbeat_before. Verify pl_clk0 before debugging reset or datapath logic."
}
puts "M11.6 PL clock heartbeat advanced: $heartbeat_before -> $heartbeat_after"

# Release the local reset through VIO. proc_sys_reset synchronizes this active-low
# command to pl_clk0, driving peripheral_aresetn to the smoke controller and the
# matching active-high peripheral_reset to the packaged HLS IP. Read the VIO
# output back from hardware before proceeding so a host-side set/commit mismatch
# cannot masquerade as an internal reset failure.
set_property OUTPUT_VALUE 1 $p_resetn
commit_hw_vio $p_resetn
after 20
refresh_hw_vio -update_output_values $vio
set reset_readback [get_property OUTPUT_VALUE $p_resetn]
if {$reset_readback ne "1"} {
    error "M11.6 smoke_resetn VIO readback mismatch after release: expected=1 actual=$reset_readback"
}
puts "M11.6 local smoke reset released through VIO; output readback=$reset_readback"

# Hold start high long enough to read the actual hardware VIO output back before
# returning it low. The smoke FSM edge-detects the rising edge, so the extended
# diagnostic pulse does not alter the autonomous workload semantics.
set_property OUTPUT_VALUE 1 $p_start
commit_hw_vio $p_start
after 10
refresh_hw_vio -update_output_values $vio
set start_high_readback [get_property OUTPUT_VALUE $p_start]
if {$start_high_readback ne "1"} {
    error "M11.6 smoke_start VIO readback mismatch while asserted: expected=1 actual=$start_high_readback"
}
puts "M11.6 smoke_start asserted through VIO; output readback=$start_high_readback"
set_property OUTPUT_VALUE 0 $p_start
commit_hw_vio $p_start
after 2
refresh_hw_vio -update_output_values $vio
set start_low_readback [get_property OUTPUT_VALUE $p_start]
if {$start_low_readback ne "0"} {
    error "M11.6 smoke_start VIO readback mismatch after deassertion: expected=0 actual=$start_low_readback"
}
puts "M11.6 smoke_start pulse committed through VIO; final output readback=$start_low_readback"

set completed 0
for {set attempt 0} {$attempt < 500} {incr attempt} {
    refresh_hw_vio $vio
    if {[get_property INPUT_VALUE $p_done] eq "1"} {
        set completed 1
        break
    }
    after 20
}
refresh_hw_vio $vio

set busy  [get_property INPUT_VALUE $p_busy]
set done  [get_property INPUT_VALUE $p_done]
set pass  [get_property INPUT_VALUE $p_pass]
set fail  [get_property INPUT_VALUE $p_fail]
set phase [get_property INPUT_VALUE $p_phase]
set tick  [get_property INPUT_VALUE $p_tick]
set fault [get_property INPUT_VALUE $p_fault]
set s0    [get_property INPUT_VALUE $p_s0]
set s1    [get_property INPUT_VALUE $p_s1]
set s2    [get_property INPUT_VALUE $p_s2]
set spike [get_property INPUT_VALUE $p_spike]
set bank  [get_property INPUT_VALUE $p_bank]
set count [get_property INPUT_VALUE $p_count]

puts "M11.6 VIO status: busy=$busy done=$done pass=$pass fail_code=$fail phase=$phase tick=$tick core_fault=$fault"
puts "M11.6 VIO neuron state0=$s0 state1=$s1 state2=$s2 spikes=$spike"
puts "M11.6 VIO recurrent bank=$bank count=$count"

if {!$completed} {
    error "M11.6 hardware smoke timed out after clock and VIO-output diagnostics. If status remains at reset values, instrument proc_sys_reset peripheral_aresetn and smoke-start observation before changing computational RTL."
}
if {$pass ne "1"} {
    error "M11.6 physical smoke failed: fail_code=$fail phase=$phase tick=$tick core_fault=$fault"
}

puts "M11.6 physical VIO smoke passed: tick=$tick, fail_code=$fail"
close_hw_manager
