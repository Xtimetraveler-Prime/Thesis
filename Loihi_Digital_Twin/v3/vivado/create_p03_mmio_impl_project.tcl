# FPGA-v3 P03.2 PS-MMIO-controlled one-engine / three-resident-context K26 shell.
#
# This shell starts from the final accepted P02 physical topology:
#
#   PL bulk paging:
#     P02 page walker
#       -> fixed 64 MiB backing-window guard
#       -> 128-bit / 256-byte AXI burst coalescer
#       -> SmartConnect
#       -> PS S_AXI_HP0_FPD
#       -> K26 DDR
#
# P03.2 adds the opposite control direction:
#
#   Cortex-A53 / PS M_AXI_HPM0_FPD
#       -> AXI Protocol Converter
#       -> p03_ps_control_regs AXI4-Lite
#       -> page / dispatch / resident-memory command signals
#
# VIO remains observation/reset-only. P03.3 will implement scheduling, routing,
# barriers, cache ownership, and result collection in Cortex-A53 software.
if {$argc != 16} {
    error "usage: create_p03_mmio_impl_project.tcl <ip_repo_dir> <project_dir> <target_part> <expected_vlnv> <controller_rtl> <memory_rtl> <reset_rtl> <hostmux_rtl> <walker_rtl> <arbiter_rtl> <range_guard_rtl> <adapter_rtl> <mmio_rtl> <report_dir> <jobs> <stage>"
}

set ip_repo_dir [file normalize [lindex $argv 0]]
set project_dir [file normalize [lindex $argv 1]]
set target_part [lindex $argv 2]
set expected_vlnv [lindex $argv 3]
set controller_rtl [file normalize [lindex $argv 4]]
set memory_rtl [file normalize [lindex $argv 5]]
set reset_rtl [file normalize [lindex $argv 6]]
set hostmux_rtl [file normalize [lindex $argv 7]]
set walker_rtl [file normalize [lindex $argv 8]]
set arbiter_rtl [file normalize [lindex $argv 9]]
set range_guard_rtl [file normalize [lindex $argv 10]]
set adapter_rtl [file normalize [lindex $argv 11]]
set mmio_rtl [file normalize [lindex $argv 12]]
set report_dir [file normalize [lindex $argv 13]]
set jobs [lindex $argv 14]
set stage [lindex $argv 15]
if {$stage ne "synth" && $stage ne "route"} {
    error "P03.2 stage must be synth or route, got: $stage"
}

foreach path [list $ip_repo_dir $controller_rtl $memory_rtl $reset_rtl $hostmux_rtl $walker_rtl $arbiter_rtl $range_guard_rtl $adapter_rtl $mmio_rtl] {
    if {![file exists $path]} { error "Required P03.2 input does not exist: $path" }
}
file mkdir $report_dir
file delete -force $project_dir
file mkdir $project_dir

set project_name "loihi_twin_v3_p03_mmio_impl"
set bd_name "loihi_twin_v3_p03_mmio_impl"
create_project $project_name $project_dir -part $target_part -force
set_property TARGET_LANGUAGE Verilog [current_project]
set_property SIMULATOR_LANGUAGE Mixed [current_project]
set_property XPM_LIBRARIES XPM_MEMORY [current_project]

set kv260_board_parts [get_board_parts -quiet xilinx.com:kv260_som:part0:*]
if {[llength $kv260_board_parts] == 0} {
    error "P03.2 requires installed KV260 SOM board files (xilinx.com:kv260_som:part0:*)."
}
set kv260_board_part [lindex [lsort -dictionary $kv260_board_parts] end]
set_property BOARD_PART $kv260_board_part [current_project]
puts "P03.2 K26 SOM board preset: $kv260_board_part"

foreach rtl [list $controller_rtl $memory_rtl $reset_rtl $hostmux_rtl $walker_rtl $arbiter_rtl $range_guard_rtl $adapter_rtl $mmio_rtl] {
    add_files -norecurse $rtl
    set_property file_type Verilog [get_files $rtl]
}
update_compile_order -fileset sources_1

set_property IP_REPO_PATHS [list $ip_repo_dir] [current_fileset]
update_ip_catalog -rebuild
if {[llength [get_ipdefs -all $expected_vlnv]] == 0} {
    error "Expected P03.2/P03 HLS IP was not found in catalog: $expected_vlnv"
}
foreach required_ip {
    xilinx.com:ip:zynq_ultra_ps_e:3.5
    xilinx.com:ip:vio:3.0
    xilinx.com:ip:xlconstant:1.1
    xilinx.com:ip:smartconnect:1.0
    xilinx.com:ip:axi_protocol_converter:2.1
} {
    if {[llength [get_ipdefs -all $required_ip]] == 0} {
        error "Required Vivado IP was not found: $required_ip"
    }
}

proc first_bd_pin {cell candidates} {
    foreach suffix $candidates {
        set pin [get_bd_pins -quiet ${cell}/${suffix}]
        if {[llength $pin] == 1} { return $pin }
    }
    return ""
}

proc hls_memory_pin {hls_name arg_name role required} {
    switch -- $role {
        address { set candidates [list ${arg_name}_address0 ${arg_name}_address ${arg_name}_Addr_A] }
        ce      { set candidates [list ${arg_name}_ce0 ${arg_name}_ce ${arg_name}_EN_A] }
        we      { set candidates [list ${arg_name}_we0 ${arg_name}_we ${arg_name}_WEN_A] }
        din     { set candidates [list ${arg_name}_d0 ${arg_name}_d ${arg_name}_Din_A] }
        dout    { set candidates [list ${arg_name}_q0 ${arg_name}_q ${arg_name}_Dout_A] }
        default { error "Unknown P03.2 HLS memory-pin role: $role" }
    }
    set pin [first_bd_pin $hls_name $candidates]
    if {$required && $pin eq ""} {
        puts "Available HLS pins for $arg_name: [get_bd_pins -quiet ${hls_name}/${arg_name}_*]"
        error "Required P03.2 HLS $role pin not found for ${hls_name}/${arg_name}"
    }
    return $pin
}

