# M08.2b Path A: generate a NEW OFFLINE fan-preserving K26 PL bitstream
# exclusively from a verified original fan-routed DCP snapshot.
# NO JTAG programming, xmutil, Linux/PS access, flash, fan or boot changes.
if {[llength $argv] != 3} {
    error "usage: m08_path_a_fan_bitstream.tcl <verified-DCP-copy> <new-evidence-dir> <expected-SHA>"
}
if {![info exists ::env(M08_ACCEPT_FAN_RTSTAT10)] ||
    $::env(M08_ACCEPT_FAN_RTSTAT10) ne "YES"} {
    error "explicit M08_ACCEPT_FAN_RTSTAT10=YES operator review required"
}
if {![string match "2025.2*" [version -short]]} {
    error "M08 fan release requires native Vivado 2025.2"
}
set dcp [file normalize [lindex $argv 0]]
set evidence [file normalize [lindex $argv 1]]
set expected [string tolower [lindex $argv 2]]
if {![file isfile $dcp] || ![file isdirectory $evidence] ||
    [file tail $dcp] ne "48_fan_post_route.dcp"} {
    error "M08 fan bitstream requires a verified copied original post-route DCP"
}
if {![regexp {^[a-f0-9]{64}$} $expected]} {
    error "M08 fan routed DCP expected SHA must be exact 64 hex chars"
}
set found [string tolower [lindex [exec sha256sum -- $dcp] 0]]
if {$found ne $expected} {
    error "M08 fan DCP SHA changed before native Vivado; no bitstream"
}
set drc_file [file join $evidence 03_fan_release_drc.rpt]
set timing_file [file join $evidence 04_fan_release_timing.rpt]
set bit_file [file join $evidence 05_m08_path_a_fan_page.bit]
set metrics_file [file join $evidence 06_fan_bitstream_metrics.txt]
foreach path [list $drc_file $timing_file $bit_file $metrics_file] {
    if {[file exists $path]} {error "M08 fan release will not overwrite an artifact"}
}
open_checkpoint $dcp
if {[get_property PART [current_project]] ne "xck26-sfvc784-2LV-c"} {
    error "M08 fan bitstream unexpected physical K26 part"
}
set top [string trim [get_property -quiet TOP [current_design]]]
if {$top ne "m08_page_ps_wrapper"} {
    error "M08 fan bitstream routed DCP wrong TOP: '$top'"
}
set fan [get_ports -quiet M08_FAN_PWM]
if {[llength $fan] != 1} {
    error "M08 fan bitstream routed checkpoint has no unique M08_FAN_PWM"
}
set pwm [lindex $fan 0]
set pin [string trim [get_property PACKAGE_PIN $pwm]]
set io [string trim [get_property IOSTANDARD $pwm]]
set direction [string toupper [string trim [get_property DIRECTION $pwm]]]
set slew [string toupper [string trim [get_property SLEW $pwm]]]
set drive [string trim [get_property DRIVE $pwm]]
if {$pin ne "A12" || $io ne "LVCMOS33" || $direction ne "OUT" ||
    $slew ne "SLOW" || $drive ne "4"} {
    error "M08 fan bitstream routed A12 output does not match original fan I/O"
}
set clocks [get_clocks -quiet]
set setup [get_timing_paths -quiet -delay_type max -max_paths 1 -nworst 1]
set hold [get_timing_paths -quiet -delay_type min -max_paths 1 -nworst 1]
if {[llength $clocks] < 1 || [llength $setup] != 1 || [llength $hold] != 1} {
    error "M08 fan bitstream routed checkpoint missing timing paths or clocks"
}
set wns [string trim [get_property SLACK [lindex $setup 0]]]
set whs [string trim [get_property SLACK [lindex $hold 0]]]
if {![string is double -strict $wns] ||
    ![string is double -strict $whs] ||
    [expr {double($wns)}] < 0 || [expr {double($whs)}] < 0} {
    error "M08 fan bitstream negative/non-numeric routed timing"
}
report_timing_summary -delay_type min_max -report_unconstrained -file $timing_file
report_drc -file $drc_file
set f [open $drc_file r]
set drc [read $f]
close $f
if {![regexp {Design State : Fully Routed} $drc] ||
    ![regexp {Checks found:\s+1} $drc] ||
    ![regexp {\|\s*RTSTAT-10\s*\|\s*Warning\s*\|[^\n]*\|\s*1\s*\|} $drc] ||
    ![regexp {15 net\(s\) have no routable loads} $drc] ||
    [regexp -nocase {\|\s*(Error|Critical Warning)\s*\|} $drc]} {
    error "M08 fan bitstream rechecked DRC differs from reviewed RTSTAT-10 only"
}
puts "M08_PATH_A_FAN_CHECKPOINT_TOP_A12_TIMING_DRC_RECHECKED=1"
# Only a genuine physical routed checkpoint; no synthesis/route or DRC waiver.
write_bitstream $bit_file
if {![file isfile $bit_file] || [file size $bit_file] < 1048576} {
    error "M08 fan output .bit missing or implausibly small"
}
set out [open $metrics_file {WRONLY CREAT EXCL}]
puts $out "META|scope|M08_PATH_A_K26_FAN_SAFE_PAGE_OFFLINE_BITSTREAM"
puts $out "META|vivado|[version -short]"
puts $out "META|part|[get_property PART [current_project]]"
puts $out "META|top|$top"
puts $out "META|checkpoint_sha256|$found"
puts $out "META|wns_ns|$wns"
puts $out "META|whs_ns|$whs"
puts $out "META|fan_pin|$pin"
puts $out "META|fan_iostandard|$io"
puts $out "META|fan_direction|$direction"
puts $out "META|drc_warning|RTSTAT-10"
puts $out "META|bit_bytes|[file size $bit_file]"
puts $out "META|board_programmed|NO"
puts $out "META|linux_overlay_installed|NO"
puts $out "META|physical_fan_continuity|NOT_VERIFIED"
puts $out "META|ps_axi|NOT_ACCESSED"
puts $out "META|compute_enabled|NO"
close $out
puts "M08_PATH_A_NEW_OFFLINE_FAN_BITSTREAM_EMITTED_NOT_PROGRAMMED"
