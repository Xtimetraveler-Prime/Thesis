# M08 D3.C -- KV260 JTAG -> AXI -> BRAM communication smoke-test candidate.
# Offline Vivado 2025.2 OWNER-PC only. Creates routed, UNRELEASED .bit.
# No board access or application loading; NO PS-to-PL HPM0/HPM1/LPD masters.
# Preserve PS TTC0 EMIO channel 2 -> A12 fan. PL clock is PS pl_clk0:
# its continuity after Linux becomes unresponsive is NOT YET PROVEN.
if {[llength $argv] != 1} {
    error "usage: m08_d3c_jtag_bram_build.tcl <new-empty-PC-evidence-folder>"
}
if {![string match "2025.2*" [version -short]]} {
    error "M08 D3C requires genuine Vivado 2025.2"
}
set evidence [file normalize [lindex $argv 0]]
set evidence_base [file normalize [file join $::env(HOME) Thesis_Evidence M08]]
if {![regexp {^m08_d3c_jtag_link_[A-Za-z0-9]+$} [file tail $evidence]] ||
    [file dirname $evidence] ne $evidence_base ||
    ![file isdirectory $evidence] || [file type $evidence] ne "directory"} {
    error "M08 D3C requires new isolated owner PC evidence folder under M08"
}
# The Vivado process creates these two native output files before sourcing Tcl.
# They are the ONLY permitted pre-created entries; reject everything else.
set allowed_precreated {00_vivado.log 01_vivado.jou}
foreach f [glob -nocomplain -directory $evidence * .*] {
    set leaf [file tail $f]
    if {$leaf in {. ..}} {continue}
    if {$leaf ni $allowed_precreated ||
        [file type $f] ne "file" || ![file isfile $f]} {
        error "M08 D3C evidence folder contains unexpected/unsafe content: $leaf"
    }
}
set part xck26-sfvc784-2LV-c
set project_dir [file join $evidence project]
set reports [file join $evidence reports]
set candidate_dir [file join $evidence bitstream_candidate]
file mkdir $reports $candidate_dir
create_project m08_d3c_jtag_link $project_dir -part $part
set parts [get_board_parts -quiet xilinx.com:kv260_som:part0:*]
if {[llength $parts] == 0} {error "KV260 SOM board preset missing"}
set_property BOARD_PART [lindex [lsort -dictionary $parts] end] [current_project]
foreach vlnv {
    xilinx.com:ip:zynq_ultra_ps_e:3.5
    xilinx.com:ip:xlslice:1.0
    xilinx.com:ip:jtag_axi:1.2
    xilinx.com:ip:smartconnect:1.0
    xilinx.com:ip:axi_bram_ctrl:4.1
    xilinx.com:ip:blk_mem_gen:8.4
    xilinx.com:ip:proc_sys_reset:5.0
    xilinx.com:ip:xlconstant:1.1
} {
    if {[llength [get_ipdefs -all -quiet $vlnv]] != 1} {
        error "Required vendor IP not uniquely installed: $vlnv"
    }
}
create_bd_design m08_d3c_jtag_link
set ps [create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e:3.5 ps]
apply_bd_automation -rule xilinx.com:bd_rule:zynq_ultra_ps_e \
    -config {apply_board_preset "1"} $ps
set_property -dict [list \
    CONFIG.PSU__USE__M_AXI_GP0 0 \
    CONFIG.PSU__USE__M_AXI_GP1 0 \
    CONFIG.PSU__USE__M_AXI_GP2 0 \
    CONFIG.PSU__FPGA_PL0_ENABLE 1 \
    CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ 100 \
    CONFIG.PSU__TTC0__WAVEOUT__ENABLE 1 \
    CONFIG.PSU__TTC0__WAVEOUT__IO EMIO] $ps
foreach prop {
    CONFIG.PSU__USE__M_AXI_GP0
    CONFIG.PSU__USE__M_AXI_GP1
    CONFIG.PSU__USE__M_AXI_GP2
} {
    if {[string trim [get_property $prop $ps]] ne "0"} {
        error "Forbidden PS-to-PL AXI master was enabled: $prop"
    }
}
foreach iface {
    ps/M_AXI_HPM0_FPD ps/M_AXI_HPM1_FPD ps/M_AXI_HPM0_LPD
} {
    if {[llength [get_bd_intf_pins -quiet $iface]] != 0} {
        error "Unexpected PS master interface $iface"
    }
}
set clkin [get_bd_pins -quiet ps/pl_clk0]
set reset_out [get_bd_pins -quiet ps/pl_resetn0]
set wave [get_bd_pins -quiet ps/emio_ttc0_wave_o]
if {[llength $clkin] != 1 || [llength $reset_out] != 1 || [llength $wave] != 1} {
    error "KV260 PS PL0 clock, reset or TTC0 EMIO did not appear"
}
set clock_hz [get_property CONFIG.FREQ_HZ $clkin]
if {![string is wideinteger -strict $clock_hz] ||
    [expr {abs(($clock_hz + 0) - 100000000)}] > 1000} {
    error "PS PL0 is not nominal 100 MHz: $clock_hz"
}
set_property -dict [list CONFIG.DIN_WIDTH 3 CONFIG.DIN_FROM 2 CONFIG.DIN_TO 2] \
    [create_bd_cell -type ip -vlnv xilinx.com:ip:xlslice:1.0 fan_slice]