proc require_bd_pin {cell pin_name} {
    set pin [get_bd_pins -quiet ${cell}/${pin_name}]
    if {[llength $pin] != 1} {
        puts "Available pins for $cell: [get_bd_pins -quiet ${cell}/*]"
        error "Required P03.2 pin missing: ${cell}/${pin_name}"
    }
    return $pin
}

proc connect_pair {left right} {
    set lp [get_bd_pins -quiet $left]
    set rp [get_bd_pins -quiet $right]
    if {[llength $lp] != 1 || [llength $rp] != 1} {
        error "Missing P03.2 connection pin: left=$left ($lp) right=$right ($rp)"
    }
    connect_bd_net $lp $rp
}

proc connect_hls_memory_fabric {hls_name fabric_name arg_name mode} {
    set address [hls_memory_pin $hls_name $arg_name address 1]
    set ce [hls_memory_pin $hls_name $arg_name ce 1]
    connect_bd_net $address [require_bd_pin $fabric_name ${arg_name}_addra]
    connect_bd_net $ce [require_bd_pin $fabric_name ${arg_name}_ena]
    if {$mode eq "rw" || $mode eq "w"} {
        set we [hls_memory_pin $hls_name $arg_name we 1]
        set din [hls_memory_pin $hls_name $arg_name din 1]
        connect_bd_net $we [require_bd_pin $fabric_name ${arg_name}_wea]
        connect_bd_net $din [require_bd_pin $fabric_name ${arg_name}_dina]
    }
    if {$mode eq "rw" || $mode eq "r"} {
        set dout [hls_memory_pin $hls_name $arg_name dout 1]
        connect_bd_net [require_bd_pin $fabric_name ${arg_name}_douta] $dout
    }
}

create_bd_design $bd_name
set ps [create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e:3.5 zynq_ultra_ps_e_0]
apply_bd_automation -rule xilinx.com:bd_rule:zynq_ultra_ps_e -config {apply_board_preset "1"} $ps
set_property -dict [list \
    CONFIG.PSU__USE__M_AXI_GP0 {1} \
    CONFIG.PSU__MAXIGP0__DATA_WIDTH {32} \
    CONFIG.PSU__USE__M_AXI_GP1 {0} \
    CONFIG.PSU__USE__M_AXI_GP2 {0} \
    CONFIG.PSU__FPGA_PL0_ENABLE {1} \
    CONFIG.PSU__USE__FABRIC__RST {0} \
    CONFIG.PSU__USE__S_AXI_GP2 {1} \
    CONFIG.PSU__SAXIGP2__DATA_WIDTH {128} \
    CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {100}] $ps

set hls [create_bd_cell -type ip -vlnv $expected_vlnv loihi_core_v2_tick_0]
set ctrl [create_bd_cell -type module -reference p08_paged_dispatch_controller p08_paged_dispatch_controller_0]
set mem [create_bd_cell -type module -reference p05_context_memory_fabric p08_context_memory_0]
set reset_cond [create_bd_cell -type module -reference p04_reset_conditioner p08_reset_conditioner_0]
set heartbeat [create_bd_cell -type module -reference p04_heartbeat p08_heartbeat_0]
set page_walker [create_bd_cell -type module -reference p02_context_page_bank_walker p02_context_page_bank_walker_0]
set page_arbiter [create_bd_cell -type module -reference p02_page_host_arbiter p02_page_host_arbiter_0]
set range_guard [create_bd_cell -type module -reference p02_ddr_backing_range_guard p02_ddr_backing_range_guard_0]
set axi_adapter [create_bd_cell -type module -reference p02_axi128_burst_adapter p02_axi128_burst_adapter_0]
set hp0_smartconnect [create_bd_cell -type ip -vlnv xilinx.com:ip:smartconnect:1.0 p02_hp0_smartconnect_0]
set_property -dict [list CONFIG.NUM_SI {1} CONFIG.NUM_MI {1}] $hp0_smartconnect
set mmio [create_bd_cell -type module -reference p03_ps_control_regs p03_ps_control_regs_0]
set hpm0_protocol_converter [create_bd_cell -type ip -vlnv xilinx.com:ip:axi_protocol_converter:2.1 p03_hpm0_protocol_converter_0]

# P03.2 leaves packet routing / next-event policy to the forthcoming P03.3
# Cortex-A53 runtime. Disable P05's former controller-side Port-B integration
# path; packet/event banks remain accessible through the PS MMIO resident path.
set const0_1 [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 p08_const0_1]
set_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {0}] $const0_1
set const0_2 [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 p08_const0_2]
set_property -dict [list CONFIG.CONST_WIDTH {2} CONFIG.CONST_VAL {0}] $const0_2
set const0_12 [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 p08_const0_12]
set_property -dict [list CONFIG.CONST_WIDTH {12} CONFIG.CONST_VAL {0}] $const0_12
set const0_32 [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 p08_const0_32]
set_property -dict [list CONFIG.CONST_WIDTH {32} CONFIG.CONST_VAL {0}] $const0_32

