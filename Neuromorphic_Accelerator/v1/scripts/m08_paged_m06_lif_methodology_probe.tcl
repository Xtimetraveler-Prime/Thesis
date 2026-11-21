# M08.4 SOURCE ONLY: re-open original already-routed K26 checkpoint and
# report exact LUTAR-1 methodology instance cell/pin paths. NEVER programs.
# No write_checkpoint/write_bitstream, JTAG, or hardware manager.
if {[llength $argv] != 2} {error "usage: <existing-original-routed.dcp> <new-PC-methodology-report-dir>"}
if {![string match "2025.2*" [version -short]]} {error "original Vivado 2025.2 needed"}
set dcp [file normalize [lindex $argv 0]]
set out [file normalize [lindex $argv 1]]
if {![file isfile $dcp] || [file extension $dcp] ne ".dcp" ||
    ![file isdirectory $out] || ![regexp {^m08_paged_m06_lif_methodology_[A-Za-z0-9]+$} [file tail $out]] ||
    [file dirname $out] ne [file normalize [file join $::env(HOME) Thesis_Evidence M08]]} {
    error "M08.4 methodology: original routed checkpoint and new exclusive owner output required"
}
set method [file join $out 10_new_image_methodology.rpt]
set cdc [file join $out 11_new_image_cdc.rpt]
if {[file exists $method] || [file exists $cdc]} {error "refuse overwrite original supplemental evidence"}
open_checkpoint $dcp
puts "M08_4_READ_ONLY_CHECKPOINT_OPENED|$dcp"
report_methodology -file $method
report_cdc -file $cdc
puts "M08_4_NEW_IMAGE_METHOD_AND_CDC_REPORTS_CREATED_OFFLINE_NO_BOARD"
close_design
