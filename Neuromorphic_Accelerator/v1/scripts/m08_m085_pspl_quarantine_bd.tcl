# M08.5 OFFLINE SOURCE-CANDIDATE: KV260 PS HPM0+HP0 BD topology.
# PURPOSE: expose/validate real 128->32 control + 128-bit PL AXI4 PS routes.
# QUARANTINE: all trust/driver/route/drain inputs HARDWIRED TO ZERO.
# This deliberately can NEVER grant a DMA lease; no live DDR is authorized.
# NO synthesis, route, bitstream, XSA release, Linux DT deploy, hardware
# manager, firmware, DMA buffers, PS MMIO or JTAG operations. In particular
# Vivado BD "validate" is NOT proof that the Linux kernel can own DDR.
#
# Requires a NEW empty owner PC evidence directory. Not accepted M08.4 dirs.
if {[llength $argv] != 1} {
    error "usage: m08_m085_pspl_quarantine_bd.tcl <NEW_EMPTY_m08_m085_pspl_bd_*_dir>"
}
if {![string match "2025.2*" [version -short]]} {
    error "M08.5 PS/PL quarantine requires exact Vivado 2025.2"
}
set evidence [file normalize [lindex $argv 0]]
set base [file normalize [file join $::env(HOME) Thesis_Evidence M08]]
if {[file dirname $evidence] ne $base ||
    ![regexp {^m08_m085_pspl_bd_[A-Za-z0-9_]+$} [file tail $evidence]] ||
    ![file isdirectory $evidence] || [file type $evidence] ne "directory"} {
    error "M08.5 PS/PL only accepts a NEW named directory in ~/Thesis_Evidence/M08"
}
foreach entry [glob -nocomplain -directory $evidence * .*] {
    set leaf [file tail $entry]
    if {$leaf in {. ..}} {continue}
    if {$leaf ni {00_vivado.log 01_vivado.jou} ||
        [file type $entry] ne "file" || ![file isfile $entry]} {
        error "Evidence directory not fresh or unexpected content: $leaf"
    }
}
set part xck26-sfvc784-2LV-c
set rtl_root [file normalize [file join [file dirname [info script]] .. rtl]]
set m08_root [file join $rtl_root m08]
set project_dir [file join $evidence project]
set reports [file join $evidence reports]
file mkdir $reports
create_project m08_m085_pspl_quarantine_bd $project_dir -part $part

# Pin actual source files by copying their exact original bytes into a
# private, exclusive read-only input snapshot. Do not pull from accepted
# bitstream workspaces; no numerical oracle outputs are injected in RTL.
set source_names {
    m08_host_staged_page_bank.sv
    m08_paged_m06_lif_engine.v
    m08_m085_ddr_page_admission.v
    m08_m085_axi128_page_engine.v
    m08_m085_axi128_page_candidate.v
    m08_m085_axi_bank_bridge.v
    m08_m085_axi_neural_shell.v
    m08_m085_kernel_dma_lease_fence.v
    m08_m085_trusted_control_abi.v
    m08_m085_work_command_sequencer.v
    m08_m085_axil_control_candidate.v
    m08_m085_axil_managed_neural_candidate.v
}
set source_dir [file join $evidence source_snapshot]
file mkdir $source_dir
foreach leaf $source_names {
    set original [file join $m08_root $leaf]
    if {![file isfile $original] || [file type $original] ne "file" ||
        [file size $original] < 100} {
        error "Required first-party M08.5 source is missing or malformed: $leaf"
    }
    set snap [file join $source_dir $leaf]
    file copy $original $snap
    add_files -fileset sources_1 -norecurse $snap
}
set por_src [file join $rtl_root m08_d3c_fabric_por.v]
if {![file isfile $por_src]} {error "Missing first-party fabric POR source"}
file copy $por_src [file join $source_dir m08_d3c_fabric_por.v]
add_files -fileset sources_1 -norecurse [file join $source_dir m08_d3c_fabric_por.v]
update_compile_order -fileset sources_1
set boards [get_board_parts -quiet xilinx.com:kv260_som:part0:*]
if {[llength $boards] == 0} {
    error "Exact KV260 SOM Vivado board preset not installed"
}
set_property BOARD_PART [lindex [lsort -dictionary $boards] end] [current_project]
foreach vlnv {
    xilinx.com:ip:zynq_ultra_ps_e:3.5
    xilinx.com:ip:smartconnect:1.0
    xilinx.com:ip:xlconstant:1.1
    xilinx.com:ip:xlslice:1.0
} {
    if {[llength [get_ipdefs -all -quiet $vlnv]] != 1} {
        error "Missing or ambiguous required vendor IP: $vlnv"
    }
}
create_bd_design m08_m085_pspl_quarantine_bd
set ps [create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e:3.5 ps]
apply_bd_automation -rule xilinx.com:bd_rule:zynq_ultra_ps_e \
    -config {apply_board_preset "1"} $ps
