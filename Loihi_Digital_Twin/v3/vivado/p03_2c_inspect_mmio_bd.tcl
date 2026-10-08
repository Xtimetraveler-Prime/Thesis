# Inspect the realized P03.2 HPM0/MMIO address path in the existing Vivado project.
if {$argc != 1} {
    error "usage: p03_2c_inspect_mmio_bd.tcl <project_xpr>"
}
set xpr [file normalize [lindex $argv 0]]
if {![file exists $xpr]} { error "missing Vivado project: $xpr" }

open_project $xpr
open_bd_design [get_files *loihi_twin_v3_p03_mmio_impl.bd]

puts "P03_2C_BD_INSPECT_BEGIN"

set mmio_intf [get_bd_intf_pins p03_ps_control_regs_0/S_AXI]
set hpm0_intf [get_bd_intf_pins zynq_ultra_ps_e_0/M_AXI_HPM0_FPD]
set sc_m [get_bd_intf_pins p03_hpm0_smartconnect_0/M00_AXI]
set sc_s [get_bd_intf_pins p03_hpm0_smartconnect_0/S00_AXI]

foreach obj [list $hpm0_intf $sc_s $sc_m $mmio_intf] {
    puts "INTF=[get_property NAME $obj]"
    foreach prop {VLNV MODE CONFIG.PROTOCOL CONFIG.ADDR_WIDTH CONFIG.DATA_WIDTH} {
        set value ""
        catch {set value [get_property $prop $obj]}
        puts "  $prop=$value"
    }
}

foreach pin_name {
    zynq_ultra_ps_e_0/M_AXI_HPM0_FPD_ARADDR
    p03_hpm0_smartconnect_0/S00_AXI_araddr
    p03_hpm0_smartconnect_0/M00_AXI_araddr
    p03_ps_control_regs_0/s_axi_araddr
    zynq_ultra_ps_e_0/M_AXI_HPM0_FPD_AWADDR
    p03_hpm0_smartconnect_0/S00_AXI_awaddr
    p03_hpm0_smartconnect_0/M00_AXI_awaddr
    p03_ps_control_regs_0/s_axi_awaddr
} {
    set pin [get_bd_pins -quiet $pin_name]
    if {[llength $pin] == 1} {
        puts "PIN=$pin_name LEFT=[get_property LEFT $pin] RIGHT=[get_property RIGHT $pin]"
    } else {
        puts "PIN=$pin_name MISSING"
    }
}

puts "MMIO_SLAVE_SEGMENTS"
foreach seg [get_bd_addr_segs -quiet -of_objects $mmio_intf] {
    puts "SEG=$seg OFFSET=[get_property OFFSET $seg] RANGE=[get_property RANGE $seg]"
    foreach prop {ADDR_WIDTH MIN_SIZE USAGE} {
        set value ""
        catch {set value [get_property $prop $seg]}
        puts "  $prop=$value"
    }
}

puts "HPM0_MASTER_SEGMENTS"
foreach seg [get_bd_addr_segs -quiet -of_objects [get_bd_addr_spaces -quiet -of_objects $hpm0_intf]] {
    puts "SEG=$seg OFFSET=[get_property OFFSET $seg] RANGE=[get_property RANGE $seg]"
}

validate_bd_design
puts "P03_2C_BD_INSPECT_END"
close_project
