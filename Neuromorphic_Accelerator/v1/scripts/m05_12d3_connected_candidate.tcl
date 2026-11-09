# M05.12d.3 — ONE integrated offline K26 PS/PL interconnect candidate.
# This candidate connects real PS→PL control, DMA→PS memory, AXIS,
# clocks and resets. Original HLS generated RTL is NOT in Git, so real
# HLS native stream/control attachment and validated addresses remain OPEN.
# NO physical PS/DDR/FPGA, bitstream, hardware server, or board automation.
if {[llength $argv] != 2} {error "usage: <v1-root> <report-path>"}
set root [lindex $argv 0]
set report_path [lindex $argv 1]
set part xck26-sfvc784-2LV-c
set ps_vlnv xilinx.com:ip:zynq_ultra_ps_e:3.5
set dma_vlnv xilinx.com:ip:axi_dma:7.1
set sc_vlnv xilinx.com:ip:smartconnect:1.0
set rst_vlnv xilinx.com:ip:proc_sys_reset:5.0
set inv_vlnv xilinx.com:ip:util_vector_logic:2.0
set const_vlnv xilinx.com:ip:xlconstant:1.1
create_project -in_memory -part $part
set_property source_mgmt_mode All [current_project]
if {[string trim [get_property source_mgmt_mode [current_project]]] ne "All"} {
    error "M05.12d.3 requires automatic RTL module reference management"
}
foreach vlnv [list $ps_vlnv $dma_vlnv $sc_vlnv $rst_vlnv $inv_vlnv $const_vlnv] {
    if {[llength [get_ipdefs -all -quiet $vlnv]] != 1} {
        error "offline K26 Vivado IP missing: $vlnv"
    }
}
foreach file {
    rtl/m05_11/m05_11_axil_session_controller.v
    rtl/m05_11/m05_trace_dma_packetizer.v
    rtl/m05_11/m05_ingress_dma_unpad.v
    rtl/m05_11/m05_11_stream_shell.v
    rtl/m05_12/m05_12d_axis_shell_ref.v
} {
    set source [file join $root $file]
    if {![file exists $source]} {error "missing original shell source $file"}
    add_files -norecurse $source
}
update_compile_order -fileset sources_1
create_bd_design m05_12d3_ps_dma_shell_connected_candidate
set ps [create_bd_cell -type ip -vlnv $ps_vlnv ps]
if {[llength $ps] != 1} {error "Zynq PS IP not instantiated"}
foreach {prop expected} {
    CONFIG.PSU__USE__M_AXI_GP0 0
    CONFIG.PSU__USE__S_AXI_GP2 0
} {
    if {[string trim [get_property $prop $ps]] ne "$expected"} {
        error "unexpected default PS property $prop"
    }
}
set_property -dict [list CONFIG.PSU__USE__M_AXI_GP0 1 \
                         CONFIG.PSU__USE__S_AXI_GP2 1] $ps
