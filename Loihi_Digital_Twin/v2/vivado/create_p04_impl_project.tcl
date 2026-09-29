# P04 two-endpoint K26 integration shell.
if {$argc != 12} {
    error "usage: create_p04_impl_project.tcl <ip_repo_dir> <project_dir> <target_part> <expected_vlnv> <router_rtl> <streamer_rtl> <controller_rtl> <memory_rtl> <hostmux_rtl> <report_dir> <jobs> <stage:synth|route>"
}

set ip_repo_dir [file normalize [lindex $argv 0]]
set project_dir [file normalize [lindex $argv 1]]
set target_part [lindex $argv 2]
set expected_vlnv [lindex $argv 3]
set router_rtl [file normalize [lindex $argv 4]]
set streamer_rtl [file normalize [lindex $argv 5]]
set controller_rtl [file normalize [lindex $argv 6]]
set memory_rtl [file normalize [lindex $argv 7]]
set hostmux_rtl [file normalize [lindex $argv 8]]
set report_dir [file normalize [lindex $argv 9]]
set jobs [lindex $argv 10]
set stage [lindex $argv 11]
if {$stage ne "synth" && $stage ne "route"} { error "P04 stage must be synth or route" }

foreach path [list $ip_repo_dir $router_rtl $streamer_rtl $controller_rtl $memory_rtl $hostmux_rtl] {
    if {![file exists $path]} { error "Required P04 input does not exist: $path" }
}
file mkdir $report_dir
file delete -force $project_dir
file mkdir $project_dir

set project_name "loihi_twin_v2_p04_impl"
set bd_name "loihi_twin_v2_p04_impl"
create_project $project_name $project_dir -part $target_part -force
set_property TARGET_LANGUAGE Verilog [current_project]
set_property SIMULATOR_LANGUAGE Mixed [current_project]
set_property XPM_LIBRARIES XPM_MEMORY [current_project]

set kv260_board_parts [get_board_parts -quiet xilinx.com:kv260_som:part0:*]
if {[llength $kv260_board_parts] == 0} {
    error "P04 requires installed KV260 SOM board files (xilinx.com:kv260_som:part0:*)."
}
set kv260_board_part [lindex [lsort -dictionary $kv260_board_parts] end]
set_property BOARD_PART $kv260_board_part [current_project]
puts "P04 K26 SOM board preset: $kv260_board_part"

foreach rtl [list $router_rtl $streamer_rtl $controller_rtl $memory_rtl $hostmux_rtl] {
    add_files -norecurse $rtl
    set_property file_type Verilog [get_files $rtl]
}
update_compile_order -fileset sources_1

set_property IP_REPO_PATHS [list $ip_repo_dir] [current_fileset]
update_ip_catalog -rebuild
if {[llength [get_ipdefs -all $expected_vlnv]] == 0} {
    error "Expected P04/P03 HLS IP was not found in catalog: $expected_vlnv"
}
foreach required_ip {
    xilinx.com:ip:zynq_ultra_ps_e:3.5
    xilinx.com:ip:vio:3.0
    xilinx.com:ip:proc_sys_reset:5.0
    xilinx.com:ip:xlconstant:1.1
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
        default { error "Unknown P04 HLS memory-pin role: $role" }
    }
    set pin [first_bd_pin $hls_name $candidates]
    if {$required && $pin eq ""} {
        puts "Available HLS pins for $arg_name: [get_bd_pins -quiet ${hls_name}/${arg_name}_*]"
        error "Required P04 HLS $role pin not found for ${hls_name}/${arg_name}"
    }
    return $pin
}

proc require_bd_pin {cell pin_name} {
    set pin [get_bd_pins -quiet ${cell}/${pin_name}]
    if {[llength $pin] != 1} {
        puts "Available pins for $cell: [get_bd_pins -quiet ${cell}/*]"
        error "Required P04 pin missing: ${cell}/${pin_name}"
    }
    return $pin
}

