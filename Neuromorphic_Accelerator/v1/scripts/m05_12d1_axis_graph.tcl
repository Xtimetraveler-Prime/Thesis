# M05.12d.1 OFFLINE PL STREAM-ONLY CONNECTED BD.
# Four genuine AXI DMA v7.1 IP stream interfaces are connected to
# the UNMODIFIED M05.11 transport through an annotated RTL module reference.
# Memory master interfaces, AXI-Lite controls, HLS, clocks, resets,
# PS, DDR, interrupts, physical buffers and address mapping UNCONNECTED.
if {[llength $argv] != 2} {error "usage: <v1-root> <report-path>"}
set root [lindex $argv 0]
set report_path [lindex $argv 1]
set part xck26-sfvc784-2LV-c
set vlnv xilinx.com:ip:axi_dma:7.1
create_project -in_memory -part $part
if {[llength [get_ipdefs -all -quiet $vlnv]] != 1} {
    error "K26 Vivado IP AXI DMA v7.1 not available"
}
foreach file {
    rtl/m05_11/m05_11_axil_session_controller.v
    rtl/m05_11/m05_trace_dma_packetizer.v
    rtl/m05_11/m05_ingress_dma_unpad.v
    rtl/m05_11/m05_11_stream_shell.v
    rtl/m05_12/m05_12d_axis_shell_ref.v
} {
    set src [file join $root $file]
    if {![file exists $src]} {error "missing source for BD module reference: $file"}
    add_files -norecurse $src
}
update_compile_order -fileset sources_1
create_bd_design m05_12d1_pl_stream_only
set refcell [create_bd_cell -type module -reference m05_12d_axis_shell_ref shell]
if {[llength $refcell] != 1} {error "RTL module reference failed"}
set report [list "META|part|$part" "META|vlnv|$vlnv" "META|scope|CONNECTED_PL_AXIS_ONLY_NO_HLS_PS_DDR" "CELL|shell|m05_12d_axis_shell_ref"]
foreach {name role} {
    dma_neurons MM2S dma_synapses MM2S dma_external MM2S dma_trace S2MM
} {
    set cell [create_bd_cell -type ip -vlnv $vlnv $name]
    set cfg [list CONFIG.c_include_sg 0 CONFIG.c_sg_length_width 24 CONFIG.c_addr_width 32 CONFIG.c_micro_dma 0 CONFIG.c_include_mm2s_dre 0 CONFIG.c_include_s2mm_dre 0]
    if {$role eq "MM2S"} {
        set cfg [concat $cfg [list CONFIG.c_include_mm2s 1 CONFIG.c_include_s2mm 0 CONFIG.c_m_axi_mm2s_data_width 256 CONFIG.c_m_axis_mm2s_tdata_width 256]]
    } else {
        set cfg [concat $cfg [list CONFIG.c_include_mm2s 0 CONFIG.c_include_s2mm 1 CONFIG.c_m_axi_s2mm_data_width 256 CONFIG.c_s_axis_s2mm_tdata_width 256]]
    }
    # Read-only async clock field is verified but NEVER written.
    set_property -dict $cfg $cell
    lappend report "CELL|$name|$role"
    foreach {key expected} [concat $cfg [list CONFIG.c_prmry_is_aclk_async 0]] {
        if {[lsearch -exact [list_property $cell] $key] < 0} {
            error "$name missing DMA configuration property $key"
        }
        set actual [string trim [get_property $key $cell]]
        if {$actual ne "$expected"} {
            error "$name $key readback '$actual' expected '$expected'"
        }
        lappend report "CFG|$name|[string range $key 7 end]|$actual"
    }
}
foreach {dma dma_if shell_if} {
    dma_neurons M_AXIS_MM2S S_AXIS_NEURONS
    dma_synapses M_AXIS_MM2S S_AXIS_SYNAPSES
    dma_external M_AXIS_MM2S S_AXIS_EXTERNAL
    dma_trace S_AXIS_S2MM M_AXIS_TRACE
} {
    set dma_pin [get_bd_intf_pins -quiet "$dma/$dma_if"]
    set shell_pin [get_bd_intf_pins -quiet "shell/$shell_if"]
    if {[llength $dma_pin] != 1 || [llength $shell_pin] != 1} {
        error "$dma missing inferred AXIS interface shell/$shell_if"
    }
    connect_bd_intf_net $dma_pin $shell_pin
    set from [get_bd_intf_nets -of_objects $dma_pin]
    set to [get_bd_intf_nets -of_objects $shell_pin]
    if {[llength $from] != 1 || [llength $to] != 1} {
        error "$dma AXIS connection has no net after command"
    }
    set a [get_property NAME [lindex $from 0]]
    set b [get_property NAME [lindex $to 0]]
    if {$a ne $b} {error "$dma and shell/$shell_if are not on same AXIS net"}
    set members [get_bd_intf_pins -of_objects [lindex $from 0]]
    if {[llength $members] != 2} {error "$dma AXIS net is not point-to-point"}
    lappend report "LINK|$dma/$dma_if|shell/$shell_if|$a"
}
# Intentionally no validate_bd_design: many essential interfaces NOT wired.
# This is actual four AXIS NET connectivity only, not a runnable system.
set f [open $report_path w]
foreach line $report {puts $f $line}
close $f
close_project
puts "PASS: M05.12d.1 genuine offline DMA-to-shell four AXIS nets (PARTIAL PL BD, NO PS/DDR)"
