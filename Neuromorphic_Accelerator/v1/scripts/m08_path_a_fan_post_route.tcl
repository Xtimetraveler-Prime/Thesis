# M08.2b Path A: GENUINE native Vivado 2025.2 K26 SYNTHESIS AND ROUTE,
# extending owner-validated dual 4KiB AXI identity/page + TTC0 fan channel 2.
# Fresh offline evidence directory only. No bitstream or physical board action.
if {[llength $argv] != 3} {
    error "usage: m08_path_a_fan_post_route.tcl <v1-root> <fresh-evidence-dir> <jobs>"
}
set root [file normalize [lindex $argv 0]]
set evidence [file normalize [lindex $argv 1]]
set jobs [lindex $argv 2]
if {![string is integer -strict $jobs] || $jobs < 1 || $jobs > 8} {
    error "M08 Path A route jobs must be integer 1..8"
}
if {![string match "2025.2*" [version -short]]} {
    error "M08 Path A requires genuine Vivado 2025.2"
}
if {![file isdirectory $evidence]} {error "M08 Path A evidence directory missing"}
set candidate [file join $root scripts m08_path_a_fan_bd_candidate.tcl]
if {![file isfile $candidate]} {error "M08 Path A requires first-party native fan BD script"}
set metrics [file join $evidence 40_fan_route_metrics.txt]
set timing [file join $evidence 41_fan_timing_post_route.rpt]
set util [file join $evidence 42_fan_utilization_post_route.rpt]
set drc [file join $evidence 43_fan_drc_post_route.rpt]
set methodology [file join $evidence 44_fan_methodology_post_route.rpt]
set clocks_report [file join $evidence 45_fan_clock_utilization_post_route.rpt]
set io_report [file join $evidence 46_fan_io_post_route.rpt]
set route_report [file join $evidence 47_fan_route_status_post_route.rpt]
set checkpoint [file join $evidence 48_fan_post_route.dcp]
foreach path [list $metrics $timing $util $drc $methodology $clocks_report $io_report $route_report $checkpoint] {
    if {[file exists $path]} {error "M08 Path A refuses to overwrite original report $path"}
}
# EXACT SAME FIRST-PARTY K26 PS + fan BD previously accepted by owner.
# This source creates a NEW project under the new folder, not opening the
# owner-accepted previous BD evidence or existing original .bit.
set argv [list $root $evidence]
source $candidate
if {[get_property PART [current_project]] ne "xck26-sfvc784-2LV-c"} {
    error "M08 Path A route unexpected physical K26 part"
}
set bd_files [get_files -quiet */m08_page_ps.bd]
if {[llength $bd_files] != 1} {
    error "M08 Path A route requires exactly one native BD"
}
set bd [lindex $bd_files 0]
set fan_ports [get_bd_ports -quiet M08_FAN_PWM]
if {[llength $fan_ports] != 1} {
    error "M08 Path A fan output vanished before native synthesis"
}
set fan_xdc [file join $evidence 21_m08_fan_pwm_a12.xdc]
set actual_xdc [get_files -quiet $fan_xdc]
if {[llength $actual_xdc] != 1} {
    error "M08 Path A generated fan XDC not loaded into constraints"
}
generate_target all $bd
set wrappers [make_wrapper -files $bd -top]
if {[llength $wrappers] != 1} {
    error "M08 Path A failed to generate unique genuine HDL wrapper"
}
add_files -norecurse $wrappers
set_property top m08_page_ps_wrapper [current_fileset]
update_compile_order -fileset sources_1
if {[get_property TOP [current_fileset]] ne "m08_page_ps_wrapper"} {
    error "M08 Path A generated RTL top missing"
}
puts "M08_PATH_A_FAN_NATIVE_WRAPPER_GENERATED=1"

# Vivado synthesis runs as a dependency of implementation; stop at routing.
set_property STEPS.PHYS_OPT_DESIGN.IS_ENABLED true [get_runs impl_1]
launch_runs impl_1 -to_step route_design -jobs $jobs
wait_on_run impl_1
set synth_run [get_runs synth_1]
set impl_run [get_runs impl_1]
set synth_progress [string trim [get_property PROGRESS $synth_run]]
set impl_progress [string trim [get_property PROGRESS $impl_run]]
set synth_status [string trim [get_property STATUS $synth_run]]
set impl_status [string trim [get_property STATUS $impl_run]]
if {$synth_progress ne "100%" || $impl_progress ne "100%" ||
    ![string match "*Complete*" $synth_status] ||
    ![string match "*Complete*" $impl_status]} {
    error "M08 Path A genuine synth/route not complete: $synth_status / $impl_status"
}
puts "M08_PATH_A_FAN_NATIVE_SYNTH_AND_ROUTE_COMPLETE=1"
open_run impl_1

