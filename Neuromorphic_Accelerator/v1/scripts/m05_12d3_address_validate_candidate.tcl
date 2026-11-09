# M05.12d.3 — same milestone; explicit REAL six-bank PS address map + BD validate.
# Separate candidate file: no mutation of earlier accepted 15-link evidence.
# Source is exact owner-attested Vitis 2025.2 neural RTL, never a mock.
# The real signed32 HLS RTL remains outside Git and is loaded only from
# owner-authenticated evidence; this trial attempts the actual HLS connection.
# It does NOT yet assign addresses or validate a complete system.
# NO physical PS/DDR/FPGA, bitstream, hardware server, or board automation.
if {[llength $argv] != 7} {error "usage: <v1-root> <graph-report> <original-HLS-RTL-directory> <explicit-proposed-map> <address-readback-report> <validation-report>"}
set root [lindex $argv 0]
set report_path [lindex $argv 1]
set rtl_dir [lindex $argv 2]
set plan_path [lindex $argv 3]
set mapped_path [lindex $argv 4]
set validation_path [lindex $argv 5]
set inventory_path [lindex $argv 6]
if {![file isdirectory $rtl_dir] || ![file exists [file join $rtl_dir m05_rolling_replay.v]]} {
    error "M05.12d.3 needs genuine Vitis generated RTL top directory"
}
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
# Read original generated Verilog siblings directly from accepted HLS evidence.
set hls_sources [concat [glob -nocomplain -directory $rtl_dir *.v] \
                        [glob -nocomplain -directory $rtl_dir *.sv]]
