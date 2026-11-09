# M05.12d.2a K26 PS/PL INTERFACE DISCOVERY ONLY.
# Offline in-memory IP catalog; NO PS CONFIG/PRESET, PS/DDR/board/addresses.
# Report precisely what the local Vivado 2025.2 PS IP exposes by DEFAULT.
if {[llength $argv] != 1} {error "usage: <original-catalog-report-path>"}
set report_path [lindex $argv 0]
set part xck26-sfvc784-2LV-c
create_project -in_memory -part $part
set_property source_mgmt_mode All [current_project]
set defs [get_ipdefs -all -quiet xilinx.com:ip:zynq_ultra_ps_e:*]
if {[llength $defs] < 1} {
    error "Zynq UltraScale+ processing system IP is absent from K26 Vivado catalog"
}
set def [lindex [lsort -dictionary $defs] end]
set vlnv [get_property VLNV $def]
if {![string match "xilinx.com:ip:zynq_ultra_ps_e:*" $vlnv]} {
    error "unexpected PS IP definition '$vlnv'"
}
create_bd_design m05_12d2a_ps_catalog_only
set cell [create_bd_cell -type ip -vlnv $vlnv ps_catalog]
if {[llength $cell] != 1} {error "cannot instantiate offline PS IP catalog"}
set report [list "META|part|$part" "META|vlnv|$vlnv" "META|scope|UNCONNECTED_PS_CATALOG_DEFAULTS_NO_PRESET_DDR" "META|source_mgmt_mode|[get_property source_mgmt_mode [current_project]]"]
# These are PS->PL control masters and PL->PS DDR access slave ports.
# 0 means NOT PRESENT WITH DEFAULT CONFIG, not absent from silicon.
foreach {name direction} {
    M_AXI_HPM0_FPD MASTER
    M_AXI_HPM1_FPD MASTER
    M_AXI_HPM0_LPD MASTER
    S_AXI_HP0_FPD SLAVE
    S_AXI_HP1_FPD SLAVE
    S_AXI_HP2_FPD SLAVE
    S_AXI_HP3_FPD SLAVE
    S_AXI_HPC0_FPD SLAVE
    S_AXI_HPC1_FPD SLAVE
    S_AXI_LPD SLAVE
    S_AXI_ACP_FPD SLAVE
    S_AXI_ACE_FPD SLAVE
} {
    set pins [get_bd_intf_pins -quiet "ps_catalog/$name"]
    if {[llength $pins] > 1} {error "ambiguous PS interface $name"}
    set active [expr {[llength $pins] == 1 ? 1 : 0}]
    set actual NA
    if {$active} {
        set actual [string toupper [string trim [get_property MODE [lindex $pins 0]]]]
        if {$actual ne $direction} {
            error "PS interface $name has mode '$actual', expected '$direction'"
        }
    }
    lappend report "IF|$name|$active|$actual"
}
# Clock/reset/interrupt pins are inventory only: no frequency or tieoffs.
foreach {name direction} {
    pl_clk0 O
    pl_resetn0 O
    pl_ps_irq0 I
    maxihpm0_fpd_aclk I
    maxihpm1_fpd_aclk I
    saxihp0_fpd_aclk I
    saxihpc0_fpd_aclk I
} {
    set pins [get_bd_pins -quiet "ps_catalog/$name"]
    if {[llength $pins] > 1} {error "ambiguous PS clock/irq pin $name"}
    set active [expr {[llength $pins] == 1 ? 1 : 0}]
    set actual NA
    if {$active} {
        set actual [string toupper [string trim [get_property DIR [lindex $pins 0]]]]
        if {$actual ne $direction} {
            error "unexpected PS pin direction for $name: '$actual' versus '$direction'"
        }
    }
    lappend report "PIN|$name|$active|$actual"
}
# Do NOT assume property names are valid for this Vivado version. Record if
# absent and require separate explicit documented config for later design.
foreach prop {
    CONFIG.PCW_USE_M_AXI_GP0
    CONFIG.PCW_USE_M_AXI_GP1
    CONFIG.PCW_USE_S_AXI_HP0
    CONFIG.PCW_USE_S_AXI_HP1
    CONFIG.PCW_USE_S_AXI_HPC0
    CONFIG.PCW_USE_S_AXI_HPC1
    CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ
    CONFIG.PCW_EN_CLK0_PORT
    CONFIG.PCW_USE_FABRIC_INTERRUPT
} {
    set value UNAVAILABLE
    if {[lsearch -exact [list_property $cell] $prop] >= 0} {
        set value [string trim [get_property $prop $cell]]
        if {$value eq ""} {set value EMPTY}
        # Serialized values must not break the independently audited framing.
        set value [string map [list "|" "%7C" "\n" "%0A" "\r" "%0D"] $value]
    }
    lappend report "PROP|[string range $prop 7 end]|$value"
}
set f [open $report_path w]
foreach line $report {puts $f $line}
close $f
close_project
puts "PASS: M05.12d.2a original offline K26 PS IP inventory (CATALOG ONLY, NO PRESET/DDR)"