set fan [create_bd_port -dir O M08_FAN_PWM]
connect_bd_net $wave [get_bd_pins fan_slice/Din]
connect_bd_net [get_bd_pins fan_slice/Dout] $fan

set jtag [create_bd_cell -type ip -vlnv xilinx.com:ip:jtag_axi:1.2 jtag_axi]
set sc [create_bd_cell -type ip -vlnv xilinx.com:ip:smartconnect:1.0 link_sc]
set ctrl [create_bd_cell -type ip -vlnv xilinx.com:ip:axi_bram_ctrl:4.1 bram_ctrl]
set bram [create_bd_cell -type ip -vlnv xilinx.com:ip:blk_mem_gen:8.4 bram]
set rst [create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 rst_pl0]
set hi [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_one]
set lo [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_zero]
set_property -dict [list CONFIG.CONST_VAL 1 CONFIG.CONST_WIDTH 1] $hi
set_property -dict [list CONFIG.CONST_VAL 0 CONFIG.CONST_WIDTH 1] $lo
set_property -dict [list CONFIG.C_EXT_RESET_HIGH 0] $rst
set_property -dict [list CONFIG.NUM_SI 1 CONFIG.NUM_MI 1] $sc
set_property -dict [list CONFIG.DATA_WIDTH 32 CONFIG.MEM_DEPTH 1024 CONFIG.SINGLE_PORT_BRAM 1] $ctrl
set_property -dict [list \
    CONFIG.Memory_Type Single_Port_RAM \
    CONFIG.Write_Width_A 32 \
    CONFIG.Read_Width_A 32 \
    CONFIG.Write_Depth_A 1024] $bram
connect_bd_intf_net [get_bd_intf_pins jtag_axi/M_AXI] \
    [get_bd_intf_pins link_sc/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins link_sc/M00_AXI] \
    [get_bd_intf_pins bram_ctrl/S_AXI]
connect_bd_intf_net [get_bd_intf_pins bram_ctrl/BRAM_PORTA] \
    [get_bd_intf_pins bram/BRAM_PORTA]
foreach sink {
    jtag_axi/aclk
    link_sc/aclk
    bram_ctrl/s_axi_aclk
    rst_pl0/slowest_sync_clk
} {
    if {[llength [get_bd_pins -quiet $sink]] != 1} {
        error "Required clock sink absent: $sink"
    }
    connect_bd_net $clkin [get_bd_pins $sink]
}
connect_bd_net $reset_out [get_bd_pins rst_pl0/ext_reset_in]
connect_bd_net [get_bd_pins const_one/dout] [get_bd_pins rst_pl0/dcm_locked]
connect_bd_net [get_bd_pins const_zero/dout] \
    [get_bd_pins rst_pl0/aux_reset_in] [get_bd_pins rst_pl0/mb_debug_sys_rst]
foreach sink {
    jtag_axi/aresetn
    link_sc/aresetn
    bram_ctrl/s_axi_aresetn
} {
    if {[llength [get_bd_pins -quiet $sink]] != 1} {
        error "Required reset sink absent: $sink"
    }
    connect_bd_net [get_bd_pins rst_pl0/peripheral_aresetn] [get_bd_pins $sink]
}
# 4 KiB AXI address window matching the 1024 x 32-bit BRAM;
# only the first sixteen bytes are used in this initial smoke test; all JTAG readbacks are 32-bit aligned.
set space [get_bd_addr_spaces -quiet jtag_axi/Data]
set segment [get_bd_addr_segs -quiet bram_ctrl/S_AXI/Mem0]
if {[llength $space] != 1 || [llength $segment] != 1} {
    error "JTAG AXI address space or BRAM segment not found; no default fallback"
}
assign_bd_address -offset 0xA0000000 -range 0x00001000 \
    -target_address_space $space $segment