# VIO output contract:
#   0 dispatch_start, 1 reset_request, 2 requested slot, 3 metadata,
#   4 timestep, 5 event read bank, 6..11 direct host/debug memory interface.
# VIO input contract exposes dispatch/HLS/host/reset status for physical checks.
set vio [create_bd_cell -type ip -vlnv xilinx.com:ip:vio:3.0 vio_p08]
set_property -dict [list \
    CONFIG.C_NUM_PROBE_IN {29} \
    CONFIG.C_NUM_PROBE_OUT {12} \
    CONFIG.C_PROBE_IN0_WIDTH {1} CONFIG.C_PROBE_IN1_WIDTH {1} CONFIG.C_PROBE_IN2_WIDTH {1} \
    CONFIG.C_PROBE_IN3_WIDTH {2} CONFIG.C_PROBE_IN4_WIDTH {7} CONFIG.C_PROBE_IN5_WIDTH {1} \
    CONFIG.C_PROBE_IN6_WIDTH {13} CONFIG.C_PROBE_IN7_WIDTH {32} CONFIG.C_PROBE_IN8_WIDTH {32} \
    CONFIG.C_PROBE_IN9_WIDTH {64} CONFIG.C_PROBE_IN10_WIDTH {64} \
    CONFIG.C_PROBE_IN11_WIDTH {1} CONFIG.C_PROBE_IN12_WIDTH {1} CONFIG.C_PROBE_IN13_WIDTH {1} \
    CONFIG.C_PROBE_IN14_WIDTH {1} CONFIG.C_PROBE_IN15_WIDTH {1} CONFIG.C_PROBE_IN16_WIDTH {1} \
    CONFIG.C_PROBE_IN17_WIDTH {11} CONFIG.C_PROBE_IN18_WIDTH {13} CONFIG.C_PROBE_IN19_WIDTH {32} \
    CONFIG.C_PROBE_IN20_WIDTH {1} CONFIG.C_PROBE_IN21_WIDTH {1} CONFIG.C_PROBE_IN22_WIDTH {1} \
    CONFIG.C_PROBE_IN23_WIDTH {1} CONFIG.C_PROBE_IN24_WIDTH {256} CONFIG.C_PROBE_IN25_WIDTH {32} \
    CONFIG.C_PROBE_IN26_WIDTH {1} CONFIG.C_PROBE_IN27_WIDTH {1} CONFIG.C_PROBE_IN28_WIDTH {1} \
    CONFIG.C_PROBE_OUT0_WIDTH {1} CONFIG.C_PROBE_OUT0_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT1_WIDTH {1} CONFIG.C_PROBE_OUT1_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT2_WIDTH {2} CONFIG.C_PROBE_OUT2_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT3_WIDTH {64} CONFIG.C_PROBE_OUT3_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT4_WIDTH {32} CONFIG.C_PROBE_OUT4_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT5_WIDTH {1} CONFIG.C_PROBE_OUT5_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT6_WIDTH {1} CONFIG.C_PROBE_OUT6_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT7_WIDTH {1} CONFIG.C_PROBE_OUT7_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT8_WIDTH {2} CONFIG.C_PROBE_OUT8_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT9_WIDTH {4} CONFIG.C_PROBE_OUT9_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT10_WIDTH {15} CONFIG.C_PROBE_OUT10_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT11_WIDTH {256} CONFIG.C_PROBE_OUT11_INIT_VAL {0x0}] $vio

# Separate paging VIO preserves the accepted P03.2 dispatch/debug probe contract.
# Outputs: start, page_out, mutable_only, resident_slot, 512 KiB record base.
# Inputs expose page completion/errors and AXI transport accounting.
set page_vio [create_bd_cell -type ip -vlnv xilinx.com:ip:vio:3.0 vio_p02_page]
set_property -dict [list \
    CONFIG.C_NUM_PROBE_IN {15} \
    CONFIG.C_NUM_PROBE_OUT {5} \
    CONFIG.C_PROBE_IN0_WIDTH {1} \
    CONFIG.C_PROBE_IN1_WIDTH {1} \
    CONFIG.C_PROBE_IN2_WIDTH {1} \
    CONFIG.C_PROBE_IN3_WIDTH {32} \
    CONFIG.C_PROBE_IN4_WIDTH {32} \
    CONFIG.C_PROBE_IN5_WIDTH {64} \
    CONFIG.C_PROBE_IN6_WIDTH {1} \
    CONFIG.C_PROBE_IN7_WIDTH {1} \
    CONFIG.C_PROBE_IN8_WIDTH {1} \
    CONFIG.C_PROBE_IN9_WIDTH {32} \
    CONFIG.C_PROBE_IN10_WIDTH {32} \
    CONFIG.C_PROBE_IN11_WIDTH {64} \
    CONFIG.C_PROBE_IN12_WIDTH {1} \
    CONFIG.C_PROBE_IN13_WIDTH {1} \
    CONFIG.C_PROBE_IN14_WIDTH {9} \
    CONFIG.C_PROBE_OUT0_WIDTH {1} CONFIG.C_PROBE_OUT0_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT1_WIDTH {1} CONFIG.C_PROBE_OUT1_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT2_WIDTH {1} CONFIG.C_PROBE_OUT2_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT3_WIDTH {2} CONFIG.C_PROBE_OUT3_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT4_WIDTH {64} CONFIG.C_PROBE_OUT4_INIT_VAL {0x0000000040000000}] $page_vio

set pl_clk [get_bd_pins zynq_ultra_ps_e_0/pl_clk0]
connect_bd_net $pl_clk \
    [get_bd_pins loihi_core_v2_tick_0/ap_clk] \
    [get_bd_pins p08_paged_dispatch_controller_0/clk] \
    [get_bd_pins p08_context_memory_0/clk] \
    [get_bd_pins p08_reset_conditioner_0/clk] \
    [get_bd_pins p08_heartbeat_0/clk] \
    [get_bd_pins p02_context_page_bank_walker_0/clk] \
    [get_bd_pins p02_page_host_arbiter_0/clk] \
    [get_bd_pins p02_axi128_burst_adapter_0/clk] \
    [get_bd_pins p02_hp0_smartconnect_0/aclk] \
    [get_bd_pins p03_ps_control_regs_0/s_axi_aclk] \
    [get_bd_pins p03_hpm0_protocol_converter_0/aclk] \
    [get_bd_pins zynq_ultra_ps_e_0/saxihp0_fpd_aclk] \
    [get_bd_pins zynq_ultra_ps_e_0/maxihpm0_fpd_aclk] \
    [get_bd_pins vio_p08/clk] \
    [get_bd_pins vio_p02_page/clk]

