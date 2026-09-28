# P03 post-route implementation shell for one packaged loihi_core_v2_tick IP.
if {$argc != 7} {
    error "usage: create_p03_impl_project.tcl <ip_repo_dir> <project_dir> <target_part> <expected_vlnv> <monitor_rtl> <report_dir> <jobs>"
}

set ip_repo_dir [file normalize [lindex $argv 0]]
set project_dir [file normalize [lindex $argv 1]]
set target_part [lindex $argv 2]
set expected_vlnv [lindex $argv 3]
set monitor_rtl [file normalize [lindex $argv 4]]
set report_dir [file normalize [lindex $argv 5]]
set jobs [lindex $argv 6]

foreach path [list $ip_repo_dir $monitor_rtl] {
    if {![file exists $path]} { error "Required P03 input does not exist: $path" }
}
file mkdir $report_dir
file delete -force $project_dir
file mkdir $project_dir

set project_name "loihi_twin_v2_p03_impl"
set bd_name "loihi_twin_v2_p03_impl"
create_project $project_name $project_dir -part $target_part -force
set_property TARGET_LANGUAGE Verilog [current_project]
set_property SIMULATOR_LANGUAGE Mixed [current_project]

set kv260_board_parts [get_board_parts -quiet xilinx.com:kv260_som:part0:*]
if {[llength $kv260_board_parts] == 0} {
    error "P03 requires installed KV260 SOM board files (xilinx.com:kv260_som:part0:*)."
}
set kv260_board_part [lindex [lsort -dictionary $kv260_board_parts] end]
set_property BOARD_PART $kv260_board_part [current_project]
puts "P03 K26 SOM board preset: $kv260_board_part"

add_files -norecurse $monitor_rtl
set_property file_type Verilog [get_files $monitor_rtl]
update_compile_order -fileset sources_1

set_property IP_REPO_PATHS [list $ip_repo_dir] [current_fileset]
update_ip_catalog -rebuild
if {[llength [get_ipdefs -all $expected_vlnv]] == 0} {
    error "Expected P03 HLS IP was not found in catalog: $expected_vlnv"
}
foreach required_ip {
    xilinx.com:ip:zynq_ultra_ps_e:3.5
    xilinx.com:ip:vio:3.0
    xilinx.com:ip:proc_sys_reset:5.0
    xilinx.com:ip:xlconstant:1.1
    xilinx.com:ip:blk_mem_gen:8.4
} {
    if {[llength [get_ipdefs -all $required_ip]] == 0} {
        error "Required Vivado IP was not found: $required_ip"
    }
}

proc connect_named_pair {net_name left right} {
    set lp [get_bd_pins -quiet $left]
    set rp [get_bd_pins -quiet $right]
    if {[llength $lp] != 1 || [llength $rp] != 1} {
        error "Missing P03 pin for $net_name: left=$lp right=$rp"
    }
    set net [create_bd_net $net_name]
    connect_bd_net -net $net $lp $rp
}

proc connect_named_triple {net_name first second third} {
    set p0 [get_bd_pins -quiet $first]
    set p1 [get_bd_pins -quiet $second]
    set p2 [get_bd_pins -quiet $third]
    if {[llength $p0] != 1 || [llength $p1] != 1 || [llength $p2] != 1} {
        error "Missing P03 pin for $net_name: first=$p0 second=$p1 third=$p2"
    }
    set net [create_bd_net $net_name]
    connect_bd_net -net $net $p0 $p1 $p2
}

proc first_bd_pin {cell candidates} {
    foreach suffix $candidates {
        set pin [get_bd_pins -quiet ${cell}/${suffix}]
        if {[llength $pin] == 1} {
            return $pin
        }
    }
    return ""
}

proc hls_memory_pin {hls_name arg_name role required} {
    switch -- $role {
        address {
            set candidates [list \
                ${arg_name}_address0 \
                ${arg_name}_address \
                ${arg_name}_Addr_A]
        }
        ce {
            set candidates [list \
                ${arg_name}_ce0 \
                ${arg_name}_ce \
                ${arg_name}_EN_A]
        }
        we {
            set candidates [list \
                ${arg_name}_we0 \
                ${arg_name}_we \
                ${arg_name}_WEN_A]
        }
        din {
            set candidates [list \
                ${arg_name}_d0 \
                ${arg_name}_d \
                ${arg_name}_Din_A]
        }
        dout {
            set candidates [list \
                ${arg_name}_q0 \
                ${arg_name}_q \
                ${arg_name}_Dout_A]
        }
        default {
            error "Unknown P03 HLS memory-pin role: $role"
        }
    }
    set pin [first_bd_pin $hls_name $candidates]
    if {$required && $pin eq ""} {
        puts "Available HLS pins for $arg_name: [get_bd_pins -quiet ${hls_name}/${arg_name}_*]"
        error "Required P03 HLS $role pin not found for ${hls_name}/${arg_name}"
    }
    return $pin
}

