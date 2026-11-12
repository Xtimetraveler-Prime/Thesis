# M08 D3.1 VERSIONED PASSIVE KV260 BD CANDIDATE. OFFLINE VIVADO 2025.2 ONLY.
#
# SECURITY CONTRACT:
# - NO PS->PL AXI master is exposed. NO SmartConnect, identity, page or UIO.
# - PS TTC0 EMIO waveout channel 2 -> slice -> M08_FAN_PWM/A12 (source continuity).
# - PS pl_clk0 is REQUESTED at 100MHz, not proved alive under Linux.
# - Does NOT create, package, or program .bit/.bit.bin, DTBO or kernel changes.
# - Does NOT assert physical fan continuity, recovery, timeout or MMIO safety.
# - Never source the original HPM0->AXI candidate; independent design.
#
# This is ONLY the D3.1 scaffold. D3.2 protected AXI requires reviewed
# PS ATB4/clock/AFI/isolation/driver lifecycle and separate owner approval.
if {[llength $argv] != 2} {
    error "usage: m08_d3a_passive_fan_bd_candidate.tcl <v1-root> <NEW-empty-evidence-dir>"
}
set root [file normalize [lindex $argv 0]]
set evidence [file normalize [lindex $argv 1]]
if {![file isdirectory $root] || ![file isdirectory $evidence]} {
    error "M08 D3A requires existing first-party root and new evidence directory"
}
if {[llength [glob -nocomplain -directory $evidence * .*]] != 0} {
    error "M08 D3A evidence directory must be NEW and empty, never originals"
}
if {![string match "2025.2*" [version -short]]} {
    error "M08 D3A requires genuine local Vivado 2025.2"
}
set part xck26-sfvc784-2LV-c
set project_dir [file join $evidence d3a_project]
set report [file join $evidence 10_d3a_passive_bd_readback.txt]
set exported [file join $evidence 11_d3a_passive_bd_export.tcl]
set fan_xdc [file join $evidence 12_d3a_fan_a12.xdc]
foreach file [list $project_dir $report $exported $fan_xdc] {
    if {[file exists $file]} {error "M08 D3A output would replace an original: $file"}
}
set ps_vlnv xilinx.com:ip:zynq_ultra_ps_e:3.5
set slice_vlnv xilinx.com:ip:xlslice:1.0
create_project m08_d3a_passive_fan $project_dir -part $part
if {[get_property PART [current_project]] ne $part} {
    error "M08 D3A KV260 part mismatch"
}
set kv260_parts [get_board_parts -quiet xilinx.com:kv260_som:part0:*]
if {[llength $kv260_parts] == 0} {
    error "M08 D3A KV260 SOM board preset missing; NO part-only fallback"
}
set board [lindex [lsort -dictionary $kv260_parts] end]
set_property BOARD_PART $board [current_project]
if {[get_property BOARD_PART [current_project]] ne $board} {
    error "M08 D3A failed to apply KV260 board part"
}
foreach ip [list $ps_vlnv $slice_vlnv] {
    if {[llength [get_ipdefs -all -quiet $ip]] != 1} {
        error "M08 D3A required genuine Vivado IP missing: $ip"
    }
}
create_bd_design m08_d3a_passive_fan
set ps [create_bd_cell -type ip -vlnv $ps_vlnv ps]
apply_bd_automation -rule xilinx.com:bd_rule:zynq_ultra_ps_e \
    -config {apply_board_preset "1"} $ps

# Disable ALL PS->PL AXI masters; do not rely on unconnected HPM outputs.
# Keep the PS PL0 clock configuration visible for later native comparison.
set_property -dict [list \
    CONFIG.PSU__USE__M_AXI_GP0 0 \
    CONFIG.PSU__USE__M_AXI_GP1 0 \
    CONFIG.PSU__USE__M_AXI_GP2 0 \
    CONFIG.PSU__FPGA_PL0_ENABLE 1 \
    CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ 100] $ps
foreach prop {
    CONFIG.PSU__USE__M_AXI_GP0
    CONFIG.PSU__USE__M_AXI_GP1
    CONFIG.PSU__USE__M_AXI_GP2
} {
    if {[string trim [get_property $prop $ps]] ne "0"} {
        error "M08 D3A fail-closed PS->PL master disable rejected for $prop"
    }
}
foreach iface {
    ps/M_AXI_HPM0_FPD ps/M_AXI_HPM1_FPD ps/M_AXI_HPM0_LPD
} {
    if {[llength [get_bd_intf_pins -quiet $iface]] != 0} {
        error "M08 D3A unexpected PS->PL AXI master exposed: $iface"
    }
}
foreach clockpin {
    ps/maxihpm0_fpd_aclk ps/maxihpm1_fpd_aclk ps/maxihpm0_lpd_aclk
} {
    if {[llength [get_bd_pins -quiet $clockpin]] != 0} {
        error "M08 D3A disabled AXI clock pin unexpectedly exposed: $clockpin"
    }
}
if {[string trim [get_property CONFIG.PSU__FPGA_PL0_ENABLE $ps]] ne "1"} {
    error "M08 D3A PL0 clock request rejected"
}
set clock_mhz [string trim [get_property CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ $ps]]
if {![string is double -strict $clock_mhz] ||
    abs(double($clock_mhz) - 100.0) > 0.000001} {
    error "M08 D3A PS PL0 nominal 100MHz request not accepted: $clock_mhz"
}
set clockpin [get_bd_pins -quiet ps/pl_clk0]
if {[llength $clockpin] != 1} {error "M08 D3A missing PS PL0 output"}
set native_hz [string trim [get_property CONFIG.FREQ_HZ $clockpin]]
if {![string is wideinteger -strict $native_hz] ||
    [expr {abs(($native_hz + 0) - 100000000)}] > 1000} {
    error "M08 D3A native PL0 frequency differs from expected KV260 preset: $native_hz"
}