proc connect_pair {left right} {
    set lp [get_bd_pins -quiet $left]
    set rp [get_bd_pins -quiet $right]
    if {[llength $lp] != 1 || [llength $rp] != 1} {
        error "Missing P04 connection pin: left=$left ($lp) right=$right ($rp)"
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
    CONFIG.PSU__USE__M_AXI_GP0 {0} \
    CONFIG.PSU__USE__M_AXI_GP1 {0} \
    CONFIG.PSU__USE__M_AXI_GP2 {0} \
    CONFIG.PSU__FPGA_PL0_ENABLE {1} \
    CONFIG.PSU__USE__FABRIC__RST {0} \
    CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {100}] $ps

set hls0 [create_bd_cell -type ip -vlnv $expected_vlnv loihi_core_v2_tick_0]
set hls1 [create_bd_cell -type ip -vlnv $expected_vlnv loihi_core_v2_tick_1]
set ctrl [create_bd_cell -type module -reference p04_two_core_controller p04_two_core_controller_0]
set mem0 [create_bd_cell -type module -reference p04_endpoint_memory_fabric p04_endpoint_memory_0]
set mem1 [create_bd_cell -type module -reference p04_endpoint_memory_fabric p04_endpoint_memory_1]
set hostmux [create_bd_cell -type module -reference p04_host_mux p04_host_mux_0]
set heartbeat [create_bd_cell -type module -reference p04_heartbeat p04_heartbeat_0]

set vio [create_bd_cell -type ip -vlnv xilinx.com:ip:vio:3.0 vio_p04]
set_property -dict [list \
    CONFIG.C_NUM_PROBE_IN {45} \
    CONFIG.C_NUM_PROBE_OUT {19} \
    CONFIG.C_PROBE_IN0_WIDTH {1} CONFIG.C_PROBE_IN1_WIDTH {1} CONFIG.C_PROBE_IN2_WIDTH {1} CONFIG.C_PROBE_IN3_WIDTH {1} \
    CONFIG.C_PROBE_IN4_WIDTH {32} CONFIG.C_PROBE_IN5_WIDTH {13} CONFIG.C_PROBE_IN6_WIDTH {13} CONFIG.C_PROBE_IN7_WIDTH {13} CONFIG.C_PROBE_IN8_WIDTH {13} \
    CONFIG.C_PROBE_IN9_WIDTH {16} CONFIG.C_PROBE_IN10_WIDTH {2} CONFIG.C_PROBE_IN11_WIDTH {1} \
    CONFIG.C_PROBE_IN12_WIDTH {32} CONFIG.C_PROBE_IN13_WIDTH {32} CONFIG.C_PROBE_IN14_WIDTH {32} CONFIG.C_PROBE_IN15_WIDTH {64} \
    CONFIG.C_PROBE_IN16_WIDTH {1} CONFIG.C_PROBE_IN17_WIDTH {1} CONFIG.C_PROBE_IN18_WIDTH {1} CONFIG.C_PROBE_IN19_WIDTH {1} \
    CONFIG.C_PROBE_IN20_WIDTH {1} CONFIG.C_PROBE_IN21_WIDTH {1} CONFIG.C_PROBE_IN22_WIDTH {1} CONFIG.C_PROBE_IN23_WIDTH {1} \
    CONFIG.C_PROBE_IN24_WIDTH {1} CONFIG.C_PROBE_IN25_WIDTH {1} CONFIG.C_PROBE_IN26_WIDTH {1} \
    CONFIG.C_PROBE_IN27_WIDTH {11} CONFIG.C_PROBE_IN28_WIDTH {13} CONFIG.C_PROBE_IN29_WIDTH {32} \
    CONFIG.C_PROBE_IN30_WIDTH {11} CONFIG.C_PROBE_IN31_WIDTH {13} CONFIG.C_PROBE_IN32_WIDTH {32} \
    CONFIG.C_PROBE_IN33_WIDTH {1} CONFIG.C_PROBE_IN34_WIDTH {1} CONFIG.C_PROBE_IN35_WIDTH {1} CONFIG.C_PROBE_IN36_WIDTH {1} CONFIG.C_PROBE_IN37_WIDTH {256} \
    CONFIG.C_PROBE_IN38_WIDTH {32} \
    CONFIG.C_PROBE_IN39_WIDTH {1} CONFIG.C_PROBE_IN40_WIDTH {1} CONFIG.C_PROBE_IN41_WIDTH {1} CONFIG.C_PROBE_IN42_WIDTH {1} CONFIG.C_PROBE_IN43_WIDTH {1} CONFIG.C_PROBE_IN44_WIDTH {1} \
    CONFIG.C_PROBE_OUT0_WIDTH {1} CONFIG.C_PROBE_OUT0_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT1_WIDTH {1} CONFIG.C_PROBE_OUT1_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT2_WIDTH {1} CONFIG.C_PROBE_OUT2_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT3_WIDTH {1} CONFIG.C_PROBE_OUT3_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT4_WIDTH {32} CONFIG.C_PROBE_OUT4_INIT_VAL {0x00000000} \
    CONFIG.C_PROBE_OUT5_WIDTH {13} CONFIG.C_PROBE_OUT5_INIT_VAL {0x001} \
    CONFIG.C_PROBE_OUT6_WIDTH {13} CONFIG.C_PROBE_OUT6_INIT_VAL {0x001} \
    CONFIG.C_PROBE_OUT7_WIDTH {11} CONFIG.C_PROBE_OUT7_INIT_VAL {0x001} \
    CONFIG.C_PROBE_OUT8_WIDTH {16} CONFIG.C_PROBE_OUT8_INIT_VAL {0x0002} \
    CONFIG.C_PROBE_OUT9_WIDTH {13} CONFIG.C_PROBE_OUT9_INIT_VAL {0x002} \
    CONFIG.C_PROBE_OUT10_WIDTH {11} CONFIG.C_PROBE_OUT10_INIT_VAL {0x001} \
    CONFIG.C_PROBE_OUT11_WIDTH {16} CONFIG.C_PROBE_OUT11_INIT_VAL {0x0002} \
    CONFIG.C_PROBE_OUT12_WIDTH {13} CONFIG.C_PROBE_OUT12_INIT_VAL {0x002} \
    CONFIG.C_PROBE_OUT13_WIDTH {1} CONFIG.C_PROBE_OUT13_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT14_WIDTH {1} CONFIG.C_PROBE_OUT14_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT15_WIDTH {1} CONFIG.C_PROBE_OUT15_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT16_WIDTH {4} CONFIG.C_PROBE_OUT16_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT17_WIDTH {15} CONFIG.C_PROBE_OUT17_INIT_VAL {0x0000} \
    CONFIG.C_PROBE_OUT18_WIDTH {256} CONFIG.C_PROBE_OUT18_INIT_VAL {0x0}] $vio

set rst [create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 proc_sys_reset_p04]
set reset_high [get_property CONFIG.C_EXT_RESET_HIGH $rst]
puts "P04 board-resolved external reset polarity: C_EXT_RESET_HIGH=$reset_high"
if {$reset_high ne "0"} {
    error "P04 requires proc_sys_reset external reset to be active-low (C_EXT_RESET_HIGH=0), got $reset_high"
}
set one [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_one_p04]
set_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {1}] $one
set zero [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_zero_p04]
set_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {0}] $zero