foreach {prop expected} {
    CONFIG.PSU__USE__M_AXI_GP0 1
    CONFIG.PSU__USE__S_AXI_GP2 1
    CONFIG.PSU__MAXIGP0__DATA_WIDTH 128
    CONFIG.PSU__SAXIGP2__DATA_WIDTH 128
} {
    if {[string trim [get_property $prop $ps]] ne "$expected"} {
        error "PS property $prop did not read back '$expected'"
    }
}
foreach {name mode} {M_AXI_HPM0_FPD MASTER S_AXI_HP0_FPD SLAVE} {
    set pin [get_bd_intf_pins -quiet "ps/$name"]
    if {[llength $pin] != 1 || [string toupper [get_property MODE $pin]] ne $mode} {
        error "PS real AXI port $name not present in correct $mode mode"
    }
}
set shell [create_bd_cell -type module -reference m05_12d_axis_shell_ref shell]
if {[llength $shell] != 1} {error "original shell module reference unavailable"}
set ctrl [create_bd_cell -type ip -vlnv $sc_vlnv ctrl_sc]
set mem [create_bd_cell -type ip -vlnv $sc_vlnv mem_sc]
# Five *real* control slave banks (four DMA+shell). The sixth is native
# generated HLS control; cannot invent this without original generated IP.
set_property -dict [list CONFIG.NUM_SI 1 CONFIG.NUM_MI 5] $ctrl
set_property -dict [list CONFIG.NUM_SI 4 CONFIG.NUM_MI 1] $mem
foreach {cell si mi} {ctrl_sc 1 5 mem_sc 4 1} {
    foreach {prop expected} [list CONFIG.NUM_SI $si CONFIG.NUM_MI $mi] {
        if {[string trim [get_property $prop [get_bd_cells $cell]]] ne "$expected"} {
            error "SmartConnect $cell $prop readback mismatch"
        }
    }
}
set reset [create_bd_cell -type ip -vlnv $rst_vlnv pl_reset]
# Genuine 2025.2 owner D3 proved that proc_sys_reset CONFIG.C_EXT_RESET_HIGH
# is READ-ONLY (BD 41-737). NEVER write it. Read the actual IP polarity and
# fail closed if it does not match the expected active-HIGH external input.
# PS pl_resetn0 is active LOW: invert at a genuine 1-bit vector logic IP.
if {[lsearch -exact [list_property $reset] CONFIG.C_EXT_RESET_HIGH] < 0} {
    error "proc_sys_reset C_EXT_RESET_HIGH not available (do not guess reset polarity)"
}
set ps_reset_ext_high [string trim [get_property CONFIG.C_EXT_RESET_HIGH $reset]]
if {$ps_reset_ext_high ne "1"} {
    error "proc_sys_reset read-only C_EXT_RESET_HIGH='$ps_reset_ext_high'; expected 1. Investigate before connecting PS reset"
}
set inv [create_bd_cell -type ip -vlnv $inv_vlnv reset_inv]
set_property -dict [list CONFIG.C_OPERATION not CONFIG.C_SIZE 1] $inv
foreach {key expected} {
    CONFIG.C_OPERATION not
    CONFIG.C_SIZE 1
} {
    if {[string trim [get_property $key $inv]] ne $expected} {
        error "1-bit reset inverter property $key does not match '$expected'"
    }
}
set high [create_bd_cell -type ip -vlnv $const_vlnv logic_one]
set low [create_bd_cell -type ip -vlnv $const_vlnv logic_zero]
set_property -dict [list CONFIG.CONST_VAL 1 CONFIG.CONST_WIDTH 1] $high
set_property -dict [list CONFIG.CONST_VAL 0 CONFIG.CONST_WIDTH 1] $low
set report [list "META|part|$part" "META|scope|OFFLINE_PS_DMA_SHELL_INTERCONNECT_CANDIDATE_NO_HLS_OR_ADDRESSES" \
    "META|source_mgmt_mode|[get_property source_mgmt_mode [current_project]]" \
    "META|ps_vlnv|$ps_vlnv" "META|dma_vlnv|$dma_vlnv" \
    "META|smartconnect_vlnv|$sc_vlnv" \
    "META|hls_control|MISSING_GENERATED_RTL" \
    "META|address_map|NOT_ASSIGNED" \
    "META|full_bd_validation|NOT_RUN" \
    "META|data_width_conversion|SMARTCONNECT_CANDIDATE_NOT_GENERATED"]