# This IS A PROPOSED NEW PS configuration, not live boot-verified AFI.
set_property -dict [list \
    CONFIG.PSU__USE__M_AXI_GP0 {1} \
    CONFIG.PSU__MAXIGP0__DATA_WIDTH {128} \
    CONFIG.PSU__USE__M_AXI_GP1 {0} \
    CONFIG.PSU__USE__M_AXI_GP2 {0} \
    CONFIG.PSU__USE__S_AXI_GP2 {1} \
    CONFIG.PSU__SAXIGP2__DATA_WIDTH {128} \
    CONFIG.PSU__FPGA_PL0_ENABLE {1} \
    CONFIG.PSU__USE__FABRIC__RST {0} \
    CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {100} \
    CONFIG.PSU__TTC0__WAVEOUT__ENABLE {1} \
    CONFIG.PSU__TTC0__WAVEOUT__IO EMIO] $ps
# No inferred alternate PS master or HP port is accepted.
proc exactly_one_pin {name} {
    set pin [get_bd_pins -quiet $name]
    if {[llength $pin] != 1} {error "Required unique BD pin missing: $name"}
    return $pin
}
proc exactly_one_intf {name} {
    set pin [get_bd_intf_pins -quiet $name]
    if {[llength $pin] != 1} {error "Required unique BD interface missing: $name"}
    return $pin
}
set hpm0 [exactly_one_intf ps/M_AXI_HPM0_FPD]
set hp0 [exactly_one_intf ps/S_AXI_HP0_FPD]
set hpm_width [get_property CONFIG.DATA_WIDTH $hpm0]
set hp_width [get_property CONFIG.DATA_WIDTH $hp0]
if {$hpm_width ne "128" || $hp_width ne "128"} {
    error "PS HPM0/HP0 width mismatch hpm=$hpm_width hp=$hp_width"
}
foreach prop {
    CONFIG.PSU__USE__M_AXI_GP1
    CONFIG.PSU__USE__M_AXI_GP2
} {
    if {[string trim [get_property $prop $ps]] ne "0"} {
        error "Unreviewed PS HPM path was enabled: $prop"
    }
}
foreach name {ps/M_AXI_HPM1_FPD ps/M_AXI_HPM0_LPD} {
    if {[llength [get_bd_intf_pins -quiet $name]] != 0} {
        error "Unexpected alternate PS HPM master: $name"
    }
}
set plclk [exactly_one_pin ps/pl_clk0]
set measured_clock [get_property CONFIG.FREQ_HZ $plclk]
if {![string is wideinteger -strict $measured_clock] ||
    [expr {abs(($measured_clock+0)-100000000)}] > 1000} {
    error "Nominal PS PL0 100 MHz clock missing: $measured_clock"
}
# Explicitly annotated 32-bit AXI4-Lite and 128-bit AXI4 pins are required.
# Failure to infer either interface is a DESIGN BLOCKER, never fallback to
# loose signal wires or a quiet JTAG path.
set dut [create_bd_cell -type module \
    -reference m08_m085_axil_managed_neural_candidate accel]
set dut_control [exactly_one_intf accel/S_AXI]
set dut_ddr [exactly_one_intf accel/M_AXI]
if {[get_property CONFIG.DATA_WIDTH $dut_control] ne "32" ||
    [get_property CONFIG.DATA_WIDTH $dut_ddr] ne "128"} {
    error "M08.5 inferred control/data width mismatch"
}
if {[get_property CONFIG.PROTOCOL $dut_control] ni {AXI4LITE AXI4Lite}} {
    error "M08.5 inferred control protocol is not AXI4-Lite"
}
# Explicit 128-bit HPM0 to 32-bit AXI4-Lite SmartConnect conversion.
set control_sc [create_bd_cell -type ip \
    -vlnv xilinx.com:ip:smartconnect:1.0 control_sc]
