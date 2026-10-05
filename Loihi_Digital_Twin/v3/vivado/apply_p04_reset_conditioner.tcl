# Replace only the functional P04 reset outputs in an isolated copy of the
# generated project with the source-controlled p04_reset_conditioner. The
# original proc_sys_reset instance remains present but no longer drives the
# HLS/custom functional reset inputs in the conditioned design.
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

# Never mutate the source implementation project in-place. Clone it into the
# final/candidate build directory and condition only that copy.
set conditioned_project_dir [file normalize [file join $report_dir .. project]]
file delete -force $conditioned_project_dir
open_project -read_only $project_xpr
save_project_as -force -exclude_run_results p04_reset_conditioned $conditioned_project_dir
close_project
set conditioned_xpr [file join $conditioned_project_dir p04_reset_conditioned.xpr]
if {![file exists $conditioned_xpr]} {
    error "P04 reset-conditioned project copy was not created: $conditioned_xpr"
}
open_project $conditioned_xpr

set bd_file [lindex [get_files -quiet */loihi_twin_v2_p04_impl.bd] 0]
if {$bd_file eq ""} { error "P04 reset-conditioner flow could not find the block design" }
open_bd_design $bd_file

# Add/refresh the source-controlled synchronous reset conditioner. Its HDL
# X_INTERFACE metadata defines ACTIVE_HIGH reset, ACTIVE_LOW resetn, and their
# association with clk. Vivado exposes those BD properties read-only, so verify.
if {[llength [get_files -quiet $reset_rtl]] == 0} {
    add_files -norecurse $reset_rtl
    set_property file_type Verilog [get_files $reset_rtl]
}
update_compile_order -fileset sources_1

if {[llength [get_bd_cells -quiet p04_reset_conditioner_0]] == 0} {
    create_bd_cell -type module -reference p04_reset_conditioner p04_reset_conditioner_0
} else {
    update_module_reference [get_bd_cells p04_reset_conditioner_0]
}

set cond_clk [get_bd_pins p04_reset_conditioner_0/clk]
set cond_reset [get_bd_pins p04_reset_conditioner_0/reset]
set cond_resetn [get_bd_pins p04_reset_conditioner_0/resetn]

set reset_polarity [get_property CONFIG.POLARITY $cond_reset]
set resetn_polarity [get_property CONFIG.POLARITY $cond_resetn]
set associated_reset [get_property CONFIG.ASSOCIATED_RESET $cond_clk]
puts "P04 reset-conditioner BD properties: reset=$reset_polarity resetn=$resetn_polarity associated_reset=$associated_reset"
if {$reset_polarity ne "ACTIVE_HIGH"} {
    error "P04 reset-conditioner active-high reset property mismatch: $reset_polarity"
}
if {$resetn_polarity ne "ACTIVE_LOW"} {
    error "P04 reset-conditioner active-low resetn property mismatch: $resetn_polarity"
}
if {$associated_reset ne "reset:resetn"} {
    error "P04 reset-conditioner clock/reset association mismatch: $associated_reset"
}

set clk_net [get_bd_nets -quiet -of_objects [get_bd_pins zynq_ultra_ps_e_0/pl_clk0]]
if {[llength $clk_net] != 1} { error "P04 expected one PL0 clock net, got '$clk_net'" }
set reset_cmd_net [get_bd_nets -quiet -of_objects [get_bd_pins vio_p04/probe_out2]]
if {[llength $reset_cmd_net] != 1} { error "P04 expected one VIO reset-command net, got '$reset_cmd_net'" }

if {[llength [get_bd_nets -quiet -of_objects $cond_clk]] == 0} {
    connect_bd_net -net $clk_net $cond_clk
}
if {[llength [get_bd_nets -quiet -of_objects [get_bd_pins p04_reset_conditioner_0/reset_request]]] == 0} {
    connect_bd_net -net $reset_cmd_net [get_bd_pins p04_reset_conditioner_0/reset_request]
}

proc p04_disconnect_pin {pin_path} {
    set pin [get_bd_pins $pin_path]
    set nets [get_bd_nets -quiet -of_objects $pin]
    if {[llength $nets] > 1} {
        error "P04 reset-conditioned flow found multiple nets on $pin_path: $nets"
    }
    if {[llength $nets] == 1} {
        disconnect_bd_net [lindex $nets 0] $pin
    }
}

foreach pin_path {
    loihi_core_v2_tick_0/ap_rst
    loihi_core_v2_tick_1/ap_rst
    p04_two_core_controller_0/resetn
    p04_endpoint_memory_0/resetn
    p04_endpoint_memory_1/resetn
    p04_heartbeat_0/resetn
} {
    p04_disconnect_pin $pin_path
}

connect_bd_net $cond_reset \
    [get_bd_pins loihi_core_v2_tick_0/ap_rst] \
    [get_bd_pins loihi_core_v2_tick_1/ap_rst]
connect_bd_net $cond_resetn \
    [get_bd_pins p04_two_core_controller_0/resetn] \
    [get_bd_pins p04_endpoint_memory_0/resetn] \
    [get_bd_pins p04_endpoint_memory_1/resetn] \
    [get_bd_pins p04_heartbeat_0/resetn]

set reset_polarity_post [get_property CONFIG.POLARITY $cond_reset]
set resetn_polarity_post [get_property CONFIG.POLARITY $cond_resetn]
puts "P04 reset-conditioner post-connect polarities: reset=$reset_polarity_post resetn=$resetn_polarity_post"
if {$reset_polarity_post ne "ACTIVE_HIGH" || $resetn_polarity_post ne "ACTIVE_LOW"} {
    error "P04 reset-conditioner polarity propagation changed source pins: reset=$reset_polarity_post resetn=$resetn_polarity_post"
}

validate_bd_design
save_bd_design
generate_target all $bd_file
update_compile_order -fileset sources_1

reset_run synth_1
launch_runs synth_1 -jobs $jobs
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {
    error "P04 reset-conditioned synthesis did not complete: [get_property STATUS [get_runs synth_1]]"
}

launch_runs impl_1 -to_step route_design -jobs $jobs
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {
    error "P04 reset-conditioned implementation did not complete: [get_property STATUS [get_runs impl_1]]"
}
open_run impl_1

report_timing_summary -delay_type min_max -max_paths 20 -report_unconstrained \
    -file [file join $report_dir timing_summary_post_route.rpt]
set util_text [report_utilization -return_string]
set util_file [open [file join $report_dir utilization_post_route.rpt] w]
puts $util_file $util_text
close $util_file
report_utilization -hierarchical -hierarchical_depth 8 \
    -file [file join $report_dir utilization_hierarchical_post_route.rpt]
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
puts $metrics "reset_strategy=source_controlled_synchronous_conditioner"
puts $metrics "reset_request_active_high=1"
puts $metrics "reset_release_cycles=16"
puts $metrics "target_part=[get_property PART [current_project]]"
puts $metrics "board_part=[get_property BOARD_PART [current_project]]"
puts $metrics "pl_clock_requested_mhz=100"
close $metrics

set bit_file [file join $report_dir p04_two_core.bit]
set ltx_file [file join $report_dir p04_two_core.ltx]
write_debug_probes -force $ltx_file
write_bitstream -force $bit_file

puts "P04 reset-conditioned implementation completed successfully."
puts "P04 canonical bitstream: $bit_file"
puts "P04 canonical probes: $ltx_file"
puts "P04 canonical reports: $report_dir"
close_project