proc require_intf {name} {
    set pin [get_bd_intf_pins -quiet $name]
    if {[llength $pin] != 1} {error "missing actual Vivado interface $name"}
    return $pin
}
proc require_pin {name} {
    set pin [get_bd_pins -quiet $name]
    if {[llength $pin] != 1} {error "missing actual Vivado scalar pin $name"}
    return $pin
}
proc link_axis_or_axi {from to} {
    global report
    set a [require_intf $from]
    set b [require_intf $to]
    if {[llength [get_bd_intf_nets -quiet -of_objects $a]] != 0 ||
        [llength [get_bd_intf_nets -quiet -of_objects $b]] != 0} {
        error "already occupied interface on intended point-to-point $from/$to"
    }
    connect_bd_intf_net $a $b
    set an [get_bd_intf_nets -of_objects $a]
    set bn [get_bd_intf_nets -of_objects $b]
    if {[llength $an] != 1 || [llength $bn] != 1 ||
        [get_property NAME $an] ne [get_property NAME $bn]} {
        error "interface $from and $to did not join the same net"
    }
    set ends [get_bd_intf_pins -of_objects $an]
    if {[llength $ends] != 2} {
        error "unexpected AXI/AXIS net endpoint count for $from -> $to"
    }
    lappend report "LINK|$from|$to|[get_property NAME $an]"
}
set dma_names {dma_neurons dma_synapses dma_external dma_trace}
foreach {name role} {
    dma_neurons MM2S
    dma_synapses MM2S
    dma_external MM2S
    dma_trace S2MM
} {
    set cell [create_bd_cell -type ip -vlnv $dma_vlnv $name]
    set config [list CONFIG.c_include_sg 0 CONFIG.c_sg_length_width 24 \
        CONFIG.c_addr_width 32 CONFIG.c_micro_dma 0 \
        CONFIG.c_include_mm2s_dre 0 CONFIG.c_include_s2mm_dre 0]
    if {$role eq "MM2S"} {
        set config [concat $config [list CONFIG.c_include_mm2s 1 CONFIG.c_include_s2mm 0 \
            CONFIG.c_m_axi_mm2s_data_width 256 CONFIG.c_m_axis_mm2s_tdata_width 256]]
    } else {
        set config [concat $config [list CONFIG.c_include_mm2s 0 CONFIG.c_include_s2mm 1 \
            CONFIG.c_m_axi_s2mm_data_width 256 CONFIG.c_s_axis_s2mm_tdata_width 256]]
    }
    set_property -dict $config $cell
    foreach {prop expected} [concat $config [list CONFIG.c_prmry_is_aclk_async 0]] {
        if {[string trim [get_property $prop $cell]] ne "$expected"} {
            error "$name DMA parameter $prop readback mismatch"
        }
    }
    lappend report "DMA|$name|$role|256|32|24"
}
# Stream links: retain all four previously owner-verified D1 pairs.
foreach {src sink} {
    dma_neurons/M_AXIS_MM2S shell/S_AXIS_NEURONS
    dma_synapses/M_AXIS_MM2S shell/S_AXIS_SYNAPSES
    dma_external/M_AXIS_MM2S shell/S_AXIS_EXTERNAL
    shell/M_AXIS_TRACE dma_trace/S_AXIS_S2MM
} {
    link_axis_or_axi $src $sink
}
# Processor AXI master reaches four DMA AXI-Lite controls AND the M05 shell.
# The HLS AXI4-Lite control port does not exist in Git and is NOT fabricated.
link_axis_or_axi ps/M_AXI_HPM0_FPD ctrl_sc/S00_AXI
foreach {index sink} {
    0 dma_neurons/S_AXI_LITE
    1 dma_synapses/S_AXI_LITE
    2 dma_external/S_AXI_LITE
    3 dma_trace/S_AXI_LITE
    4 shell/s_axi
} {
    link_axis_or_axi [format "ctrl_sc/M%02d_AXI" $index] $sink
}
# PL DMA memory masters to PS HP0_FPD through one 4:1 SmartConnect.
# Current DMA MM is 256-bit; PS HP0 is 128-bit. Conversion MUST later be
# confirmed after IP output generation and BD validation, not assumed here.
foreach {index src} {
    0 dma_neurons/M_AXI_MM2S
    1 dma_synapses/M_AXI_MM2S
    2 dma_external/M_AXI_MM2S
    3 dma_trace/M_AXI_S2MM
} {
    link_axis_or_axi $src [format "mem_sc/S%02d_AXI" $index]
}
link_axis_or_axi mem_sc/M00_AXI ps/S_AXI_HP0_FPD
# One PL clock domain for this candidate, with a synchronized reset IP.
# Verify actual scalar BD net memberships; a pin readback alone is not enough.
set clocks {ps/pl_clk0 ps/maxihpm0_fpd_aclk ps/saxihp0_fpd_aclk ctrl_sc/aclk mem_sc/aclk pl_reset/slowest_sync_clk shell/clk}
set reset_pins {pl_reset/peripheral_aresetn shell/rst_n}
foreach name $dma_names {
    lappend clocks "$name/s_axi_lite_aclk"
    lappend reset_pins "$name/axi_resetn"
}
# AMD AXI DMA PG021: m_axi_mm2s_aclk clocks both MM2S AXI-MM and
# M_AXIS_MM2S; m_axi_s2mm_aclk clocks S2MM AXI-MM and S_AXIS_S2MM.
# Separate *m_axis_mm2s_aclk/s_axis_s2mm_aclk* pins are AXI VDMA,
# not these tested AXI DMA v7.1 instances. Genuine owner D3 failure:
# absent dma_neurons/m_axis_mm2s_aclk (2026-11-09 03:02 UTC).
foreach name {dma_neurons dma_synapses dma_external} {
    lappend clocks "$name/m_axi_mm2s_aclk"
}
lappend clocks "dma_trace/m_axi_s2mm_aclk"
set cpins {}
foreach name $clocks {lappend cpins [require_pin $name]}
connect_bd_net {*}$cpins
foreach name $clocks {
    set nets [get_bd_nets -of_objects [require_pin $name]]
    if {[llength $nets] != 1} {error "clock not actually net-connected: $name"}
    lappend report "CLK|$name|[get_property NAME $nets]"
}
# Make an explicit active-low → active-high reset inversion, rather than
# incorrectly writing the read-only Processor System Reset polarity parameter.
connect_bd_net [require_pin ps/pl_resetn0] [require_pin reset_inv/Op1]
connect_bd_net [require_pin reset_inv/Res] [require_pin pl_reset/ext_reset_in]
foreach {name expected_dir} {
    ps/pl_resetn0 O
    reset_inv/Op1 I
    reset_inv/Res O
    pl_reset/ext_reset_in I
} {
    set pin [require_pin $name]
    set actual_dir [string toupper [string trim [get_property DIR $pin]]]
    if {$actual_dir ne $expected_dir} {
        error "wrong reset inverter connection direction $name='$actual_dir' expected $expected_dir"
    }
    set nets [get_bd_nets -of_objects $pin]
    if {[llength $nets] != 1} {
        error "reset inverter segment missing actual Vivado net $name"
    }
    lappend report "RESETDIR|$name|$actual_dir"
    lappend report "RESETFEED|$name|[get_property NAME $nets]"
}
# Two *separate* nets are required: PS resetn→inverter, inverter→reset IP.
set resetn_net [get_property NAME [get_bd_nets -of_objects [require_pin ps/pl_resetn0]]]
set inverter_input_net [get_property NAME [get_bd_nets -of_objects [require_pin reset_inv/Op1]]]
set inverted_net [get_property NAME [get_bd_nets -of_objects [require_pin reset_inv/Res]]]
set external_net [get_property NAME [get_bd_nets -of_objects [require_pin pl_reset/ext_reset_in]]]
if {$resetn_net ne $inverter_input_net || $inverted_net ne $external_net ||
    $resetn_net eq $inverted_net} {
    error "PS active-low to processor-reset active-high inverter nets are not distinct and paired"
}
lappend report "RESETCFG|C_EXT_RESET_HIGH|$ps_reset_ext_high"
foreach key {CONFIG.C_OPERATION CONFIG.C_SIZE} {
    lappend report "RESETINV|[string range $key 7 end]|[get_property $key $inv]"
}
connect_bd_net [require_pin logic_one/dout] [require_pin pl_reset/dcm_locked]
connect_bd_net [require_pin logic_zero/dout] [require_pin pl_reset/aux_reset_in] \
    [require_pin pl_reset/mb_debug_sys_rst]
