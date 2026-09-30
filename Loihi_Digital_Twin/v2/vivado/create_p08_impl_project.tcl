# P08 host-paged one-engine / three-resident-context K26 integration shell.
#
# This shell reuses the accepted P05 full-context UltraRAM fabric and the same
# P03-compatible HLS compute engine.  The P05 three-context scheduler/router is
# intentionally replaced by p08_paged_dispatch_controller: exactly one resident
# logical core is dispatched at a time, while the host owns backing-store page
# replacement, cross-page packet routing, and the global algorithmic barrier.
if {$argc != 10} {
    error "usage: create_p08_impl_project.tcl <ip_repo_dir> <project_dir> <target_part> <expected_vlnv> <controller_rtl> <memory_rtl> <reset_rtl> <hostmux_rtl> <report_dir> <jobs>"
}

set ip_repo_dir [file normalize [lindex $argv 0]]
set project_dir [file normalize [lindex $argv 1]]
set target_part [lindex $argv 2]
set expected_vlnv [lindex $argv 3]
set controller_rtl [file normalize [lindex $argv 4]]
set memory_rtl [file normalize [lindex $argv 5]]
set reset_rtl [file normalize [lindex $argv 6]]
set hostmux_rtl [file normalize [lindex $argv 7]]
set report_dir [file normalize [lindex $argv 8]]
set jobs [lindex $argv 9]

foreach path [list $ip_repo_dir $controller_rtl $memory_rtl $reset_rtl $hostmux_rtl] {
    if {![file exists $path]} { error "Required P08 input does not exist: $path" }
}
file mkdir $report_dir
file delete -force $project_dir
file mkdir $project_dir

set project_name "loihi_twin_v2_p08_impl"
set bd_name "loihi_twin_v2_p08_impl"
create_project $project_name $project_dir -part $target_part -force
set_property TARGET_LANGUAGE Verilog [current_project]
set_property SIMULATOR_LANGUAGE Mixed [current_project]
set_property XPM_LIBRARIES XPM_MEMORY [current_project]

set kv260_board_parts [get_board_parts -quiet xilinx.com:kv260_som:part0:*]
if {[llength $kv260_board_parts] == 0} {
    error "P08 requires installed KV260 SOM board files (xilinx.com:kv260_som:part0:*)."
}
set kv260_board_part [lindex [lsort -dictionary $kv260_board_parts] end]
set_property BOARD_PART $kv260_board_part [current_project]
puts "P08 K26 SOM board preset: $kv260_board_part"

foreach rtl [list $controller_rtl $memory_rtl $reset_rtl $hostmux_rtl] {
    add_files -norecurse $rtl
    set_property file_type Verilog [get_files $rtl]
}
update_compile_order -fileset sources_1

set_property IP_REPO_PATHS [list $ip_repo_dir] [current_fileset]
update_ip_catalog -rebuild
if {[llength [get_ipdefs -all $expected_vlnv]] == 0} {
    error "Expected P08/P03 HLS IP was not found in catalog: $expected_vlnv"
}
foreach required_ip {
    xilinx.com:ip:zynq_ultra_ps_e:3.5
    xilinx.com:ip:vio:3.0
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
        default { error "Unknown P08 HLS memory-pin role: $role" }
    }
    set pin [first_bd_pin $hls_name $candidates]
    if {$required && $pin eq ""} {
        puts "Available HLS pins for $arg_name: [get_bd_pins -quiet ${hls_name}/${arg_name}_*]"
        error "Required P08 HLS $role pin not found for ${hls_name}/${arg_name}"
    }
    return $pin
}

proc require_bd_pin {cell pin_name} {
    set pin [get_bd_pins -quiet ${cell}/${pin_name}]
    if {[llength $pin] != 1} {
        puts "Available pins for $cell: [get_bd_pins -quiet ${cell}/*]"
        error "Required P08 pin missing: ${cell}/${pin_name}"
    }
    return $pin
}

