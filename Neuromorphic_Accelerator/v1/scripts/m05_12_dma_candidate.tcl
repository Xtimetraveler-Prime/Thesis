# M05.12c OFFLINE four-channel AXI DMA IP candidate (no PS, DDR, board or wiring).
if {[llength $argv] != 1} {error "expected output report"}
set out [lindex $argv 0]
set part xck26-sfvc784-2LV-c
set vlnv xilinx.com:ip:axi_dma:7.1
create_project -in_memory -part $part
if {[llength [get_ipdefs -all -quiet $vlnv]] != 1} {error "expected exactly one AXI DMA 7.1 definition"}
create_bd_design m05_12c_unconnected_candidate
set result [list "META|part|$part" "META|vlnv|$vlnv" "META|scope|UNCONNECTED_OFFLINE_CANDIDATE_NO_PS_DDR"]
foreach {name role} {dma_neurons MM2S dma_synapses MM2S dma_external MM2S dma_trace S2MM} {
    set cell [create_bd_cell -type ip -vlnv $vlnv $name]
    set cfg [list CONFIG.c_include_sg 0 CONFIG.c_sg_length_width 24 CONFIG.c_addr_width 32 CONFIG.c_micro_dma 0 CONFIG.c_include_mm2s_dre 0 CONFIG.c_include_s2mm_dre 0]
    if {$role eq "MM2S"} {
        set cfg [concat $cfg [list CONFIG.c_include_mm2s 1 CONFIG.c_include_s2mm 0 CONFIG.c_m_axi_mm2s_data_width 256 CONFIG.c_m_axis_mm2s_tdata_width 256]]
    } else {
        set cfg [concat $cfg [list CONFIG.c_include_mm2s 0 CONFIG.c_include_s2mm 1 CONFIG.c_m_axi_s2mm_data_width 256 CONFIG.c_s_axis_s2mm_tdata_width 256]]
    }
    set_property -dict $cfg $cell
    lappend result "CELL|$name|$role"
    # c_prmry_is_aclk_async is READ-ONLY in Vivado 2025.2 AXI DMA v7.1.
    # Do not set it: original owner run emitted four BD 41-737 CRITICAL WARNINGs.
    # Still require and record its ACTUAL value 0; never waive async check.
    foreach {key wanted} [concat $cfg [list CONFIG.c_prmry_is_aclk_async 0]] {
        if {[lsearch -exact [list_property $cell] $key] < 0} {error "$name missing IP property $key"}
        set actual [string trim [get_property $key $cell]]
        if {$actual ne "$wanted"} {error "$name IP readback $key=$actual expected=$wanted"}
        set short [string range $key 7 end]
        lappend result "CFG|$name|$short|$actual"
    }
    foreach pin {M_AXIS_MM2S S_AXIS_S2MM M_AXI_MM2S M_AXI_S2MM S_AXI_LITE} {
        set present [expr {[llength [get_bd_intf_pins -quiet "$name/$pin"]] > 0 ? 1 : 0}]
        set expected [expr {$pin eq "S_AXI_LITE" || ($role eq "MM2S" && $pin in {M_AXIS_MM2S M_AXI_MM2S}) || ($role eq "S2MM" && $pin in {S_AXIS_S2MM M_AXI_S2MM})}]
        if {$present != $expected} {error "$name $pin presence=$present expected=$expected"}
        lappend result "PIN|$name|$pin|$present"
    }
}
set f [open $out w]
foreach item $result {puts $f $item}
close $f
close_project
puts "PASS: M05.12c four AXI DMA configurations read back (UNCONNECTED, no PS/DDR/board)"
