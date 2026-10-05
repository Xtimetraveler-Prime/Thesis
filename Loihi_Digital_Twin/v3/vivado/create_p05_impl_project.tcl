# P05 one-engine / three-full-context K26 integration shell.
if {$argc != 12} {
    error "usage: create_p05_impl_project.tcl <ip_repo_dir> <project_dir> <target_part> <expected_vlnv> <streamer_rtl> <controller_rtl> <memory_rtl> <reset_rtl> <hostmux_rtl> <report_dir> <jobs> <stage:synth|route>"
}

set ip_repo_dir [file normalize [lindex $argv 0]]
set project_dir [file normalize [lindex $argv 1]]
set target_part [lindex $argv 2]
set expected_vlnv [lindex $argv 3]
set streamer_rtl [file normalize [lindex $argv 4]]
set controller_rtl [file normalize [lindex $argv 5]]
set memory_rtl [file normalize [lindex $argv 6]]
set reset_rtl [file normalize [lindex $argv 7]]
set hostmux_rtl [file normalize [lindex $argv 8]]
set report_dir [file normalize [lindex $argv 9]]
set jobs [lindex $argv 10]
set stage [lindex $argv 11]
if {$stage ne "synth" && $stage ne "route"} { error "P05 stage must be synth or route" }

foreach path [list $ip_repo_dir $streamer_rtl $controller_rtl $memory_rtl $reset_rtl $hostmux_rtl] {
    if {![file exists $path]} { error "Required P05 input does not exist: $path" }
}
file mkdir $report_dir
file delete -force $project_dir
file mkdir $project_dir

set project_name "loihi_twin_v2_p05_impl"
set bd_name "loihi_twin_v2_p05_impl"
create_project $project_name $project_dir -part $target_part -force
set_property TARGET_LANGUAGE Verilog [current_project]
set_property SIMULATOR_LANGUAGE Mixed [current_project]
set_property XPM_LIBRARIES XPM_MEMORY [current_project]

set kv260_board_parts [get_board_parts -quiet xilinx.com:kv260_som:part0:*]
if {[llength $kv260_board_parts] == 0} {
    error "P05 requires installed KV260 SOM board files (xilinx.com:kv260_som:part0:*)."
}
set kv260_board_part [lindex [lsort -dictionary $kv260_board_parts] end]
set_property BOARD_PART $kv260_board_part [current_project]
puts "P05 K26 SOM board preset: $kv260_board_part"

foreach rtl [list $streamer_rtl $controller_rtl $memory_rtl $reset_rtl $hostmux_rtl] {
    add_files -norecurse $rtl
    set_property file_type Verilog [get_files $rtl]
}
update_compile_order -fileset sources_1

set_property IP_REPO_PATHS [list $ip_repo_dir] [current_fileset]
update_ip_catalog -rebuild
if {[llength [get_ipdefs -all $expected_vlnv]] == 0} {
    error "Expected P05/P03 HLS IP was not found in catalog: $expected_vlnv"
}
foreach required_ip {
    xilinx.com:ip:zynq_ultra_ps_e:3.5
    xilinx.com:ip:vio:3.0
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
        default { error "Unknown P05 HLS memory-pin role: $role" }
    }
    set pin [first_bd_pin $hls_name $candidates]
    if {$required && $pin eq ""} {
        puts "Available HLS pins for $arg_name: [get_bd_pins -quiet ${hls_name}/${arg_name}_*]"
        error "Required P05 HLS $role pin not found for ${hls_name}/${arg_name}"
    }
    return $pin
}

proc require_bd_pin {cell pin_name} {
    set pin [get_bd_pins -quiet ${cell}/${pin_name}]
    if {[llength $pin] != 1} {
        puts "Available pins for $cell: [get_bd_pins -quiet ${cell}/*]"
        error "Required P05 pin missing: ${cell}/${pin_name}"
    }
    return $pin
}

