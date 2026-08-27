# M11.6 physical implementation: K26 PS clock + VIO/JTAG smoke shell around
# the behaviorally complete recurrent core and packaged neuron_step_v1 IP.
if {$argc != 16} {
    error "usage: create_m11_6_project.tcl <ip_repo_dir> <project_dir> <target_part> <expected_vlnv> <decoder_rtl> <phase_b_rtl> <neuron_rtl> <integrated_rtl> <route_rtl> <recurrent_rtl> <smoke_rtl> <smoke_bd_rtl> <smoke_vectors> <report_dir> <artifact_dir> <jobs>"
}

set ip_repo_dir    [file normalize [lindex $argv 0]]
set project_dir    [file normalize [lindex $argv 1]]
set target_part    [lindex $argv 2]
set expected_vlnv  [lindex $argv 3]
set decoder_rtl    [file normalize [lindex $argv 4]]
set phase_b_rtl    [file normalize [lindex $argv 5]]
set neuron_rtl     [file normalize [lindex $argv 6]]
set integrated_rtl [file normalize [lindex $argv 7]]
set route_rtl      [file normalize [lindex $argv 8]]
set recurrent_rtl  [file normalize [lindex $argv 9]]
set smoke_rtl      [file normalize [lindex $argv 10]]
set smoke_bd_rtl   [file normalize [lindex $argv 11]]
set smoke_vectors  [file normalize [lindex $argv 12]]
set report_dir     [file normalize [lindex $argv 13]]
set artifact_dir   [file normalize [lindex $argv 14]]
set jobs           [lindex $argv 15]

set project_name "neuromorphic_twin_m11_6"
set bd_name "neuromorphic_twin_m11_6"
set smoke_module "m11_6_smoke_controller_bd_v1"

foreach path [list $ip_repo_dir $decoder_rtl $phase_b_rtl $neuron_rtl $integrated_rtl $route_rtl $recurrent_rtl $smoke_rtl $smoke_bd_rtl $smoke_vectors] {
    if {![file exists $path]} {
        error "Required M11.6 input does not exist: $path"
    }
}
file mkdir $report_dir
file mkdir $artifact_dir

proc connect_verified_pair {smoke_pin hls_pin} {
    set sp [get_bd_pins -quiet smoke_0/${smoke_pin}]
    set hp [get_bd_pins -quiet neuron_step_v1_0/${hls_pin}]
    if {[llength $sp] != 1 || [llength $hp] != 1} {
        error "Missing M11.6 integration pin: smoke=$smoke_pin ($sp), hls=$hls_pin ($hp)"
    }
    connect_bd_net $sp $hp
    set sn [get_bd_nets -quiet -of_objects $sp]
    set hn [get_bd_nets -quiet -of_objects $hp]
    if {[llength $sn] != 1 || [llength $hn] != 1 || [lindex $sn 0] ne [lindex $hn 0]} {
        error "M11.6 integration pin connectivity mismatch: smoke=$smoke_pin nets=$sn, hls=$hls_pin nets=$hn"
    }
}

proc connect_named_pair {net_name left_pin right_pin} {
    set lp [get_bd_pins -quiet $left_pin]
    set rp [get_bd_pins -quiet $right_pin]
    if {[llength $lp] != 1 || [llength $rp] != 1} {
        error "Missing M11.6 VIO connection pin for $net_name: left=$lp right=$rp"
    }
    set net [create_bd_net $net_name]
    connect_bd_net -net $net $lp $rp
}

file delete -force $project_dir
file mkdir $project_dir
create_project $project_name $project_dir -part $target_part -force
set_property TARGET_LANGUAGE Verilog [current_project]
set_property SIMULATOR_LANGUAGE Mixed [current_project]

# The K26 part alone does not initialize the Zynq UltraScale+ PS package/DDR
# configuration. Select the installed KV260 SOM board file dynamically; this is
# a SOM-level preset for the K26 PS/DDR/dedicated I/O and does not constrain any
# carrier-card PL pins.
set kv260_board_parts [get_board_parts -quiet xilinx.com:kv260_som:part0:*]
if {[llength $kv260_board_parts] == 0} {
    error "M11.6 requires the Vivado KV260 SOM board files (xilinx.com:kv260_som:part0:*)."
}
set kv260_board_part [lindex [lsort -dictionary $kv260_board_parts] end]
set_property BOARD_PART $kv260_board_part [current_project]
puts "M11.6 K26 SOM board preset: $kv260_board_part"

