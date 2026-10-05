# Add temporary clock/reset observability to an already-generated P04 project.
if {$argc != 4} {
    error "usage: create_p04_reset_debug.tcl <project.xpr> <debug_rtl> <report_dir> <jobs>"
}

set project_xpr [file normalize [lindex $argv 0]]
set debug_rtl [file normalize [lindex $argv 1]]
set report_dir [file normalize [lindex $argv 2]]
set jobs [lindex $argv 3]

foreach path [list $project_xpr $debug_rtl] {
    if {![file exists $path]} { error "P04 reset diagnostic input missing: $path" }
}
file mkdir $report_dir

open_project $project_xpr
set bd_file [lindex [get_files -quiet */loihi_twin_v2_p04_impl.bd] 0]
if {$bd_file eq ""} { error "P04 reset diagnostic could not find the block design" }
open_bd_design $bd_file

if {[llength [get_bd_cells -quiet p04_reset_debug_probe_0]] == 0} {
    add_files -norecurse $debug_rtl
    set_property file_type Verilog [get_files $debug_rtl]
    update_compile_order -fileset sources_1
    create_bd_cell -type module -reference p04_reset_debug_probe p04_reset_debug_probe_0
}

set vio [get_bd_cells vio_p04]
set_property -dict [list \
    CONFIG.C_NUM_PROBE_IN {47} \
    CONFIG.C_PROBE_IN45_WIDTH {32} \
    CONFIG.C_PROBE_IN46_WIDTH {1}] $vio

# Probe 45: reset-independent counter clocked directly by PS PL0.
set clk_pin [get_bd_pins zynq_ultra_ps_e_0/pl_clk0]
set raw_clk_pin [get_bd_pins p04_reset_debug_probe_0/clk]
if {[llength [get_bd_nets -quiet -of_objects $raw_clk_pin]] == 0} {
    connect_bd_net $clk_pin $raw_clk_pin
}
set raw_count [get_bd_pins p04_reset_debug_probe_0/raw_clock_count]
if {[llength [get_bd_nets -quiet -of_objects [get_bd_pins vio_p04/probe_in45]]] == 0} {
    connect_bd_net $raw_count [get_bd_pins vio_p04/probe_in45]
}

# Probe 46: actual synchronized active-low reset delivered to the functional
# P04 controller/memory/heartbeat fabric.
set aresetn_pin [get_bd_pins proc_sys_reset_p04/peripheral_aresetn]
set aresetn_net [get_bd_nets -quiet -of_objects $aresetn_pin]
if {[llength $aresetn_net] != 1} {
    error "P04 reset diagnostic expected exactly one peripheral_aresetn net, got '$aresetn_net'"
}
if {[llength [get_bd_nets -quiet -of_objects [get_bd_pins vio_p04/probe_in46]]] == 0} {
    connect_bd_net -net $aresetn_net [get_bd_pins vio_p04/probe_in46]
}

validate_bd_design
save_bd_design
generate_target all $bd_file
update_compile_order -fileset sources_1

reset_run synth_1
launch_runs synth_1 -jobs $jobs
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {
    error "P04 reset diagnostic synthesis did not complete: [get_property STATUS [get_runs synth_1]]"
}

launch_runs impl_1 -to_step route_design -jobs $jobs
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {
    error "P04 reset diagnostic implementation did not complete: [get_property STATUS [get_runs impl_1]]"
}
open_run impl_1
report_timing_summary -delay_type min_max -max_paths 20 -report_unconstrained \
    -file [file join $report_dir timing_summary_post_route.rpt]
write_checkpoint -force [file join $report_dir p04_reset_diag_post_route.dcp]
write_debug_probes -force [file join $report_dir p04_reset_diag.ltx]
write_bitstream -force [file join $report_dir p04_reset_diag.bit]

puts "P04 reset diagnostic implementation completed successfully."
puts "P04 reset diagnostic bitstream: [file join $report_dir p04_reset_diag.bit]"
puts "P04 reset diagnostic probes: [file join $report_dir p04_reset_diag.ltx]"
close_project
