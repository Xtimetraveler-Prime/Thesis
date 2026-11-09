# M05.12b OFFLINE, IN-MEMORY Vivado catalog inspection for K26 part.
# NOT a connected PS/PL block design. No physical DMA datapath is tested.
if {[llength $argv] != 1} {
    error "One output capability-text path required"
}
set report_path [lindex $argv 0]
create_project -in_memory -part xck26-sfvc784-2LV-c
set dma_defs [get_ipdefs -all -quiet xilinx.com:ip:axi_dma:*]
if {[llength $dma_defs] == 0} {
    error "AXI DMA IP definition not available in this Vivado catalog"
}
set dma_def [lindex [lsort $dma_defs] end]
set dma_vlnv [get_property VLNV $dma_def]
create_bd_design m05_12_catalog_only
set probe [create_bd_cell -type ip -vlnv $dma_vlnv dma_catalog_probe]
set f [open $report_path w]
puts $f "PART=xck26-sfvc784-2LV-c"
puts $f "IP_VLNV=$dma_vlnv"
puts $f "STATUS=UNCONNECTED_IN_MEMORY_CATALOG_ONLY"
puts $f "REQUIRES=real_BD_interface_address_clock_reset_cache_review"
foreach name {
    CONFIG.c_include_sg
    CONFIG.c_include_mm2s
    CONFIG.c_include_s2mm
    CONFIG.c_m_axis_mm2s_tdata_width
    CONFIG.c_s_axis_s2mm_tdata_width
    CONFIG.c_m_axi_mm2s_data_width
    CONFIG.c_m_axi_s2mm_data_width
    CONFIG.c_sg_length_width
    CONFIG.c_addr_width
    CONFIG.c_prmry_is_aclk_async
    CONFIG.c_micro_dma
    CONFIG.c_include_mm2s_dre
    CONFIG.c_include_s2mm_dre
} {
    if {[lsearch -exact [list_property $probe] $name] < 0} {
        puts $f "$name=UNAVAILABLE_IN_THIS_PROBE"
    } else {
        puts $f "$name=[get_property $name $probe]"
    }
}
close $f
close_project
puts "PASS: M05.12 K26 Vivado AXI DMA IP catalog-only inspection"
