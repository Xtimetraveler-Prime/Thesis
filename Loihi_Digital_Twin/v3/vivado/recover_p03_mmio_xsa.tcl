# Recover an already-routed P03.2 project after XSA export failed because
# impl_1 stopped at route_design instead of the project-run write_bitstream step.
if {$argc != 2} {
    error "usage: recover_p03_mmio_xsa.tcl <project_xpr> <report_dir>"
}

set project_xpr [file normalize [lindex $argv 0]]
set report_dir [file normalize [lindex $argv 1]]

if {![file exists $project_xpr]} {
    error "P03.2 recovery project missing: $project_xpr"
}
file mkdir $report_dir

open_project $project_xpr

set impl_run [get_runs -quiet impl_1]
if {[llength $impl_run] != 1} {
    error "P03.2 recovery expected exactly one impl_1 run"
}

puts "P03_2_RECOVERY_INITIAL_STATUS=[get_property STATUS $impl_run]"
launch_runs impl_1 -to_step write_bitstream
wait_on_run impl_1
puts "P03_2_RECOVERY_FINAL_STATUS=[get_property STATUS $impl_run]"

open_run impl_1

set project_dir [get_property DIRECTORY [current_project]]
set project_name [get_property NAME [current_project]]
set impl_run_dir [file join $project_dir "${project_name}.runs" impl_1]
set impl_bit_files [glob -nocomplain [file join $impl_run_dir *.bit]]
if {[llength $impl_bit_files] != 1} {
    error "P03.2 recovery expected exactly one run-owned bitstream in $impl_run_dir, got [llength $impl_bit_files]"
}

set bit_file [file join $report_dir p03_2_ps_mmio.bit]
set ltx_file [file join $report_dir p03_2_ps_mmio.ltx]
set xsa_file [file join $report_dir p03_2_ps_mmio.xsa]

file copy -force [lindex $impl_bit_files 0] $bit_file
write_debug_probes -force $ltx_file
write_hw_platform -fixed -include_bit -force -file $xsa_file

foreach required [list $bit_file $ltx_file $xsa_file] {
    if {![file exists $required]} {
        error "P03.2 recovery artifact missing: $required"
    }
}

puts "PASS: P03.2 existing routed project advanced through write_bitstream"
puts "PASS: P03.2 fixed XSA export completed successfully"
puts "P03_2_RECOVERY_BIT=$bit_file"
puts "P03_2_RECOVERY_LTX=$ltx_file"
puts "P03_2_RECOVERY_XSA=$xsa_file"

close_project