# Keep the exact trusted fan hardware route used by the original M08:
# PS TTC0 WAVEOUT[2] -> xlslice[2] -> PACKAGE_PIN A12.
foreach prop {
    CONFIG.PSU__TTC0__WAVEOUT__ENABLE
    CONFIG.PSU__TTC0__WAVEOUT__IO
} {
    if {[lsearch -exact [list_property $ps] $prop] < 0} {
        error "M08 D3A genuine PS TTC0 property missing: $prop"
    }
}
set_property -dict [list \
    CONFIG.PSU__TTC0__WAVEOUT__ENABLE {1} \
    CONFIG.PSU__TTC0__WAVEOUT__IO {EMIO}] $ps
if {[string trim [get_property CONFIG.PSU__TTC0__WAVEOUT__ENABLE $ps]] ne "1" ||
    [string toupper [string trim [get_property CONFIG.PSU__TTC0__WAVEOUT__IO $ps]]] ne "EMIO"} {
    error "M08 D3A failed to preserve PS TTC0 EMIO waveout configuration"
}
set wave [get_bd_pins -quiet ps/emio_ttc0_wave_o]
if {[llength $wave] != 1} {error "M08 D3A missing TTC0 EMIO waveout bus"}
set fan_slice [create_bd_cell -type ip -vlnv $slice_vlnv m08_d3a_ttc0_fan_slice]
set_property -dict [list CONFIG.DIN_WIDTH 3 CONFIG.DIN_FROM 2 CONFIG.DIN_TO 2] $fan_slice
set din [get_bd_pins -quiet m08_d3a_ttc0_fan_slice/Din]
set dout [get_bd_pins -quiet m08_d3a_ttc0_fan_slice/Dout]
if {[llength $din] != 1 || [llength $dout] != 1} {
    error "M08 D3A expected fan slice channel-2 pins missing"
}
set fan_port [create_bd_port -dir O M08_FAN_PWM]
connect_bd_net $wave $din
connect_bd_net $dout $fan_port

# No first-party PL AXI RTL or IP is admitted in this D3.1 scaffold.
foreach forbidden {
    ctrl_sc identity page
} {
    if {[llength [get_bd_cells -quiet $forbidden]] != 0} {
        error "M08 D3A unexpectedly included an original unsafe AXI cell: $forbidden"
    }
}
validate_bd_design -force
# Validation can regenerate PS outputs; fail closed on drift.
foreach iface {
    ps/M_AXI_HPM0_FPD ps/M_AXI_HPM1_FPD ps/M_AXI_HPM0_LPD
} {
    if {[llength [get_bd_intf_pins -quiet $iface]] != 0} {
        error "M08 D3A AXI master unexpectedly reappeared after validation: $iface"
    }
}
if {[get_property CONFIG.DOUT_WIDTH $fan_slice] ne "1"} {
    error "M08 D3A fan slice must emit one output"
}
save_bd_design
write_bd_tcl -force $exported

set out [open $fan_xdc {WRONLY CREAT EXCL}]
puts $out {# KV260 K26 original TTC0 channel-2 fan PWM route -> A12}
puts $out {set_property PACKAGE_PIN A12 [get_ports {M08_FAN_PWM}]}
puts $out {set_property IOSTANDARD LVCMOS33 [get_ports {M08_FAN_PWM}]}
puts $out {set_property SLEW SLOW [get_ports {M08_FAN_PWM}]}
puts $out {set_property DRIVE 4 [get_ports {M08_FAN_PWM}]}
close $out
add_files -fileset constrs_1 -norecurse $fan_xdc

set o [open $report {WRONLY CREAT EXCL}]
puts $o {schema=m08-d3a-kv260-passive-fan-bd-v1}
puts $o {candidate=m08-d3a-passive-fan-v1}
puts $o "vivado_version=[version -short]"
puts $o "part=[get_property PART [current_project]]"
puts $o "board_part=[get_property BOARD_PART [current_project]]"
puts $o {ps_preset=YES}
puts $o {ps_hpm0_fpd=DISABLED}
puts $o {ps_hpm1_fpd=DISABLED}
puts $o {ps_hpm0_lpd=DISABLED}
puts $o {smartconnect=ABSENT}
puts $o {identity_slave=ABSENT}
puts $o {page_slave=ABSENT}
puts $o {linux_uio_devices=ZERO}
puts $o "ps_pl0_nominal_request_mhz=$clock_mhz"
puts $o "ps_pl0_native_frequency_hz=$native_hz"
puts $o {ps_pl0_runtime_enabled=UNKNOWN}
puts $o {afi_boot_ownership=UNKNOWN}
puts $o {ps_atb4_configuration=UNKNOWN}
puts $o {ps_timeout_protection=NOT_PROVEN}
puts $o {physical_fan_cooling=NOT_PROVEN}
puts $o {fan_source=ps/emio_ttc0_wave_o[2]}
puts $o {fan_route=TTC0_WAVEOUT2_TO_A12}
puts $o {fan_pin=A12}
puts $o {fan_iostandard=LVCMOS33}
puts $o {fan_slew=SLOW}
puts $o {fan_drive=4}
puts $o {validated_bd=YES}
puts $o {synthesis=NOT_RUN}
puts $o {implementation=NOT_RUN}
puts $o {bitstream=NOT_GENERATED}
puts $o {linux_dtbo=NOT_GENERATED}
puts $o {hardware_programmed=NO}
puts $o {hardware_mmio_authorized=NO}
close $o
puts {M08_D3A_PASSIVE_FAN_ONLY_BD_VALIDATED_NO_AXI_NO_BITSTREAM_NO_BOARD}
