# M12.1.3 physical implementation: K26 PS clock + VIO/JTAG host-stepped trace shell.
if {$argc != 17} {
    error "usage: create_m12_1_3_project.tcl <ip_repo_dir> <project_dir> <target_part> <expected_vlnv> <decoder_rtl> <phase_b_rtl> <neuron_rtl> <integrated_rtl> <route_rtl> <recurrent_rtl> <bridge_rtl> <capture_rtl> <capture_bd_rtl> <capture_vectors> <report_dir> <artifact_dir> <jobs>"
}

set ip_repo_dir    [file normalize [lindex $argv 0]]
set project_dir    [file normalize [lindex $argv 1]]
set target_part    [lindex $argv 2]
set expected_vlnv  [lindex $argv 3]
set decoder_rtl    [file normalize [lindex $argv 4]]
set phase_b_rtl    [file normalize [lindex $argv 5]]
set neuron_rtl     [file normalize [lindex $argv 6]]
set integrated_rtl [file normalize [lindex $argv 7]]
set route_rtl      [file normalize [lindex $argv 8]]
set recurrent_rtl  [file normalize [lindex $argv 9]]
set bridge_rtl     [file normalize [lindex $argv 10]]
set capture_rtl    [file normalize [lindex $argv 11]]
set capture_bd_rtl [file normalize [lindex $argv 12]]
set capture_vectors [file normalize [lindex $argv 13]]
set report_dir     [file normalize [lindex $argv 14]]
set artifact_dir   [file normalize [lindex $argv 15]]
set jobs           [lindex $argv 16]

set project_name "neuromorphic_twin_m12_1_3"
set bd_name "neuromorphic_twin_m12_1_3"
set capture_module "m12_1_capture_controller_bd_v1"

foreach path [list $ip_repo_dir $decoder_rtl $phase_b_rtl $neuron_rtl $integrated_rtl $route_rtl $recurrent_rtl $bridge_rtl $capture_rtl $capture_bd_rtl $capture_vectors] {
    if {![file exists $path]} {
        error "Required M12.1.3 input does not exist: $path"
    }
}
file mkdir $report_dir
file mkdir $artifact_dir

proc connect_verified_pair {capture_pin hls_pin} {
    set cp [get_bd_pins -quiet capture_0/${capture_pin}]
    set hp [get_bd_pins -quiet neuron_step_v1_0/${hls_pin}]
    if {[llength $cp] != 1 || [llength $hp] != 1} {
        error "Missing M12.1.3 integration pin: capture=$capture_pin ($cp), hls=$hls_pin ($hp)"
    }
    connect_bd_net $cp $hp
    set cn [get_bd_nets -quiet -of_objects $cp]
    set hn [get_bd_nets -quiet -of_objects $hp]
    if {[llength $cn] != 1 || [llength $hn] != 1 || [lindex $cn 0] ne [lindex $hn 0]} {
        error "M12.1.3 integration pin connectivity mismatch: capture=$capture_pin nets=$cn, hls=$hls_pin nets=$hn"
    }
}

proc connect_named_pair {net_name left_pin right_pin} {
    set lp [get_bd_pins -quiet $left_pin]
    set rp [get_bd_pins -quiet $right_pin]
    if {[llength $lp] != 1 || [llength $rp] != 1} {
        error "Missing M12.1.3 VIO connection pin for $net_name: left=$lp right=$rp"
    }
    set net [create_bd_net $net_name]
    connect_bd_net -net $net $lp $rp
}

file delete -force $project_dir
file mkdir $project_dir
create_project $project_name $project_dir -part $target_part -force
set_property TARGET_LANGUAGE Verilog [current_project]
set_property SIMULATOR_LANGUAGE Mixed [current_project]

set kv260_board_parts [get_board_parts -quiet xilinx.com:kv260_som:part0:*]
if {[llength $kv260_board_parts] == 0} {
    error "M12.1.3 requires the Vivado KV260 SOM board files (xilinx.com:kv260_som:part0:*)."
}
set kv260_board_part [lindex [lsort -dictionary $kv260_board_parts] end]
set_property BOARD_PART $kv260_board_part [current_project]
puts "M12.1.3 K26 SOM board preset: $kv260_board_part"

