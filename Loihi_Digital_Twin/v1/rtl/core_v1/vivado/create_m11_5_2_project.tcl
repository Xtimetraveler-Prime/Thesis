# Recreate and simulate the M11.5.2 neuron-array controller with the real
# packaged neuron_step_v1 HLS IP.
#
# Usage:
#   vivado -mode batch -source create_m11_5_2_project.tcl -tclargs \
#       <ip_repo_dir> <project_dir> <target_part> <expected_vlnv> \
#       <controller_rtl> <controller_bd_rtl> <tb_file> <vector_include>

if {$argc != 8} {
    error "usage: create_m11_5_2_project.tcl <ip_repo_dir> <project_dir> <target_part> <expected_vlnv> <controller_rtl> <controller_bd_rtl> <tb_file> <vector_include>"
}

set ip_repo_dir       [file normalize [lindex $argv 0]]
set project_dir       [file normalize [lindex $argv 1]]
set target_part       [lindex $argv 2]
set expected_vlnv     [lindex $argv 3]
set controller_rtl    [file normalize [lindex $argv 4]]
set controller_bd_rtl [file normalize [lindex $argv 5]]
set tb_file           [file normalize [lindex $argv 6]]
set vector_include    [file normalize [lindex $argv 7]]

set project_name "neuromorphic_twin_m11_5_2"
set bd_name "neuromorphic_twin_m11_5_2"
set controller_name "neuron_array_controller_bd_v1"

foreach path [list $ip_repo_dir $controller_rtl $controller_bd_rtl $tb_file $vector_include] {
    if {![file exists $path]} {
        error "Required M11.5.2 input does not exist: $path"
    }
}

proc expose_scalar_pin {cell_name pin_name} {
    set pin [get_bd_pins -quiet ${cell_name}/${pin_name}]
    if {[llength $pin] != 1} {
        error "Expected one pin ${cell_name}/${pin_name}, found: $pin"
    }

    set dir [get_property DIR $pin]
    set left [get_property LEFT $pin]
    set right [get_property RIGHT $pin]

    if {$left eq "" || $right eq "" || $left == -1 || $right == -1} {
        set port [create_bd_port -dir $dir $pin_name]
    } else {
        set port [create_bd_port -dir $dir -from $left -to $right $pin_name]
    }
    connect_bd_net $port $pin
}

proc connect_verified_pair {controller_pin hls_pin} {
    set cp [get_bd_pins -quiet controller_0/${controller_pin}]
    set hp [get_bd_pins -quiet neuron_step_v1_0/${hls_pin}]
    if {[llength $cp] != 1 || [llength $hp] != 1} {
        error "Missing integration pin: controller=$controller_pin ($cp), hls=$hls_pin ($hp)"
    }

    connect_bd_net $cp $hp

    set controller_nets [get_bd_nets -quiet -of_objects $cp]
    set hls_nets [get_bd_nets -quiet -of_objects $hp]
    if {[llength $controller_nets] != 1 || [llength $hls_nets] != 1} {
        error "Integration pins are not connected: controller=$controller_pin nets=$controller_nets, hls=$hls_pin nets=$hls_nets"
    }
    if {[lindex $controller_nets 0] ne [lindex $hls_nets 0]} {
        error "Integration pins are on different nets: controller=$controller_pin nets=$controller_nets, hls=$hls_pin nets=$hls_nets"
    }

    puts "M11.5.2 connected controller_0/$controller_pin -> neuron_step_v1_0/$hls_pin on [lindex $hls_nets 0]"
}

file delete -force $project_dir
file mkdir $project_dir
create_project $project_name $project_dir -part $target_part -force
set_property TARGET_LANGUAGE Verilog [current_project]
set_property SIMULATOR_LANGUAGE Mixed [current_project]

# Vivado Module Reference accepts Verilog/VHDL only at the referenced top.
# Keep the actual controller implementation as SystemVerilog underneath a thin
# Verilog-2001 wrapper. Sources are staged under a no-space path by the runner.
add_files -norecurse [list $controller_rtl $controller_bd_rtl]
set_property file_type SystemVerilog [get_files $controller_rtl]
set_property file_type Verilog [get_files $controller_bd_rtl]
update_compile_order -fileset sources_1

set_property IP_REPO_PATHS [list $ip_repo_dir] [current_fileset]
update_ip_catalog -rebuild

set matching_ipdefs [get_ipdefs -all $expected_vlnv]
if {[llength $matching_ipdefs] == 0} {
    error "Expected packaged HLS IP was not found in the catalog: $expected_vlnv"
}

create_bd_design $bd_name
set controller_cell [create_bd_cell -type module -reference $controller_name controller_0]
set hls_cell [create_bd_cell -type ip -vlnv $expected_vlnv neuron_step_v1_0]