proc connect_hls_memory_native {hls_name arg_name depth width clock_pin zero_pin} {
    # P03 uses ap_memory at the HLS boundary.  Unlike the grouped HLS bram
    # interface, ap_memory presents word-addressed discrete signals.  Those
    # signals map directly to a native single-port Block Memory Generator and
    # therefore avoid IP-Integrator MEM_SIZE/READ_LATENCY metadata conflicts.
    set address [hls_memory_pin $hls_name $arg_name address 1]
    set ce [hls_memory_pin $hls_name $arg_name ce 1]
    set we [hls_memory_pin $hls_name $arg_name we 0]
    set din [hls_memory_pin $hls_name $arg_name din 0]
    set dout [hls_memory_pin $hls_name $arg_name dout 0]

    set mem [create_bd_cell -type ip -vlnv xilinx.com:ip:blk_mem_gen:8.4 ${arg_name}_mem]
    set_property -dict [list \
        CONFIG.Memory_Type {Single_Port_RAM} \
        CONFIG.Write_Width_A $width \
        CONFIG.Read_Width_A $width \
        CONFIG.Write_Depth_A $depth] $mem

    set clka [get_bd_pins -quiet ${arg_name}_mem/clka]
    set addra [get_bd_pins -quiet ${arg_name}_mem/addra]
    set ena [get_bd_pins -quiet ${arg_name}_mem/ena]
    set wea [get_bd_pins -quiet ${arg_name}_mem/wea]
    set bmg_din [get_bd_pins -quiet ${arg_name}_mem/dina]
    set bmg_dout [get_bd_pins -quiet ${arg_name}_mem/douta]

    if {[llength $clka] != 1 || [llength $addra] != 1 || [llength $wea] != 1} {
        puts "Available BMG pins for $arg_name: [get_bd_pins -quiet ${arg_name}_mem/*]"
        error "Required native BMG pins missing for ${arg_name}_mem"
    }

    connect_bd_net $clock_pin $clka
    connect_bd_net $address $addra
    if {[llength $ena] == 1} {
        connect_bd_net $ce $ena
    }

    if {$we ne ""} {
        if {$din eq "" || [llength $bmg_din] != 1} {
            error "P03 write-enabled memory $arg_name is missing a data-input pin"
        }
        connect_bd_net $we $wea
        connect_bd_net $din $bmg_din
    } else {
        connect_bd_net $zero_pin $wea
    }

    if {$dout ne ""} {
        if {[llength $bmg_dout] != 1} {
            error "P03 readable memory $arg_name is missing BMG douta"
        }
        connect_bd_net $bmg_dout $dout
    }

    puts "P03 native memory: $arg_name depth=$depth width=$width hls_address=$address hls_ce=$ce hls_we=$we hls_din=$din hls_dout=$dout"
}

create_bd_design $bd_name
set ps [create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e:3.5 zynq_ultra_ps_e_0]
apply_bd_automation -rule xilinx.com:bd_rule:zynq_ultra_ps_e -config {apply_board_preset "1"} $ps
set_property -dict [list \
    CONFIG.PSU__USE__M_AXI_GP0 {0} \
    CONFIG.PSU__USE__M_AXI_GP1 {0} \
    CONFIG.PSU__USE__M_AXI_GP2 {0} \
    CONFIG.PSU__FPGA_PL0_ENABLE {1} \
    CONFIG.PSU__USE__FABRIC__RST {0} \
    CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {100}] $ps

