# P03.2c dual-analyzer diagnostic capture.
# System ILA: PS HPM0 AXI4 -> AXI Protocol Converter (one interface slot).
# Native ILA: passive read-channel taps at p03_ps_control_regs AXI4-Lite.
#
# Both analyzers are armed before the wrapper issues one physical 32-bit read.
if {$argc < 3 || $argc > 4} {
    error "usage: p03_2c_ila_capture.tcl <output_dir> <armed_marker> <ltx> ?<hw_server_url>?"
}
set output_dir [file normalize [lindex $argv 0]]
set armed_marker [file normalize [lindex $argv 1]]
set ltx_file [file normalize [lindex $argv 2]]
set server_url "localhost:3121"
if {$argc == 4} { set server_url [lindex $argv 3] }

if {![file exists $ltx_file]} { error "P03.2c ILA probes file missing: $ltx_file" }
file mkdir $output_dir
file delete -force $armed_marker

proc p03_k26_device {} {
    foreach candidate [get_hw_devices] {
        set name [string tolower [get_property NAME $candidate]]
        set part ""
        catch {set part [string tolower [get_property PART $candidate]]}
        if {[string match "*xck26*" $name] || [string match "*xczu5*" $name] ||
            [string match "*xck26*" $part] || [string match "*xczu5*" $part]} {
            return $candidate
        }
    }
    error "P03.2c ILA capture could not identify K26 device"
}

proc p03_ila_by_cell {device needle} {
    set matches {}
    foreach ila [get_hw_ilas -of_objects $device] {
        set name [string tolower [get_property CELL_NAME $ila]]
        if {[string match "*$needle*" $name]} {
            lappend matches $ila
        }
    }
    if {[llength $matches] != 1} {
        puts "P03_2C_ILA_AVAILABLE=[get_hw_ilas -of_objects $device]"
        error "Expected one ILA with cell name containing $needle, got $matches"
    }
    return [lindex $matches 0]
}

proc p03_dump_probes {ila tag} {
    puts "P03_2C_ILA_${tag}_PROBES_BEGIN"
    foreach probe [get_hw_probes -of_objects $ila] {
        puts "P03_2C_ILA_${tag}_PROBE=[get_property NAME $probe]"
        catch {set_property DISPLAY_RADIX HEX $probe}
    }
    puts "P03_2C_ILA_${tag}_PROBES_END"
}

proc p03_trigger_probe {ila patterns} {
    set matches {}
    foreach probe [get_hw_probes -of_objects $ila] {
        set name [string tolower [get_property NAME $probe]]
        foreach pattern $patterns {
            if {[string match $pattern $name]} {
                lappend matches $probe
                break
            }
        }
    }
    if {[llength $matches] != 1} {
        error "P03.2c could not uniquely identify ARVALID trigger among [get_hw_probes -of_objects $ila] using $patterns; matches=$matches"
    }
    return [lindex $matches 0]
}

proc p03_arm_ila {ila trigger} {
    # reset_hw_ila establishes BASIC_ONLY / AND / ALWAYS / 1 window.
    # On the physical P03.2c System ILA, Vivado 2025.2 reports
    # CONTROL.TRIGGER_MODE as read-only even though older versions and
    # generic UG835 examples allow set_property. Never write a control
    # property when the required default is already in effect.
    reset_hw_ila $ila
    foreach {property expected} {
        CONTROL.TRIGGER_MODE BASIC_ONLY
        CONTROL.TRIGGER_CONDITION AND
        CONTROL.CAPTURE_MODE ALWAYS
        CONTROL.WINDOW_COUNT 1
    } {
        set actual [get_property $property $ila]
        puts "P03_2C_ILA_DEFAULT_${property}=$actual"
        if {$actual ne $expected} {
            error "P03.2c ILA $ila default $property expected $expected, got $actual"
        }
    }
    # Default TRIGGER_POSITION=0 gives a post-trigger read response window.
    # The read transaction is initiated only after BOTH analyzers are armed.
    # Leave CONTROL properties at their verified reset defaults and only
    # configure the probe comparator used for the basic hardware trigger.
    set_property TRIGGER_COMPARE_VALUE "eq1'b1" $trigger
    puts "P03_2C_ILA_ARM_TRIGGER=[get_property NAME $trigger]"
    run_hw_ila $ila
}

proc p03_export_ila {ila dir stem timeout_seconds} {
    if {[catch {wait_on_hw_ila -timeout $timeout_seconds $ila} detail]} {
        puts "P03_2C_ILA_NO_TRIGGER=${stem}:$detail"
        return 0
    }
    set data [upload_hw_ila_data $ila]
    set path [file join $dir $stem]
    write_hw_ila_data -force "${path}.ila" $data
    write_hw_ila_data -force -csv_file "${path}.csv" $data
    write_hw_ila_data -force -vcd_file "${path}.vcd" $data
    puts "P03_2C_ILA_CAPTURE=${path}.ila"
    puts "P03_2C_ILA_CAPTURE=${path}.csv"
    puts "P03_2C_ILA_CAPTURE=${path}.vcd"
    return 1
}

open_hw_manager
connect_hw_server -url $server_url
open_hw_target
set device [p03_k26_device]
current_hw_device $device
set_property PROBES.FILE $ltx_file $device
catch {set_property FULL_PROBES.FILE $ltx_file $device}
refresh_hw_device $device

set upstream [p03_ila_by_cell $device "system_ila"]
set downstream [p03_ila_by_cell $device "p03_mmio_native_ila"]
puts "P03_2C_ILA_UPSTREAM_CELL=[get_property CELL_NAME $upstream]"
puts "P03_2C_ILA_DOWNSTREAM_CELL=[get_property CELL_NAME $downstream]"
p03_dump_probes $upstream UPSTREAM
p03_dump_probes $downstream DOWNSTREAM

set upstream_arvalid [p03_trigger_probe $upstream {
    *p03_hpm0_ps_to_converter_axi*arvalid* *slot_0*arvalid* *slot0*arvalid*
}]
set downstream_arvalid [p03_trigger_probe $downstream {
    *p03_diag_arvalid* *probe0*
}]
p03_arm_ila $upstream $upstream_arvalid
p03_arm_ila $downstream $downstream_arvalid

set marker [open $armed_marker w]
puts $marker "armed"
close $marker
puts "P03_2C_ILA_ARMED=1"
flush stdout

# Export upstream first: even if the converter never reaches the AXI4-Lite
# slave and its native ILA does not trigger, the upstream capture is evidence.
set upstream_ok [p03_export_ila $upstream $output_dir p03_2c_hpm0_capture 30]
set downstream_ok [p03_export_ila $downstream $output_dir p03_2c_mmio_slave_capture 15]

close_hw_manager
if {!$upstream_ok} { error "P03.2c upstream PS HPM0 read did not trigger" }
if {!$downstream_ok} {
    puts "P03_2C_ILA_INFO=Upstream captured; downstream did not trigger. Inspect upstream evidence."
    error "P03.2c downstream MMIO slave read did not trigger; upstream evidence preserved."
}
puts "PASS: P03.2c dual ILA read-channel capture completed"