# Reset and heartbeat.
connect_pair vio_p08/probe_out1 p08_reset_conditioner_0/reset_request
connect_pair p08_reset_conditioner_0/reset loihi_core_v2_tick_0/ap_rst
connect_bd_net [get_bd_pins p08_reset_conditioner_0/resetn] \
    [get_bd_pins p08_paged_dispatch_controller_0/resetn] \
    [get_bd_pins p08_context_memory_0/resetn] \
    [get_bd_pins p08_heartbeat_0/resetn] \
    [get_bd_pins p02_context_page_bank_walker_0/resetn] \
    [get_bd_pins p02_page_host_arbiter_0/resetn] \
    [get_bd_pins p02_axi128_burst_adapter_0/resetn] \
    [get_bd_pins p02_hp0_smartconnect_0/aresetn] \
    [get_bd_pins p03_ps_control_regs_0/s_axi_aresetn] \
    [get_bd_pins p03_hpm0_protocol_converter_0/aresetn] \
    [get_bd_pins vio_p08/probe_in28]

# Dispatch command inputs now come from PS-visible MMIO.
connect_pair p03_ps_control_regs_0/dispatch_start p08_paged_dispatch_controller_0/dispatch_start
connect_pair p03_ps_control_regs_0/dispatch_context_slot p08_paged_dispatch_controller_0/requested_context_slot
connect_pair p03_ps_control_regs_0/dispatch_metadata p08_paged_dispatch_controller_0/context_metadata
connect_pair p03_ps_control_regs_0/dispatch_timestep p08_paged_dispatch_controller_0/dispatch_timestep
connect_pair p03_ps_control_regs_0/dispatch_event_read_bank p08_paged_dispatch_controller_0/requested_event_read_bank
connect_pair p02_page_host_arbiter_0/debug_busy p08_paged_dispatch_controller_0/host_busy

# HLS control/scalar integration.
connect_pair p08_paged_dispatch_controller_0/core_start loihi_core_v2_tick_0/ap_start
connect_bd_net [get_bd_pins loihi_core_v2_tick_0/ap_ready] \
    [get_bd_pins p08_paged_dispatch_controller_0/core_ready] [get_bd_pins vio_p08/probe_in14]
connect_pair loihi_core_v2_tick_0/ap_idle vio_p08/probe_in15
connect_bd_net [get_bd_pins loihi_core_v2_tick_0/ap_done] \
    [get_bd_pins p08_paged_dispatch_controller_0/core_done] [get_bd_pins vio_p08/probe_in16]
connect_pair loihi_core_v2_tick_0/spike_count vio_p08/probe_in17
connect_bd_net [get_bd_pins loihi_core_v2_tick_0/packet_count] \
    [get_bd_pins p08_paged_dispatch_controller_0/core_packet_count] [get_bd_pins vio_p08/probe_in18]
connect_bd_net [get_bd_pins loihi_core_v2_tick_0/status_flags] \
    [get_bd_pins p08_paged_dispatch_controller_0/core_status] [get_bd_pins vio_p08/probe_in19]
connect_pair p08_paged_dispatch_controller_0/core_compartment_count loihi_core_v2_tick_0/compartment_count
connect_pair p08_paged_dispatch_controller_0/core_event_count loihi_core_v2_tick_0/event_count
connect_pair p08_paged_dispatch_controller_0/core_synapse_count loihi_core_v2_tick_0/synapse_count
connect_pair p08_paged_dispatch_controller_0/core_route_count loihi_core_v2_tick_0/route_count
connect_pair p08_paged_dispatch_controller_0/core_timestep loihi_core_v2_tick_0/timestep

# HLS memory ports to the accepted full-context P05 memory fabric.
foreach spec {
    {config_words r} {state_words rw} {axon_words r} {synapse_words r}
    {route_desc_words r} {route_words r} {input_events r} {trace_words w}
    {packet_words w}
} {
    lassign $spec arg mode
    connect_hls_memory_fabric loihi_core_v2_tick_0 p08_context_memory_0 $arg $mode
}

# One selected resident slot is visible to the HLS engine per dispatch.
connect_pair p08_paged_dispatch_controller_0/active_context_slot p08_context_memory_0/active_context_slot
connect_pair p08_paged_dispatch_controller_0/event_read_bank p08_context_memory_0/event_read_bank
connect_pair p08_paged_dispatch_controller_0/busy p08_context_memory_0/compute_busy

# Disable former P05 controller-side packet/event integration. Host software owns
# packet readback and backing next-event insertion between dispatches.
connect_bd_net [get_bd_pins p08_const0_1/dout] \
    [get_bd_pins p08_context_memory_0/integration_packet_en] \
    [get_bd_pins p08_context_memory_0/integration_event_we]
connect_bd_net [get_bd_pins p08_const0_2/dout] \
    [get_bd_pins p08_context_memory_0/integration_packet_context] \
    [get_bd_pins p08_context_memory_0/integration_event_context]
connect_bd_net [get_bd_pins p08_const0_12/dout] \
    [get_bd_pins p08_context_memory_0/integration_packet_addr] \
    [get_bd_pins p08_context_memory_0/integration_event_addr]
connect_pair p08_const0_32/dout p08_context_memory_0/integration_event_data

# Existing VIO debug access now enters the Port-B arbiter.
connect_pair p03_ps_control_regs_0/debug_req p02_page_host_arbiter_0/debug_req
connect_pair p03_ps_control_regs_0/debug_write p02_page_host_arbiter_0/debug_write
connect_pair p03_ps_control_regs_0/debug_context_slot p02_page_host_arbiter_0/debug_context_slot
connect_pair p03_ps_control_regs_0/debug_bank p02_page_host_arbiter_0/debug_bank
connect_pair p03_ps_control_regs_0/debug_addr p02_page_host_arbiter_0/debug_addr
connect_pair p03_ps_control_regs_0/debug_wdata p02_page_host_arbiter_0/debug_wdata

# Arbiter drives the accepted P05 memory-fabric Port B.
connect_pair p02_page_host_arbiter_0/fabric_req p08_context_memory_0/host_req
connect_pair p02_page_host_arbiter_0/fabric_write p08_context_memory_0/host_write
connect_pair p02_page_host_arbiter_0/fabric_context_slot p08_context_memory_0/host_context_slot
connect_pair p02_page_host_arbiter_0/fabric_bank p08_context_memory_0/host_bank
connect_pair p02_page_host_arbiter_0/fabric_addr p08_context_memory_0/host_addr
connect_pair p02_page_host_arbiter_0/fabric_wdata p08_context_memory_0/host_wdata
connect_pair p08_context_memory_0/host_busy p02_page_host_arbiter_0/fabric_busy
connect_pair p08_context_memory_0/host_ack p02_page_host_arbiter_0/fabric_ack
connect_pair p08_context_memory_0/host_rvalid p02_page_host_arbiter_0/fabric_rvalid
connect_pair p08_context_memory_0/host_error p02_page_host_arbiter_0/fabric_error
connect_pair p08_context_memory_0/host_rdata p02_page_host_arbiter_0/fabric_rdata