foreach source_file [list $decoder_rtl $phase_b_rtl $neuron_rtl $integrated_rtl $route_rtl $recurrent_rtl $bridge_rtl $capture_rtl] {
    add_files -norecurse $source_file
    set_property file_type SystemVerilog [get_files $source_file]
}
add_files -norecurse $capture_bd_rtl
set_property file_type Verilog [get_files $capture_bd_rtl]
add_files -norecurse $capture_vectors
set_property file_type {Verilog Header} [get_files $capture_vectors]
set_property include_dirs [list [file dirname $capture_vectors]] [get_filesets sources_1]
update_compile_order -fileset sources_1

set_property IP_REPO_PATHS [list $ip_repo_dir] [current_fileset]
update_ip_catalog -rebuild
if {[llength [get_ipdefs -all $expected_vlnv]] == 0} {
    error "Expected packaged HLS IP was not found in the catalog: $expected_vlnv"
}
foreach required_ip {xilinx.com:ip:zynq_ultra_ps_e:3.5 xilinx.com:ip:vio:3.0 xilinx.com:ip:proc_sys_reset:5.0 xilinx.com:ip:xlconstant:1.1} {
    if {[llength [get_ipdefs -all $required_ip]] == 0} {
        error "Required Vivado IP was not found in the catalog: $required_ip"
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

set pl_clk0_pin [get_bd_pins -quiet zynq_ultra_ps_e_0/pl_clk0]
if {[llength $pl_clk0_pin] != 1} {
    error "M12.1.3 KV260 PS preset did not expose the required pl_clk0 fabric clock."
}

set capture [create_bd_cell -type module -reference $capture_module capture_0]
set hls [create_bd_cell -type ip -vlnv $expected_vlnv neuron_step_v1_0]
set vio [create_bd_cell -type ip -vlnv xilinx.com:ip:vio:3.0 vio_m12_1_3]
set_property -dict [list \
    CONFIG.C_NUM_PROBE_IN {26} \
    CONFIG.C_NUM_PROBE_OUT {6} \
    CONFIG.C_PROBE_IN0_WIDTH {32} \
    CONFIG.C_PROBE_IN1_WIDTH {1} \
    CONFIG.C_PROBE_IN2_WIDTH {1} \
    CONFIG.C_PROBE_IN3_WIDTH {1} \
    CONFIG.C_PROBE_IN4_WIDTH {1} \
    CONFIG.C_PROBE_IN5_WIDTH {1} \
    CONFIG.C_PROBE_IN6_WIDTH {1} \
    CONFIG.C_PROBE_IN7_WIDTH {1} \
    CONFIG.C_PROBE_IN8_WIDTH {8} \
    CONFIG.C_PROBE_IN9_WIDTH {8} \
    CONFIG.C_PROBE_IN10_WIDTH {32} \
    CONFIG.C_PROBE_IN11_WIDTH {1} \
    CONFIG.C_PROBE_IN12_WIDTH {8} \
    CONFIG.C_PROBE_IN13_WIDTH {1} \
    CONFIG.C_PROBE_IN14_WIDTH {13} \
    CONFIG.C_PROBE_IN15_WIDTH {13} \
    CONFIG.C_PROBE_IN16_WIDTH {13} \
    CONFIG.C_PROBE_IN17_WIDTH {13} \
    CONFIG.C_PROBE_IN18_WIDTH {13} \
    CONFIG.C_PROBE_IN19_WIDTH {13} \
    CONFIG.C_PROBE_IN20_WIDTH {1} \
    CONFIG.C_PROBE_IN21_WIDTH {16} \
    CONFIG.C_PROBE_IN22_WIDTH {3} \
    CONFIG.C_PROBE_IN23_WIDTH {12} \
    CONFIG.C_PROBE_IN24_WIDTH {64} \
    CONFIG.C_PROBE_IN25_WIDTH {1} \
    CONFIG.C_PROBE_OUT0_WIDTH {1} CONFIG.C_PROBE_OUT0_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT1_WIDTH {1} CONFIG.C_PROBE_OUT1_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT2_WIDTH {1} CONFIG.C_PROBE_OUT2_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT3_WIDTH {3} CONFIG.C_PROBE_OUT3_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT4_WIDTH {12} CONFIG.C_PROBE_OUT4_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT5_WIDTH {1} CONFIG.C_PROBE_OUT5_INIT_VAL {0x0}] $vio

set local_reset [create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 proc_sys_reset_m12_1_3]
set const_one [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_one_m12_1_3]
set_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {1}] $const_one
set const_zero [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_zero_m12_1_3]
set_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {0}] $const_zero

