# M08 D2: OFFLINE ONLY — inspect the ORIGINAL K26 fan-preserving routed DCP.
# Input is owner-original, SHA pinned, full route; output is NEW evidence dir.
# This Tcl does not create/modify a hardware project, bitstream, device tree,
# boot state, JTAG session, FPGA image, or physical/virtual MMIO.
if {[llength $argv] != 3} {
    error "usage: m08_d2_fan_dcp_readonly_forensics.tcl <owner-original-fan-DCP> <NEW-evidence-dir> <expected-sha256>"
}
if {![string match "2025.2*" [version -short]]} {
    error "M08 D2 forensic native DCP inspection requires genuine Vivado 2025.2"
}
set dcp [file normalize [lindex $argv 0]]
set evidence [file normalize [lindex $argv 1]]
set expected_sha [string tolower [lindex $argv 2]]
if {![file isfile $dcp] || ![file isdirectory $evidence] ||
    [file tail $dcp] ne "48_fan_post_route.dcp" ||
    ![regexp {^[a-f0-9]{64}$} $expected_sha]} {
    error "M08 D2 requires original routed fan checkpoint, new evidence folder and SHA256"
}
set actual_sha [string tolower [lindex [exec sha256sum -- $dcp] 0]]
if {$actual_sha ne $expected_sha} {
    error "M08 D2 original fan DCP SHA256 mismatch BEFORE native open"
}
foreach file {
    10_dcp_identity.txt
    11_dcp_timing.rpt
    12_dcp_drc.rpt
    13_dcp_methodology.rpt
    14_dcp_clock_utilization.rpt
    15_dcp_clock_interaction.rpt
    16_dcp_reset_net_inventory.txt
    17_dcp_cdc.rpt
    18_dcp_exception_coverage.rpt
    19_dcp_ignored_paths_inventory.txt
} {
    if {[file exists [file join $evidence $file]]} {
        error "M08 D2 refuses to overwrite previously generated evidence file $file"
    }
}

open_checkpoint $dcp
set part [get_property PART [current_design]]
set top [get_property -quiet TOP [current_design]]
if {$part ne "xck26-sfvc784-2LV-c" || $top ne "m08_page_ps_wrapper"} {
    error "M08 D2 original K26 part/top mismatch: part=$part top=$top"
}
set fan [get_ports -quiet M08_FAN_PWM]
if {[llength $fan] != 1} { error "M08 D2 original routed PWM output missing" }
set port [lindex $fan 0]
set pin [get_property PACKAGE_PIN $port]
set iostandard [get_property IOSTANDARD $port]
set direction [get_property DIRECTION $port]
if {$pin ne "A12" || $iostandard ne "LVCMOS33" || $direction ne "OUT"} {
    error "M08 D2 fan path not original K26 A12/LVCMOS33/OUT"
}
set clocks [get_clocks -quiet]
if {[llength $clocks] == 0} { error "M08 D2 routed DCP has no clocks" }
set setup [get_timing_paths -quiet -delay_type max -max_paths 1 -nworst 1]
set hold [get_timing_paths -quiet -delay_type min -max_paths 1 -nworst 1]
if {[llength $setup] != 1 || [llength $hold] != 1} {
    error "M08 D2 routed DCP missing timing paths"
}
set wns [string trim [get_property SLACK [lindex $setup 0]]]
set whs [string trim [get_property SLACK [lindex $hold 0]]]
if {![string is double -strict $wns] || ![string is double -strict $whs] ||
    [expr {double($wns)}] < 0 || [expr {double($whs)}] < 0} {
    error "M08 D2 routed DCP timing was not nonnegative"
}
# Native reports: do NOT suppress RTSTAT-10 or reinterpret it as harmless.
report_timing_summary -file [file join $evidence 11_dcp_timing.rpt]
report_drc -file [file join $evidence 12_dcp_drc.rpt]
report_methodology -file [file join $evidence 13_dcp_methodology.rpt]
report_clock_utilization -file [file join $evidence 14_dcp_clock_utilization.rpt]
report_clock_interaction -file [file join $evidence 15_dcp_clock_interaction.rpt]

# Inspect actual *routed* reset pipeline occurrences and clocks.
# Name searches are diagnostics, not guaranteed IP hierarchy coverage.
set rst_net_objs [get_nets -hier -quiet -filter {NAME =~ *mi_handler_m_sc_areset_pipe*}]
set net_file [open [file join $evidence 16_dcp_reset_net_inventory.txt] {WRONLY CREAT EXCL}]
puts $net_file "schema=m08-d2-native-fan-dcp-reset-net-inventory-v1"
puts $net_file "scope=SOURCE_AND_ROUTED_NETLIST_ONLY_NOT_LINUX_RUNTIME"
puts $net_file "match_pattern=*mi_handler_m_sc_areset_pipe*"
puts $net_file "matching_net_count=[llength $rst_net_objs]"
foreach net [lsort -dictionary $rst_net_objs] {
    puts $net_file "RESET_NET|[get_property NAME $net]"
}
puts $net_file "reset_warning_proven_root_cause=NO"
puts $net_file "runtime_pl_clk0_enabled=UNKNOWN"
puts $net_file "runtime_pl_resetn0_released=UNKNOWN"
puts $net_file "ps_atb_instance4_enabled=UNKNOWN"
close $net_file

