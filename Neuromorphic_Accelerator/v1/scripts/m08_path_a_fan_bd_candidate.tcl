# M08.2b Path A: OFFLINE, new fan-preserving K26 BD candidate.
# Runs genuine original M08 PS HPM0 -> identity + 256B page BD generator
# in a FRESH evidence project, then adds TTC0 channel-2 EMIO waveout.
# This is NOT a programmed image, fan-continuity proof or DT/OS integration.
# Read-only in relation to the ORIGINAL accepted M08 sources/evidence.
if {[llength $argv] != 2} {
    error "usage: m08_path_a_fan_bd_candidate.tcl <v1-root> <fresh-evidence-dir>"
}
set root [file normalize [lindex $argv 0]]
set evidence [file normalize [lindex $argv 1]]
if {![file isdirectory $root] || ![file isdirectory $evidence]} {
    error "M08 Path A requires existing v1 source root and fresh evidence directory"
}
if {![string match "2025.2*" [version -short]]} {
    error "M08 Path A fan candidate requires real Vivado 2025.2"
}
set baseline [file join $root scripts m08_page_ps_bd_candidate.tcl]
if {![file isfile $baseline]} { error "M08 accepted original BD source missing" }
set fan_report [file join $evidence 20_m08_fan_bd_readback.txt]
set fan_xdc [file join $evidence 21_m08_fan_pwm_a12.xdc]
set fan_bd_export [file join $evidence 22_m08_fan_bd_export.tcl]
foreach out [list $fan_report $fan_xdc $fan_bd_export] {
    if {[file exists $out]} {
        error "M08 Path A refuses to replace existing original/new evidence: $out"
    }
}
# The accepted first-party baseline creates a new Vivado K26 project, uses
# the genuine SOM board preset, verifies 99,999,001Hz PS clock and TWO
# nonoverlapping identity/page AXI4-Lite slave apertures, and saves BD.
set argv [list $root $evidence]
source $baseline
set ps [get_bd_cells -quiet ps]
if {[llength $ps] != 1} { error "M08 Path A missing unique accepted PS BD cell" }
set baseline_report [file join $evidence 02_vivado_page_bd_readback.txt]
if {![file isfile $baseline_report]} {
    error "M08 Path A original validated BD report missing"
}
set rf [open $baseline_report r]
set baseline_text [read $rf]
close $rf
foreach marker {
    META|validated_bd|YES
    META|compute_enabled|NO
    META|physical_kv260|NOT_PROGRAMMED
    M08_PAGE_GENUINE_LOCAL_KV260_PS_TO_IDENTITY_AND_SAFE_PAGE_BD
} {
    if {[string first $marker $baseline_text] < 0} {
        error "M08 Path A baseline report missing $marker"
    }
}
# AMD Kria K26 base firmware: PS TTC0 wave-out channel 2 routes through EMIO
# to HD pin HDA20 = physical A12, with LVCMOS33 and low slew/drive.
# Preserve the canonical PS->two-slave AXI interfaces. Do NOT reinterpret
# the clock-input pin: TTC0 fan PWM is the WAVEOUT output [2].
foreach prop {
    CONFIG.PSU__TTC0__WAVEOUT__ENABLE
    CONFIG.PSU__TTC0__WAVEOUT__IO
} {
    if {[lsearch -exact [list_property $ps] $prop] < 0} {
        error "M08 Path A current genuine PS IP does not expose $prop"
    }
}
set_property -dict [list \
    CONFIG.PSU__TTC0__WAVEOUT__ENABLE {1} \
    CONFIG.PSU__TTC0__WAVEOUT__IO {EMIO}] $ps
