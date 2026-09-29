# Replace only the functional P04 reset outputs in an existing generated project
# with the source-controlled p04_reset_conditioner. The original proc_sys_reset
# instance may remain present for diagnostic comparison, but it no longer drives
# HLS/custom functional reset inputs after this patch.
if {$argc != 4} {
    error "usage: apply_p04_reset_conditioner.tcl <project.xpr> <reset_rtl> <report_dir> <jobs>"
}

set project_xpr [file normalize [lindex $argv 0]]
set reset_rtl [file normalize [lindex $argv 1]]
set report_dir [file normalize [lindex $argv 2]]
set jobs [lindex $argv 3]

foreach path [list $project_xpr $reset_rtl] {
    if {![file exists $path]} { error "P04 reset-conditioner input missing: $path" }
}
file mkdir $report_dir

open_project $project_xpr
set bd_file [lindex [get_files -quiet */loihi_twin_v2_p04_impl.bd] 0]
if {$bd_file eq ""} { error "P04 reset-conditioner flow could not find the block design" }
open_bd_design $bd_file

if {[llength [get_bd_cells -quiet p04_reset_conditioner_0]] == 0} {
    add_files -norecurse $reset_rtl
    set_property file_type Verilog [get_files $reset_rtl]
    update_compile_order -fileset sources_1
    create_bd_cell -type module -reference p04_reset_conditioner p04_reset_conditioner_0
}

# Reuse the exact PL0 clock and VIO reset-command nets already present in P04.
set clk_net [get_bd_nets -quiet -of_objects [get_bd_pins zynq_ultra_ps_e_0/pl_clk0]]
if {[llength $clk_net] != 1} { error "P04 expected one PL0 clock net, got '$clk_net'" }
set reset_cmd_net [get_bd_nets -quiet -of_objects [get_bd_pins vio_p04/probe_out2]]
if {[llength $reset_cmd_net] != 1} { error "P04 expected one VIO reset-command net, got '$reset_cmd_net'" }

if {[llength [get_bd_nets -quiet -of_objects [get_bd_pins p04_reset_conditioner_0/clk]]] == 0} {
    connect_bd_net -net $clk_net [get_bd_pins p04_reset_conditioner_0/clk]
}
if {[llength [get_bd_nets -quiet -of_objects [get_bd_pins p04_reset_conditioner_0/reset_request]]] == 0} {
    connect_bd_net -net $reset_cmd_net [get_bd_pins p04_reset_conditioner_0/reset_request]
}

# Detach proc_sys_reset from the functional endpoints. It is intentionally left
# instantiated so diagnostic builds can still observe its stuck output.
set old_reset_net [get_bd_nets -quiet -of_objects [get_bd_pins proc_sys_reset_p04/peripheral_reset]]
set old_resetn_net [get_bd_nets -quiet -of_objects [get_bd_pins proc_sys_reset_p04/peripheral_aresetn]]
if {[llength $old_reset_net] != 1 || [llength $old_resetn_net] != 1} {
    error "P04 expected proc_sys_reset functional reset nets"
}

# disconnect_bd_net uses positional syntax: <net> <objects>... . Unlike
# connect_bd_net, it does not accept a -net option (Vivado UG835).
disconnect_bd_net $old_reset_net \
    [get_bd_pins loihi_core_v2_tick_0/ap_rst] \
    [get_bd_pins loihi_core_v2_tick_1/ap_rst]
disconnect_bd_net $old_resetn_net \
    [get_bd_pins p04_two_core_controller_0/resetn] \
    [get_bd_pins p04_endpoint_memory_0/resetn] \
    [get_bd_pins p04_endpoint_memory_1/resetn] \
    [get_bd_pins p04_heartbeat_0/resetn]

connect_bd_net [get_bd_pins p04_reset_conditioner_0/reset] \
    [get_bd_pins loihi_core_v2_tick_0/ap_rst] \
    [get_bd_pins loihi_core_v2_tick_1/ap_rst]
connect_bd_net [get_bd_pins p04_reset_conditioner_0/resetn] \
    [get_bd_pins p04_two_core_controller_0/resetn] \
    [get_bd_pins p04_endpoint_memory_0/resetn] \
    [get_bd_pins p04_endpoint_memory_1/resetn] \
    [get_bd_pins p04_heartbeat_0/resetn]

validate_bd_design
save_bd_design
generate_target all $bd_file
update_compile_order -fileset sources_1

reset_run synth_1
launch_runs synth_1 -jobs $jobs
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {
    error "P04 reset-conditioner synthesis did not complete: [get_property STATUS [get_runs synth_1]]"
}

launch_runs impl_1 -to_step route_design -jobs $jobs
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {
    error "P04 reset-conditioner implementation did not complete: [get_property STATUS [get_runs impl_1]]"
}
open_run impl_1
report_timing_summary -delay_type min_max -max_paths 20 -report_unconstrained \
    -file [file join $report_dir timing_summary_post_route.rpt]
report_utilization -file [file join $report_dir utilization_post_route.rpt]
report_bus_skew -file [file join $report_dir bus_skew_post_route.rpt]
write_checkpoint -force [file join $report_dir p04_reset_conditioner_post_route.dcp]
write_debug_probes -force [file join $report_dir p04_reset_conditioner.ltx]
write_bitstream -force [file join $report_dir p04_reset_conditioner.bit]

puts "P04 reset-conditioner implementation completed successfully."
puts "P04 reset-conditioner bitstream: [file join $report_dir p04_reset_conditioner.bit]"
puts "P04 reset-conditioner probes: [file join $report_dir p04_reset_conditioner.ltx]"
close_project