set pl_clk [get_bd_pins zynq_ultra_ps_e_0/pl_clk0]
connect_bd_net $pl_clk \
    [get_bd_pins loihi_core_v2_tick_0/ap_clk] [get_bd_pins loihi_core_v2_tick_1/ap_clk] \
    [get_bd_pins p04_two_core_controller_0/clk] \
    [get_bd_pins p04_endpoint_memory_0/clk] [get_bd_pins p04_endpoint_memory_1/clk] \
    [get_bd_pins p04_heartbeat_0/clk] [get_bd_pins vio_p04/clk] \
    [get_bd_pins proc_sys_reset_p04/slowest_sync_clk]
connect_pair vio_p04/probe_out2 proc_sys_reset_p04/ext_reset_in
connect_bd_net [get_bd_pins const_one_p04/dout] [get_bd_pins proc_sys_reset_p04/dcm_locked] [get_bd_pins proc_sys_reset_p04/aux_reset_in]
connect_bd_net [get_bd_pins const_zero_p04/dout] [get_bd_pins proc_sys_reset_p04/mb_debug_sys_rst]
connect_bd_net [get_bd_pins proc_sys_reset_p04/peripheral_reset] [get_bd_pins loihi_core_v2_tick_0/ap_rst] [get_bd_pins loihi_core_v2_tick_1/ap_rst]
connect_bd_net [get_bd_pins proc_sys_reset_p04/peripheral_aresetn] \
    [get_bd_pins p04_two_core_controller_0/resetn] [get_bd_pins p04_endpoint_memory_0/resetn] \
    [get_bd_pins p04_endpoint_memory_1/resetn] [get_bd_pins p04_heartbeat_0/resetn]