proc connect_pair {left right} {
    set lp [get_bd_pins -quiet $left]
    set rp [get_bd_pins -quiet $right]
    if {[llength $lp] != 1 || [llength $rp] != 1} {
        error "Missing P05 connection pin: left=$left ($lp) right=$right ($rp)"
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
set ctrl [create_bd_cell -type module -reference p05_virtualized_controller p05_virtualized_controller_0]
set mem [create_bd_cell -type module -reference p05_context_memory_fabric p05_context_memory_0]
set reset_cond [create_bd_cell -type module -reference p04_reset_conditioner p05_reset_conditioner_0]
set heartbeat [create_bd_cell -type module -reference p04_heartbeat p05_heartbeat_0]

set vio [create_bd_cell -type ip -vlnv xilinx.com:ip:vio:3.0 vio_p05]
set_property -dict [list \
    CONFIG.C_NUM_PROBE_IN {36} \
    CONFIG.C_NUM_PROBE_OUT {12} \
    CONFIG.C_PROBE_IN0_WIDTH {1} CONFIG.C_PROBE_IN1_WIDTH {1} CONFIG.C_PROBE_IN2_WIDTH {1} CONFIG.C_PROBE_IN3_WIDTH {1} \
    CONFIG.C_PROBE_IN4_WIDTH {32} CONFIG.C_PROBE_IN5_WIDTH {39} CONFIG.C_PROBE_IN6_WIDTH {39} CONFIG.C_PROBE_IN7_WIDTH {3} \
    CONFIG.C_PROBE_IN8_WIDTH {1} CONFIG.C_PROBE_IN9_WIDTH {32} CONFIG.C_PROBE_IN10_WIDTH {32} CONFIG.C_PROBE_IN11_WIDTH {32} \
    CONFIG.C_PROBE_IN12_WIDTH {64} CONFIG.C_PROBE_IN13_WIDTH {1} CONFIG.C_PROBE_IN14_WIDTH {1} CONFIG.C_PROBE_IN15_WIDTH {1} \
    CONFIG.C_PROBE_IN16_WIDTH {1} CONFIG.C_PROBE_IN17_WIDTH {1} CONFIG.C_PROBE_IN18_WIDTH {1} CONFIG.C_PROBE_IN19_WIDTH {2} \
    CONFIG.C_PROBE_IN20_WIDTH {7} CONFIG.C_PROBE_IN21_WIDTH {1} CONFIG.C_PROBE_IN22_WIDTH {1} CONFIG.C_PROBE_IN23_WIDTH {1} \
    CONFIG.C_PROBE_IN24_WIDTH {1} CONFIG.C_PROBE_IN25_WIDTH {11} CONFIG.C_PROBE_IN26_WIDTH {13} CONFIG.C_PROBE_IN27_WIDTH {32} \
    CONFIG.C_PROBE_IN28_WIDTH {1} CONFIG.C_PROBE_IN29_WIDTH {1} CONFIG.C_PROBE_IN30_WIDTH {1} CONFIG.C_PROBE_IN31_WIDTH {1} \
    CONFIG.C_PROBE_IN32_WIDTH {256} CONFIG.C_PROBE_IN33_WIDTH {32} CONFIG.C_PROBE_IN34_WIDTH {1} CONFIG.C_PROBE_IN35_WIDTH {1} \
    CONFIG.C_PROBE_OUT0_WIDTH {1} CONFIG.C_PROBE_OUT0_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT1_WIDTH {1} CONFIG.C_PROBE_OUT1_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT2_WIDTH {1} CONFIG.C_PROBE_OUT2_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT3_WIDTH {1} CONFIG.C_PROBE_OUT3_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT4_WIDTH {32} CONFIG.C_PROBE_OUT4_INIT_VAL {0x00000000} \
    CONFIG.C_PROBE_OUT5_WIDTH {192} CONFIG.C_PROBE_OUT5_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT6_WIDTH {1} CONFIG.C_PROBE_OUT6_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT7_WIDTH {1} CONFIG.C_PROBE_OUT7_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT8_WIDTH {2} CONFIG.C_PROBE_OUT8_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT9_WIDTH {4} CONFIG.C_PROBE_OUT9_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT10_WIDTH {15} CONFIG.C_PROBE_OUT10_INIT_VAL {0x0000} \
    CONFIG.C_PROBE_OUT11_WIDTH {256} CONFIG.C_PROBE_OUT11_INIT_VAL {0x0}] $vio

set pl_clk [get_bd_pins zynq_ultra_ps_e_0/pl_clk0]
connect_bd_net $pl_clk \
    [get_bd_pins loihi_core_v2_tick_0/ap_clk] \
    [get_bd_pins p05_virtualized_controller_0/clk] \
    [get_bd_pins p05_context_memory_0/clk] \
    [get_bd_pins p05_reset_conditioner_0/clk] \
    [get_bd_pins p05_heartbeat_0/clk] \
    [get_bd_pins vio_p05/clk]

connect_pair vio_p05/probe_out2 p05_reset_conditioner_0/reset_request
connect_pair p05_reset_conditioner_0/reset loihi_core_v2_tick_0/ap_rst
connect_bd_net [get_bd_pins p05_reset_conditioner_0/resetn] \
    [get_bd_pins p05_virtualized_controller_0/resetn] \
    [get_bd_pins p05_context_memory_0/resetn] \
    [get_bd_pins p05_heartbeat_0/resetn]

# Controller command/configuration inputs.
connect_pair vio_p05/probe_out0 p05_virtualized_controller_0/epoch_load
connect_pair vio_p05/probe_out1 p05_virtualized_controller_0/tick_start
connect_pair vio_p05/probe_out3 p05_virtualized_controller_0/service_reverse
connect_pair vio_p05/probe_out4 p05_virtualized_controller_0/epoch_timestep
connect_pair vio_p05/probe_out5 p05_virtualized_controller_0/context_metadata

# HLS control/scalar integration.
connect_pair p05_virtualized_controller_0/core_start loihi_core_v2_tick_0/ap_start
connect_bd_net [get_bd_pins loihi_core_v2_tick_0/ap_ready] \
    [get_bd_pins p05_virtualized_controller_0/core_ready] [get_bd_pins vio_p05/probe_in22]
connect_bd_net [get_bd_pins loihi_core_v2_tick_0/ap_done] \
    [get_bd_pins p05_virtualized_controller_0/core_done] [get_bd_pins vio_p05/probe_in24]
connect_pair loihi_core_v2_tick_0/ap_idle vio_p05/probe_in23
connect_bd_net [get_bd_pins loihi_core_v2_tick_0/packet_count] \
    [get_bd_pins p05_virtualized_controller_0/core_packet_count] [get_bd_pins vio_p05/probe_in26]
connect_bd_net [get_bd_pins loihi_core_v2_tick_0/status_flags] \
    [get_bd_pins p05_virtualized_controller_0/core_status] [get_bd_pins vio_p05/probe_in27]
connect_pair loihi_core_v2_tick_0/spike_count vio_p05/probe_in25
connect_pair p05_virtualized_controller_0/core_compartment_count loihi_core_v2_tick_0/compartment_count
connect_pair p05_virtualized_controller_0/core_event_count loihi_core_v2_tick_0/event_count
connect_pair p05_virtualized_controller_0/core_synapse_count loihi_core_v2_tick_0/synapse_count
connect_pair p05_virtualized_controller_0/core_route_count loihi_core_v2_tick_0/route_count
connect_pair p05_virtualized_controller_0/core_timestep loihi_core_v2_tick_0/timestep

# HLS memory ports to the full-context shared memory fabric.
foreach spec {
    {config_words r} {state_words rw} {axon_words r} {synapse_words r}
    {route_desc_words r} {route_words r} {input_events r} {trace_words w}
    {packet_words w}
} {
    lassign $spec arg mode
    connect_hls_memory_fabric loihi_core_v2_tick_0 p05_context_memory_0 $arg $mode
}

# Scheduler/context-memory integration.
connect_pair p05_virtualized_controller_0/active_context_slot p05_context_memory_0/active_context_slot
connect_pair p05_virtualized_controller_0/event_read_bank p05_context_memory_0/event_read_bank
connect_pair p05_virtualized_controller_0/busy p05_context_memory_0/compute_busy
connect_pair p05_context_memory_0/host_busy p05_virtualized_controller_0/host_busy
connect_pair p05_virtualized_controller_0/packet_mem_en p05_context_memory_0/integration_packet_en
connect_pair p05_virtualized_controller_0/packet_mem_context p05_context_memory_0/integration_packet_context
connect_pair p05_virtualized_controller_0/packet_mem_addr p05_context_memory_0/integration_packet_addr
connect_pair p05_context_memory_0/integration_packet_data p05_virtualized_controller_0/packet_mem_data
connect_pair p05_virtualized_controller_0/event_mem_we p05_context_memory_0/integration_event_we
connect_pair p05_virtualized_controller_0/event_mem_context p05_context_memory_0/integration_event_context
connect_pair p05_virtualized_controller_0/event_mem_addr p05_context_memory_0/integration_event_addr
connect_pair p05_virtualized_controller_0/event_mem_data p05_context_memory_0/integration_event_data

# Direct banked host/debug interface. probe_out8 is physical context slot, not
# logical core identity.
connect_pair vio_p05/probe_out6 p05_context_memory_0/host_req
connect_pair vio_p05/probe_out7 p05_context_memory_0/host_write
connect_pair vio_p05/probe_out8 p05_context_memory_0/host_context_slot
connect_pair vio_p05/probe_out9 p05_context_memory_0/host_bank
connect_pair vio_p05/probe_out10 p05_context_memory_0/host_addr
connect_pair vio_p05/probe_out11 p05_context_memory_0/host_wdata

# Controller observations.
connect_pair p05_virtualized_controller_0/tick_done vio_p05/probe_in0
connect_pair p05_virtualized_controller_0/busy vio_p05/probe_in1
connect_pair p05_virtualized_controller_0/start_blocked vio_p05/probe_in2
connect_pair p05_virtualized_controller_0/epoch_loaded vio_p05/probe_in3
connect_pair p05_virtualized_controller_0/current_timestep vio_p05/probe_in4
connect_pair p05_virtualized_controller_0/current_event_counts_flat vio_p05/probe_in5
connect_pair p05_virtualized_controller_0/next_event_counts_flat vio_p05/probe_in6
connect_pair p05_virtualized_controller_0/barrier_completed_mask vio_p05/probe_in7
connect_pair p05_virtualized_controller_0/barrier_can_advance vio_p05/probe_in8
connect_pair p05_virtualized_controller_0/local_packet_count vio_p05/probe_in9
connect_pair p05_virtualized_controller_0/remote_packet_count vio_p05/probe_in10
connect_pair p05_virtualized_controller_0/completed_ticks vio_p05/probe_in11
connect_pair p05_virtualized_controller_0/last_tick_cycles vio_p05/probe_in12
connect_pair p05_virtualized_controller_0/error_metadata vio_p05/probe_in13
connect_pair p05_virtualized_controller_0/error_event_overflow vio_p05/probe_in14
connect_pair p05_virtualized_controller_0/error_bad_packet_valid vio_p05/probe_in15
connect_pair p05_virtualized_controller_0/error_bad_destination vio_p05/probe_in16
connect_pair p05_virtualized_controller_0/error_bad_timestep vio_p05/probe_in17
connect_pair p05_virtualized_controller_0/error_core_status vio_p05/probe_in18
connect_pair p05_virtualized_controller_0/active_context_slot vio_p05/probe_in19
connect_pair p05_virtualized_controller_0/active_logical_core_id vio_p05/probe_in20
connect_pair p05_virtualized_controller_0/event_read_bank vio_p05/probe_in21

# Host/memory/reset observations.
connect_pair p05_context_memory_0/host_busy vio_p05/probe_in28
connect_pair p05_context_memory_0/host_ack vio_p05/probe_in29
connect_pair p05_context_memory_0/host_rvalid vio_p05/probe_in30
connect_pair p05_context_memory_0/host_error vio_p05/probe_in31
connect_pair p05_context_memory_0/host_rdata vio_p05/probe_in32
connect_pair p05_heartbeat_0/count vio_p05/probe_in33
connect_pair p05_context_memory_0/hls_address_error vio_p05/probe_in34
connect_pair p05_context_memory_0/integration_address_error vio_p05/probe_in35

validate_bd_design
save_bd_design
puts "P05 one-engine three-context block design validated successfully."

set bd_file [lindex [get_files -quiet */${bd_name}.bd] 0]
if {$bd_file eq ""} { error "P05 block design file was not found" }
generate_target all $bd_file
set wrapper_files [make_wrapper -files $bd_file -top]
if {[llength $wrapper_files] == 0} { error "P05 Vivado wrapper generation failed" }
add_files -norecurse $wrapper_files
set_property top ${bd_name}_wrapper [current_fileset]
update_compile_order -fileset sources_1

if {$stage eq "synth"} {
    launch_runs synth_1 -jobs $jobs
    wait_on_run synth_1
    if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {
        error "P05 synthesis did not complete: [get_property STATUS [get_runs synth_1]]"
    }
    open_run synth_1
    set util_text [report_utilization -return_string]
    set util_file [open [file join $report_dir utilization_post_synth.rpt] w]
    puts $util_file $util_text
    close $util_file
    report_utilization -hierarchical -hierarchical_depth 8 -file [file join $report_dir utilization_hierarchical_post_synth.rpt]
    report_timing_summary -delay_type min_max -max_paths 20 -report_unconstrained -file [file join $report_dir timing_summary_post_synth.rpt]
    write_checkpoint -force [file join $report_dir p05_post_synth.dcp]

    set metrics [open [file join $report_dir p05_post_synth_metrics.txt] w]
    if {[regexp {\| Block RAM Tile\s+\|\s+([0-9.]+)\s+\|} $util_text -> bram_tiles]} { puts $metrics "block_ram_tiles=$bram_tiles" }
    if {[regexp {\| URAM\s+\|\s+([0-9.]+)\s+\|} $util_text -> uram_count]} { puts $metrics "uram=$uram_count" }
    puts $metrics "logical_contexts=3"
    puts $metrics "physical_engines=1"
    puts $metrics "estimated_uram288=47"
    puts $metrics "double_buffered_events=1"
    puts $metrics "logical_capacity_changed=0"
    puts $metrics "reset_strategy=source_controlled_synchronous_conditioner"
    puts $metrics "target_part=$target_part"
    puts $metrics "board_part=$kv260_board_part"
    puts $metrics "pl_clock_requested_mhz=100"
    close $metrics

    puts "P05 integration synthesis completed successfully."
    return
}

set_property STEPS.PHYS_OPT_DESIGN.IS_ENABLED true [get_runs impl_1]
launch_runs impl_1 -to_step route_design -jobs $jobs
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {
    error "P05 implementation did not complete: [get_property STATUS [get_runs impl_1]]"
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
write_checkpoint -force [file join $report_dir p05_post_route.dcp]

set primitive_file [open [file join $report_dir memory_primitives_post_route.rpt] w]
foreach c [lsort [get_cells -hierarchical -filter {REF_NAME == RAMB36E2 || REF_NAME == RAMB18E2 || REF_NAME == URAM288}]] {
    puts $primitive_file "[get_property REF_NAME $c] $c"
}
close $primitive_file

set metrics [open [file join $report_dir p05_post_route_metrics.txt] w]
set setup_paths [get_timing_paths -quiet -delay_type max -max_paths 1 -nworst 1]
set hold_paths [get_timing_paths -quiet -delay_type min -max_paths 1 -nworst 1]
if {[llength $setup_paths] > 0} { puts $metrics "wns_ns=[get_property SLACK [lindex $setup_paths 0]]" } else { puts $metrics "wns_ns=NA" }
if {[llength $hold_paths] > 0} { puts $metrics "whs_ns=[get_property SLACK [lindex $hold_paths 0]]" } else { puts $metrics "whs_ns=NA" }
if {[regexp {\| Block RAM Tile\s+\|\s+([0-9.]+)\s+\|} $util_text -> bram_tiles]} { puts $metrics "block_ram_tiles=$bram_tiles" }
if {[regexp {\| URAM\s+\|\s+([0-9.]+)\s+\|} $util_text -> uram_count]} { puts $metrics "uram=$uram_count" }
puts $metrics "logical_contexts=3"
puts $metrics "physical_engines=1"
puts $metrics "estimated_uram288=47"
puts $metrics "double_buffered_events=1"
puts $metrics "logical_capacity_changed=0"
puts $metrics "reset_strategy=source_controlled_synchronous_conditioner"
puts $metrics "target_part=$target_part"
puts $metrics "board_part=$kv260_board_part"
puts $metrics "pl_clock_requested_mhz=100"
close $metrics

set bit_file [file join $report_dir p05_virtualized.bit]
set ltx_file [file join $report_dir p05_virtualized.ltx]
write_debug_probes -force $ltx_file
write_bitstream -force $bit_file
puts "P05 routed implementation completed successfully."
puts "P05 bitstream: $bit_file"
puts "P05 debug probes: $ltx_file"
puts "P05 reports: $report_dir"
