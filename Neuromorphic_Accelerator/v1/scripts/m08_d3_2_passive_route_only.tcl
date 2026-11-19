# M08 D3.2 passive KV260 offline place-and-route EVIDENCE ONLY.
# NEVER generate .bit/.bin/.dtbo or touch hardware; HPM0/HPM1/LPD disabled.
# Operates only on NEW private synthesis folder produced in this route run.
if {[llength $argv] != 1} {
    error "usage: m08_d3_2_passive_route_only.tcl <NEW-passive-synth/output>"
}
if {![string match "2025.2*" [version -short]]} {
    error "M08 D3.2 route requires original local Vivado 2025.2"
}
set out [file normalize [lindex $argv 0]]
set run [file dirname $out]
set base [file normalize [file join $::env(HOME) Thesis_Evidence M08]]
if {[file tail $out] ne "output" ||
    ![regexp {^m08_d3_2_passive_synth_[a-zA-Z0-9]+$} [file tail $run]] ||
    [file dirname $run] ne $base} {
    error "M08 D3.2 route refused non-fresh owner PC evidence path"
}
foreach name {
    10_d3a_passive_bd_readback.txt
    12_d3a_fan_a12.xdc
    20_passive_synth_readback.txt
    21_passive_synth_utilization.rpt
    22_passive_synth_timing.rpt
} {
    set candidate [file join $out $name]
    if {![file isfile $candidate] || [file type $candidate] ne "file"} {
        error "M08 D3.2 missing fresh synthesis artifact: $name"
    }
}
set status_file [file join $out 40_passive_route_readback.txt]
set timing_file [file join $out 41_passive_route_timing.rpt]
set drc_file [file join $out 42_passive_route_drc.rpt]
set util_file [file join $out 43_passive_route_utilization.rpt]
set clock_file [file join $out 44_passive_route_clocks.rpt]
foreach name [list $status_file $timing_file $drc_file $util_file $clock_file] {
    if {[file exists $name]} {error "M08 D3.2 route refuses to overwrite: $name"}
}
set xpr [file join $out d3a_project m08_d3a_passive_fan.xpr]
if {![file isfile $xpr] || [file type $xpr] ne "file"} {
    error "M08 D3.2 expected fresh passive Vivado project missing"
}
set fh [open [file join $out 20_passive_synth_readback.txt] r]
set synth_text [read $fh]
close $fh
foreach expected {
    "schema=m08-d3-2-passive-synth-only-v1"
    "ps_to_pl_axi=DISABLED"
    "smartconnect=ABSENT"
    "identity_slave=ABSENT"
    "page_slave=ABSENT"
    "fan_pin=A12"
    "synth_run_progress=100%"
    "implementation=NOT_RUN"
    "bitstream=NOT_GENERATED"
    "hardware_mmio_authorized=NO"
} {
    if {[lsearch -exact [split $synth_text "\n"] $expected] < 0} {
        error "M08 D3.2 route cannot trust synthetic-only parent: $expected"
    }
}
open_project $xpr
if {[get_property PART [current_project]] ne "xck26-sfvc784-2LV-c" ||
    ![string match "xilinx.com:kv260_som:part0:*" [get_property BOARD_PART [current_project]]]} {
    error "M08 D3.2 route target is not original KV260 K26"
}
set bds [get_files -all -quiet *m08_d3a_passive_fan.bd]
if {[llength $bds] != 1} {error "M08 D3.2 route unexpected BD set"}
open_bd_design [lindex $bds 0]
foreach prop {
    CONFIG.PSU__USE__M_AXI_GP0
    CONFIG.PSU__USE__M_AXI_GP1
    CONFIG.PSU__USE__M_AXI_GP2
} {
    if {[string trim [get_property $prop [get_bd_cells ps]]] ne "0"} {
        error "M08 D3.2 route PS AXI interface re-enabled: $prop"
    }
}
foreach iface {
    ps/M_AXI_HPM0_FPD ps/M_AXI_HPM1_FPD ps/M_AXI_HPM0_LPD
} {
    if {[llength [get_bd_intf_pins -quiet $iface]] != 0} {
        error "M08 D3.2 route unexpectedly connected PS AXI: $iface"
    }
}
foreach cell {ctrl_sc identity page} {
    if {[llength [get_bd_cells -quiet $cell]] != 0} {
        error "M08 D3.2 route contains forbidden AXI cell: $cell"
    }
}
if {[llength [get_bd_ports -quiet M08_FAN_PWM]] != 1} {
    error "M08 D3.2 route lost TTC0 fan output"
}
set sr [get_runs synth_1]
if {[llength $sr] != 1 || [get_property PROGRESS $sr] ne "100%" ||
    ![string match "*Complete!*" [get_property STATUS $sr]]} {
    error "M08 D3.2 route requires completed genuine synthesis"
}
# Physical implementation through route_design ONLY, no write_bitstream.
launch_runs impl_1 -to_step route_design -jobs 2
wait_on_run impl_1
set ir [get_runs impl_1]
set step_status [get_property STATUS $ir]
set step_progress [get_property PROGRESS $ir]
if {![string match "*Complete!*" $step_status] || $step_progress ne "100%"} {
    error "M08 D3.2 route_design failed: $step_status ($step_progress)"
}
open_run impl_1
if {[llength [get_ports -quiet M08_FAN_PWM]] != 1} {
    error "M08 D3.2 implemented fan output missing"
}
if {[get_property PACKAGE_PIN [get_ports M08_FAN_PWM]] ne "A12" ||
    [get_property IOSTANDARD [get_ports M08_FAN_PWM]] ne "LVCMOS33"} {
    error "M08 D3.2 implemented fan pin/IOSTANDARD drift"
}
# Read-only netlist reports; all raw violations must be independently reviewed.
report_timing_summary -file $timing_file
report_drc -file $drc_file
report_utilization -file $util_file
report_clocks -file $clock_file
set fh [open $status_file {WRONLY CREAT EXCL}]
puts $fh {schema=m08-d3-2-passive-route-only-v1}
puts $fh {candidate=m08-d3a-passive-fan-v1}
puts $fh "vivado_version=[version -short]"
puts $fh "part=[get_property PART [current_project]]"
puts $fh "board_part=[get_property BOARD_PART [current_project]]"
puts $fh "route_run_status=$step_status"
puts $fh "route_run_progress=$step_progress"
puts $fh {ps_to_pl_axi=DISABLED}
puts $fh {fan_port=M08_FAN_PWM}
puts $fh {fan_pin=A12}
puts $fh {fan_iostandard=LVCMOS33}
puts $fh {report_drc=GENERATED_NOT_A_PASS_CLAIM}
puts $fh {report_timing=GENERATED_NOT_A_PASS_CLAIM}
puts $fh {report_clocks=GENERATED_NOT_A_PASS_CLAIM}
puts $fh {bitstream=NOT_GENERATED}
puts $fh {dtbo=NOT_GENERATED}
puts $fh {board_programmed=NO}
puts $fh {hardware_mmio_authorized=NO}
puts $fh {physical_fan_continuity=NOT_PROVEN}
close $fh
puts {M08_D3_2_PASSIVE_ROUTE_COMPLETE_REPORTS_NOT_REVIEWED_NO_BITSTREAM_NO_BOARD}