set hp0_sc [create_bd_cell -type ip \
    -vlnv xilinx.com:ip:smartconnect:1.0 hp0_sc]
foreach sc [list $control_sc $hp0_sc] {
    set_property -dict [list CONFIG.NUM_SI {1} CONFIG.NUM_MI {1}] $sc
}
connect_bd_intf_net $hpm0 [exactly_one_intf control_sc/S00_AXI]
connect_bd_intf_net [exactly_one_intf control_sc/M00_AXI] $dut_control
connect_bd_intf_net $dut_ddr [exactly_one_intf hp0_sc/S00_AXI]
connect_bd_intf_net [exactly_one_intf hp0_sc/M00_AXI] $hp0

# Unlike the original M08.4 JTAG design, the PS PL0 clock and HPM0/HP0
# ports are a proposed dependency. POR is intentionally independent of
# PS pl_resetn0 (it is NOT a physical interconnect drain/reset proof).
set por [create_bd_cell -type module \
    -reference m08_d3c_fabric_por fabric_por]
connect_bd_net $plclk \
    [exactly_one_pin accel/clk] \
    [exactly_one_pin fabric_por/clk] \
    [exactly_one_pin control_sc/aclk] \
    [exactly_one_pin hp0_sc/aclk] \
    [exactly_one_pin ps/maxihpm0_fpd_aclk] \
    [exactly_one_pin ps/saxihp0_fpd_aclk]
set por_reset [exactly_one_pin fabric_por/aresetn]
connect_bd_net $por_reset \
    [exactly_one_pin accel/resetn] \
    [exactly_one_pin control_sc/aresetn] \
    [exactly_one_pin hp0_sc/aresetn]

# NEVER constant-high these inputs in a build. All four are in one
# shared zero net. The candidate is therefore impossible to GRANT,
# even when a developer mistakenly writes the MMIO COMMAND register.
set deny [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 deny_all]
set_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {0}] $deny
set deny_pin [exactly_one_pin deny_all/dout]
foreach p {
    accel/csr_trusted
    accel/driver_bound_verified
    accel/control_route_verified
    accel/interconnect_drain_ack
} {
    connect_bd_net $deny_pin [exactly_one_pin $p]
}
# TTC0 EMIO -> PL fan PWM output with the same constraints as the
# original validated K26 experiments. Routing is not cooling proof.
set fan_slice [create_bd_cell -type ip -vlnv xilinx.com:ip:xlslice:1.0 fan_slice]
set_property -dict [list \
    CONFIG.DIN_WIDTH 3 CONFIG.DIN_FROM 2 CONFIG.DIN_TO 2] $fan_slice
set fan_port [create_bd_port -dir O M08_FAN_PWM]
connect_bd_net [exactly_one_pin ps/emio_ttc0_wave_o] \
    [exactly_one_pin fan_slice/Din]
connect_bd_net [exactly_one_pin fan_slice/Dout] $fan_port

# Routing decoder maps; these are *ADDRESS REGIONS* not allocated Linux
# memory, physical DDR authorization, or proof of IOMMU/AFI boot settings.
set control_segs [get_bd_addr_segs -quiet -of_objects $dut_control]
set ps_spaces [get_bd_addr_spaces -quiet -of_objects $hpm0]
if {[llength $control_segs] != 1 || [llength $ps_spaces] != 1} {
    error "M08.5 missing exactly one AXI-Lite register segment or HPM0 space"
}
assign_bd_address -offset 0xA4000000 -range 0x00001000 \
    -target_address_space [lindex $ps_spaces 0] [lindex $control_segs 0]
set hp0_low [get_bd_addr_segs -quiet ps/SAXIGP2/HP0_DDR_LOW]
set pl_spaces [get_bd_addr_spaces -quiet -of_objects $dut_ddr]
if {[llength $hp0_low] != 1 || [llength $pl_spaces] != 1} {
    error "M08.5 missing exact HP0_DDR_LOW or actual accelerator AXI4 space"
}
assign_bd_address -offset 0x00000000 -range 0x80000000 \
    -target_address_space [lindex $pl_spaces 0] [lindex $hp0_low 0]