# Controller command/configuration inputs from VIO.
connect_pair vio_p04/probe_out0 p04_two_core_controller_0/epoch_load
connect_pair vio_p04/probe_out1 p04_two_core_controller_0/tick_start
connect_pair vio_p04/probe_out3 p04_two_core_controller_0/service_reverse
connect_pair vio_p04/probe_out4 p04_two_core_controller_0/epoch_timestep
connect_pair vio_p04/probe_out5 p04_two_core_controller_0/epoch_event_count0
connect_pair vio_p04/probe_out6 p04_two_core_controller_0/epoch_event_count1
connect_pair vio_p04/probe_out7 p04_two_core_controller_0/compartment_count0
connect_pair vio_p04/probe_out8 p04_two_core_controller_0/synapse_count0
connect_pair vio_p04/probe_out9 p04_two_core_controller_0/route_count0
connect_pair vio_p04/probe_out10 p04_two_core_controller_0/compartment_count1
connect_pair vio_p04/probe_out11 p04_two_core_controller_0/synapse_count1
connect_pair vio_p04/probe_out12 p04_two_core_controller_0/route_count1

# HLS scalar/control integration.
connect_pair p04_two_core_controller_0/core0_start loihi_core_v2_tick_0/ap_start
connect_pair p04_two_core_controller_0/core1_start loihi_core_v2_tick_1/ap_start
connect_bd_net [get_bd_pins loihi_core_v2_tick_0/ap_ready] [get_bd_pins p04_two_core_controller_0/core0_ready] [get_bd_pins vio_p04/probe_in39]
connect_bd_net [get_bd_pins loihi_core_v2_tick_1/ap_ready] [get_bd_pins p04_two_core_controller_0/core1_ready] [get_bd_pins vio_p04/probe_in40]
connect_bd_net [get_bd_pins loihi_core_v2_tick_0/ap_done] [get_bd_pins p04_two_core_controller_0/core0_done] [get_bd_pins vio_p04/probe_in43]
connect_bd_net [get_bd_pins loihi_core_v2_tick_1/ap_done] [get_bd_pins p04_two_core_controller_0/core1_done] [get_bd_pins vio_p04/probe_in44]
connect_pair loihi_core_v2_tick_0/ap_idle vio_p04/probe_in41
connect_pair loihi_core_v2_tick_1/ap_idle vio_p04/probe_in42
connect_bd_net [get_bd_pins loihi_core_v2_tick_0/packet_count] [get_bd_pins p04_two_core_controller_0/core0_packet_count] [get_bd_pins vio_p04/probe_in28]
connect_bd_net [get_bd_pins loihi_core_v2_tick_1/packet_count] [get_bd_pins p04_two_core_controller_0/core1_packet_count] [get_bd_pins vio_p04/probe_in31]
connect_bd_net [get_bd_pins loihi_core_v2_tick_0/status_flags] [get_bd_pins p04_two_core_controller_0/core0_status] [get_bd_pins vio_p04/probe_in29]
connect_bd_net [get_bd_pins loihi_core_v2_tick_1/status_flags] [get_bd_pins p04_two_core_controller_0/core1_status] [get_bd_pins vio_p04/probe_in32]
connect_pair loihi_core_v2_tick_0/spike_count vio_p04/probe_in27
connect_pair loihi_core_v2_tick_1/spike_count vio_p04/probe_in30
connect_pair p04_two_core_controller_0/core0_event_count loihi_core_v2_tick_0/event_count
connect_pair p04_two_core_controller_0/core1_event_count loihi_core_v2_tick_1/event_count
connect_bd_net [get_bd_pins p04_two_core_controller_0/core_timestep] [get_bd_pins loihi_core_v2_tick_0/timestep] [get_bd_pins loihi_core_v2_tick_1/timestep]
connect_pair vio_p04/probe_out7 loihi_core_v2_tick_0/compartment_count
connect_pair vio_p04/probe_out8 loihi_core_v2_tick_0/synapse_count
connect_pair vio_p04/probe_out9 loihi_core_v2_tick_0/route_count
connect_pair vio_p04/probe_out10 loihi_core_v2_tick_1/compartment_count
connect_pair vio_p04/probe_out11 loihi_core_v2_tick_1/synapse_count
connect_pair vio_p04/probe_out12 loihi_core_v2_tick_1/route_count