# The original routed report showed a SAME-clock Partial False Path
# classification; inspect exception coverage instead of silently accepting
# all static WNS paths as covering the whole fabric. report_exceptions may
# be unavailable on a native host; capture the failure, never claim PASS.
set exception_status "UNAVAILABLE"
if {[catch {report_exceptions -coverage -file [file join $evidence 18_dcp_exception_coverage.rpt]} exception_error]} {
    set exception_reason [string map [list "\n" " " "\r" " "] $exception_error]
    puts "M08_D2_EXCEPTION_COVERAGE_UNAVAILABLE=$exception_reason"
} else {
    set exception_status "GENERATED_REQUIRES_OWNER_REVIEW"
}
# get_timing_paths -user_ignored is a diagnostic *sample*, not an exhaustive
# path audit. No timing constraints are changed or waived.
set ignored_status "UNAVAILABLE"
set ignored_count 0
set ignored_output [open [file join $evidence 19_dcp_ignored_paths_inventory.txt] {WRONLY CREAT EXCL}]
puts $ignored_output "schema=m08-d2-routed-ignored-timing-paths-sample-v1"
puts $ignored_output "sample_max_paths=30"
if {[catch {get_timing_paths -user_ignored -max_paths 30 -nworst 1} ignored_paths]} {
    set ignored_reason [string map [list "\n" " " "\r" " "] $ignored_paths]
    puts $ignored_output "status=UNAVAILABLE"
    puts $ignored_output "error=$ignored_reason"
} else {
    set ignored_status "SAMPLED_NOT_EXHAUSTIVE"
    set ignored_count [llength $ignored_paths]
    puts $ignored_output "status=$ignored_status"
    puts $ignored_output "sample_returned=$ignored_count"
    foreach path_obj $ignored_paths {
        puts $ignored_output "IGNORED_PATH|[get_property -quiet STARTPOINT_PIN $path_obj]|[get_property -quiet ENDPOINT_PIN $path_obj]"
    }
}
puts $ignored_output "all_false_paths_reviewed=NO"
puts $ignored_output "runtime_clock_reset_proven=NO"
close $ignored_output

# CDC report can fail in some tool/licensing contexts; preserve the exact
# tool result and DO NOT relabel an unavailable report as a clean CDC pass.
set cdc_status "NOT_RUN"
if {[catch {report_cdc -file [file join $evidence 17_dcp_cdc.rpt]} cdc_error]} {
    set cdc_status "UNAVAILABLE"
    set cdc_reason [string map [list "\n" " " "\r" " "] $cdc_error]
    puts "M08_D2_CDC_REPORT_UNAVAILABLE=$cdc_reason"
} else {
    set cdc_status "GENERATED_REQUIRES_OWNER_REVIEW"
}
set f [open [file join $evidence 10_dcp_identity.txt] {WRONLY CREAT EXCL}]
puts $f "schema=m08-d2-native-fan-dcp-readonly-v1"
puts $f "vivado=[version -short]"
puts $f "dcp_sha256=$actual_sha"
puts $f "part=$part"
puts $f "top=$top"
puts $f "fan_pin=$pin"
puts $f "fan_iostandard=$iostandard"
puts $f "fan_direction=$direction"
puts $f "clock_count=[llength $clocks]"
puts $f "wns_ns=$wns"
puts $f "whs_ns=$whs"
puts $f "reset_pipeline_net_matches=[llength $rst_net_objs]"
puts $f "cdc_report=$cdc_status"
puts $f "exception_coverage_report=$exception_status"
puts $f "ignored_paths_diagnostic=$ignored_status"
puts $f "ignored_paths_sample_count=$ignored_count"
puts $f "timing_exceptions_signed_off=NO"
puts $f "original_routed_dcp=YES"
puts $f "no_source_or_owner_artifact_mutation=INTENDED"
puts $f "live_clock_reset_or_atb_verified=NO"
puts $f "root_cause_proven=NO"
puts $f "axi_slave_timeout_protection_verified=NO"
puts $f "physical_mmio_performed=NO"
puts $f "new_bitstream_created=NO"
puts $f "board_programmed=NO"
close $f
puts "M08_D2_NATIVE_FAN_DCP_READONLY_INSPECTION_COMPLETED_NO_BOARD"
close_design
