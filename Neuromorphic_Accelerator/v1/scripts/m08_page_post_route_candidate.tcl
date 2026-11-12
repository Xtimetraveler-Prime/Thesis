# M08.2b.4a genuine NATIVE K26 PS->identity+signed16 safe-page
# SYNTHESIS and ROUTED IMPLEMENTATION, REPORTS and checkpoint ONLY.
# No bitstream, flash/JTAG, physical KV260, Linux MMIO, DMA or PS DDR.
# Derives the exact M08.2b.3 already owner-accepted native BD candidate;
# never opens or modifies its original owner evidence folder.
if {[llength $argv] != 3} {
    error "usage: m08_page_post_route_candidate.tcl <v1-root> <NEW-evidence-dir> <jobs>"
}
set root [file normalize [lindex $argv 0]]
set evidence [file normalize [lindex $argv 1]]
set jobs [lindex $argv 2]
if {![string is integer -strict $jobs] || $jobs < 1 || $jobs > 8} {
    error "M08 jobs must be bounded integer 1..8"
}
set candidate [file join $root scripts m08_page_ps_bd_candidate.tcl]
if {![file isfile $candidate] || ![file isdirectory $evidence]} {
    error "M08 requires first-party validated BD script and fresh evidence folder"
}
set metrics_file [file join $evidence 04_implementation_metrics.txt]
set timing_file [file join $evidence 05_timing_summary_post_route.rpt]
set util_file [file join $evidence 06_utilization_post_route.rpt]
set drc_file [file join $evidence 07_drc_post_route.rpt]
set methodology_file [file join $evidence 08_methodology_post_route.rpt]
set clocks_file [file join $evidence 09_clock_utilization_post_route.rpt]
set checkpoint_file [file join $evidence 10_m08_page_post_route.dcp]
foreach f [list $metrics_file $timing_file $util_file $drc_file \
                $methodology_file $clocks_file $checkpoint_file] {
    if {[file exists $f]} {error "M08 will not overwrite an existing original report $f"}
}

# The validated BD script requires two args and creates <evidence>/project.
# Reuse it verbatim; never try to reassemble its PS clock, reset, address
# or module-reference configuration in a second incomplete implementation.
set argv [list $root $evidence]
source $candidate
if {[get_property PART [current_project]] ne "xck26-sfvc784-2LV-c"} {
    error "M08 route project selected the wrong K26 device"
}
set bd_files [get_files -quiet */m08_page_ps.bd]
if {[llength $bd_files] != 1} {
    error "M08 source-proven native page BD missing or duplicated"
}
set bd [lindex $bd_files 0]
generate_target all $bd
set wrapper_files [make_wrapper -files $bd -top]
if {[llength $wrapper_files] != 1} {
    error "M08 native wrapper generation failed or returned multiple files"
}
add_files -norecurse $wrapper_files
set_property top m08_page_ps_wrapper [current_fileset]
update_compile_order -fileset sources_1
if {[get_property top [current_fileset]] ne "m08_page_ps_wrapper"} {
    error "M08 expected generated BD top was not selected"
}
puts "M08_PAGE_GENUINE_NATIVE_WRAPPER_GENERATED=1"

# An actual routed K26 path is necessary before any bitstream release.
# Launching impl_1 automatically runs its dependent synth_1 stage.
set_property STEPS.PHYS_OPT_DESIGN.IS_ENABLED true [get_runs impl_1]
launch_runs impl_1 -to_step route_design -jobs $jobs
wait_on_run impl_1
set synth_run [get_runs synth_1]
set impl_run [get_runs impl_1]
set synth_progress [get_property PROGRESS $synth_run]
set impl_progress [get_property PROGRESS $impl_run]
set synth_status [get_property STATUS $synth_run]
set impl_status [get_property STATUS $impl_run]
if {$synth_progress ne "100%" || $impl_progress ne "100%" ||
    ![string match "*Complete*" $synth_status] ||
    ![string match "*Complete*" $impl_status]} {
    error "M08 native synth/route incomplete: synthesis='$synth_status' ($synth_progress), impl='$impl_status' ($impl_progress)"
}
puts "M08_PAGE_GENUINE_NATIVE_SYNTH_AND_ROUTE_COMPLETED=1"
open_run impl_1

report_timing_summary -delay_type min_max -max_paths 20 \
    -report_unconstrained -file $timing_file
report_utilization -file $util_file
report_drc -file $drc_file
report_methodology -file $methodology_file
report_clock_utilization -file $clocks_file
write_checkpoint $checkpoint_file

# Actual routed slack, not a nominal 100 MHz estimate or HLS timing.
# Fail closed on missing, nonnumeric, or negative setup/hold evidence.
set setup_paths [get_timing_paths -quiet -delay_type max -max_paths 1 -nworst 1]
set hold_paths [get_timing_paths -quiet -delay_type min -max_paths 1 -nworst 1]
set setup_slack NA
set hold_slack NA
if {[llength $setup_paths] > 0} {
    set setup_slack [string trim [get_property SLACK [lindex $setup_paths 0]]]
}
if {[llength $hold_paths] > 0} {
    set hold_slack [string trim [get_property SLACK [lindex $hold_paths 0]]]
}
set clocks [get_clocks -quiet]
set o [open $metrics_file {WRONLY CREAT EXCL}]
puts $o "META|scope|M08_GENUINE_LOCAL_KV260_PAGE_SAFE_POST_ROUTE"
puts $o "META|part|[get_property PART [current_project]]"
puts $o "META|vivado_version|[version -short]"
puts $o "META|synthesis_status|$synth_status"
puts $o "META|implementation_status|$impl_status"
puts $o "META|synthesis_progress|$synth_progress"
puts $o "META|implementation_progress|$impl_progress"
puts $o "META|wns_ns|$setup_slack"
puts $o "META|whs_ns|$hold_slack"
puts $o "META|clock_count|[llength $clocks]"
puts $o "META|no_bitstream|YES"
puts $o "META|no_board_programming|YES"
puts $o "META|compute_enabled|NO"
puts $o "META|physical_ddr|NOT_ACCESSED"
puts $o "META|linux_mmio|NOT_ACCESSED"
close $o
if {![string is double -strict $setup_slack] ||
    ![string is double -strict $hold_slack] ||
    [llength $clocks] == 0} {
    error "M08 routed design has missing setup/hold or clock constraints: wns='$setup_slack' whs='$hold_slack' clocks=[llength $clocks]"
}
if {[expr {double($setup_slack)}] < 0.0 || [expr {double($hold_slack)}] < 0.0} {
    error "M08 post-route timing FAILED: actual setup WNS=$setup_slack ns, hold WHS=$hold_slack ns"
}
puts "M08_PAGE_POST_ROUTE_TIMING_NONNEGATIVE_NO_BITSTREAM=1"
puts "M08_PAGE_NATIVE_ROUTE_REPORTS_GENERATED_UNREVIEWED_DRC_NO_BOARD"