# Page walker owns the alternate arbiter side.
connect_pair p02_context_page_bank_walker_0/busy p02_page_host_arbiter_0/page_active
connect_pair p02_context_page_bank_walker_0/host_req p02_page_host_arbiter_0/page_req
connect_pair p02_context_page_bank_walker_0/host_write p02_page_host_arbiter_0/page_write
connect_pair p02_context_page_bank_walker_0/host_context_slot p02_page_host_arbiter_0/page_context_slot
connect_pair p02_context_page_bank_walker_0/host_bank p02_page_host_arbiter_0/page_bank
connect_pair p02_context_page_bank_walker_0/host_addr p02_page_host_arbiter_0/page_addr
connect_pair p02_context_page_bank_walker_0/host_wdata p02_page_host_arbiter_0/page_wdata
connect_pair p02_page_host_arbiter_0/page_busy p02_context_page_bank_walker_0/host_busy
connect_pair p02_page_host_arbiter_0/page_ack p02_context_page_bank_walker_0/host_ack
connect_pair p02_page_host_arbiter_0/page_rvalid p02_context_page_bank_walker_0/host_rvalid
connect_pair p02_page_host_arbiter_0/page_error p02_context_page_bank_walker_0/host_error
connect_pair p02_page_host_arbiter_0/page_rdata p02_context_page_bank_walker_0/host_rdata

# Walker DDR requests are confined to the fixed 64 MiB backing window.
connect_pair p02_context_page_bank_walker_0/ddr_req p02_ddr_backing_range_guard_0/req
connect_pair p02_context_page_bank_walker_0/ddr_write p02_ddr_backing_range_guard_0/req_write
connect_pair p02_context_page_bank_walker_0/ddr_addr p02_ddr_backing_range_guard_0/req_addr
connect_pair p02_context_page_bank_walker_0/ddr_size_bytes p02_ddr_backing_range_guard_0/req_size_bytes
connect_pair p02_context_page_bank_walker_0/ddr_wdata p02_ddr_backing_range_guard_0/req_wdata
connect_pair p02_ddr_backing_range_guard_0/busy p02_context_page_bank_walker_0/ddr_busy
connect_pair p02_ddr_backing_range_guard_0/ack p02_context_page_bank_walker_0/ddr_ack
connect_pair p02_ddr_backing_range_guard_0/rvalid p02_context_page_bank_walker_0/ddr_rvalid
connect_pair p02_ddr_backing_range_guard_0/error p02_context_page_bank_walker_0/ddr_error
connect_pair p02_ddr_backing_range_guard_0/rdata p02_context_page_bank_walker_0/ddr_rdata

# Guarded scalar stream enters the accepted P02.3b1 AXI burst adapter.
connect_pair p02_ddr_backing_range_guard_0/downstream_req p02_axi128_burst_adapter_0/req
connect_pair p02_ddr_backing_range_guard_0/downstream_write p02_axi128_burst_adapter_0/req_write
connect_pair p02_ddr_backing_range_guard_0/downstream_addr p02_axi128_burst_adapter_0/req_addr
connect_pair p02_ddr_backing_range_guard_0/downstream_size_bytes p02_axi128_burst_adapter_0/req_size_bytes
connect_pair p02_ddr_backing_range_guard_0/downstream_wdata p02_axi128_burst_adapter_0/req_wdata
connect_pair p02_axi128_burst_adapter_0/busy p02_ddr_backing_range_guard_0/downstream_busy
connect_pair p02_axi128_burst_adapter_0/ack p02_ddr_backing_range_guard_0/downstream_ack
connect_pair p02_axi128_burst_adapter_0/rvalid p02_ddr_backing_range_guard_0/downstream_rvalid
connect_pair p02_axi128_burst_adapter_0/error p02_ddr_backing_range_guard_0/downstream_error
connect_pair p02_axi128_burst_adapter_0/rdata p02_ddr_backing_range_guard_0/downstream_rdata

# Real 128-bit AXI4 HP0 transport into PS DDR.
connect_bd_intf_net [get_bd_intf_pins p02_axi128_burst_adapter_0/M_AXI] \
    [get_bd_intf_pins p02_hp0_smartconnect_0/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins p02_hp0_smartconnect_0/M00_AXI] \
    [get_bd_intf_pins zynq_ultra_ps_e_0/S_AXI_HP0_FPD]

set hp0_ddr_low [get_bd_addr_segs -quiet zynq_ultra_ps_e_0/SAXIGP2/HP0_DDR_LOW]
if {[llength $hp0_ddr_low] != 1} {
    error "P03.2 HP0 DDR_LOW address segment was not found."
}
assign_bd_address -offset 0x00000000 -range 0x80000000 \
    -target_address_space [get_bd_addr_spaces p02_axi128_burst_adapter_0/M_AXI] \
    $hp0_ddr_low -force

# PS -> PL control path on M_AXI_HPM0_FPD.
# A dedicated AXI Protocol Converter is used because there is exactly one
# control slave; no HPM0 SmartConnect routing fabric is required.
connect_bd_intf_net [get_bd_intf_pins zynq_ultra_ps_e_0/M_AXI_HPM0_FPD] \
    [get_bd_intf_pins p03_hpm0_protocol_converter_0/S_AXI]
connect_bd_intf_net [get_bd_intf_pins p03_hpm0_protocol_converter_0/M_AXI] \
    [get_bd_intf_pins p03_ps_control_regs_0/S_AXI]

set mmio_segments [get_bd_addr_segs -quiet -of_objects \
    [get_bd_intf_pins p03_ps_control_regs_0/S_AXI]]
