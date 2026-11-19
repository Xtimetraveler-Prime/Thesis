# M08 D3.2 PASSIVE FAN SYNTHESIS-ONLY PC CHECKPOINT (not a protected AXI image).
# Must run AFTER a FRESH invocation of m08_d3a_passive_fan_bd_candidate.tcl
# in the SAME NEW M08_D3.2 evidence directory. NEVER use an older owner run.
# No HPM, SmartConnect, AXI page, identity slave, DTBO, bitstream or hardware.
# No launch_runs impl_1, write_bitstream, packaging, SSH, JTAG or PS MMIO.
# This script is intended for genuine OWNER-PC Vivado 2025.2 only.
if {[llength $argv] != 1} {
    error "usage: m08_d3_2_passive_synth_only.tcl <NEW-run/output>"
}
if {![string match "2025.2*" [version -short]]} {
    error "M08 D3.2 PASSIVE synthesis requires genuine Vivado 2025.2"
}
set out [file normalize [lindex $argv 0]]
set run [file dirname $out]
set base [file normalize [file join $::env(HOME) Thesis_Evidence M08]]
if {[file tail $out] ne "output" ||
    ![regexp {^m08_d3_2_passive_synth_[a-zA-Z0-9]+$} [file tail $run]] ||
    [file dirname $run] ne $base} {
    error "M08 D3.2 passive synthesis only allowed under NEW owner M08 evidence folder"
}
if {![file isdirectory $out] || [file type $out] ne "directory"} {
    error "M08 D3.2 missing original new-run BD output folder"
}
set native_report [file join $out 10_d3a_passive_bd_readback.txt]
set original_xdc [file join $out 12_d3a_fan_a12.xdc]
set original_export [file join $out 11_d3a_passive_bd_export.tcl]
set xpr [file join $out d3a_project m08_d3a_passive_fan.xpr]
set synth_report [file join $out 20_passive_synth_readback.txt]
set util_report [file join $out 21_passive_synth_utilization.rpt]
set timing_report [file join $out 22_passive_synth_timing.rpt]
foreach f [list $native_report $original_xdc $original_export $xpr] {
    if {![file isfile $f] || [file type $f] ne "file"} {
        error "M08 D3.2 missing/linked fresh passive BD project input: $f"
    }
}
foreach f [list $synth_report $util_report $timing_report] {
    if {[file exists $f]} {
        error "M08 D3.2 synthesizer refuses to overwrite any prior evidence: $f"
    }
}
set fd [open $native_report r]
set native_text [read $fd]
close $fd
foreach expected {
    "schema=m08-d3a-kv260-passive-fan-bd-v1"
    "ps_hpm0_fpd=DISABLED"
    "ps_hpm1_fpd=DISABLED"
    "ps_hpm0_lpd=DISABLED"
    "smartconnect=ABSENT"
    "identity_slave=ABSENT"
    "page_slave=ABSENT"
    "linux_uio_devices=ZERO"
    "fan_route=TTC0_WAVEOUT2_TO_A12"
    "validated_bd=YES"
    "synthesis=NOT_RUN"
    "implementation=NOT_RUN"
    "bitstream=NOT_GENERATED"
    "hardware_mmio_authorized=NO"
} {
    if {[lsearch -exact [split $native_text "\n"] $expected] < 0} {
        error "M08 D3.2 source BD native report lacks REQUIRED no-AXI assertion: $expected"
    }
}
set fd [open $original_xdc r]
set fan_xdc_text [read $fd]
close $fd
foreach line {
    "set_property PACKAGE_PIN A12 [get_ports {M08_FAN_PWM}]"
    "set_property IOSTANDARD LVCMOS33 [get_ports {M08_FAN_PWM}]"
} {
    if {[lsearch -exact [split $fan_xdc_text "\n"] $line] < 0} {
        error "M08 D3.2 fan XDC lost required A12/LVCMOS33 constraint"
    }
}
open_project $xpr
if {[get_property PART [current_project]] ne "xck26-sfvc784-2LV-c"} {
    error "M08 D3.2 passive synthesis opened wrong K26 part"
}
if {![string match "xilinx.com:kv260_som:part0:*" \
        [get_property BOARD_PART [current_project]]]} {
    error "M08 D3.2 passive synthesis opened project without KV260 board preset"
}
set bd_files [get_files -all -quiet *m08_d3a_passive_fan.bd]
if {[llength $bd_files] != 1} {
    error "M08 D3.2 expected exactly one passive BD file, no other design"
}
open_bd_design [lindex $bd_files 0]
foreach prop {
    CONFIG.PSU__USE__M_AXI_GP0
    CONFIG.PSU__USE__M_AXI_GP1
    CONFIG.PSU__USE__M_AXI_GP2
} {
    if {[string trim [get_property $prop [get_bd_cells ps]]] ne "0"} {
        error "M08 D3.2 reopened PS HPM master unexpectedly ENABLED: $prop"
    }
}
foreach iface {
    ps/M_AXI_HPM0_FPD ps/M_AXI_HPM1_FPD ps/M_AXI_HPM0_LPD
} {
    if {[llength [get_bd_intf_pins -quiet $iface]] != 0} {
        error "M08 D3.2 reopened BD exposes forbidden PS->PL AXI interface: $iface"
    }
}
foreach cell {
    ctrl_sc identity page
} {
    if {[llength [get_bd_cells -quiet $cell]] != 0} {
        error "M08 D3.2 passive BD unexpectedly contains original AXI cell: $cell"
    }
}
if {[llength [get_bd_ports -quiet M08_FAN_PWM]] != 1} {
    error "M08 D3.2 fan-only port disappeared"
}
validate_bd_design -force
# Re-check after Vivado validation in case a PS interface was regenerated.
foreach iface {
    ps/M_AXI_HPM0_FPD ps/M_AXI_HPM1_FPD ps/M_AXI_HPM0_LPD
} {
    if {[llength [get_bd_intf_pins -quiet $iface]] != 0} {
        error "M08 D3.2 forbidden AXI interface regenerated: $iface"
    }
}
generate_target all $bd_files
set wrapper [make_wrapper -files $bd_files -top]
if {[llength $wrapper] != 1 || ![file isfile [lindex $wrapper 0]]} {
    error "M08 D3.2 synthesis wrapper not generated"
}
add_files -norecurse $wrapper
set_property top m08_d3a_passive_fan_wrapper [current_fileset]
update_compile_order -fileset sources_1
if {[get_property top [current_fileset]] ne "m08_d3a_passive_fan_wrapper"} {
    error "M08 D3.2 synthesis top not passive fan wrapper"
}
# Critical boundary: launch synth_1 ONLY. Do not run impl_1 or generate .bit.
launch_runs synth_1 -jobs 2
wait_on_run synth_1
set run_status [get_property STATUS [get_runs synth_1]]
set progress [get_property PROGRESS [get_runs synth_1]]
if {![string match "*Complete!*" $run_status] || $progress ne "100%"} {
    error "M08 D3.2 genuine passive synthesis did not complete: $run_status ($progress)"
}
open_run synth_1
if {[llength [get_ports -quiet M08_FAN_PWM]] != 1} {
    error "M08 D3.2 synthesizer removed fan output; no valid checkpoint"
}
if {[get_property PACKAGE_PIN [get_ports M08_FAN_PWM]] ne "A12"} {
    error "M08 D3.2 synthesizer lost A12 package constraint"
}
if {[get_property IOSTANDARD [get_ports M08_FAN_PWM]] ne "LVCMOS33"} {
    error "M08 D3.2 synthesizer lost LVCMOS33 fan I/O constraint"
}
report_utilization -file $util_report
report_timing_summary -file $timing_report
set fd [open $synth_report {WRONLY CREAT EXCL}]
puts $fd {schema=m08-d3-2-passive-synth-only-v1}
puts $fd {candidate=m08-d3a-passive-fan-v1}
puts $fd "vivado_version=[version -short]"
puts $fd "part=[get_property PART [current_project]]"
puts $fd "board_part=[get_property BOARD_PART [current_project]]"
puts $fd "synth_run_status=$run_status"
puts $fd "synth_run_progress=$progress"
puts $fd {ps_to_pl_axi=DISABLED}
puts $fd {smartconnect=ABSENT}
puts $fd {identity_slave=ABSENT}
puts $fd {page_slave=ABSENT}
puts $fd {fan_port=M08_FAN_PWM}
puts $fd {fan_pin=A12}
puts $fd {fan_iostandard=LVCMOS33}
puts $fd {timing_report=GENERATED_NOT_ROUTED}
puts $fd {implementation=NOT_RUN}
puts $fd {bitstream=NOT_GENERATED}
puts $fd {linux_dtbo=NOT_GENERATED}
puts $fd {physical_fan_cooling=NOT_PROVEN}
puts $fd {boot_atb4_aib13_afi_clock_ownership=UNKNOWN}
puts $fd {hardware_programmed=NO}
puts $fd {hardware_mmio_authorized=NO}
close $fd
puts {M08_D3_2_PASSIVE_SYNTH_COMPLETE_NO_AXI_NO_IMPL_NO_BITSTREAM_NO_BOARD}