validate_bd_design -force
# Review actually realized clocks/routes/trust nets, not just source strings.
foreach name {
    accel/clk control_sc/aclk hp0_sc/aclk
    ps/maxihpm0_fpd_aclk ps/saxihp0_fpd_aclk
} {
    set n [get_bd_nets -quiet -of_objects [exactly_one_pin $name]]
    set clk_n [get_bd_nets -quiet -of_objects $plclk]
    if {[llength $n] != 1 || $n ne $clk_n} {
        error "Clock is not tied to nominal PL0: $name"
    }
}
foreach name {accel/resetn control_sc/aresetn hp0_sc/aresetn} {
    set n [get_bd_nets -quiet -of_objects [exactly_one_pin $name]]
    set rn [get_bd_nets -quiet -of_objects $por_reset]
    if {[llength $n] != 1 || $n ne $rn} {
        error "Reset is not driven from the source-only POR: $name"
    }
}
foreach name {
    accel/csr_trusted
    accel/driver_bound_verified
    accel/control_route_verified
    accel/interconnect_drain_ack
} {
    set n [get_bd_nets -quiet -of_objects [exactly_one_pin $name]]
    set dn [get_bd_nets -quiet -of_objects $deny_pin]
    if {[llength $n] != 1 || $n ne $dn} {
        error "CRITICAL: failed to tie trust/drain to zero: $name"
    }
}
set xdc [file join $reports 10_fan_a12.xdc]
set f [open $xdc {WRONLY CREAT EXCL}]
puts $f {set_property PACKAGE_PIN A12 [get_ports {M08_FAN_PWM}]}
puts $f {set_property IOSTANDARD LVCMOS33 [get_ports {M08_FAN_PWM}]}
puts $f {set_property SLEW SLOW [get_ports {M08_FAN_PWM}]}
puts $f {set_property DRIVE 4 [get_ports {M08_FAN_PWM}]}
close $f
add_files -fileset constrs_1 -norecurse $xdc
save_bd_design
set bd_files [get_files -all -quiet *m08_m085_pspl_quarantine_bd.bd]
if {[llength $bd_files] != 1} {
    error "M08.5 cannot identify unique quarantined PSPL block diagram"
}
# No synth/implementation/bitstream. A successful BD validation is NOT a
# first-image release and the RTL will remain grant-disabled when routed.
set report [file join $reports 20_quarantined_bd_observation.txt]
set f [open $report {WRONLY CREAT EXCL}]
puts $f {schema=m08-m085-kv260-pspl-quarantine-bd-v1}
puts $f {status=OFFLINE_BD_TOPOLOGY_ONLY_NEVER_DMA_READY}
puts $f {target_part=xck26-sfvc784-2LV-c}
puts $f {vivado_version=2025.2}
puts $f {ps_master=ps/M_AXI_HPM0_FPD}
puts $f {ps_slave=ps/S_AXI_HP0_FPD}
puts $f {ps_hpm0_width=128}
puts $f {ps_hp0_width=128}
puts $f {pl_control_protocol=AXI4LITE}
puts $f {pl_control_width=32}
puts $f {pl_data_protocol=AXI4}
puts $f {pl_data_width=128}
puts $f {pl0_nominal_hz=100000000}
puts $f {mmio_map=0xA4000000/0x1000_SOURCE_ONLY}
puts $f {hp0_route_map=0x00000000/0x80000000_NOT_DMA_OWNERSHIP}
puts $f {csr_trusted=HARDWIRED_ZERO}
puts $f {driver_bound_verified=HARDWIRED_ZERO}
puts $f {control_route_verified=HARDWIRED_ZERO}
puts $f {interconnect_drain_ack=HARDWIRED_ZERO}
puts $f {native_synth=NOT_RUN}
puts $f {native_route=NOT_RUN}
puts $f {bitstream=NOT_CREATED}
puts $f {linux_dma_driver=NOT_PRESENT}
puts $f {board_programming=NOT_PERFORMED}
close $f
puts "M08_M085_QUARANTINED_PSPL_BD_COMPLETE_NO_DMA_NO_BITSTREAM"