set rstpins [list [require_pin pl_reset/interconnect_aresetn] \
    [require_pin ctrl_sc/aresetn] [require_pin mem_sc/aresetn]]
connect_bd_net {*}$rstpins
foreach name {ctrl_sc/aresetn mem_sc/aresetn} {
    set n [get_bd_nets -of_objects [require_pin $name]]
    if {[llength $n] != 1} {error "interconnect reset unconnected $name"}
    lappend report "RESET|$name|[get_property NAME $n]"
}
set rpins [list [require_pin pl_reset/peripheral_aresetn]]
foreach name [lrange $reset_pins 1 end] {lappend rpins [require_pin $name]}
connect_bd_net {*}$rpins
foreach name [lrange $reset_pins 1 end] {
    set n [get_bd_nets -of_objects [require_pin $name]]
    if {[llength $n] != 1} {error "peripheral reset unconnected $name"}
    lappend report "RESET|$name|[get_property NAME $n]"
}
foreach {key expected} {
    CONFIG.PSU__MAXIGP0__DATA_WIDTH 128
    CONFIG.PSU__SAXIGP2__DATA_WIDTH 128
} {
    lappend report "PSCFG|[string range $key 7 end]|[get_property $key $ps]"
}
set f [open $report_path w]
foreach item $report {puts $f $item}
close $f
close_project
puts "PASS: M05.12d.3 offline PS/PL four-DMA control/memory/stream/clock graph (PARTIAL: NO HLS/ADDR/DDR)"