if {[llength $hls_sources] < 2} {error "no actual generated HLS Verilog siblings"}
foreach source [lsort $hls_sources] {
    add_files -norecurse $source
}
update_compile_order -fileset sources_1
create_bd_design m05_12d3_real_signed32_hls_six_control_address_candidate
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
set hls [create_bd_cell -type module -reference m05_rolling_replay hls]
if {[llength $hls] != 1} {error "authentic Vitis generated HLS Module Reference unavailable"}
set ctrl [create_bd_cell -type ip -vlnv $sc_vlnv ctrl_sc]
set mem [create_bd_cell -type ip -vlnv $sc_vlnv mem_sc]
# Keep all five previously verified AXI-Lite bank identities and expose
# the real generated HLS module's control as independent sixth AXI-Lite bank.
set_property -dict [list CONFIG.NUM_SI 1 CONFIG.NUM_MI 6] $ctrl
set_property -dict [list CONFIG.NUM_SI 4 CONFIG.NUM_MI 1] $mem
foreach {cell si mi} {ctrl_sc 1 6 mem_sc 4 1} {
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
set report [list "META|part|$part" "META|scope|OFFLINE_PS_DMA_SHELL_REAL_HLS_NATIVE_AXI_STREAM_INTERFACE_CANDIDATE" \
    "META|source_mgmt_mode|[get_property source_mgmt_mode [current_project]]" \
    "META|ps_vlnv|$ps_vlnv" "META|dma_vlnv|$dma_vlnv" \
    "META|smartconnect_vlnv|$sc_vlnv" \
    "META|hls_control|REAL_GENERATED_MODULE_REF_CANDIDATE" \
    "META|address_map|NOT_ASSIGNED" \
    "META|full_bd_validation|NOT_RUN" \
    "META|data_width_conversion|SMARTCONNECT_CANDIDATE_NOT_GENERATED" \
    "META|native_hls_streams|4_GENUINE_AXIS_INTERFACE_NETS_12_PIN_CONTRACTS"]
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
# OWNER OBSERVED BD 41-1306 when connecting every inferred AXIS signal
# individually. AMD UG994 says those pins are then removed from their inferred
# AXIS interface and write_bd_tcl may not reconstruct them consistently.
# Verify original native 128/192-bit scalar signal widths and DIR *without*
# connecting the individual signal pins, then connect the real 4 AXIS groups.
proc assert_native_pin {name dir width} {
    global report
    set pin [require_pin $name]
    set actual_dir [string toupper [string trim [get_property DIR $pin]]]
    if {$actual_dir ne $dir} {
        error "actual native HLS signal direction $name=$actual_dir wanted $dir"
    }
    if {$width > 1} {
        set left [get_property LEFT $pin]
        set right [get_property RIGHT $pin]
        if {![string is integer -strict $left] || ![string is integer -strict $right] ||
            [expr {abs($left - $right) + 1}] != $width} {
            error "actual native HLS TDATA width for $name expected $width got LEFT=$left RIGHT=$right"
        }
    }
    lappend report "NATIVEPIN|$name|$dir|$width"
}
foreach {pin dir width} {
    shell/hls_neuron_tdata O 128
    hls/neurons_TDATA I 128
    shell/hls_neuron_tvalid O 1
    hls/neurons_TVALID I 1
    hls/neurons_TREADY O 1
    shell/hls_neuron_tready I 1
    shell/hls_synapse_tdata O 192
    hls/synapses_TDATA I 192
    shell/hls_synapse_tvalid O 1
    hls/synapses_TVALID I 1
    hls/synapses_TREADY O 1
    shell/hls_synapse_tready I 1
    shell/hls_external_tdata O 128
    hls/external_events_TDATA I 128
    shell/hls_external_tvalid O 1
    hls/external_events_TVALID I 1
    hls/external_events_TREADY O 1
    shell/hls_external_tready I 1
    hls/trace_TDATA O 192
    shell/hls_trace_tdata I 192
    hls/trace_TVALID O 1
    shell/hls_trace_tvalid I 1
    shell/hls_trace_tready O 1
    hls/trace_TREADY I 1
} {
    assert_native_pin $pin $dir $width
}
proc link_native_axis {from to} {
    global report
    set master [require_intf $from]
    set slave [require_intf $to]
    foreach {pin mode} [list $master MASTER $slave SLAVE] {
        set actual [string toupper [string trim [get_property MODE $pin]]]
        if {$actual ne $mode} {
            error "generated native AXIS interface [get_property NAME $pin] MODE=$actual expected $mode"
        }
    }
    if {[llength [get_bd_intf_nets -quiet -of_objects $master]] ||
        [llength [get_bd_intf_nets -quiet -of_objects $slave]]} {
        error "native HLS AXIS interface was already connected"
    }
    connect_bd_intf_net $master $slave
    set ma [get_bd_intf_nets -of_objects $master]
    set sl [get_bd_intf_nets -of_objects $slave]
    if {[llength $ma] != 1 || [llength $sl] != 1 ||
        [get_property NAME $ma] ne [get_property NAME $sl]} {
        error "native AXIS interface nets do not match $from -> $to"
    }
    set ends [get_bd_intf_pins -of_objects $ma]
    if {[llength $ends] != 2} {
        error "native AXIS interface not exactly point-to-point $from -> $to"
    }
    lappend report "NATIVEINTF|$from|$to|[get_property NAME $ma]"
}
foreach {master slave} {
    shell/hls_neuron hls/neurons
    shell/hls_synapse hls/synapses
    shell/hls_external hls/external_events
    hls/trace shell/hls_trace
} {
    link_native_axis $master $slave
}
# Only genuine generated RTL module exposes sixth AXI4-Lite control.
set hls_axi [get_bd_intf_pins -quiet hls/s_axi_control]
if {[llength $hls_axi] != 1 ||
    [string toupper [get_property MODE $hls_axi]] ne "SLAVE"} {
    error "genuine HLS RTL does not expose Vivado SLAVE s_axi_control interface (no fake fallback)"
}
lappend report "HLSINTF|s_axi_control|SLAVE"

# Processor AXI master reaches four DMA controls, unchanged shell,
# and real HLS/s_axi_control. No fake interface is instantiated.
link_axis_or_axi ps/M_AXI_HPM0_FPD ctrl_sc/S00_AXI
foreach {index sink} {
    0 dma_neurons/S_AXI_LITE
    1 dma_synapses/S_AXI_LITE
    2 dma_external/S_AXI_LITE
    3 dma_trace/S_AXI_LITE
    4 shell/s_axi
    5 hls/s_axi_control
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
set clocks {ps/pl_clk0 ps/maxihpm0_fpd_aclk ps/saxihp0_fpd_aclk ctrl_sc/aclk mem_sc/aclk pl_reset/slowest_sync_clk shell/clk hls/ap_clk}
set reset_pins {pl_reset/peripheral_aresetn shell/rst_n hls/ap_rst_n}
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
# DISCOVERY ONLY: never assign a fabricated PS base or decode here.
# Record original Vivado 2025.2 exposed address spaces and six actual slave
# address-segment containers. This guides later explicit address mapping.
# No new register segment can be invented. No missing segment may be silently invented.
set addrfile [open $inventory_path w]
puts $addrfile "META|scope|OFFLINE_READ_ONLY_VIVADO_ADDRESS_INVENTORY_NOT_DECODE_PROOF"
foreach {bank interface} {
    dma_neurons dma_neurons/S_AXI_LITE
    dma_synapses dma_synapses/S_AXI_LITE
    dma_external dma_external/S_AXI_LITE
    dma_trace dma_trace/S_AXI_LITE
    shell shell/s_axi
    hls hls/s_axi_control
} {
    set candidates [get_bd_addr_segs -quiet -of_objects [require_intf $interface]]
    if {[llength $candidates] == 0} {
        puts $addrfile "SLAVE|$bank|$interface|NO_BD_SEGMENT_YET"
    } else {
        foreach segment $candidates {
            # Genuine owner Vivado 2025.2 exposed all six bd_addr_seg
            # objects, but their PATH property read back EMPTY here.
            # UG835 get_bd_addr_segs returns the segment object itself,
            # whose Tcl string representation is the canonical segment
            # path (e.g. /dma_neurons/S_AXI_LITE/Reg). Do not fabricate
            # a path, guess base addresses, or mislabel the object missing.
            set observed [string trim $segment]
            if {$observed eq "" || ![string match "/$bank/*" $observed]} {
                error "actual BD address segment object path not anchored to $bank/$interface: '$observed'"
            }
            puts $addrfile "SLAVE|$bank|$interface|$observed"
        }
    }
}
set spaces [get_bd_addr_spaces -quiet -of_objects [require_intf ps/M_AXI_HPM0_FPD]]
if {[llength $spaces] == 0} {puts $addrfile "SPACE|ps/M_AXI_HPM0_FPD|NO_BD_SPACE_YET"}
foreach space $spaces {
    puts $addrfile "SPACE|ps/M_AXI_HPM0_FPD|[get_property PATH $space]"
}
puts $addrfile "META|address_assignment|NOT_RUN"
puts $addrfile "META|physical_ddr|NOT_AUTHORIZED"
close $addrfile

# Preserve the previously owner-PASS real HLS native-grouped physical Vivado
# graph as a separately audited artifact before attempting ANY address changes.
set graphfile [open $report_path w]
foreach item $report {puts $graphfile $item}
close $graphfile

# All addresses are explicit operator-selected OFFLINE candidate values in
# the supplied separate 7-line map file. No default/auto assignment and
# absolutely NO physical PS/DDR/Linux MMIO permission is implied.
if {![file isfile $plan_path]} {error "missing explicit six-bank offline address plan"}
set pf [open $plan_path r]
set plan_lines [split [string trim [read $pf]] "\n"]
close $pf
if {[llength $plan_lines] != 7 ||
    [lindex $plan_lines 0] ne "META|scope|OFFLINE_CANDIDATE_SIX_PS_AXI_LITE_APERTURES_NOT_OS_APPROVED"} {
    error "six actual operator-provided AXI4-Lite apertures required; never auto-select PS bases"
}
set control_space [get_bd_addr_spaces -quiet -of_objects [require_intf ps/M_AXI_HPM0_FPD]]
if {[llength $control_space] != 1 || [string trim $control_space] ne "/ps/Data"} {
    error "expected exactly one real Zynq PS control master address space /ps/Data"
}
set af [open $mapped_path w]
puts $af "META|scope|OFFLINE_VIVADO_PS_CONTROL_SIX_SLAVE_ADDRESS_READBACK"
puts $af "SPACE|ps/M_AXI_HPM0_FPD|$control_space"
set before_end 0
set index 1
foreach {bank interface} {
    dma_neurons dma_neurons/S_AXI_LITE
    dma_synapses dma_synapses/S_AXI_LITE
    dma_external dma_external/S_AXI_LITE
    dma_trace dma_trace/S_AXI_LITE
    shell shell/s_axi
    hls hls/s_axi_control
} {
    set fields [split [lindex $plan_lines $index] "|"]
    if {[llength $fields] != 4 || [lindex $fields 0] ne "BANK" ||
        [lindex $fields 1] ne $bank} {
        error "wrong or reordered original PS control aperture $bank"
    }
    set base_text [lindex $fields 2]
    set length_text [lindex $fields 3]
    if {![regexp {^0x[0-9A-Fa-f]{1,16}$} $base_text] ||
        ![regexp {^0x[0-9A-Fa-f]{1,16}$} $length_text]} {
        error "candidate PS control aperture must use explicit bounded hexadecimal"
    }
    set wanted_base [expr {$base_text + 0}]
    set wanted_range [expr {$length_text + 0}]
    if {$wanted_base <= 0 || $wanted_range < 4096 ||
        $wanted_range > 1048576 || ($wanted_range & ($wanted_range - 1)) != 0 ||
        $wanted_base % $wanted_range != 0 ||
        $wanted_base < $before_end ||
        $wanted_base + $wanted_range > 1099511627776} {
        error "invalid, unaligned, overlapping or out-of-bounds explicit PS control aperture $bank"
    }
    set before_end [expr {$wanted_base + $wanted_range}]
    set source [get_bd_addr_segs -quiet -of_objects [require_intf $interface]]
    if {[llength $source] != 1 ||
        ![string match "/$interface/*" [string trim $source]]} {
        error "missing/ambiguous real original Vivado control slave address segment for $bank"
    }
    set slave [lindex $source 0]
    # Avoid silently remapping a previously assigned master segment.
    set mapped_before [get_bd_addr_segs -quiet -of_objects $slave]
    if {[llength $mapped_before] != 0} {
        error "control slave $slave already mapped; refusing to overwrite any address"
    }
    set created [assign_bd_address -target_address_space $control_space \
                     -offset $base_text -range $length_text $slave]
    if {[llength $created] != 1} {
        error "Vivado failed explicit operator-proposed PS assignment of real slave $slave"
    }
    # Require actual readback, including forward+reverse relation of master
    # and slave, not merely trusting the Tcl assign_bd_address return value.
    set masters [get_bd_addr_segs -quiet -of_objects $slave]
    if {[llength $masters] != 1 || [string trim $masters] ne [string trim $created]} {
        error "unexpected master-segment relationship after assigning $slave"
    }
    set master [lindex $masters 0]
    if {![string match "/ps/Data/*" "$master"]} {
        error "assigned $bank into wrong master namespace: $master"
    }
    set reverse [get_bd_addr_segs -quiet -of_objects $master]
    if {[llength $reverse] != 1 || [lindex $reverse 0] ne "$slave"} {
        error "master reverse mapping does not resolve authentic control slave $slave"
    }
    set rb_base [get_property OFFSET $master]
    set rb_range [get_property RANGE $master]
    if {![regexp {^0x[0-9A-Fa-f]+$} $rb_base] ||
        ![regexp {^0x[0-9A-Fa-f]+$} $rb_range]} {
        error "actual Vivado master segment OFFSET/RANGE missing for $bank"
    }
    if {[expr {$rb_base + 0}] != $wanted_base ||
        [expr {$rb_range + 0}] != $wanted_range} {
        error "actual Vivado master segment OFFSET/RANGE differs from original explicit offline plan for $bank"
    }
    puts $af "READBACK|$bank|$slave|$master|[format {0x%08X} $wanted_base]|[format {0x%08X} $wanted_range]"
    flush $af
    incr index
}
puts $af "META|address_assignment|SIX_EXPLICIT_VIVADO_ASSIGNMENTS_READ_BACK"
puts $af "META|physical_board|NOT_AUTHORIZED"
close $af
puts "PASS: M05.12d.3 six explicitly proposed actual Vivado PS address segments assigned and fully read back (OFFLINE, NOT OS MMIO)"

# Full, genuine Vivado block-design validation. Capture status separately:
# a failure must remain a failure, even if all SIX address segments passed.
# Do not claim generated SmartConnect width conversion, output products, DDR
# ownership, or device timing from the validation status alone.
set vrc [catch {validate_bd_design -force} vmsg]
set vf [open $validation_path w]
if {$vrc} {
    puts $vf "VALIDATION|FAIL|FULL_BD_VALIDATE_FORCE"
    close $vf
    puts stderr "M05_D3_REAL_BD_VALIDATION_FAILURE: $vmsg"
    error "M05.12d.3 actual Vivado full block design validation failed; see original log"
}
puts $vf "VALIDATION|PASS|FULL_BD_VALIDATE_FORCE"
close $vf
close_project
puts "PASS: M05.12d.3 explicit SIX control-banks and genuine full Vivado block design validation (NO IP GENERATION/BOARD/DDR)"
