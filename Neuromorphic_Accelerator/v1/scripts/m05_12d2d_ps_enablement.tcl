# M05.12d.2d OFFLINE CONTROLLED K26 PS PORT ENABLEMENT PROBE.
# Uses ONLY proven-owner D2c Vivado 2025.2 PSU property names/readbacks.
# In-memory project, no board, no boot, no PS preset, no DDR, no AXI links.
if {[llength $argv] != 1} {error "usage: <original-enable-report-path>"}
set report_path [lindex $argv 0]
set part xck26-sfvc784-2LV-c
set vlnv xilinx.com:ip:zynq_ultra_ps_e:3.5
create_project -in_memory -part $part
set_property source_mgmt_mode All [current_project]
if {[llength [get_ipdefs -all -quiet $vlnv]] != 1} {
    error "expected genuine K26 Zynq UltraScale+ PS 3.5 IP absent"
}
create_bd_design m05_12d2d_ps_port_enablement_only
set ps [create_bd_cell -type ip -vlnv $vlnv ps_probe]
if {[llength $ps] != 1} {error "PS IP cell missing"}
set report [list "META|part|$part" "META|vlnv|$vlnv" \
    "META|source_mgmt_mode|[get_property source_mgmt_mode [current_project]]" \
    "META|scope|SCRATCH_PS_PORT_ENABLE_ONLY_NO_PRESET_DDR"]
# Previous genuine default K26 D2a/D2c proved these precise defaults.
foreach {key old_value} {
    PSU__USE__M_AXI_GP0 0
    PSU__USE__S_AXI_GP2 0
} {
    if {[lsearch -exact [list_property $ps] "CONFIG.$key"] < 0} {
        error "missing owner-discovered PS IP property CONFIG.$key"
    }
    set actual [string trim [get_property "CONFIG.$key" $ps]]
    if {$actual ne $old_value} {
        error "unexpected PS default CONFIG.$key='$actual' expected '$old_value'"
    }
    lappend report "DEFAULT|$key|$actual"
}
# Record exact default pin map. Only the LPD control master was originally on.
foreach {name expected} {
    M_AXI_HPM0_FPD 0
    S_AXI_HP0_FPD 0
    M_AXI_HPM0_LPD 1
} {
    set pins [get_bd_intf_pins -quiet "ps_probe/$name"]
    if {[llength $pins] != $expected} {error "unexpected default pin $name"}
    set mode NA
    if {$expected} {
        set mode [string toupper [string trim [get_property MODE [lindex $pins 0]]]]
        if {$mode ne "MASTER"} {error "LPD control port not MASTER"}
    }
    lappend report "BEFORE|$name|$expected|$mode"
}
# Only explicit scratch-cell writes; no PS board preset or automation.
set_property -dict [list \
    CONFIG.PSU__USE__M_AXI_GP0 1 \
    CONFIG.PSU__USE__S_AXI_GP2 1] $ps
foreach {key expected} {
    PSU__USE__M_AXI_GP0 1
    PSU__USE__S_AXI_GP2 1
    PSU__USE__M_AXI_GP2 1
} {
    set actual [string trim [get_property "CONFIG.$key" $ps]]
    if {$actual ne "$expected"} {
        error "PS property post-write readback $key='$actual' expected '$expected'"
    }
    lappend report "READBACK|$key|$actual"
}
# Directly require *REAL* mapped AXI pins, not just CONFIG property readback.
foreach {name role} {
    M_AXI_HPM0_FPD MASTER
    S_AXI_HP0_FPD SLAVE
    M_AXI_HPM0_LPD MASTER
} {
    set pins [get_bd_intf_pins -quiet "ps_probe/$name"]
    if {[llength $pins] != 1} {
        error "PS parameter toggled, but actual AXI interface $name not exposed"
    }
    set actual [string toupper [string trim [get_property MODE [lindex $pins 0]]]]
    if {$actual ne $role} {error "PS $name mode '$actual' expected '$role'"}
    lappend report "AFTER|$name|1|$actual"
}
# Clock/readout inventory only. A bare pin does NOT prove domain, frequency,
# reset sequencing, real PS DDR initialization, or a validated connected BD.
foreach {name direction} {
    pl_clk0 O
    pl_resetn0 O
    maxihpm0_fpd_aclk I
    saxihp0_fpd_aclk I
} {
    set pins [get_bd_pins -quiet "ps_probe/$name"]
    if {[llength $pins] != 1} {error "required clock/reset pin $name missing"}
    set actual [string toupper [string trim [get_property DIR [lindex $pins 0]]]]
    if {$actual ne $direction} {error "clock/reset pin $name has unexpected direction"}
    lappend report "PIN|$name|1|$actual"
}
foreach {key expected} {
    PSU__MAXIGP0__DATA_WIDTH 128
    PSU__SAXIGP2__DATA_WIDTH 128
} {
    set actual [string trim [get_property "CONFIG.$key" $ps]]
    if {$actual ne "$expected"} {
        error "expected 128-bit PS AXI port property $key, read '$actual'"
    }
    lappend report "WIDTH|$key|$actual"
}
foreach key {
    PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ
    PSU__CRL_APB__PL0_REF_CTRL__ACT_FREQMHZ
} {
    set actual [string trim [get_property "CONFIG.$key" $ps]]
    if {![string is double -strict $actual] || $actual <= 0} {
        error "invalid PS clock property $key='$actual'"
    }
    lappend report "CLOCKCFG|$key|$actual"
}
set f [open $report_path w]
foreach row $report {puts $f $row}
close $f
close_project
puts "PASS: M05.12d.2d offline PS HPM0_FPD and HP0_FPD actual pins enabled (NO PS PRESET/DDR/BOARD)"
