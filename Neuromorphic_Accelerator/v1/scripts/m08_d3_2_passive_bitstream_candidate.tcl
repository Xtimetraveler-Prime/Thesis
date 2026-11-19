# M08 D3.2 PASSIVE FAN BITSTREAM CANDIDATE, OFFLINE PC ONLY.
# Owner requested offline .bit generation, NOT board programming or boot use.
# Only fresh source+route runs allowed; historical evidence must stay intact.
# NO HPM0/HPM1/LPD, SmartConnect, page, identity, Linux UIO or FPGA manager.
# This creates one UNRELEASED .bit from a routed passive design; not .bit.bin.
if {[llength $argv] != 2} {
    error "usage: m08_d3_2_passive_bitstream_candidate.tcl <fresh-run/output> <fresh-run/bitstream_candidate>"
}
if {![string match "2025.2*" [version -short]]} {
    error "M08 D3.2 candidate requires local genuine Vivado 2025.2"
}
set out [file normalize [lindex $argv 0]]
set run [file dirname $out]
set candidate_dir [file normalize [lindex $argv 1]]
set evidence_base [file normalize [file join $::env(HOME) Thesis_Evidence M08]]
if {[file tail $out] ne "output" ||
    ![regexp {^m08_d3_2_passive_synth_[A-Za-z0-9]+$} [file tail $run]] ||
    [file dirname $run] ne $evidence_base ||
    $candidate_dir ne [file join $run bitstream_candidate]} {
    error "M08 D3.2 bitstream candidate refuses nonfresh or external evidence paths"
}
if {![file isdirectory $candidate_dir] ||
    [file type $candidate_dir] ne "directory"} {
    error "M08 D3.2 fresh candidate directory must already exist"
}
foreach f [glob -nocomplain -directory $candidate_dir * .*] {
    if {[file tail $f] ni {. ..}} {
        error "M08 D3.2 candidate folder must be EMPTY to prevent overwrite"
    }
}
foreach required {
    10_d3a_passive_bd_readback.txt
    12_d3a_fan_a12.xdc
    20_passive_synth_readback.txt
    40_passive_route_readback.txt
    41_passive_route_timing.rpt
    42_passive_route_drc.rpt
    43_passive_route_utilization.rpt
    44_passive_route_clocks.rpt
} {
    set f [file join $out $required]
    if {![file isfile $f] || [file type $f] ne "file"} {
        error "M08 D3.2 missing/linked fresh passive evidence: $required"
    }
}
foreach field {
    {schema=m08-d3-2-passive-route-only-v1}
    {route_run_progress=100%}
    {ps_to_pl_axi=DISABLED}
    {fan_port=M08_FAN_PWM}
    {fan_pin=A12}
    {fan_iostandard=LVCMOS33}
    {bitstream=NOT_GENERATED}
    {board_programmed=NO}
    {hardware_mmio_authorized=NO}
} {
    set fd [open [file join $out 40_passive_route_readback.txt] r]
    set route_text [read $fd]
    close $fd
    if {[lsearch -exact [split $route_text "\n"] $field] < 0} {
        error "M08 D3.2 passive route report contract not met: $field"
    }
}
set project [file join $out d3a_project m08_d3a_passive_fan.xpr]
if {![file isfile $project] || [file type $project] ne "file"} {
    error "M08 D3.2 expected genuine fresh passive project missing"
}
open_project $project
if {[get_property PART [current_project]] ne "xck26-sfvc784-2LV-c" ||
    ![string match "xilinx.com:kv260_som:part0:*" [get_property BOARD_PART [current_project]]]} {
    error "M08 D3.2 candidate wrong PS/K26 native part/board"
}
set bds [get_files -all -quiet *m08_d3a_passive_fan.bd]
if {[llength $bds] != 1} {
    error "M08 D3.2 bitgen expects exactly one passive BD"
}
open_bd_design [lindex $bds 0]
foreach prop {
    CONFIG.PSU__USE__M_AXI_GP0
    CONFIG.PSU__USE__M_AXI_GP1
    CONFIG.PSU__USE__M_AXI_GP2
} {
    if {[string trim [get_property $prop [get_bd_cells ps]]] ne "0"} {
        error "M08 D3.2 candidate unexpected PS AXI master: $prop"
    }
}
foreach iface {
    ps/M_AXI_HPM0_FPD ps/M_AXI_HPM1_FPD ps/M_AXI_HPM0_LPD
} {
    if {[llength [get_bd_intf_pins -quiet $iface]] != 0} {
        error "M08 D3.2 candidate exposes unsafe PS-to-PL AXI: $iface"
    }
}
foreach cell {ctrl_sc identity page} {
    if {[llength [get_bd_cells -quiet $cell]] != 0} {
        error "M08 D3.2 passive candidate contains forbidden AXI cell: $cell"
    }
}
if {[llength [get_bd_ports -quiet M08_FAN_PWM]] != 1} {
    error "M08 D3.2 candidate lost fan PWM output"
}
set ir [get_runs impl_1]
if {[llength $ir] != 1 ||
    [get_property PROGRESS $ir] ne "100%" ||
    ![string match "*Complete!*" [get_property STATUS $ir]]} {
    error "M08 D3.2 candidate requires previously completed route_design"
}
open_run impl_1
set fan [get_ports -quiet M08_FAN_PWM]
if {[llength $fan] != 1 ||
    [get_property PACKAGE_PIN $fan] ne "A12" ||
    [get_property IOSTANDARD $fan] ne "LVCMOS33"} {
    error "M08 D3.2 post-route fan pin, buffer or voltage constraints drifted"
}
# No launch_runs, no firmware generation, no program_hw_devices/JTAG.
set bit [file join $candidate_dir m08_d3_2_passive_fan_UNRELEASED.bit]
if {[file exists $bit]} {error "M08 D3.2 refusing bitstream overwrite"}
write_bitstream -file $bit
# Vendor command may return Tcl OK even when bitgen reports an error.
if {![file isfile $bit] || [file type $bit] ne "file" ||
    [file size $bit] < 100000 ||
    [file size $bit] > 100000000} {
    error "M08 D3.2 bitstream command did not produce plausible genuine .bit bytes"
}
set receipt [file join $candidate_dir 61_unreleased_bitstream_readback.txt]
set fd [open $receipt {WRONLY CREAT EXCL}]
puts $fd {schema=m08-d3-2-passive-unreleased-bitstream-v1}
puts $fd {candidate=m08-d3a-passive-fan-v1}
puts $fd "vivado_version=[version -short]"
puts $fd "part=[get_property PART [current_project]]"
puts $fd "board_part=[get_property BOARD_PART [current_project]]"
puts $fd "source_route_status=[get_property STATUS $ir]"
puts $fd {ps_to_pl_axi=DISABLED}
puts $fd {identity_slave=ABSENT}
puts $fd {page_slave=ABSENT}
puts $fd {fan_output=A12_LVCMOS33}
puts $fd {bitstream=CREATED_OFFLINE_UNRELEASED}
puts $fd "bitstream_size_bytes=[file size $bit]"
puts $fd {bit_bin=NOT_CREATED}
puts $fd {dtbo=NOT_CREATED}
puts $fd {boot_image=NOT_CREATED}
puts $fd {board_programmed=NO}
puts $fd {physical_fan_continuity=NOT_PROVEN}
puts $fd {boot_rollback=NOT_PROVEN}
puts $fd {physical_programming_authorized=NO}
puts $fd {hardware_mmio_authorized=NO}
puts $fd {original_quarantined_image_reused=NO}
close $fd
puts {M08_D3_2_PASSIVE_BITSTREAM_CANDIDATE_CREATED_OFFLINE_UNRELEASED_NO_BOARD}
