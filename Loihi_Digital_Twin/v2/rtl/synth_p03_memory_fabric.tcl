if {$argc != 4} {
    error "usage: synth_p03_memory_fabric.tcl <host_bridge_rtl> <memory_fabric_rtl> <target_part> <report_dir>"
}

set host_bridge_rtl [file normalize [lindex $argv 0]]
set memory_fabric_rtl [file normalize [lindex $argv 1]]
set target_part [lindex $argv 2]
set report_dir [file normalize [lindex $argv 3]]
file mkdir $report_dir

create_project -in_memory p03_memory_fabric_synth -part $target_part
set_property TARGET_LANGUAGE Verilog [current_project]
set_property XPM_LIBRARIES XPM_MEMORY [current_project]
add_files -norecurse [list $host_bridge_rtl $memory_fabric_rtl]
update_compile_order -fileset sources_1

synth_design -top p03_memory_fabric -part $target_part

set util_text [report_utilization -return_string]
set util_file [open [file join $report_dir utilization_memory_fabric_synth.rpt] w]
puts $util_file $util_text
close $util_file
report_utilization -hierarchical -hierarchical_depth 8 \
    -file [file join $report_dir utilization_memory_fabric_hierarchical_synth.rpt]

set primitive_file [open [file join $report_dir memory_primitives_synth.rpt] w]
foreach c [lsort [get_cells -hierarchical -filter {REF_NAME == RAMB36E2 || REF_NAME == RAMB18E2 || REF_NAME == URAM288}]] {
    puts $primitive_file "[get_property REF_NAME $c] $c"
}
close $primitive_file

set metrics [open [file join $report_dir memory_fabric_synth_metrics.txt] w]
set expected_external_memory_bits 3375104
set minimum_bram_tiles 90.0
puts $metrics "expected_external_memory_bits=$expected_external_memory_bits"
puts $metrics "minimum_bram_tiles=$minimum_bram_tiles"
puts $metrics "memory_shell=xpm_true_dual_port_v2"

if {[regexp {\| Block RAM Tile\s+\|\s+([0-9.]+)\s+\|} $util_text -> bram_tiles]} {
    puts $metrics "block_ram_tiles=$bram_tiles"
    puts "P03_XPM_SYNTH_BRAM_TILES=$bram_tiles"
    if {[expr {double($bram_tiles) < $minimum_bram_tiles}]} {
        close $metrics
        error "P03 XPM synthesis retention failed: Block RAM Tile=$bram_tiles, expected at least $minimum_bram_tiles"
    }
} else {
    close $metrics
    error "P03 XPM synthesis gate could not parse Block RAM Tile utilization"
}
close $metrics

puts "P03 XPM memory-fabric synthesis retention gate passed."