# Physically routed top-level fan pin must still match the new K26 XDC.
# Do not infer output package wiring from BD design alone.
set physical_ports [get_ports -quiet M08_FAN_PWM]
if {[llength $physical_ports] != 1} {
    error "M08 Path A routed design missing unique physical fan output port"
}
set pwm [lindex $physical_ports 0]
set pin [string trim [get_property PACKAGE_PIN $pwm]]
set standard [string trim [get_property IOSTANDARD $pwm]]
set direction [string toupper [string trim [get_property DIRECTION $pwm]]]
set slew [string toupper [string trim [get_property SLEW $pwm]]]
set drive [string trim [get_property DRIVE $pwm]]
if {$pin ne "A12" || $standard ne "LVCMOS33" || $direction ne "OUT" ||
    $slew ne "SLOW" || $drive ne "4"} {
    error "M08 Path A fan physical port constraint mismatch: pin=$pin standard=$standard direction=$direction slew=$slew drive=$drive"
}
puts "M08_PATH_A_FAN_ROUTED_IO_A12_LVCMOS33_OUT=1"

report_timing_summary -delay_type min_max -max_paths 20 -report_unconstrained -file $timing
report_utilization -file $util
report_drc -file $drc
report_methodology -file $methodology
report_clock_utilization -file $clocks_report
report_io -file $io_report
report_route_status -file $route_report
write_checkpoint $checkpoint

set setup [get_timing_paths -quiet -delay_type max -max_paths 1 -nworst 1]
set hold [get_timing_paths -quiet -delay_type min -max_paths 1 -nworst 1]
set setup_slack NA
set hold_slack NA
if {[llength $setup] == 1} {set setup_slack [string trim [get_property SLACK [lindex $setup 0]]]}
if {[llength $hold] == 1} {set hold_slack [string trim [get_property SLACK [lindex $hold 0]]]}
set clocks [get_clocks -quiet]
set out [open $metrics {WRONLY CREAT EXCL}]
puts $out "META|scope|M08_PATH_A_NATIVE_K26_FAN_AND_DUAL_AXI_POST_ROUTE"
puts $out "META|part|[get_property PART [current_project]]"
puts $out "META|vivado_version|[version -short]"
puts $out "META|synthesis_status|$synth_status"
puts $out "META|implementation_status|$impl_status"
puts $out "META|synthesis_progress|$synth_progress"
puts $out "META|implementation_progress|$impl_progress"
puts $out "META|wns_ns|$setup_slack"
puts $out "META|whs_ns|$hold_slack"
puts $out "META|clock_count|[llength $clocks]"
puts $out "META|fan_port|M08_FAN_PWM"
puts $out "META|fan_pin|$pin"
puts $out "META|fan_iostandard|$standard"
puts $out "META|fan_direction|$direction"
puts $out "META|fan_slew|$slew"
puts $out "META|fan_drive|$drive"
puts $out "META|no_bitstream|YES"
puts $out "META|no_board_programming|YES"
puts $out "META|compute_enabled|NO"
puts $out "META|physical_fan_continuity|NOT_VERIFIED"
puts $out "META|linux_overlay|NOT_INSTALLED"
puts $out "META|ps_axi|NOT_ACCESSED"
puts $out "META|physical_ddr|NOT_ACCESSED"
close $out
if {![string is double -strict $setup_slack] ||
    ![string is double -strict $hold_slack] ||
    [llength $clocks] < 1} {
    error "M08 Path A genuine routed timing path/clock missing: setup=$setup_slack hold=$hold_slack"
}
if {[expr {double($setup_slack)}] < 0.0 || [expr {double($hold_slack)}] < 0.0} {
    error "M08 Path A timing closure FAILED setup=$setup_slack hold=$hold_slack"
}
puts "M08_PATH_A_FAN_NATIVE_POST_ROUTE_NONNEGATIVE_SLACK=1"
puts "M08_PATH_A_FAN_ROUTE_REPORTS_GENERATED_DRC_UNREVIEWED_NO_BITSTREAM_NO_BOARD"