validate_bd_design -force
foreach iface {
    ps/M_AXI_HPM0_FPD ps/M_AXI_HPM1_FPD ps/M_AXI_HPM0_LPD
} {
    if {[llength [get_bd_intf_pins -quiet $iface]] != 0} {
        error "PS AXI interface unexpectedly regenerated after validation"
    }
}
set jtag_space [get_bd_addr_segs -quiet -of_objects $space]
if {[llength $jtag_space] != 1} {error "JTAG mapped segment count must be exactly one"}
set mapped_offset [get_property OFFSET [lindex $jtag_space 0]]
if {[catch {expr {wide($mapped_offset)}} mapped_base] ||
    $mapped_base != 2684354560} {
    error "Native mapped JTAG BRAM address is not exactly 0xA0000000"
}
save_bd_design

set xdc [file join $reports 10_fan_a12.xdc]
set f [open $xdc {WRONLY CREAT EXCL}]
puts $f {set_property PACKAGE_PIN A12 [get_ports {M08_FAN_PWM}]}
puts $f {set_property IOSTANDARD LVCMOS33 [get_ports {M08_FAN_PWM}]}
puts $f {set_property SLEW SLOW [get_ports {M08_FAN_PWM}]}
puts $f {set_property DRIVE 4 [get_ports {M08_FAN_PWM}]}
close $f
add_files -fileset constrs_1 -norecurse $xdc
set bd_files [get_files -all -quiet *m08_d3c_jtag_link.bd]
if {[llength $bd_files] != 1} {error "Expected unique JTAG link BD"}
generate_target all $bd_files
set wrapper [make_wrapper -files $bd_files -top]
if {[llength $wrapper] != 1 || ![file isfile [lindex $wrapper 0]]} {
    error "Cannot generate JTAG link wrapper"
}
add_files -norecurse $wrapper
set_property top m08_d3c_jtag_link_wrapper [current_fileset]
update_compile_order -fileset sources_1

# Produce route/bit candidate on owner PC. This script does NOT PROGRAM BOARD.
launch_runs synth_1 -jobs 2
wait_on_run synth_1
if {![string match "*Complete!*" [get_property STATUS [get_runs synth_1]]]} {
    error "JTAG link native synth did not complete"
}
launch_runs impl_1 -to_step route_design -jobs 2
wait_on_run impl_1
if {![string match "*Complete!*" [get_property STATUS [get_runs impl_1]]]} {
    error "JTAG link native route did not complete"
}
open_run impl_1
if {[get_property PACKAGE_PIN [get_ports M08_FAN_PWM]] ne "A12" ||
    [get_property IOSTANDARD [get_ports M08_FAN_PWM]] ne "LVCMOS33"} {
    error "Fan A12 constraint missing from implemented design"
}
report_drc -file [file join $reports 20_route_drc.rpt]
report_timing_summary -file [file join $reports 21_route_timing.rpt]
report_utilization -file [file join $reports 22_route_utilization.rpt]
report_clocks -file [file join $reports 23_route_clocks.rpt]
set bit [file join $candidate_dir m08_d3c_jtag_bram_UNRELEASED.bit]
if {[file exists $bit]} {error "Refusing to overwrite JTAG link bitstream"}
write_bitstream -file $bit
if {![file isfile $bit] || [file size $bit] < 100000} {
    error "No plausible native JTAG BRAM .bit created"
}
set receipt [file join $reports 30_native_result.txt]
set f [open $receipt {WRONLY CREAT EXCL}]
puts $f {schema=m08-d3c-jtag-bram-offline-build-v1}
puts $f "vivado_version=[version -short]"
puts $f "part=[get_property PART [current_project]]"
puts $f "board_part=[get_property BOARD_PART [current_project]]"
puts $f {ps_to_pl_hpm=DISABLED}
puts $f {jtag_axi=ENABLED_PL}
puts $f {ps_pl0_clock_request_hz=100000000}
puts $f {ps_pl0_runtime_clock_proven=NO}
puts $f {bram_map_base=0xA0000000}
puts $f {bram_map_range=0x00001000}
puts $f {test_window_bytes=4096}
puts $f {fan_route=TTC0_WAVEOUT2_TO_A12}
puts $f {linux_management_compatibility=NOT_PROVEN}
puts $f {hardware_bitstream_programmed=NO}
puts $f {hardware_jtag_axil_readback_proven=NO}
puts $f {hardware_neural_execution_proven=NO}
puts $f "bitstream_size_bytes=[file size $bit]"
close $f
puts {M08_D3C_JTAG_BRAM_OFFLINE_BITSTREAM_CREATED_NOT_PROGRAMMED}