# HLS memory ports to the two resource-scaled endpoint fabrics.
foreach spec {
    {config_words r} {state_words rw} {axon_words r} {synapse_words r}
    {route_desc_words r} {route_words r} {input_events r} {trace_words w}
    {packet_words w}
} {
    lassign $spec arg mode
    connect_hls_memory_fabric loihi_core_v2_tick_0 p04_endpoint_memory_0 $arg $mode
    connect_hls_memory_fabric loihi_core_v2_tick_1 p04_endpoint_memory_1 $arg $mode
}

# Controller packet-drain / next-event memory paths.
connect_pair p04_two_core_controller_0/core0_packet_mem_en p04_endpoint_memory_0/integration_packet_en
connect_pair p04_two_core_controller_0/core0_packet_mem_addr p04_endpoint_memory_0/integration_packet_addr
connect_pair p04_endpoint_memory_0/integration_packet_data p04_two_core_controller_0/core0_packet_mem_data
connect_pair p04_two_core_controller_0/core1_packet_mem_en p04_endpoint_memory_1/integration_packet_en
connect_pair p04_two_core_controller_0/core1_packet_mem_addr p04_endpoint_memory_1/integration_packet_addr
connect_pair p04_endpoint_memory_1/integration_packet_data p04_two_core_controller_0/core1_packet_mem_data
connect_pair p04_two_core_controller_0/core0_event_mem_we p04_endpoint_memory_0/integration_event_we
connect_pair p04_two_core_controller_0/core0_event_mem_addr p04_endpoint_memory_0/integration_event_addr
connect_pair p04_two_core_controller_0/core0_event_mem_data p04_endpoint_memory_0/integration_event_data
connect_pair p04_two_core_controller_0/core1_event_mem_we p04_endpoint_memory_1/integration_event_we
connect_pair p04_two_core_controller_0/core1_event_mem_addr p04_endpoint_memory_1/integration_event_addr
connect_pair p04_two_core_controller_0/core1_event_mem_data p04_endpoint_memory_1/integration_event_data
connect_bd_net [get_bd_pins p04_two_core_controller_0/busy] [get_bd_pins p04_endpoint_memory_0/compute_busy] [get_bd_pins p04_endpoint_memory_1/compute_busy] [get_bd_pins vio_p04/probe_in1]
connect_bd_net [get_bd_pins p04_endpoint_memory_0/host_busy] [get_bd_pins p04_two_core_controller_0/host_busy0] [get_bd_pins p04_host_mux_0/busy0]
connect_bd_net [get_bd_pins p04_endpoint_memory_1/host_busy] [get_bd_pins p04_two_core_controller_0/host_busy1] [get_bd_pins p04_host_mux_0/busy1]

