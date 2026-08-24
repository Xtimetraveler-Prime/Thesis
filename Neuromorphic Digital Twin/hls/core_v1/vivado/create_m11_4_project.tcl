# Recreate the M11.4 Vivado project around the packaged neuron_step_v1 IP.
#
# Usage:
#   vivado -mode batch -source create_m11_4_project.tcl -tclargs \
#       <ip_repo_dir> <project_dir> <target_part> <expected_vlnv>

if {$argc != 4} {
    error "usage: create_m11_4_project.tcl <ip_repo_dir> <project_dir> <target_part> <expected_vlnv>"
}

set ip_repo_dir [file normalize [lindex $argv 0]]
set project_dir [file normalize [lindex $argv 1]]
set target_part [lindex $argv 2]
set expected_vlnv [lindex $argv 3]
set project_name "neuromorphic_twin_m11_4"
set bd_name "neuromorphic_twin_core"

if {![file isdirectory $ip_repo_dir]} {
    error "IP repository does not exist: $ip_repo_dir"
}

file delete -force $project_dir
file mkdir $project_dir

create_project $project_name $project_dir -part $target_part -force
set_property TARGET_LANGUAGE Verilog [current_project]
set_property SIMULATOR_LANGUAGE Mixed [current_project]

# Register the packaged HLS IP with the Vivado IP catalog.
set_property IP_REPO_PATHS [list $ip_repo_dir] [current_fileset]
update_ip_catalog -rebuild

set matching_ipdefs [get_ipdefs -all $expected_vlnv]
if {[llength $matching_ipdefs] == 0} {
    set neuron_matches [get_ipdefs -all -quiet *neuron_step_v1*]
    puts "Available neuron_step_v1-like IP definitions: $neuron_matches"
    error "Expected packaged IP was not found in the catalog: $expected_vlnv"
}

create_bd_design $bd_name
set hls_cell [create_bd_cell -type ip -vlnv $expected_vlnv neuron_step_v1_0]

# ap_start can carry a default driver in the packaged HLS metadata. Vivado's
# cell-wide make_bd_pins_external therefore may leave it tied to zero instead
# of creating a source port. Query this pin from the cell object itself, then
# create and connect a real transaction-start input explicitly.
set ap_start_pin [get_bd_pins -quiet -of_objects $hls_cell -filter {NAME == "ap_start"}]
if {[llength $ap_start_pin] != 1} {
    error "Expected exactly one HLS ap_start pin, found: $ap_start_pin"
}
set ap_start_port [create_bd_port -dir I ap_start]
connect_bd_net $ap_start_port $ap_start_pin

# M11.4 keeps the verified HLS core isolated. Make every other currently
# unconnected scalar control/data pin external so later M11.5 logic can
# connect state memories, tick control, and observability without changing
# this verified IP boundary.
make_bd_pins_external $hls_cell

validate_bd_design
save_bd_design

set bd_files [get_files -quiet */${bd_name}.bd]
if {[llength $bd_files] != 1} {
    error "Expected exactly one block-design file for $bd_name, found: $bd_files"
}
set bd_file [lindex $bd_files 0]

generate_target all $bd_file
set wrapper_files [make_wrapper -files $bd_file -top]
if {[llength $wrapper_files] > 0} {
    add_files -norecurse $wrapper_files
}
update_compile_order -fileset sources_1

# Persist both a project-level and BD-level recreation script as generated
# evidence. The source-controlled script in this directory remains normative.
write_bd_tcl -force [file join $project_dir recreate_neuromorphic_twin_core_bd.tcl]
write_project_tcl -force [file join $project_dir recreate_m11_4_project.tcl]

# create_project already created the project at the requested path, and the
# design/source commands above update that active project in place. Vivado
# 2025.2 exposes save_project_as for copying/renaming projects; there is no
# zero-argument save_project operation to perform here.

puts ""
puts "M11.4 Vivado project created successfully."
puts "Project: [file join $project_dir ${project_name}.xpr]"
puts "Target part: $target_part"
puts "Packaged HLS IP: $expected_vlnv"
puts "Block design: $bd_name"
puts "External block-design ports:"
foreach port [lsort [get_bd_ports]] {
    set dir [get_property DIR $port]
    set left [get_property LEFT $port]
    set right [get_property RIGHT $port]
    if {$left eq "" || $right eq "" || $left == -1 || $right == -1} {
        puts "  $port ($dir)"
    } else {
        puts "  $port ($dir, ${left}:${right})"
    }
}

close_project