connect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_clk0] \
    [get_bd_pins capture_0/ap_clk] \
    [get_bd_pins neuron_step_v1_0/ap_clk] \
    [get_bd_pins vio_m12_1_3/clk] \
    [get_bd_pins proc_sys_reset_m12_1_3/slowest_sync_clk]
connect_named_pair capture_resetn vio_m12_1_3/probe_out5 proc_sys_reset_m12_1_3/ext_reset_in
connect_bd_net [get_bd_pins const_one_m12_1_3/dout] \
    [get_bd_pins proc_sys_reset_m12_1_3/dcm_locked] \
    [get_bd_pins proc_sys_reset_m12_1_3/aux_reset_in]
connect_bd_net [get_bd_pins const_zero_m12_1_3/dout] \
    [get_bd_pins proc_sys_reset_m12_1_3/mb_debug_sys_rst]
set reset_released_net [create_bd_net reset_released]
connect_bd_net -net $reset_released_net \
    [get_bd_pins proc_sys_reset_m12_1_3/peripheral_aresetn] \
    [get_bd_pins capture_0/capture_resetn] \
    [get_bd_pins vio_m12_1_3/probe_in2]
connect_bd_net [get_bd_pins proc_sys_reset_m12_1_3/peripheral_reset] \
    [get_bd_pins neuron_step_v1_0/ap_rst]

set handshake_pairs {
    hls_ap_start ap_start
    hls_ap_done  ap_done
    hls_ap_idle  ap_idle
    hls_ap_ready ap_ready
}
foreach {capture_pin hls_pin} $handshake_pairs {
    connect_verified_pair $capture_pin $hls_pin
}
set scalar_pairs {
    hls_current_before             current_before
    hls_voltage_before             voltage_before
    hls_refractory_before          refractory_before
    hls_synaptic_input             synaptic_input
    hls_current_decay              current_decay
    hls_voltage_decay              voltage_decay
    hls_threshold                  threshold
    hls_bias                       bias
    hls_reset_voltage              reset_voltage
    hls_refractory_ticks           refractory_ticks
    hls_current_after              current_after
    hls_current_after_ap_vld       current_after_ap_vld
    hls_voltage_after              voltage_after
    hls_voltage_after_ap_vld       voltage_after_ap_vld
    hls_refractory_after           refractory_after
    hls_refractory_after_ap_vld    refractory_after_ap_vld
    hls_spiked                     spiked
    hls_spiked_ap_vld              spiked_ap_vld
}
foreach {capture_pin hls_pin} $scalar_pairs {
    connect_verified_pair $capture_pin $hls_pin
}

