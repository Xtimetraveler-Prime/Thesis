# M08.2b implementation/deployment gate: emit a NEW OFFLINE PL bitstream
# ONLY from the exact original owner K26 routed checkpoint, after strict
# independent SHA/timing/DRC preflight. No hardware-manager/board commands.
# This is the PS-only 256B state PAGE, compute DISABLED; not M06 inference.
if {[llength $argv] != 2} {
    error "usage: m08_page_bitstream_candidate.tcl <ORIGINAL-ROUTE-DCP> <NEW-RELEASE-EVIDENCE-DIR>"
}
if {![string match "2025.2*" [version -short]]} {
    error "M08 requires native Vivado 2025.2"
}
set checkpoint [file normalize [lindex $argv 0]]
set evidence [file normalize [lindex $argv 1]]
if {![file isfile $checkpoint] || ![file isdirectory $evidence]} {
    error "M08 requires the ORIGINAL routed DCP and fresh release directory"
}
if {[file tail $checkpoint] ne "10_m08_page_post_route.dcp"} {
    error "M08 release input is not the original M08.2b routed checkpoint"
}
set drc_file [file join $evidence 03_rechecked_drc.rpt]
set timing_file [file join $evidence 04_rechecked_timing.rpt]
set bit_file [file join $evidence 05_m08_safe_page.bit]
set metrics_file [file join $evidence 06_bitstream_native_metrics.txt]
foreach path [list $drc_file $timing_file $bit_file $metrics_file] {
    if {[file exists $path]} {
        error "M08 will not overwrite an original release artifact: $path"
    }
}

# AMD UG835 2025.2: open_checkpoint loads the full routed design,
# netlist, constraints and placement/routing into a NON-project session.
# It is not allowed to silently re-synthesize or change clock/RTL here.
open_checkpoint $checkpoint
if {[get_property PART [current_project]] ne "xck26-sfvc784-2LV-c"} {
    error "M08 rejected unexpected native K26 checkpoint PART"
}
if {[get_property NAME [current_design]] ne "m08_page_ps_wrapper"} {
    error "M08 rejected unexpected routed PS/page top"
}
set clocks [get_clocks -quiet]
if {[llength $clocks] < 1} {
    error "M08 no original timing clocks after opening post-route checkpoint"
}
set setup_paths [get_timing_paths -quiet -delay_type max -max_paths 1 -nworst 1]
set hold_paths [get_timing_paths -quiet -delay_type min -max_paths 1 -nworst 1]
if {[llength $setup_paths] != 1 || [llength $hold_paths] != 1} {
    error "M08 release checkpoint lacks original routed setup/hold timing paths"
}
set wns [string trim [get_property SLACK [lindex $setup_paths 0]]]
set whs [string trim [get_property SLACK [lindex $hold_paths 0]]]
if {![string is double -strict $wns] || ![string is double -strict $whs] ||
    [expr {double($wns)}] < 0.0 || [expr {double($whs)}] < 0.0} {
    error "M08 release checkpoint timing negative/non-numeric: WNS=$wns WHS=$whs"
}
report_timing_summary -delay_type min_max -report_unconstrained -file $timing_file
report_drc -file $drc_file
set fp [open $drc_file r]
set drc_text [read $fp]
close $fp
# Deliberate, REVIEWED exception: exactly ONE RTSTAT-10 Warning,
# reporting 15 internal SmartConnect reset-pipeline nets with no loads.
# Never demote/waive DRC severity using set_property or set_msg_config.
if {![regexp {Checks found:\s+1} $drc_text] ||
    ![regexp {\|\s*RTSTAT-10\s*\|\s*Warning\s*\|[^\n]*\|\s*1\s*\|} $drc_text] ||
    ![regexp {15 net\(s\) have no routable loads} $drc_text] ||
    [regexp -nocase {\|\s*(Error|Critical Warning)\s*\|} $drc_text]} {
    error "M08 post-route DRC differs from accepted single SmartConnect RTSTAT-10 warning"
}
puts "M08_PAGE_RELEASE_CHECKPOINT_TIMING_AND_DRC_RECHECKED=1"
# write_bitstream runs its own final required Vivado DRC; a failure must
# stop here and preserve the new original log. No -force or waiver.
write_bitstream $bit_file
if {![file isfile $bit_file] || [file size $bit_file] < 1024} {
    error "M08 genuine Vivado bitstream missing or implausibly short"
}
set o [open $metrics_file {WRONLY CREAT EXCL}]
puts $o "META|scope|M08_GENUINE_LOCAL_KV260_PS_SAFE_PAGE_BITSTREAM_NO_BOARD"
puts $o "META|vivado_version|[version -short]"
puts $o "META|part|[get_property PART [current_project]]"
puts $o "META|top|[get_property NAME [current_design]]"
puts $o "META|wns_ns|$wns"
puts $o "META|whs_ns|$whs"
puts $o "META|clock_count|[llength $clocks]"
puts $o "META|drc_warning|RTSTAT-10"
puts $o "META|compute_enabled|NO"
puts $o "META|board_programmed|NO"
puts $o "META|linux_mmio|NOT_ACCESSED"
puts $o "META|physical_ddr|NOT_ACCESSED"
close $o
puts "M08_PAGE_GENUINE_OFFLINE_BITSTREAM_EMITTED_NOT_PROGRAMMED"