if {[string trim [get_property CONFIG.PSU__TTC0__WAVEOUT__ENABLE $ps]] ne "1" ||
    [string toupper [string trim [get_property CONFIG.PSU__TTC0__WAVEOUT__IO $ps]]] ne "EMIO"} {
    error "M08 Path A PS TTC0 EMIO waveout configuration did not stick"
}
set wave [get_bd_pins -quiet ps/emio_ttc0_wave_o]
if {[llength $wave] != 1} {
    error "M08 Path A expected unique PS TTC0 EMIO waveout bus"
}
set slice_vlnv "xilinx.com:ip:xlslice:1.0"
if {[llength [get_ipdefs -quiet -all $slice_vlnv]] != 1} {
    error "M08 Path A genuine AMD xlslice IP missing"
}
set slice [create_bd_cell -type ip -vlnv $slice_vlnv m08_ttc0_fan_slice]
set_property -dict [list CONFIG.DIN_WIDTH 3 CONFIG.DIN_FROM 2 CONFIG.DIN_TO 2] $slice
set din [get_bd_pins -quiet m08_ttc0_fan_slice/Din]
set dout [get_bd_pins -quiet m08_ttc0_fan_slice/Dout]
if {[llength $din] != 1 || [llength $dout] != 1} {
    error "M08 Path A fan channel-2 output slice not present"
}
set port [create_bd_port -dir O M08_FAN_PWM]
connect_bd_net $wave $din
connect_bd_net $dout $port
validate_bd_design -force
save_bd_design
write_bd_tcl -force $fan_bd_export

# New evidence-only XDC: the original accepted M08 bitstream is untouched.
# Final pinouts must be verified by genuine K26 Vivado route + original DT.
set f [open $fan_xdc {WRONLY CREAT EXCL}]
puts $f {# K26 KV260 fan PWM: PS TTC0 waveout channel 2 -> HDA20/A12}
puts $f {set_property PACKAGE_PIN A12 [get_ports {M08_FAN_PWM}]}
puts $f {set_property IOSTANDARD LVCMOS33 [get_ports {M08_FAN_PWM}]}
puts $f {set_property SLEW SLOW [get_ports {M08_FAN_PWM}]}
puts $f {set_property DRIVE 4 [get_ports {M08_FAN_PWM}]}
close $f
add_files -fileset constrs_1 -norecurse $fan_xdc
# Requery baseline master and slaves after adding TTC0; fail if drifted.
set master [get_bd_intf_pins -quiet ps/M_AXI_HPM0_FPD]
set identity [get_bd_intf_pins -quiet identity/S_AXI]
set page [get_bd_intf_pins -quiet page/S_AXI]
if {[llength $master] != 1 || [llength $identity] != 1 || [llength $page] != 1} {
    error "M08 Path A fan update lost original PS master or identity/page slave"
}
set rf [open $baseline_report r]
set baseline_text [read $rf]
close $rf
set lines {}
foreach line [split $baseline_text "\n"] {
    if {[string match "APERTURE_IDENTITY|*" $line] ||
        [string match "APERTURE_PAGE|*" $line]} {
        lappend lines $line
    }
}
if {[llength $lines] != 2} {
    error "M08 Path A baseline original TWO independent AXI windows absent"
}
set out [open $fan_report {WRONLY CREAT EXCL}]
puts $out "schema=m08-path-a-kv260-fan-bd-offline-v1"
puts $out "vivado=[version -short]"
puts $out "board_part=[get_property BOARD_PART [current_project]]"
puts $out "part=[get_property PART [current_project]]"
puts $out "fan_source=ps/emio_ttc0_wave_o\[2\]"
puts $out "fan_route=ps/emio_ttc0_wave_o->m08_ttc0_fan_slice\[2\]->M08_FAN_PWM"
puts $out "fan_pin=A12"
puts $out "fan_iostandard=LVCMOS33"
puts $out "fan_output_width=[get_property CONFIG.DOUT_WIDTH $slice]"
puts $out "fan_ttc0_enable=[get_property CONFIG.PSU__TTC0__WAVEOUT__ENABLE $ps]"
puts $out "fan_ttc0_io=[get_property CONFIG.PSU__TTC0__WAVEOUT__IO $ps]"
puts $out "original_compute_enabled=NO"
foreach line $lines { puts $out $line }
puts $out "validated_bd=YES"
puts $out "physical_fan_pwm_verified=NO"
puts $out "routed=NO"
puts $out "bitstream_generated=NO"
puts $out "linux_overlay_installed=NO"
puts $out "board_programmed=NO"
close $out
puts "M08_PATH_A_K26_FAN_BD_OFFLINE_VALIDATED_NO_BOARD_NO_BITSTREAM"