# Shared host/debug path.
connect_pair vio_p04/probe_out13 p04_host_mux_0/req
connect_pair vio_p04/probe_out14 p04_host_mux_0/write
connect_pair vio_p04/probe_out15 p04_host_mux_0/core_select
connect_pair vio_p04/probe_out16 p04_host_mux_0/bank
connect_pair vio_p04/probe_out17 p04_host_mux_0/addr
connect_pair vio_p04/probe_out18 p04_host_mux_0/wdata
foreach suffix {write bank addr wdata} {
    connect_pair p04_host_mux_0/${suffix}0 p04_endpoint_memory_0/host_${suffix}
    connect_pair p04_host_mux_0/${suffix}1 p04_endpoint_memory_1/host_${suffix}
}
connect_pair p04_host_mux_0/req0 p04_endpoint_memory_0/host_req
connect_pair p04_host_mux_0/req1 p04_endpoint_memory_1/host_req
foreach suffix {ack rvalid error rdata} {
    connect_pair p04_endpoint_memory_0/host_${suffix} p04_host_mux_0/${suffix}0
    connect_pair p04_endpoint_memory_1/host_${suffix} p04_host_mux_0/${suffix}1
}
connect_pair p04_host_mux_0/busy vio_p04/probe_in33
connect_pair p04_host_mux_0/ack vio_p04/probe_in34
connect_pair p04_host_mux_0/rvalid vio_p04/probe_in35
connect_pair p04_host_mux_0/error vio_p04/probe_in36
connect_pair p04_host_mux_0/rdata vio_p04/probe_in37

# Controller/debug observations.
connect_pair p04_two_core_controller_0/tick_done vio_p04/probe_in0
connect_pair p04_two_core_controller_0/start_blocked vio_p04/probe_in2
connect_pair p04_two_core_controller_0/epoch_loaded vio_p04/probe_in3
connect_pair p04_two_core_controller_0/current_timestep vio_p04/probe_in4
connect_pair p04_two_core_controller_0/current_event_count0 vio_p04/probe_in5
connect_pair p04_two_core_controller_0/current_event_count1 vio_p04/probe_in6
connect_pair p04_two_core_controller_0/next_event_count0 vio_p04/probe_in7
connect_pair p04_two_core_controller_0/next_event_count1 vio_p04/probe_in8
connect_pair p04_two_core_controller_0/in_flight_count vio_p04/probe_in9
connect_pair p04_two_core_controller_0/barrier_completed_mask vio_p04/probe_in10
connect_pair p04_two_core_controller_0/barrier_can_advance vio_p04/probe_in11
connect_pair p04_two_core_controller_0/local_packet_count vio_p04/probe_in12
connect_pair p04_two_core_controller_0/remote_packet_count vio_p04/probe_in13
connect_pair p04_two_core_controller_0/completed_ticks vio_p04/probe_in14
connect_pair p04_two_core_controller_0/last_tick_cycles vio_p04/probe_in15
connect_pair p04_two_core_controller_0/error_physical_capacity vio_p04/probe_in16
connect_pair p04_two_core_controller_0/error_event_overflow vio_p04/probe_in17
connect_pair p04_two_core_controller_0/error_event_axon vio_p04/probe_in18
connect_pair p04_two_core_controller_0/error_core_status vio_p04/probe_in19
connect_pair p04_two_core_controller_0/error_router_bad_valid vio_p04/probe_in20
connect_pair p04_two_core_controller_0/error_router_bad_destination vio_p04/probe_in21
connect_pair p04_two_core_controller_0/error_router_bad_timestep vio_p04/probe_in22
connect_pair p04_endpoint_memory_0/hls_address_error vio_p04/probe_in23
connect_pair p04_endpoint_memory_0/integration_address_error vio_p04/probe_in24
connect_pair p04_endpoint_memory_1/hls_address_error vio_p04/probe_in25
connect_pair p04_endpoint_memory_1/integration_address_error vio_p04/probe_in26
connect_pair p04_heartbeat_0/count vio_p04/probe_in38

validate_bd_design
save_bd_design
puts "P04 two-endpoint block design validated successfully."