set hls [create_bd_cell -type ip -vlnv $expected_vlnv loihi_core_v2_tick_0]
set monitor [create_bd_cell -type module -reference p03_run_monitor p03_run_monitor_0]
set vio [create_bd_cell -type ip -vlnv xilinx.com:ip:vio:3.0 vio_p03]
set_property -dict [list \
    CONFIG.C_NUM_PROBE_IN {10} \
    CONFIG.C_NUM_PROBE_OUT {7} \
    CONFIG.C_PROBE_IN0_WIDTH {1} \
    CONFIG.C_PROBE_IN1_WIDTH {1} \
    CONFIG.C_PROBE_IN2_WIDTH {1} \
    CONFIG.C_PROBE_IN3_WIDTH {11} \
    CONFIG.C_PROBE_IN4_WIDTH {13} \
    CONFIG.C_PROBE_IN5_WIDTH {32} \
    CONFIG.C_PROBE_IN6_WIDTH {1} \
    CONFIG.C_PROBE_IN7_WIDTH {1} \
    CONFIG.C_PROBE_IN8_WIDTH {64} \
    CONFIG.C_PROBE_IN9_WIDTH {32} \
    CONFIG.C_NUM_PROBE_OUT {7} \
    CONFIG.C_PROBE_OUT0_WIDTH {1} CONFIG.C_PROBE_OUT0_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT1_WIDTH {1} CONFIG.C_PROBE_OUT1_INIT_VAL {0x0} \
    CONFIG.C_PROBE_OUT2_WIDTH {11} CONFIG.C_PROBE_OUT2_INIT_VAL {0x003} \
    CONFIG.C_PROBE_OUT3_WIDTH {13} CONFIG.C_PROBE_OUT3_INIT_VAL {0x001} \
    CONFIG.C_PROBE_OUT4_WIDTH {16} CONFIG.C_PROBE_OUT4_INIT_VAL {0x0003} \
    CONFIG.C_PROBE_OUT5_WIDTH {13} CONFIG.C_PROBE_OUT5_INIT_VAL {0x003} \
    CONFIG.C_PROBE_OUT6_WIDTH {32} CONFIG.C_PROBE_OUT6_INIT_VAL {0x00000000}] $vio

set rst [create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 proc_sys_reset_p03]
set one [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_one_p03]
set_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {1}] $one
set zero [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_zero_p03]
set_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {0}] $zero

set pl_clk_pin [get_bd_pins zynq_ultra_ps_e_0/pl_clk0]
set zero_pin [get_bd_pins const_zero_p03/dout]

connect_bd_net $pl_clk_pin \
    [get_bd_pins loihi_core_v2_tick_0/ap_clk] \
    [get_bd_pins p03_run_monitor_0/ap_clk] \
    [get_bd_pins vio_p03/clk] \
    [get_bd_pins proc_sys_reset_p03/slowest_sync_clk]
connect_named_pair p03_reset_command vio_p03/probe_out1 proc_sys_reset_p03/ext_reset_in
connect_bd_net [get_bd_pins const_one_p03/dout] \
    [get_bd_pins proc_sys_reset_p03/dcm_locked] \
    [get_bd_pins proc_sys_reset_p03/aux_reset_in]
connect_bd_net $zero_pin [get_bd_pins proc_sys_reset_p03/mb_debug_sys_rst]
connect_bd_net [get_bd_pins proc_sys_reset_p03/peripheral_reset] [get_bd_pins loihi_core_v2_tick_0/ap_rst]
connect_bd_net [get_bd_pins proc_sys_reset_p03/peripheral_aresetn] [get_bd_pins p03_run_monitor_0/resetn]

# One named net per HLS transaction event. The monitor observes the same start
# and done signals as the HLS IP; no secondary net may share either pin.
connect_named_triple p03_start \
    vio_p03/probe_out0 \
    loihi_core_v2_tick_0/ap_start \
    p03_run_monitor_0/start
connect_named_triple p03_done \
    loihi_core_v2_tick_0/ap_done \
    p03_run_monitor_0/done \
    vio_p03/probe_in0

connect_named_pair p03_compartment_count vio_p03/probe_out2 loihi_core_v2_tick_0/compartment_count
connect_named_pair p03_event_count vio_p03/probe_out3 loihi_core_v2_tick_0/event_count
connect_named_pair p03_synapse_count vio_p03/probe_out4 loihi_core_v2_tick_0/synapse_count
connect_named_pair p03_route_count vio_p03/probe_out5 loihi_core_v2_tick_0/route_count
connect_named_pair p03_timestep vio_p03/probe_out6 loihi_core_v2_tick_0/timestep

connect_named_pair p03_idle loihi_core_v2_tick_0/ap_idle vio_p03/probe_in1
connect_named_pair p03_ready loihi_core_v2_tick_0/ap_ready vio_p03/probe_in2
connect_named_pair p03_spike_count loihi_core_v2_tick_0/spike_count vio_p03/probe_in3
connect_named_pair p03_packet_count loihi_core_v2_tick_0/packet_count vio_p03/probe_in4
connect_named_pair p03_status_flags loihi_core_v2_tick_0/status_flags vio_p03/probe_in5
connect_named_pair p03_monitor_busy p03_run_monitor_0/busy vio_p03/probe_in6
connect_named_pair p03_start_seen p03_run_monitor_0/start_seen vio_p03/probe_in7
connect_named_pair p03_last_run_cycles p03_run_monitor_0/last_run_cycles vio_p03/probe_in8
connect_named_pair p03_heartbeat p03_run_monitor_0/heartbeat vio_p03/probe_in9