# Wire every ap_ctrl_hs member explicitly. UG994 documents that once an
# individual interface signal is manually connected it is removed from the
# interface connection and must be manually completed. Avoid mixing an inferred
# acc_handshake connection with scalar overrides: all four members are explicit
# and each resulting net is verified before block-design validation.
set handshake_pairs {
    hls_ap_start ap_start
    hls_ap_done  ap_done
    hls_ap_idle  ap_idle
    hls_ap_ready ap_ready
}
foreach {controller_pin hls_pin} $handshake_pairs {
    connect_verified_pair $controller_pin $hls_pin
}

# Connect every scalar neuron datapath/result signal directly to the packaged
# HLS IP. Width mismatches are intentionally fatal during BD validation.
set scalar_pairs {
    hls_current_before             current_before
    hls_voltage_before             voltage_before
    hls_refractory_before          refractory_before
    hls_synaptic_input             synaptic_input
    hls_current_decay              current_decay
    hls_voltage_decay              voltage_decay
    hls_threshold                  threshold
    hls_bias                       bias
    hls_reset_voltage              reset_voltage
    hls_refractory_ticks           refractory_ticks
    hls_current_after              current_after
    hls_current_after_ap_vld       current_after_ap_vld
    hls_voltage_after              voltage_after
    hls_voltage_after_ap_vld       voltage_after_ap_vld
    hls_refractory_after           refractory_after
    hls_refractory_after_ap_vld    refractory_after_ap_vld
    hls_spiked                     spiked
    hls_spiked_ap_vld              spiked_ap_vld
}
foreach {controller_pin hls_pin} $scalar_pairs {
    connect_verified_pair $controller_pin $hls_pin
}

# One 100 MHz clock and active-high reset feed both blocks. Supplying FREQ_HZ at
# port creation avoids the transient user-clock warning produced when the value
# is assigned only afterward.
set clk_port [create_bd_port -dir I -type clk -freq_hz 100000000 ap_clk]
connect_bd_net $clk_port [get_bd_pins controller_0/ap_clk] [get_bd_pins neuron_step_v1_0/ap_clk]

set rst_port [create_bd_port -dir I -type rst ap_rst]
set_property CONFIG.POLARITY ACTIVE_HIGH $rst_port
connect_bd_net $rst_port [get_bd_pins controller_0/ap_rst] [get_bd_pins neuron_step_v1_0/ap_rst]

# Stable testbench/host-facing port names. HLS-facing pins are already internal.
set external_controller_pins {
    core_reset_start
    tick_start
    neuron_count
    busy
    core_reset_done
    tick_done
    tick
    fault
    fault_code
    active_neuron
    config_we
    config_addr
    config_wdata
    state_we
    state_addr
    state_wdata
    accum_we
    accum_addr
    accum_wdata
    debug_re
    debug_addr
    debug_rvalid
    debug_config_rdata
    debug_state_rdata
    debug_accum_rdata
    debug_spike_rdata
}
foreach pin_name $external_controller_pins {
    expose_scalar_pin controller_0 $pin_name
}

validate_bd_design
save_bd_design

puts ""
puts "M11.5.2 real-IP block design validated successfully."
puts "Controller module reference: $controller_name"
puts "Packaged HLS IP: $expected_vlnv"
puts "Control handshake: explicit ap_start/ap_done/ap_idle/ap_ready scalar nets"

set bd_files [get_files -quiet */${bd_name}.bd]
if {[llength $bd_files] != 1} {
    error "Expected exactly one block-design file for $bd_name, found: $bd_files"
}
set bd_file [lindex $bd_files 0]

generate_target all $bd_file
set wrapper_files [make_wrapper -files $bd_file -top]
if {[llength $wrapper_files] == 0} {
    error "Vivado did not generate an HDL wrapper for $bd_name"
}
add_files -norecurse $wrapper_files
update_compile_order -fileset sources_1

add_files -fileset sim_1 -norecurse [list $tb_file $vector_include]
set_property file_type SystemVerilog [get_files $tb_file]
set_property file_type "Verilog Header" [get_files $vector_include]
set_property include_dirs [list [file dirname $vector_include]] [get_filesets sim_1]
set_property top tb_neuromorphic_twin_m11_5_2 [get_filesets sim_1]
update_compile_order -fileset sim_1

puts ""
puts "=== M11.5.2 real packaged-IP behavioral simulation ==="
launch_simulation -simset sim_1 -mode behavioral
run all
close_sim

puts ""
puts "M11.5.2 real packaged-IP Vivado simulation flow completed."
puts "Project: [file join $project_dir ${project_name}.xpr]"
puts "Block design: $bd_name"
close_project