set bd_file [lindex [get_files -quiet */${bd_name}.bd] 0]
if {$bd_file eq ""} { error "P04 block design file was not found" }
generate_target all $bd_file
set wrapper_files [make_wrapper -files $bd_file -top]
if {[llength $wrapper_files] == 0} { error "P04 Vivado wrapper generation failed" }
add_files -norecurse $wrapper_files
set_property top ${bd_name}_wrapper [current_fileset]
update_compile_order -fileset sources_1

if {$stage eq "synth"} {
    launch_runs synth_1 -jobs $jobs
    wait_on_run synth_1
    if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {
        error "P04 synthesis did not complete: [get_property STATUS [get_runs synth_1]]"
    }
    open_run synth_1
    set util_text [report_utilization -return_string]
    set util_file [open [file join $report_dir utilization_post_synth.rpt] w]
    puts $util_file $util_text
    close $util_file
    report_utilization -hierarchical -hierarchical_depth 8 -file [file join $report_dir utilization_hierarchical_post_synth.rpt]
    report_timing_summary -delay_type min_max -max_paths 20 -report_unconstrained -file [file join $report_dir timing_summary_post_synth.rpt]
    write_checkpoint -force [file join $report_dir p04_post_synth.dcp]
    puts "P04 integration synthesis completed successfully."
    return
}

set_property STEPS.PHYS_OPT_DESIGN.IS_ENABLED true [get_runs impl_1]
launch_runs impl_1 -to_step route_design -jobs $jobs
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {
    error "P04 implementation did not complete: [get_property STATUS [get_runs impl_1]]"
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
write_checkpoint -force [file join $report_dir p04_post_route.dcp]

set primitive_file [open [file join $report_dir memory_primitives_post_route.rpt] w]
foreach c [lsort [get_cells -hierarchical -filter {REF_NAME == RAMB36E2 || REF_NAME == RAMB18E2 || REF_NAME == URAM288}]] {
    puts $primitive_file "[get_property REF_NAME $c] $c"
}
close $primitive_file

set metrics [open [file join $report_dir p04_post_route_metrics.txt] w]
set setup_paths [get_timing_paths -quiet -delay_type max -max_paths 1 -nworst 1]
set hold_paths [get_timing_paths -quiet -delay_type min -max_paths 1 -nworst 1]
if {[llength $setup_paths] > 0} { puts $metrics "wns_ns=[get_property SLACK [lindex $setup_paths 0]]" } else { puts $metrics "wns_ns=NA" }
if {[llength $hold_paths] > 0} { puts $metrics "whs_ns=[get_property SLACK [lindex $hold_paths 0]]" } else { puts $metrics "whs_ns=NA" }
if {[regexp {\| Block RAM Tile\s+\|\s+([0-9.]+)\s+\|} $util_text -> bram_tiles]} { puts $metrics "block_ram_tiles=$bram_tiles" }
if {[regexp {\| URAM\s+\|\s+([0-9.]+)\s+\|} $util_text -> uram_count]} { puts $metrics "uram=$uram_count" }
puts $metrics "physical_fixture_compartments_per_endpoint=16"
puts $metrics "physical_fixture_axons_per_endpoint=64"
puts $metrics "physical_fixture_synapse_entries_per_endpoint=256"
puts $metrics "physical_fixture_routes_per_endpoint=64"
puts $metrics "physical_fixture_events_per_endpoint=64"
puts $metrics "physical_fixture_packets_per_endpoint=64"
puts $metrics "logical_capacity_changed=0"
puts $metrics "target_part=$target_part"
puts $metrics "board_part=$kv260_board_part"
puts $metrics "pl_clock_requested_mhz=100"
close $metrics

set bit_file [file join $report_dir p04_two_core.bit]
set ltx_file [file join $report_dir p04_two_core.ltx]
write_debug_probes -force $ltx_file
write_bitstream -force $bit_file
puts "P04 routed implementation completed successfully."
puts "P04 bitstream: $bit_file"
puts "P04 debug probes: $ltx_file"
puts "P04 reports: $report_dir"