if {[llength $mmio_segments] != 1} {
    error "P03.2 expected exactly one MMIO slave address segment, got [llength $mmio_segments]"
}
set hpm0_spaces [get_bd_addr_spaces -quiet -of_objects \
    [get_bd_intf_pins zynq_ultra_ps_e_0/M_AXI_HPM0_FPD]]
if {[llength $hpm0_spaces] != 1} {
    error "P03.2 expected exactly one HPM0 master address space, got [llength $hpm0_spaces]"
}
assign_bd_address -offset 0xA4000000 -range 0x00001000 \
    -target_address_space [lindex $hpm0_spaces 0] \
    [lindex $mmio_segments 0] -force

# Paging command inputs now come from PS-visible MMIO.
connect_pair p03_ps_control_regs_0/page_start p02_context_page_bank_walker_0/cmd_start
connect_pair p03_ps_control_regs_0/page_out p02_context_page_bank_walker_0/cmd_page_out
connect_pair p03_ps_control_regs_0/page_mutable_only p02_context_page_bank_walker_0/cmd_mutable_only
connect_pair p03_ps_control_regs_0/page_context_slot p02_context_page_bank_walker_0/cmd_context_slot
connect_pair p03_ps_control_regs_0/page_record_base p02_context_page_bank_walker_0/cmd_record_base

connect_pair p02_context_page_bank_walker_0/busy vio_p02_page/probe_in0
connect_pair p02_context_page_bank_walker_0/transfer_done vio_p02_page/probe_in1
connect_pair p02_context_page_bank_walker_0/start_blocked vio_p02_page/probe_in2
connect_pair p02_context_page_bank_walker_0/bytes_transferred vio_p02_page/probe_in3
connect_pair p02_context_page_bank_walker_0/completed_transfers vio_p02_page/probe_in4
connect_pair p02_context_page_bank_walker_0/last_transfer_cycles vio_p02_page/probe_in5
connect_pair p02_context_page_bank_walker_0/error_command vio_p02_page/probe_in6
connect_pair p02_context_page_bank_walker_0/error_host vio_p02_page/probe_in7
connect_pair p02_context_page_bank_walker_0/error_ddr vio_p02_page/probe_in8
connect_pair p02_axi128_burst_adapter_0/completed_read_bursts vio_p02_page/probe_in9
connect_pair p02_axi128_burst_adapter_0/completed_write_bursts vio_p02_page/probe_in10
connect_pair p02_axi128_burst_adapter_0/axi_bytes_moved vio_p02_page/probe_in11
connect_pair p02_axi128_burst_adapter_0/protocol_error vio_p02_page/probe_in12
connect_pair p02_ddr_backing_range_guard_0/range_error vio_p02_page/probe_in13
connect_pair p02_axi128_burst_adapter_0/pending_write_bytes vio_p02_page/probe_in14

# MMIO page status inputs.
connect_pair p02_context_page_bank_walker_0/busy p03_ps_control_regs_0/page_busy
connect_pair p02_context_page_bank_walker_0/transfer_done p03_ps_control_regs_0/page_done
connect_pair p02_context_page_bank_walker_0/start_blocked p03_ps_control_regs_0/page_start_blocked
connect_pair p02_context_page_bank_walker_0/bytes_transferred p03_ps_control_regs_0/page_bytes_transferred
connect_pair p02_context_page_bank_walker_0/completed_transfers p03_ps_control_regs_0/page_completed_transfers
connect_pair p02_context_page_bank_walker_0/last_transfer_cycles p03_ps_control_regs_0/page_last_transfer_cycles
connect_pair p02_context_page_bank_walker_0/error_command p03_ps_control_regs_0/page_error_command
connect_pair p02_context_page_bank_walker_0/error_host p03_ps_control_regs_0/page_error_host
connect_pair p02_context_page_bank_walker_0/error_ddr p03_ps_control_regs_0/page_error_ddr
connect_pair p02_axi128_burst_adapter_0/completed_read_bursts p03_ps_control_regs_0/page_completed_read_bursts
connect_pair p02_axi128_burst_adapter_0/completed_write_bursts p03_ps_control_regs_0/page_completed_write_bursts
connect_pair p02_axi128_burst_adapter_0/axi_bytes_moved p03_ps_control_regs_0/page_axi_bytes_moved
connect_pair p02_axi128_burst_adapter_0/protocol_error p03_ps_control_regs_0/page_protocol_error
connect_pair p02_ddr_backing_range_guard_0/range_error p03_ps_control_regs_0/page_range_error
connect_pair p02_axi128_burst_adapter_0/pending_write_bytes p03_ps_control_regs_0/page_pending_write_bytes

# MMIO dispatch status inputs.
connect_pair p08_paged_dispatch_controller_0/busy p03_ps_control_regs_0/dispatch_busy
connect_pair p08_paged_dispatch_controller_0/dispatch_done p03_ps_control_regs_0/dispatch_done
connect_pair p08_paged_dispatch_controller_0/start_blocked p03_ps_control_regs_0/dispatch_start_blocked
connect_pair p08_paged_dispatch_controller_0/active_context_slot p03_ps_control_regs_0/dispatch_active_context_slot
connect_pair p08_paged_dispatch_controller_0/active_logical_core_id p03_ps_control_regs_0/dispatch_active_logical_core_id
connect_pair p08_paged_dispatch_controller_0/event_read_bank p03_ps_control_regs_0/dispatch_active_event_bank
connect_pair p08_paged_dispatch_controller_0/packet_count_latched p03_ps_control_regs_0/dispatch_packet_count
connect_pair p08_paged_dispatch_controller_0/status_latched p03_ps_control_regs_0/dispatch_core_status
connect_pair p08_paged_dispatch_controller_0/completed_dispatches p03_ps_control_regs_0/dispatch_completed
connect_pair p08_paged_dispatch_controller_0/last_dispatch_cycles p03_ps_control_regs_0/dispatch_last_cycles
connect_pair p08_paged_dispatch_controller_0/error_metadata p03_ps_control_regs_0/dispatch_error_metadata
connect_pair p08_paged_dispatch_controller_0/error_packet_overflow p03_ps_control_regs_0/dispatch_error_packet_overflow
connect_pair p08_paged_dispatch_controller_0/error_core_status p03_ps_control_regs_0/dispatch_error_core_status
connect_pair p08_context_memory_0/hls_address_error p03_ps_control_regs_0/dispatch_memory_address_error

