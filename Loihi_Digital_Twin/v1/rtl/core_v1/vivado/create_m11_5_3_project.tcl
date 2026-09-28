# Recreate and simulate the M11.5.3 packed-M08 Phase-B + real HLS integration.
if {$argc != 11} {
    error "usage: create_m11_5_3_project.tcl <ip_repo_dir> <project_dir> <target_part> <expected_vlnv> <decoder_rtl> <phase_b_rtl> <neuron_rtl> <integrated_rtl> <integrated_bd_rtl> <tb_file> <vector_include>"
}

set ip_repo_dir       [file normalize [lindex $argv 0]]
set project_dir       [file normalize [lindex $argv 1]]
set target_part       [lindex $argv 2]
set expected_vlnv     [lindex $argv 3]
set decoder_rtl       [file normalize [lindex $argv 4]]
set phase_b_rtl       [file normalize [lindex $argv 5]]
set neuron_rtl        [file normalize [lindex $argv 6]]
set integrated_rtl    [file normalize [lindex $argv 7]]
set integrated_bd_rtl [file normalize [lindex $argv 8]]
set tb_file           [file normalize [lindex $argv 9]]
set vector_include    [file normalize [lindex $argv 10]]

set project_name "neuromorphic_twin_m11_5_3"
set bd_name "neuromorphic_twin_m11_5_3"
set controller_name "integrated_core_controller_bd_v1"

foreach path [list $ip_repo_dir $decoder_rtl $phase_b_rtl $neuron_rtl $integrated_rtl $integrated_bd_rtl $tb_file $vector_include] {
    if {![file exists $path]} {
        error "Required M11.5.3 input does not exist: $path"
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
        error "Missing M11.5.3 integration pin: controller=$controller_pin ($cp), hls=$hls_pin ($hp)"
    }
    connect_bd_net $cp $hp
    set cn [get_bd_nets -quiet -of_objects $cp]
    set hn [get_bd_nets -quiet -of_objects $hp]
    if {[llength $cn] != 1 || [llength $hn] != 1 || [lindex $cn 0] ne [lindex $hn 0]} {
        error "M11.5.3 integration pin connectivity mismatch: controller=$controller_pin nets=$cn, hls=$hls_pin nets=$hn"
    }
    puts "M11.5.3 connected controller_0/$controller_pin -> neuron_step_v1_0/$hls_pin on [lindex $hn 0]"
}

file delete -force $project_dir
file mkdir $project_dir
create_project $project_name $project_dir -part $target_part -force
set_property TARGET_LANGUAGE Verilog [current_project]
set_property SIMULATOR_LANGUAGE Mixed [current_project]

foreach source_file [list $decoder_rtl $phase_b_rtl $neuron_rtl $integrated_rtl] {
    add_files -norecurse $source_file
    set_property file_type SystemVerilog [get_files $source_file]
}
add_files -norecurse $integrated_bd_rtl
set_property file_type Verilog [get_files $integrated_bd_rtl]
update_compile_order -fileset sources_1

set_property IP_REPO_PATHS [list $ip_repo_dir] [current_fileset]
update_ip_catalog -rebuild
if {[llength [get_ipdefs -all $expected_vlnv]] == 0} {
    error "Expected packaged HLS IP was not found in the catalog: $expected_vlnv"
}

create_bd_design $bd_name
set controller_cell [create_bd_cell -type module -reference $controller_name controller_0]
set hls_cell [create_bd_cell -type ip -vlnv $expected_vlnv neuron_step_v1_0]

set handshake_pairs {
    hls_ap_start ap_start
    hls_ap_done  ap_done
    hls_ap_idle  ap_idle
    hls_ap_ready ap_ready
}
foreach {controller_pin hls_pin} $handshake_pairs {
    connect_verified_pair $controller_pin $hls_pin
}

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

set clk_port [create_bd_port -dir I -type clk -freq_hz 100000000 ap_clk]
connect_bd_net $clk_port [get_bd_pins controller_0/ap_clk] [get_bd_pins neuron_step_v1_0/ap_clk]
set rst_port [create_bd_port -dir I -type rst ap_rst]
set_property CONFIG.POLARITY ACTIVE_HIGH $rst_port
connect_bd_net $rst_port [get_bd_pins controller_0/ap_rst] [get_bd_pins neuron_step_v1_0/ap_rst]

set external_controller_pins {
    core_reset_start tick_start neuron_count axon_count synapse_count format_count
    external_event_count recurrent_event_count busy core_reset_done tick_done tick
    fault fault_code active_neuron phase_b_active_source phase_b_active_event_index
    phase_b_active_synapse_index config_we config_addr config_wdata state_we state_addr
    state_wdata format_we format_addr format_wdata synapse_we synapse_addr synapse_wdata
    row_we row_addr row_wdata external_we external_addr external_wdata recurrent_we
    recurrent_addr recurrent_wdata debug_re debug_addr debug_rvalid debug_config_rdata
    debug_state_rdata debug_accum_rdata debug_spike_rdata
}
foreach pin_name $external_controller_pins {
    expose_scalar_pin controller_0 $pin_name
}

validate_bd_design
save_bd_design
puts ""
puts "M11.5.3 packed-M08 real-HLS block design validated successfully."
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
set_property top tb_neuromorphic_twin_m11_5_3 [get_filesets sim_1]
update_compile_order -fileset sim_1

puts ""
puts "=== M11.5.3 packed M08 + real HLS behavioral simulation ==="
launch_simulation -simset sim_1 -mode behavioral
run all
close_sim

puts ""
puts "M11.5.3 packed-M08 + real packaged-HLS Vivado simulation flow completed."
puts "Project: [file join $project_dir ${project_name}.xpr]"
puts "Block design: $bd_name"
close_project