# Named nets form the stable Hardware Manager API used by capture_m12_1_3_trace.tcl.
connect_named_pair clock_heartbeat                    capture_0/clock_heartbeat vio_m12_1_3/probe_in0
connect_named_pair start_seen                         capture_0/start_seen vio_m12_1_3/probe_in1
connect_named_pair capture_busy                       capture_0/capture_busy vio_m12_1_3/probe_in3
connect_named_pair step_ready                         capture_0/step_ready vio_m12_1_3/probe_in4
connect_named_pair trace_window_open                  capture_0/trace_window_open vio_m12_1_3/probe_in5
connect_named_pair capture_done                       capture_0/capture_done vio_m12_1_3/probe_in6
connect_named_pair capture_fault                      capture_0/capture_fault vio_m12_1_3/probe_in7
connect_named_pair capture_fault_code                 capture_0/capture_fault_code vio_m12_1_3/probe_in8
connect_named_pair capture_phase                      capture_0/capture_phase vio_m12_1_3/probe_in9
connect_named_pair observed_tick                      capture_0/observed_tick vio_m12_1_3/probe_in10
connect_named_pair observed_core_fault                capture_0/observed_core_fault vio_m12_1_3/probe_in11
connect_named_pair observed_core_fault_code           capture_0/observed_core_fault_code vio_m12_1_3/probe_in12
connect_named_pair observed_recurrent_bank            capture_0/observed_recurrent_bank vio_m12_1_3/probe_in13
connect_named_pair observed_recurrent_count           capture_0/observed_recurrent_count vio_m12_1_3/probe_in14
connect_named_pair observed_recurrent_bank0_count     capture_0/observed_recurrent_bank0_count vio_m12_1_3/probe_in15
connect_named_pair observed_recurrent_bank1_count     capture_0/observed_recurrent_bank1_count vio_m12_1_3/probe_in16
connect_named_pair observed_consumed_recurrent_count  capture_0/observed_consumed_recurrent_count vio_m12_1_3/probe_in17
connect_named_pair observed_routed_recurrent_count    capture_0/observed_routed_recurrent_count vio_m12_1_3/probe_in18
connect_named_pair observed_external_event_count      capture_0/observed_external_event_count vio_m12_1_3/probe_in19
connect_named_pair trace_read_ready                   capture_0/trace_read_ready vio_m12_1_3/probe_in20
connect_named_pair trace_response_seq                 capture_0/trace_response_seq vio_m12_1_3/probe_in21
connect_named_pair trace_response_space               capture_0/trace_response_space vio_m12_1_3/probe_in22
connect_named_pair trace_response_addr                capture_0/trace_response_addr vio_m12_1_3/probe_in23
connect_named_pair trace_response_data                capture_0/trace_response_data vio_m12_1_3/probe_in24
connect_named_pair trace_response_error               capture_0/trace_response_error vio_m12_1_3/probe_in25

connect_named_pair capture_start                      vio_m12_1_3/probe_out0 capture_0/capture_start
connect_named_pair capture_step                       vio_m12_1_3/probe_out1 capture_0/capture_step
connect_named_pair trace_read_req                     vio_m12_1_3/probe_out2 capture_0/trace_read_req
connect_named_pair trace_read_space                   vio_m12_1_3/probe_out3 capture_0/trace_read_space
connect_named_pair trace_read_addr                    vio_m12_1_3/probe_out4 capture_0/trace_read_addr

validate_bd_design
save_bd_design
puts "M12.1.3 physical trace-capture block design validated successfully."

set bd_files [get_files -quiet */${bd_name}.bd]
if {[llength $bd_files] != 1} {
    error "Expected exactly one M12.1.3 block-design file, found: $bd_files"
}
set bd_file [lindex $bd_files 0]
generate_target all $bd_file
set wrapper_files [make_wrapper -files $bd_file -top]
if {[llength $wrapper_files] == 0} {
    error "Vivado did not generate an HDL wrapper for M12.1.3"
}
add_files -norecurse $wrapper_files
set_property top ${bd_name}_wrapper [current_fileset]
update_compile_order -fileset sources_1

puts ""
puts "=== M12.1.3 synthesis ==="
launch_runs synth_1 -jobs $jobs
wait_on_run synth_1
set synth_status [get_property STATUS [get_runs synth_1]]
puts "M12.1.3 synth_1 status: $synth_status"
if {[string first "Complete" $synth_status] < 0} {
    error "M12.1.3 synthesis did not complete successfully: $synth_status"
}