# MMIO resident-memory response inputs.
connect_pair p02_page_host_arbiter_0/debug_busy p03_ps_control_regs_0/debug_busy
connect_pair p02_page_host_arbiter_0/debug_ack p03_ps_control_regs_0/debug_ack
connect_pair p02_page_host_arbiter_0/debug_rvalid p03_ps_control_regs_0/debug_rvalid
connect_pair p02_page_host_arbiter_0/debug_error p03_ps_control_regs_0/debug_error
connect_pair p02_page_host_arbiter_0/debug_rdata p03_ps_control_regs_0/debug_rdata

# Dispatch observations.
connect_pair p08_paged_dispatch_controller_0/dispatch_done vio_p08/probe_in0
connect_pair p08_paged_dispatch_controller_0/busy vio_p08/probe_in1
connect_pair p08_paged_dispatch_controller_0/start_blocked vio_p08/probe_in2
connect_pair p08_paged_dispatch_controller_0/active_context_slot vio_p08/probe_in3
connect_pair p08_paged_dispatch_controller_0/active_logical_core_id vio_p08/probe_in4
connect_pair p08_paged_dispatch_controller_0/event_read_bank vio_p08/probe_in5
connect_pair p08_paged_dispatch_controller_0/packet_count_latched vio_p08/probe_in6
connect_pair p08_paged_dispatch_controller_0/status_latched vio_p08/probe_in7
connect_pair p08_paged_dispatch_controller_0/completed_dispatches vio_p08/probe_in8
connect_pair p08_paged_dispatch_controller_0/active_cycles vio_p08/probe_in9
connect_pair p08_paged_dispatch_controller_0/last_dispatch_cycles vio_p08/probe_in10
connect_pair p08_paged_dispatch_controller_0/error_metadata vio_p08/probe_in11
connect_pair p08_paged_dispatch_controller_0/error_packet_overflow vio_p08/probe_in12
connect_pair p08_paged_dispatch_controller_0/error_core_status vio_p08/probe_in13

# Host/memory observations.
connect_pair p02_page_host_arbiter_0/debug_busy vio_p08/probe_in20
connect_pair p02_page_host_arbiter_0/debug_ack vio_p08/probe_in21
connect_pair p02_page_host_arbiter_0/debug_rvalid vio_p08/probe_in22
connect_pair p02_page_host_arbiter_0/debug_error vio_p08/probe_in23
connect_pair p02_page_host_arbiter_0/debug_rdata vio_p08/probe_in24
connect_pair p08_heartbeat_0/count vio_p08/probe_in25
connect_pair p08_context_memory_0/hls_address_error vio_p08/probe_in26
connect_pair p08_context_memory_0/integration_address_error vio_p08/probe_in27

validate_bd_design
save_bd_design
puts "P03.2 HP0 DDR-paged one-engine / three-resident-context block design validated successfully."

set bd_file [lindex [get_files -quiet */${bd_name}.bd] 0]
if {$bd_file eq ""} { error "P03.2 block design file was not found" }
generate_target all $bd_file
set wrapper_files [make_wrapper -files $bd_file -top]
if {[llength $wrapper_files] == 0} { error "P03.2 Vivado wrapper generation failed" }
add_files -norecurse $wrapper_files
set_property top ${bd_name}_wrapper [current_fileset]
update_compile_order -fileset sources_1

if {$stage eq "synth"} {
    launch_runs synth_1 -jobs $jobs
    wait_on_run synth_1
    if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {
        error "P03.2 synthesis did not complete: [get_property STATUS [get_runs synth_1]]"
    }
    open_run synth_1

    set util_text [report_utilization -return_string]
    set util_file [open [file join $report_dir utilization_post_synth.rpt] w]
    puts $util_file $util_text
    close $util_file
    report_utilization -hierarchical -hierarchical_depth 10 -file [file join $report_dir utilization_hierarchical_post_synth.rpt]
    report_timing_summary -delay_type min_max -max_paths 20 -report_unconstrained -file [file join $report_dir timing_summary_post_synth.rpt]
    write_checkpoint -force [file join $report_dir p03_2_mmio_post_synth.dcp]

    set metrics [open [file join $report_dir p03_2_post_synth_metrics.txt] w]
    if {[regexp {\| Block RAM Tile\s+\|\s+([0-9.]+)\s+\|} $util_text -> bram_tiles]} { puts $metrics "block_ram_tiles=$bram_tiles" }
    if {[regexp {\| URAM\s+\|\s+([0-9.]+)\s+\|} $util_text -> uram_count]} { puts $metrics "uram=$uram_count" }
    puts $metrics "resident_context_slots=3"
    puts $metrics "physical_engines=1"
    puts $metrics "logical_capacity_changed=0"
    puts $metrics "p02_ddr_backing_base=0x40000000"
    puts $metrics "p02_ddr_backing_bytes=0x04000000"
    puts $metrics "p02_ddr_record_bytes=0x00080000"
    puts $metrics "p02_ddr_logical_capacity=128"
    puts $metrics "p02_hp0_enabled=1"
    puts $metrics "p02_hp0_data_width_bits=128"
puts $metrics "p03_hpm0_enabled=1"
puts $metrics "p03_hpm0_data_width_bits=32"
puts $metrics "p03_hpm0_transport=axi_protocol_converter"
puts $metrics "p03_mmio_base=0xA4000000"
puts $metrics "p03_mmio_range_bytes=0x00001000"
puts $metrics "p03_mmio_controls_page=1"
puts $metrics "p03_mmio_controls_dispatch=1"
puts $metrics "p03_mmio_controls_resident_memory=1"
    puts $metrics "p02_axi_burst_beats=16"
    puts $metrics "p02_axi_burst_bytes=256"
    puts $metrics "p02_ddr_range_guard=1"
    puts $metrics "p02_page_walker=1"
    puts $metrics "p02_page_host_arbiter=1"
    puts $metrics "p02_host_controls_page_command=0"
    puts $metrics "p03_ps_runtime_implemented=0"
    puts $metrics "target_part=$target_part"
    puts $metrics "board_part=$kv260_board_part"
    puts $metrics "pl_clock_requested_mhz=100"
    close $metrics

    puts "P03.2 integration synthesis completed successfully."
    return
}