foreach source_file [list $decoder_rtl $phase_b_rtl $neuron_rtl $integrated_rtl $route_rtl $recurrent_rtl $smoke_rtl] {
    add_files -norecurse $source_file
    set_property file_type SystemVerilog [get_files $source_file]
}
add_files -norecurse $smoke_bd_rtl
set_property file_type Verilog [get_files $smoke_bd_rtl]
add_files -norecurse $smoke_vectors
set_property file_type {Verilog Header} [get_files $smoke_vectors]
set_property include_dirs [list [file dirname $smoke_vectors]] [get_filesets sources_1]
update_compile_order -fileset sources_1

set_property IP_REPO_PATHS [list $ip_repo_dir] [current_fileset]
update_ip_catalog -rebuild
if {[llength [get_ipdefs -all $expected_vlnv]] == 0} {
    error "Expected packaged HLS IP was not found in the catalog: $expected_vlnv"
}
foreach required_ip {xilinx.com:ip:zynq_ultra_ps_e:3.5 xilinx.com:ip:vio:3.0} {
    if {[llength [get_ipdefs -all $required_ip]] == 0} {
        error "Required Vivado IP was not found in the catalog: $required_ip"
    }
}

create_bd_design $bd_name

# Use the K26 processing system only as a carrier-independent 100 MHz PL clock
# source. The Zynq MPSoC cell must first receive its SOM board preset through
# Block Automation; that step initializes the PS/DDR configuration and dedicated
# I/O. The M11.6 JTAG smoke deliberately does not depend on the software-managed
# PS fabric-reset GPIO; reset ownership is local to VIO inside the PL shell.
set ps [create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e:3.5 zynq_ultra_ps_e_0]
apply_bd_automation -rule xilinx.com:bd_rule:zynq_ultra_ps_e \
    -config {apply_board_preset "1"} $ps
set_property -dict [list \
    CONFIG.PSU__USE__M_AXI_GP0 {0} \
    CONFIG.PSU__USE__M_AXI_GP1 {0} \
    CONFIG.PSU__USE__M_AXI_GP2 {0} \
    CONFIG.PSU__FPGA_PL0_ENABLE {1} \
    CONFIG.PSU__USE__FABRIC__RST {0} \
    CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {100}] $ps

# Unlike Zynq-7000 PS7 flows, the KV260/K26 Zynq UltraScale+ MPSoC preset does
# not require top-level DDR/FIXED_IO block-design interface ports. Those are
# dedicated PS/SOM resources configured by the board preset. For M11.6 the only
# PS-to-PL signal required by the JTAG shell is the fabric clock below.
set pl_clk0_pin [get_bd_pins -quiet zynq_ultra_ps_e_0/pl_clk0]
if {[llength $pl_clk0_pin] != 1} {
    error "M11.6 KV260 PS preset did not expose the required pl_clk0 fabric clock."
}
puts "M11.6 PS Block Automation configured K26 SOM; PL clock boundary: clk=$pl_clk0_pin"

set smoke [create_bd_cell -type module -reference $smoke_module smoke_0]
set hls [create_bd_cell -type ip -vlnv $expected_vlnv neuron_step_v1_0]
set vio [create_bd_cell -type ip -vlnv xilinx.com:ip:vio:3.0 vio_m11_6]
set_property -dict [list \
    CONFIG.C_NUM_PROBE_IN {14} \
    CONFIG.C_NUM_PROBE_OUT {2} \
    CONFIG.C_PROBE_IN0_WIDTH {1} \
    CONFIG.C_PROBE_IN1_WIDTH {1} \
    CONFIG.C_PROBE_IN2_WIDTH {1} \
    CONFIG.C_PROBE_IN3_WIDTH {8} \
    CONFIG.C_PROBE_IN4_WIDTH {8} \
    CONFIG.C_PROBE_IN5_WIDTH {32} \
    CONFIG.C_PROBE_IN6_WIDTH {8} \
    CONFIG.C_PROBE_IN7_WIDTH {64} \
    CONFIG.C_PROBE_IN8_WIDTH {64} \
    CONFIG.C_PROBE_IN9_WIDTH {64} \
    CONFIG.C_PROBE_IN10_WIDTH {3} \
    CONFIG.C_PROBE_IN11_WIDTH {1} \
    CONFIG.C_PROBE_IN12_WIDTH {13} \
    CONFIG.C_PROBE_IN13_WIDTH {32} \
    CONFIG.C_PROBE_OUT0_WIDTH {1} \
    CONFIG.C_PROBE_OUT0_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT1_WIDTH {1} \
    CONFIG.C_PROBE_OUT1_INIT_VAL {0x0}] $vio