puts ""
puts "=== M12.1.3 implementation + bitstream ==="
launch_runs impl_1 -to_step write_bitstream -jobs $jobs
wait_on_run impl_1
set impl_status [get_property STATUS [get_runs impl_1]]
puts "M12.1.3 impl_1 status: $impl_status"
if {[string first "Complete" $impl_status] < 0} {
    error "M12.1.3 implementation/bitstream did not complete successfully: $impl_status"
}
open_run impl_1
puts "M12.1.3 implementation completed successfully."

report_utilization -file [file join $report_dir utilization_impl.rpt]
report_utilization -hierarchical -hierarchical_depth 6 -file [file join $report_dir utilization_hierarchical_impl.rpt]
report_ram_utilization -include_lutram -file [file join $report_dir ram_utilization_impl.rpt] -csv [file join $report_dir ram_utilization_impl.csv]
report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose -max_paths 20 -file [file join $report_dir timing_summary_impl.rpt]
report_timing -delay_type max -max_paths 20 -nworst 20 -path_type full_clock_expanded -file [file join $report_dir setup_paths_impl.rpt]
report_timing -delay_type min -max_paths 20 -nworst 20 -path_type full_clock_expanded -file [file join $report_dir hold_paths_impl.rpt]
report_route_status -file [file join $report_dir route_status_impl.rpt]
report_methodology -file [file join $report_dir methodology_impl.rpt]
report_drc -file [file join $report_dir drc_impl.rpt]
report_clocks -file [file join $report_dir clocks_impl.rpt]
write_checkpoint -force [file join $artifact_dir neuromorphic_twin_m12_1_3_routed.dcp]
write_debug_probes -force [file join $artifact_dir neuromorphic_twin_m12_1_3.ltx]

set worst_setup [get_timing_paths -quiet -delay_type max -max_paths 1 -nworst 1]
set worst_hold [get_timing_paths -quiet -delay_type min -max_paths 1 -nworst 1]
if {[llength $worst_setup] != 1 || [llength $worst_hold] != 1} {
    error "M12.1.3 could not obtain routed setup/hold timing paths."
}
set wns [get_property SLACK [lindex $worst_setup 0]]
set whs [get_property SLACK [lindex $worst_hold 0]]
puts "M12.1.3 routed worst setup slack: $wns ns"
puts "M12.1.3 routed worst hold slack: $whs ns"
if {$wns < 0.0 || $whs < 0.0} {
    error "M12.1.3 routed timing failed: WNS=$wns ns WHS=$whs ns"
}
puts "M12.1.3 routed timing check passed: WNS=$wns ns, WHS=$whs ns"

set drc_errors [get_drc_violations -quiet -filter {SEVERITY == Error}]
if {[llength $drc_errors] != 0} {
    error "M12.1.3 implemented design has DRC errors: $drc_errors"
}

set impl_dir [get_property DIRECTORY [get_runs impl_1]]
set bit_files [glob -nocomplain -directory $impl_dir *.bit]
if {[llength $bit_files] != 1} {
    error "M12.1.3 expected exactly one generated .bit file in $impl_dir, found: $bit_files"
}
set bit_src [lindex $bit_files 0]
set bit_dst [file join $artifact_dir neuromorphic_twin_m12_1_3.bit]
file copy -force $bit_src $bit_dst
write_hw_platform -fixed -include_bit -force -file [file join $artifact_dir neuromorphic_twin_m12_1_3.xsa]

if {![file exists $bit_dst]} {
    error "M12.1.3 bitstream copy was not created: $bit_dst"
}
puts "M12.1.3 bitstream generated successfully."
puts "Bitstream: $bit_dst"
puts "Debug probes: [file join $artifact_dir neuromorphic_twin_m12_1_3.ltx]"
puts "Hardware handoff: [file join $artifact_dir neuromorphic_twin_m12_1_3.xsa]"
puts "Reports: $report_dir"
close_project