set_property STEPS.PHYS_OPT_DESIGN.IS_ENABLED true [get_runs impl_1]
launch_runs impl_1 -to_step write_bitstream -jobs $jobs
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {
    error "P03.2 implementation did not complete: [get_property STATUS [get_runs impl_1]]"
}
open_run impl_1

report_timing_summary -delay_type min_max -max_paths 20 -report_unconstrained -file [file join $report_dir timing_summary_post_route.rpt]
set util_text [report_utilization -return_string]
set util_file [open [file join $report_dir utilization_post_route.rpt] w]
puts $util_file $util_text
close $util_file
report_utilization -hierarchical -hierarchical_depth 8 -file [file join $report_dir utilization_hierarchical_post_route.rpt]
report_clock_utilization -file [file join $report_dir clock_utilization_post_route.rpt]
report_bus_skew -file [file join $report_dir bus_skew_post_route.rpt]
report_drc -file [file join $report_dir drc_post_route.rpt]
report_methodology -file [file join $report_dir methodology_post_route.rpt]
write_checkpoint -force [file join $report_dir p03_2_mmio_post_route.dcp]

set primitive_file [open [file join $report_dir memory_primitives_post_route.rpt] w]
foreach c [lsort [get_cells -hierarchical -filter {REF_NAME == RAMB36E2 || REF_NAME == RAMB18E2 || REF_NAME == URAM288}]] {
    puts $primitive_file "[get_property REF_NAME $c] $c"
}
close $primitive_file

set metrics [open [file join $report_dir p03_2_post_route_metrics.txt] w]
set setup_paths [get_timing_paths -quiet -delay_type max -max_paths 1 -nworst 1]
set hold_paths [get_timing_paths -quiet -delay_type min -max_paths 1 -nworst 1]
if {[llength $setup_paths] > 0} { puts $metrics "wns_ns=[get_property SLACK [lindex $setup_paths 0]]" } else { puts $metrics "wns_ns=NA" }
if {[llength $hold_paths] > 0} { puts $metrics "whs_ns=[get_property SLACK [lindex $hold_paths 0]]" } else { puts $metrics "whs_ns=NA" }
if {[regexp {\| Block RAM Tile\s+\|\s+([0-9.]+)\s+\|} $util_text -> bram_tiles]} { puts $metrics "block_ram_tiles=$bram_tiles" }
if {[regexp {\| URAM\s+\|\s+([0-9.]+)\s+\|} $util_text -> uram_count]} { puts $metrics "uram=$uram_count" }
puts $metrics "p02_reference_logical_backing_contexts=5"
puts $metrics "resident_context_slots=3"
puts $metrics "physical_engines=1"
puts $metrics "external_host_paged_dispatch=0"
puts $metrics "on_fabric_cross_page_router=0"
puts $metrics "p03_ps_routing_runtime_implemented=0"
puts $metrics "p03_ps_barrier_runtime_implemented=0"
puts $metrics "logical_capacity_changed=0"
puts $metrics "reset_strategy=source_controlled_synchronous_conditioner"
puts $metrics "target_part=$target_part"
puts $metrics "board_part=$kv260_board_part"
puts $metrics "pl_clock_requested_mhz=100"
puts $metrics "p02_ddr_backing_base=0x40000000"
puts $metrics "p02_ddr_backing_bytes=0x04000000"
puts $metrics "p02_ddr_record_bytes=0x00080000"
puts $metrics "p02_ddr_logical_capacity=128"
puts $metrics "p02_hp0_enabled=1"
puts $metrics "p02_hp0_data_width_bits=128"
puts $metrics "p03_hpm0_enabled=1"
puts $metrics "p03_hpm0_data_width_bits=32"
puts $metrics "p03_hpm0_transport=axi_protocol_converter"
puts $metrics "p03_mmio_base=0xA4000000"
puts $metrics "p03_mmio_range_bytes=0x00001000"
puts $metrics "p03_mmio_controls_page=1"
puts $metrics "p03_mmio_controls_dispatch=1"
puts $metrics "p03_mmio_controls_resident_memory=1"
puts $metrics "p02_axi_burst_beats=16"
puts $metrics "p02_axi_burst_bytes=256"
puts $metrics "p02_ddr_range_guard=1"
puts $metrics "p02_page_walker=1"
puts $metrics "p02_page_host_arbiter=1"
puts $metrics "p02_host_controls_page_command=0"
puts $metrics "p03_ps_runtime_implemented=0"
close $metrics

set bit_file [file join $report_dir p03_2_ps_mmio.bit]
set ltx_file [file join $report_dir p03_2_ps_mmio.ltx]
set xsa_file [file join $report_dir p03_2_ps_mmio.xsa]
write_debug_probes -force $ltx_file

set impl_run_dir [file join $project_dir "${project_name}.runs" impl_1]
set impl_bit_files [glob -nocomplain [file join $impl_run_dir *.bit]]
if {[llength $impl_bit_files] != 1} {
    error "P03.2 expected exactly one run-owned bitstream in $impl_run_dir, got [llength $impl_bit_files]"
}
set impl_bit_file [lindex $impl_bit_files 0]
file copy -force $impl_bit_file $bit_file

write_hw_platform -fixed -include_bit -force -file $xsa_file
puts "P03.2 routed implementation completed successfully."
puts "P03.2 bitstream: $bit_file"
puts "P03.2 debug probes: $ltx_file"
puts "P03.2 fixed XSA: $xsa_file"
puts "P03.2 reports: $report_dir"