proc connect_pair {left right} {
    set lp [get_bd_pins -quiet $left]
    set rp [get_bd_pins -quiet $right]
    if {[llength $lp] != 1 || [llength $rp] != 1} {
        error "Missing P08 connection pin: left=$left ($lp) right=$right ($rp)"
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

set hls [create_bd_cell -type ip -vlnv $expected_vlnv loihi_core_v2_tick_0]
set ctrl [create_bd_cell -type module -reference p08_paged_dispatch_controller p08_paged_dispatch_controller_0]
set mem [create_bd_cell -type module -reference p05_context_memory_fabric p08_context_memory_0]
set reset_cond [create_bd_cell -type module -reference p04_reset_conditioner p08_reset_conditioner_0]
set heartbeat [create_bd_cell -type module -reference p04_heartbeat p08_heartbeat_0]

# The P08 controller deliberately leaves packet routing / next-event writes to
# the host after each dispatch.  Disable P05's former controller-side Port-B
# integration path; packet/event banks remain fully accessible through host I/O.
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

set pl_clk [get_bd_pins zynq_ultra_ps_e_0/pl_clk0]
connect_bd_net $pl_clk \
    [get_bd_pins loihi_core_v2_tick_0/ap_clk] \
    [get_bd_pins p08_paged_dispatch_controller_0/clk] \
    [get_bd_pins p08_context_memory_0/clk] \
    [get_bd_pins p08_reset_conditioner_0/clk] \
    [get_bd_pins p08_heartbeat_0/clk] \
    [get_bd_pins vio_p08/clk]

# Reset and heartbeat.
connect_pair vio_p08/probe_out1 p08_reset_conditioner_0/reset_request
connect_pair p08_reset_conditioner_0/reset loihi_core_v2_tick_0/ap_rst
connect_bd_net [get_bd_pins p08_reset_conditioner_0/resetn] \
    [get_bd_pins p08_paged_dispatch_controller_0/resetn] \
    [get_bd_pins p08_context_memory_0/resetn] \
    [get_bd_pins p08_heartbeat_0/resetn] \
    [get_bd_pins vio_p08/probe_in28]

# Dispatch command inputs.
connect_pair vio_p08/probe_out0 p08_paged_dispatch_controller_0/dispatch_start
connect_pair vio_p08/probe_out2 p08_paged_dispatch_controller_0/requested_context_slot
connect_pair vio_p08/probe_out3 p08_paged_dispatch_controller_0/context_metadata
connect_pair vio_p08/probe_out4 p08_paged_dispatch_controller_0/dispatch_timestep
connect_pair vio_p08/probe_out5 p08_paged_dispatch_controller_0/requested_event_read_bank
connect_pair p08_context_memory_0/host_busy p08_paged_dispatch_controller_0/host_busy

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

# Direct banked host/debug interface.  Slot identity is physical residency only.
connect_pair vio_p08/probe_out6 p08_context_memory_0/host_req
connect_pair vio_p08/probe_out7 p08_context_memory_0/host_write
connect_pair vio_p08/probe_out8 p08_context_memory_0/host_context_slot
connect_pair vio_p08/probe_out9 p08_context_memory_0/host_bank
connect_pair vio_p08/probe_out10 p08_context_memory_0/host_addr
connect_pair vio_p08/probe_out11 p08_context_memory_0/host_wdata

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
connect_pair p08_context_memory_0/host_busy vio_p08/probe_in20
connect_pair p08_context_memory_0/host_ack vio_p08/probe_in21
connect_pair p08_context_memory_0/host_rvalid vio_p08/probe_in22
connect_pair p08_context_memory_0/host_error vio_p08/probe_in23
connect_pair p08_context_memory_0/host_rdata vio_p08/probe_in24
connect_pair p08_heartbeat_0/count vio_p08/probe_in25
connect_pair p08_context_memory_0/hls_address_error vio_p08/probe_in26
connect_pair p08_context_memory_0/integration_address_error vio_p08/probe_in27

validate_bd_design
save_bd_design
puts "P08 host-paged one-engine / three-resident-context block design validated successfully."

set bd_file [lindex [get_files -quiet */${bd_name}.bd] 0]
if {$bd_file eq ""} { error "P08 block design file was not found" }
generate_target all $bd_file
set wrapper_files [make_wrapper -files $bd_file -top]
if {[llength $wrapper_files] == 0} { error "P08 Vivado wrapper generation failed" }
add_files -norecurse $wrapper_files
set_property top ${bd_name}_wrapper [current_fileset]
update_compile_order -fileset sources_1

set_property STEPS.PHYS_OPT_DESIGN.IS_ENABLED true [get_runs impl_1]
launch_runs impl_1 -to_step route_design -jobs $jobs
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {
    error "P08 implementation did not complete: [get_property STATUS [get_runs impl_1]]"
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
write_checkpoint -force [file join $report_dir p08_post_route.dcp]

set primitive_file [open [file join $report_dir memory_primitives_post_route.rpt] w]
foreach c [lsort [get_cells -hierarchical -filter {REF_NAME == RAMB36E2 || REF_NAME == RAMB18E2 || REF_NAME == URAM288}]] {
    puts $primitive_file "[get_property REF_NAME $c] $c"
}
close $primitive_file

set metrics [open [file join $report_dir p08_post_route_metrics.txt] w]
set setup_paths [get_timing_paths -quiet -delay_type max -max_paths 1 -nworst 1]
set hold_paths [get_timing_paths -quiet -delay_type min -max_paths 1 -nworst 1]
if {[llength $setup_paths] > 0} { puts $metrics "wns_ns=[get_property SLACK [lindex $setup_paths 0]]" } else { puts $metrics "wns_ns=NA" }
if {[llength $hold_paths] > 0} { puts $metrics "whs_ns=[get_property SLACK [lindex $hold_paths 0]]" } else { puts $metrics "whs_ns=NA" }
if {[regexp {\| Block RAM Tile\s+\|\s+([0-9.]+)\s+\|} $util_text -> bram_tiles]} { puts $metrics "block_ram_tiles=$bram_tiles" }
if {[regexp {\| URAM\s+\|\s+([0-9.]+)\s+\|} $util_text -> uram_count]} { puts $metrics "uram=$uram_count" }
puts $metrics "p08_expected_logical_backing_contexts=5"
puts $metrics "resident_context_slots=3"
puts $metrics "physical_engines=1"
puts $metrics "host_paged_dispatch=1"
puts $metrics "on_fabric_cross_page_router=0"
puts $metrics "host_owns_cross_page_routing=1"
puts $metrics "host_owns_global_barrier=1"
puts $metrics "logical_capacity_changed=0"
puts $metrics "reset_strategy=source_controlled_synchronous_conditioner"
puts $metrics "target_part=$target_part"
puts $metrics "board_part=$kv260_board_part"
puts $metrics "pl_clock_requested_mhz=100"
close $metrics

set bit_file [file join $report_dir p08_host_paged.bit]
set ltx_file [file join $report_dir p08_host_paged.ltx]
write_debug_probes -force $ltx_file
write_bitstream -force $bit_file
puts "P08 routed implementation completed successfully."
puts "P08 bitstream: $bit_file"
puts "P08 debug probes: $ltx_file"
puts "P08 reports: $report_dir"
