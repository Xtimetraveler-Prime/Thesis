# Arm/capture the two-slot P03.2c HPM0 System ILA.
#
# SLOT_0_AXI monitors PS M_AXI_HPM0_FPD -> AXI Protocol Converter.
# SLOT_1_AXI monitors AXI Protocol Converter -> p03_ps_control_regs.
#
# The script triggers on SLOT_0 read-address VALID. The wrapper halts all A53
# cores before arming and issues exactly one physical MMIO read after the
# P03_2C_ILA_ARMED marker is created.
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

proc p03_hpm0_ila {device} {
    set all_ilas [get_hw_ilas -of_objects $device]
    if {[llength $all_ilas] == 1} {
        return [lindex $all_ilas 0]
    }

    set matches {}
    foreach candidate $all_ilas {
        set found_upstream 0
        set found_downstream 0
        foreach probe [get_hw_probes -of_objects $candidate] {
            set pname [string tolower [get_property NAME $probe]]
            if {[string match "*p03_hpm0_ps_to_converter_axi*" $pname]} {
                set found_upstream 1
            }
            if {[string match "*p03_hpm0_converter_to_mmio_axi*" $pname]} {
                set found_downstream 1
            }
        }
        if {$found_upstream && $found_downstream} {
            lappend matches $candidate
        }
    }
    if {[llength $matches] != 1} {
        puts "P03_2C_ILA_AVAILABLE=$all_ilas"
        error "P03.2c expected exactly one HPM0 System ILA, got [llength $matches]"
    }
    return [lindex $matches 0]
}

proc p03_slot0_arvalid_probe {ila} {
    set matches {}
    foreach probe [get_hw_probes -of_objects $ila] {
        set name [string tolower [get_property NAME $probe]]
        if {[string match "*p03_hpm0_ps_to_converter_axi*arvalid*" $name] ||
            [string match "*slot_0*arvalid*" $name] ||
            [string match "*slot0*arvalid*" $name]} {
            lappend matches $probe
        }
    }
    if {[llength $matches] != 1} {
        puts "P03_2C_ILA_PROBE_INVENTORY_BEGIN"
        foreach probe [get_hw_probes -of_objects $ila] {
            puts "P03_2C_ILA_PROBE=[get_property NAME $probe]"
        }
        puts "P03_2C_ILA_PROBE_INVENTORY_END"
        error "P03.2c could not uniquely identify SLOT_0 ARVALID probe"
    }
    return [lindex $matches 0]
}

open_hw_manager
connect_hw_server -url $server_url
open_hw_target
set device [p03_k26_device]
current_hw_device $device
set_property PROBES.FILE $ltx_file $device
catch {set_property FULL_PROBES.FILE $ltx_file $device}
refresh_hw_device $device

set ila [p03_hpm0_ila $device]
puts "P03_2C_ILA_OBJECT=$ila"
puts "P03_2C_ILA_CELL=[get_property CELL_NAME $ila]"

puts "P03_2C_ILA_PROBE_INVENTORY_BEGIN"
foreach probe [get_hw_probes -of_objects $ila] {
    puts "P03_2C_ILA_PROBE=[get_property NAME $probe]"
    catch {set_property DISPLAY_RADIX HEX $probe}
    catch {set_property DISPLAY_AS_ENUM false $probe}
    catch {set_property TRIGGER_COMPARE_VALUE X $probe}
}
puts "P03_2C_ILA_PROBE_INVENTORY_END"

set arvalid_probe [p03_slot0_arvalid_probe $ila]
puts "P03_2C_ILA_TRIGGER_PROBE=[get_property NAME $arvalid_probe]"

reset_hw_ila $ila
set_property CONTROL.WINDOW_COUNT 1 $ila
set_property CONTROL.TRIGGER_POSITION 512 $ila
set_property CONTROL.TRIGGER_MODE BASIC_ONLY $ila
set_property CONTROL.TRIGGER_CONDITION AND $ila
set_property CONTROL.CAPTURE_MODE ALWAYS $ila
set_property TRIGGER_COMPARE_VALUE "eq1'b1" $arvalid_probe

run_hw_ila $ila

set mf [open $armed_marker w]
puts $mf "armed"
close $mf
puts "P03_2C_ILA_ARMED=1"
flush stdout

wait_on_hw_ila -timeout 30 $ila
set data [upload_hw_ila_data $ila]

set ila_path [file join $output_dir p03_2c_hpm0_capture.ila]
set csv_path [file join $output_dir p03_2c_hpm0_capture.csv]
set vcd_path [file join $output_dir p03_2c_hpm0_capture.vcd]
write_hw_ila_data -force $ila_path $data
write_hw_ila_data -force -csv_file $csv_path $data
write_hw_ila_data -force -vcd_file $vcd_path $data

puts "P03_2C_ILA_CAPTURE_ILA=$ila_path"
puts "P03_2C_ILA_CAPTURE_CSV=$csv_path"
puts "P03_2C_ILA_CAPTURE_VCD=$vcd_path"
puts "PASS: P03.2c HPM0 System ILA capture completed"

close_hw_manager