# Full transparent one-core memory boundary.  ap_memory gives word-addressed
# discrete HLS pins, which are connected directly to native BMG pins.
connect_hls_memory_native loihi_core_v2_tick_0 config_words 1024 128 $pl_clk_pin $zero_pin
connect_hls_memory_native loihi_core_v2_tick_0 state_words 1024 64 $pl_clk_pin $zero_pin
connect_hls_memory_native loihi_core_v2_tick_0 axon_words 4096 64 $pl_clk_pin $zero_pin
connect_hls_memory_native loihi_core_v2_tick_0 synapse_words 32768 64 $pl_clk_pin $zero_pin
connect_hls_memory_native loihi_core_v2_tick_0 route_desc_words 1024 32 $pl_clk_pin $zero_pin
connect_hls_memory_native loihi_core_v2_tick_0 route_words 4096 32 $pl_clk_pin $zero_pin
connect_hls_memory_native loihi_core_v2_tick_0 input_events 4096 32 $pl_clk_pin $zero_pin
connect_hls_memory_native loihi_core_v2_tick_0 trace_words 1024 256 $pl_clk_pin $zero_pin
connect_hls_memory_native loihi_core_v2_tick_0 packet_words 4096 64 $pl_clk_pin $zero_pin

validate_bd_design

foreach arg_name {
    config_words state_words axon_words synapse_words route_desc_words
    route_words input_events trace_words packet_words
} {
    set mem [get_bd_cells ${arg_name}_mem]
    puts "P03 resolved native memory: $arg_name write_width=[get_property CONFIG.Write_Width_A $mem] read_width=[get_property CONFIG.Read_Width_A $mem] depth=[get_property CONFIG.Write_Depth_A $mem]"
}

save_bd_design
puts "P03 implementation block design validated successfully."

set bd_file [lindex [get_files -quiet */${bd_name}.bd] 0]
if {$bd_file eq ""} { error "P03 block design file was not found" }
generate_target all $bd_file
set wrapper_files [make_wrapper -files $bd_file -top]
if {[llength $wrapper_files] == 0} { error "P03 Vivado wrapper generation failed" }
add_files -norecurse $wrapper_files
set_property top ${bd_name}_wrapper [current_fileset]
update_compile_order -fileset sources_1

set_property STEPS.PHYS_OPT_DESIGN.IS_ENABLED true [get_runs impl_1]
launch_runs impl_1 -to_step route_design -jobs $jobs
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {
    error "P03 implementation did not complete: [get_property STATUS [get_runs impl_1]]"
}
open_run impl_1

report_timing_summary -delay_type min_max -max_paths 20 -report_unconstrained \
    -file [file join $report_dir timing_summary_post_route.rpt]
report_utilization -file [file join $report_dir utilization_post_route.rpt]
report_utilization -hierarchical -hierarchical_depth 4 \
    -file [file join $report_dir utilization_hierarchical_post_route.rpt]
report_clock_utilization -file [file join $report_dir clock_utilization_post_route.rpt]
report_drc -file [file join $report_dir drc_post_route.rpt]
report_methodology -file [file join $report_dir methodology_post_route.rpt]
write_checkpoint -force [file join $report_dir p03_post_route.dcp]

# Use the same routed timing-path queries that were proven in the v1 K26 flow.
set setup_paths [get_timing_paths -quiet -delay_type max -max_paths 1 -nworst 1]
set hold_paths [get_timing_paths -quiet -delay_type min -max_paths 1 -nworst 1]
set metrics [open [file join $report_dir p03_post_route_metrics.txt] w]
if {[llength $setup_paths] > 0} {
    set wns [get_property SLACK [lindex $setup_paths 0]]
    puts $metrics "wns_ns=$wns"
    puts "P03_POST_ROUTE_WNS_NS=$wns"
} else {
    puts $metrics "wns_ns=NA"
    puts "P03_POST_ROUTE_WNS_NS=NA"
}
if {[llength $hold_paths] > 0} {
    set whs [get_property SLACK [lindex $hold_paths 0]]
    puts $metrics "whs_ns=$whs"
    puts "P03_POST_ROUTE_WHS_NS=$whs"
} else {
    puts $metrics "whs_ns=NA"
    puts "P03_POST_ROUTE_WHS_NS=NA"
}
puts $metrics "target_part=$target_part"
puts $metrics "board_part=$kv260_board_part"
puts $metrics "pl_clock_requested_mhz=100"
close $metrics

puts "P03 routed implementation completed successfully."
puts "P03 reports: $report_dir"