# Clock/reset boundary. The K26 PS reports its realizable PL0 frequency as
# approximately 100 MHz (99,999,001 Hz with this board preset). Module Reference
# clock metadata inherits that propagated PS value. Reset is deliberately local:
# VIO probe_out1 asynchronously asserts the smoke reset; the existing two-flop
# synchronizer in the smoke controller releases it synchronously and produces the
# matching active-high HLS ap_rst. A reset-independent heartbeat proves pl_clk0.
connect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_clk0] \
    [get_bd_pins smoke_0/ap_clk] \
    [get_bd_pins neuron_step_v1_0/ap_clk] \
    [get_bd_pins vio_m11_6/clk]
connect_verified_pair hls_ap_rst ap_rst
connect_named_pair smoke_resetn vio_m11_6/probe_out1 smoke_0/smoke_resetn
connect_named_pair clock_heartbeat smoke_0/clock_heartbeat vio_m11_6/probe_in13
puts "M11.6 local reset/heartbeat boundary: reset=VIO smoke_resetn heartbeat=clock_heartbeat"

set handshake_pairs {
    hls_ap_start ap_start
    hls_ap_done  ap_done
    hls_ap_idle  ap_idle
    hls_ap_ready ap_ready
}
foreach {smoke_pin hls_pin} $handshake_pairs {
    connect_verified_pair $smoke_pin $hls_pin
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
foreach {smoke_pin hls_pin} $scalar_pairs {
    connect_verified_pair $smoke_pin $hls_pin
}

# Named nets are deliberate: the generated LTX then exposes stable, searchable
# VIO probe names for the batch hardware-smoke script.
connect_named_pair smoke_start                  vio_m11_6/probe_out0 smoke_0/smoke_start
connect_named_pair smoke_busy                   smoke_0/smoke_busy vio_m11_6/probe_in0
connect_named_pair smoke_done                   smoke_0/smoke_done vio_m11_6/probe_in1
connect_named_pair smoke_pass                   smoke_0/smoke_pass vio_m11_6/probe_in2
connect_named_pair smoke_fail_code              smoke_0/smoke_fail_code vio_m11_6/probe_in3
connect_named_pair smoke_phase                  smoke_0/smoke_phase vio_m11_6/probe_in4
connect_named_pair observed_tick                smoke_0/observed_tick vio_m11_6/probe_in5
connect_named_pair observed_core_fault_code     smoke_0/observed_core_fault_code vio_m11_6/probe_in6
connect_named_pair observed_state0              smoke_0/observed_state0 vio_m11_6/probe_in7
connect_named_pair observed_state1              smoke_0/observed_state1 vio_m11_6/probe_in8
connect_named_pair observed_state2              smoke_0/observed_state2 vio_m11_6/probe_in9
connect_named_pair observed_spikes              smoke_0/observed_spikes vio_m11_6/probe_in10
connect_named_pair observed_recurrent_bank      smoke_0/observed_recurrent_bank vio_m11_6/probe_in11
connect_named_pair observed_recurrent_count     smoke_0/observed_recurrent_count vio_m11_6/probe_in12

validate_bd_design
save_bd_design
puts "M11.6 hardware-smoke block design validated successfully."

set bd_files [get_files -quiet */${bd_name}.bd]
if {[llength $bd_files] != 1} {
    error "Expected exactly one M11.6 block-design file, found: $bd_files"
}
set bd_file [lindex $bd_files 0]
generate_target all $bd_file
set wrapper_files [make_wrapper -files $bd_file -top]
if {[llength $wrapper_files] == 0} {
    error "Vivado did not generate an HDL wrapper for M11.6"
}
add_files -norecurse $wrapper_files
set_property top ${bd_name}_wrapper [current_fileset]
update_compile_order -fileset sources_1

puts ""
puts "=== M11.6 synthesis ==="
launch_runs synth_1 -jobs $jobs
wait_on_run synth_1
set synth_status [get_property STATUS [get_runs synth_1]]
puts "M11.6 synth_1 status: $synth_status"
if {[string first "Complete" $synth_status] < 0} {
    error "M11.6 synthesis did not complete successfully: $synth_status"
}

puts ""
puts "=== M11.6 implementation + bitstream ==="
launch_runs impl_1 -to_step write_bitstream -jobs $jobs
wait_on_run impl_1
set impl_status [get_property STATUS [get_runs impl_1]]
puts "M11.6 impl_1 status: $impl_status"
if {[string first "Complete" $impl_status] < 0} {
    error "M11.6 implementation/bitstream did not complete successfully: $impl_status"
}
open_run impl_1
puts "M11.6 implementation completed successfully."

report_utilization -file [file join $report_dir utilization_impl.rpt]
report_utilization -hierarchical -hierarchical_depth 6 -file [file join $report_dir utilization_hierarchical_impl.rpt]
report_ram_utilization -include_lutram -file [file join $report_dir ram_utilization_impl.rpt] -csv [file join $report_dir ram_utilization_impl.csv]
report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose -max_paths 20 -file [file join $report_dir timing_summary_impl.rpt]
report_timing -delay_type max -max_paths 20 -nworst 20 -path_type full_clock_expanded -file [file join $report_dir setup_paths_impl.rpt]
report_timing -delay_type min -max_paths 20 -nworst 20 -path_type full_clock_expanded -file [file join $report_dir hold_paths_impl.rpt]
report_route_status -file [file join $report_dir route_status_impl.rpt]
report_methodology -file [file join $report_dir methodology_impl.rpt]
report_drc -file [file join $report_dir drc_impl.rpt]
report_clocks -file [file join $report_dir clocks_impl.rpt]
write_checkpoint -force [file join $artifact_dir neuromorphic_twin_m11_6_routed.dcp]
write_debug_probes -force [file join $artifact_dir neuromorphic_twin_m11_6.ltx]

set worst_setup [get_timing_paths -quiet -delay_type max -max_paths 1 -nworst 1]
set worst_hold [get_timing_paths -quiet -delay_type min -max_paths 1 -nworst 1]
if {[llength $worst_setup] != 1 || [llength $worst_hold] != 1} {
    error "M11.6 could not obtain routed setup/hold timing paths."
}
set wns [get_property SLACK [lindex $worst_setup 0]]
set whs [get_property SLACK [lindex $worst_hold 0]]
puts "M11.6 routed worst setup slack: $wns ns"
puts "M11.6 routed worst hold slack: $whs ns"
if {$wns < 0.0 || $whs < 0.0} {
    error "M11.6 routed timing failed: WNS=$wns ns WHS=$whs ns"
}
puts "M11.6 routed timing check passed: WNS=$wns ns, WHS=$whs ns"

set drc_errors [get_drc_violations -quiet -filter {SEVERITY == Error}]
if {[llength $drc_errors] != 0} {
    error "M11.6 implemented design has DRC errors: $drc_errors"
}

set impl_dir [get_property DIRECTORY [get_runs impl_1]]
set bit_files [glob -nocomplain -directory $impl_dir *.bit]
if {[llength $bit_files] != 1} {
    error "M11.6 expected exactly one generated .bit file in $impl_dir, found: $bit_files"
}
set bit_src [lindex $bit_files 0]
set bit_dst [file join $artifact_dir neuromorphic_twin_m11_6.bit]
file copy -force $bit_src $bit_dst

# Preserve a hardware handoff containing the PS configuration and generated
# bitstream. The board smoke still programs the .bit directly through Vivado.
write_hw_platform -fixed -include_bit -force -file [file join $artifact_dir neuromorphic_twin_m11_6.xsa]

if {![file exists $bit_dst]} {
    error "M11.6 bitstream copy was not created: $bit_dst"
}
puts "M11.6 bitstream generated successfully."
puts "Bitstream: $bit_dst"
puts "Debug probes: [file join $artifact_dir neuromorphic_twin_m11_6.ltx]"
puts "Hardware handoff: [file join $artifact_dir neuromorphic_twin_m11_6.xsa]"
puts "Reports: $report_dir"
close_project
