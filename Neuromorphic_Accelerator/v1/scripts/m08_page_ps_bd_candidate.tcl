# M08.2b.3 — genuine local Vivado K26 PS→SmartConnect→identity + signed16
# 256-byte SAFE PAGE PS AXI4-Lite SLAVES. Offline BD validation candidate.
# No engine (DISPATCH disabled), bitstream, Linux MMIO, DDR, DMA or board
# programming. Original accepted M08.2a identity evidence is immutable.
# Vivado 2025.2 must be available LOCALLY. No JTAG/hw_server/flash commands.
if {[llength $argv] != 2} {
    error "usage: m08_page_ps_bd_candidate.tcl <v1-root> <fresh-evidence-dir>"
}
set root [file normalize [lindex $argv 0]]
set evidence [file normalize [lindex $argv 1]]
set source_names [list \
    rtl/m08/m08_axil_readonly_identity.v \
    rtl/m08/m08_host_staged_page_bank.sv \
    rtl/m08/m08_axil_page_control.sv \
    rtl/m08/m08_ps_page_safe_shell.sv]
foreach name $source_names {
    if {![file isfile [file join $root $name]]} {
        error "M08 page BD missing first-party source '$name'"
    }
}
if {![file isdirectory $evidence]} {
    error "M08 page BD requires a new existing evidence folder"
}
set report [file join $evidence 02_vivado_page_bd_readback.txt]
set design_export [file join $evidence 03_page_bd_export.tcl]
if {[file exists $report] || [file exists $design_export]} {
    error "M08 must NOT overwrite an original evidence report"
}
set expected_part xck26-sfvc784-2LV-c
set requested_clock_hz 100000000
# About 10 ppm: accepts 99,999,001 Hz observed on the real KV260 preset,
# but still rejects the prior 96,968,727 Hz without a board preset.
set maximum_clock_deviation_hz 1000
set ps_vlnv xilinx.com:ip:zynq_ultra_ps_e:3.5
set sc_vlnv xilinx.com:ip:smartconnect:1.0
set rst_vlnv xilinx.com:ip:proc_sys_reset:5.0
set inv_vlnv xilinx.com:ip:util_vector_logic:2.0
set const_vlnv xilinx.com:ip:xlconstant:1.1

# Fail if a local Vivado version/part/IP is incompatible; no fallback stubs.
set version [version -short]
if {![string match "2025.2*" $version]} {
    error "M08 requires genuine Vivado 2025.2, got '$version'"
}
set project_dir [file join $evidence project]
if {[file exists $project_dir]} {
    error "M08 will not overwrite any existing Vivado project"
}
create_project m08_page_ps $project_dir -part $expected_part
set_property source_mgmt_mode All [current_project]
if {[get_property PART [current_project]] ne $expected_part} {
    error "M08 K26 Vivado part mismatch"
}
# The accepted Loihi v2 P03/P04/P05/P08 K26 implementations select a
# genuine KV260 SOM BOARD_PART before applying the PS board preset. Without
# that preset, our fourth genuine M08 run still reported 96,968,727 Hz on
# pl_clk0 despite a 100 MHz PS property request. Never invent board files
# or silently fall back to a part-only PS configuration.
set kv260_board_parts [get_board_parts -quiet xilinx.com:kv260_som:part0:*]
if {[llength $kv260_board_parts] == 0} {
    error "M08 requires installed KV260 SOM board files (xilinx.com:kv260_som:part0:*)"
}
set kv260_board_part [lindex [lsort -dictionary $kv260_board_parts] end]
set_property BOARD_PART $kv260_board_part [current_project]
if {[get_property BOARD_PART [current_project]] ne $kv260_board_part} {
    error "M08 KV260 BOARD_PART selection was not accepted"
}
puts "M08_KV260_BOARD_PART=$kv260_board_part"
# Vivado 2025.2 get_ipdefs requires an open project. Preserve the strict
# first-party AMD IP check, but run it only after create_project succeeds.
foreach vlnv [list $ps_vlnv $sc_vlnv $rst_vlnv $inv_vlnv $const_vlnv] {
    if {[llength [get_ipdefs -all -quiet $vlnv]] != 1} {
        error "M08 genuine AMD Vivado IP not available: $vlnv"
    }
}
foreach name $source_names {
    add_files -norecurse [file join $root $name]
}
update_compile_order -fileset sources_1
create_bd_design m08_page_ps

proc pin_required {path} {
    set p [get_bd_pins -quiet $path]
    if {[llength $p] != 1} {error "M08 missing genuine BD scalar pin $path"}
    return $p
}
proc intf_required {path} {
    set p [get_bd_intf_pins -quiet $path]
    if {[llength $p] != 1} {error "M08 missing genuine BD AXI interface $path"}
    return $p
}

set ps [create_bd_cell -type ip -vlnv $ps_vlnv ps]
# Reuse only the accepted Loihi PS board-initialization sequence, NOT its
# host-paged neural architecture or physical/DDR access. Re-apply the exact
# identity-only GP/clock configuration after the KV260 board preset.
apply_bd_automation -rule xilinx.com:bd_rule:zynq_ultra_ps_e \
    -config {apply_board_preset "1"} $ps
puts "M08_KV260_PS_BOARD_PRESET_APPLIED=1"
# The PS default exposed M_AXI_HPM0_LPD in the owner's genuine 2025.2
# run; its unconnected maxihpm0_lpd_aclk blocked validate_bd_design.
# Select ONLY FPD HPM0 for this identity-only PS->PL address path.
# The accepted Loihi Digital Twin P03/P04/P05/P08 K26 Tcl explicitly set
# PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ 100.  Our third genuine M08 run
# otherwise generated 96968727 Hz, while the AXI4-Lite RTL declares 100 MHz.
# The preset supplies actual KV260 PS reference-clock parameters. Disable
# both other PS AXI masters; this probe keeps only its explicit FPD HPM0.
set_property -dict [list CONFIG.PSU__USE__M_AXI_GP0 1 \
                         CONFIG.PSU__USE__M_AXI_GP1 0 \
                         CONFIG.PSU__USE__M_AXI_GP2 0 \
                         CONFIG.PSU__FPGA_PL0_ENABLE 1 \
                         CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ 100] $ps
if {[string trim [get_property CONFIG.PSU__USE__M_AXI_GP0 $ps]] ne "1"} {
    error "M08 PS HPM0 FPD master could not be enabled"
}
if {[string trim [get_property CONFIG.PSU__USE__M_AXI_GP2 $ps]] ne "0"} {
    error "M08 unused PS HPM0 LPD master could not be disabled"
}
if {[string trim [get_property CONFIG.PSU__USE__M_AXI_GP1 $ps]] ne "0"} {
    error "M08 unused PS HPM1 FPD master could not be disabled"
}
if {[llength [get_bd_intf_pins -quiet ps/M_AXI_HPM1_FPD]] != 0 ||
    [llength [get_bd_pins -quiet ps/maxihpm1_fpd_aclk]] != 0} {
    error "M08 unused PS HPM1 FPD interface/clock remains exposed"
}
if {[string trim [get_property CONFIG.PSU__FPGA_PL0_ENABLE $ps]] ne "1"} {
    error "M08 PS PL0 clock output could not be enabled"
}
set requested_ps_mhz [string trim [get_property CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ $ps]]
if {![string is double -strict $requested_ps_mhz] ||
    abs(double($requested_ps_mhz) - 100.0) > 0.000001} {
    error "M08 PS PL0 requested 100 MHz frequency was not accepted: '$requested_ps_mhz'"
}
# A request of 100 MHz does not guarantee exactly 100,000,000 Hz:
# genuine KV260 board-preset Vivado 2025.2 emitted 99,999,001 Hz.
# Limit the source deviation to 1,000 Hz (~10 ppm); NEVER relabel a
# 96,968,727 Hz default as nominal 100 MHz, and never forge FREQ_HZ.
set ps_clock_hz [string trim [get_property CONFIG.FREQ_HZ [pin_required ps/pl_clk0]]]
if {![string is wideinteger -strict $ps_clock_hz]} {
    error "M08 PS PL0 actual FREQ_HZ is not a valid integer: '$ps_clock_hz'"
}
set actual_clock_deviation_hz [expr {abs(($ps_clock_hz+0) - $requested_clock_hz)}]
if {$actual_clock_deviation_hz > $maximum_clock_deviation_hz} {
    error "M08 PS PL0 actual FREQ_HZ outside 1000 Hz budget: expected $requested_clock_hz got '$ps_clock_hz'"
}
puts "M08_GENUINE_PS_PL0_CLOCK_HZ=$ps_clock_hz"
puts "M08_PS_PL0_CLOCK_DEVIATION_HZ=$actual_clock_deviation_hz"
if {[llength [get_bd_intf_pins -quiet ps/M_AXI_HPM0_LPD]] != 0 ||
    [llength [get_bd_pins -quiet ps/maxihpm0_lpd_aclk]] != 0} {
    error "M08 unused PS HPM0 LPD interface/clock remains exposed"
}
if {[string trim [get_property CONFIG.PSU__MAXIGP0__DATA_WIDTH $ps]] ne "128"} {
    error "M08 expected proven K26 HPM0 FPD 128-bit master"
}
set master [intf_required ps/M_AXI_HPM0_FPD]
if {[string toupper [get_property MODE $master]] ne "MASTER"} {
    error "M08 PS HPM0 interface not MASTER"
}

set identity [create_bd_cell -type module -reference m08_axil_readonly_identity identity]
set page [create_bd_cell -type module -reference m08_ps_page_safe_shell page]
set slave [intf_required identity/S_AXI]
set page_slave [intf_required page/S_AXI]
foreach iface [list $slave $page_slave] {
    if {[string toupper [get_property MODE $iface]] ne "SLAVE"} {
        error "M08 PS-to-page BD AXI4-Lite SLAVE inference failed: $iface"
    }
}
set smart [create_bd_cell -type ip -vlnv $sc_vlnv ctrl_sc]
set_property -dict [list CONFIG.NUM_SI 1 CONFIG.NUM_MI 2] $smart
if {[string trim [get_property CONFIG.NUM_SI $smart]] ne "1" ||
    [string trim [get_property CONFIG.NUM_MI $smart]] ne "2"} {
    error "M08 expected exactly one PS master and TWO distinct PL slaves"
}
set reset [create_bd_cell -type ip -vlnv $rst_vlnv pl_reset]
# M05 original owner: this is a READ-ONLY PS reset polarity IP parameter.
# Invert PS active-low pl_resetn0 rather than overriding C_EXT_RESET_HIGH.
if {[lsearch -exact [list_property $reset] CONFIG.C_EXT_RESET_HIGH] < 0 ||
    [string trim [get_property CONFIG.C_EXT_RESET_HIGH $reset]] ne "1"} {
    error "M08 reset conditioner has unexpected ext_reset_in polarity"
}
set inv [create_bd_cell -type ip -vlnv $inv_vlnv reset_inv]
set_property -dict [list CONFIG.C_OPERATION not CONFIG.C_SIZE 1] $inv
set one [create_bd_cell -type ip -vlnv $const_vlnv logic_one]
set zero [create_bd_cell -type ip -vlnv $const_vlnv logic_zero]
set_property -dict [list CONFIG.CONST_VAL 1 CONFIG.CONST_WIDTH 1] $one
set_property -dict [list CONFIG.CONST_VAL 0 CONFIG.CONST_WIDTH 1] $zero

connect_bd_intf_net [intf_required ps/M_AXI_HPM0_FPD] [intf_required ctrl_sc/S00_AXI]
connect_bd_intf_net [intf_required ctrl_sc/M00_AXI] [intf_required identity/S_AXI]
connect_bd_intf_net [intf_required ctrl_sc/M01_AXI] [intf_required page/S_AXI]
foreach endpoint {ps/pl_clk0 ps/maxihpm0_fpd_aclk ctrl_sc/aclk pl_reset/slowest_sync_clk identity/aclk page/aclk} {
    pin_required $endpoint
}
connect_bd_net [pin_required ps/pl_clk0] \
    [pin_required ps/maxihpm0_fpd_aclk] [pin_required ctrl_sc/aclk] \
    [pin_required pl_reset/slowest_sync_clk] [pin_required identity/aclk] \
    [pin_required page/aclk]
connect_bd_net [pin_required ps/pl_resetn0] [pin_required reset_inv/Op1]
connect_bd_net [pin_required reset_inv/Res] [pin_required pl_reset/ext_reset_in]
connect_bd_net [pin_required logic_one/dout] [pin_required pl_reset/dcm_locked]
connect_bd_net [pin_required logic_zero/dout] \
    [pin_required pl_reset/aux_reset_in] [pin_required pl_reset/mb_debug_sys_rst]
connect_bd_net [pin_required pl_reset/interconnect_aresetn] [pin_required ctrl_sc/aresetn]
connect_bd_net [pin_required pl_reset/peripheral_aresetn] \
    [pin_required identity/aresetn] [pin_required page/aresetn]

set space [get_bd_addr_spaces -quiet -of_objects $master]
set slave_segments [get_bd_addr_segs -quiet -of_objects $slave]
set page_segments [get_bd_addr_segs -quiet -of_objects $page_slave]
if {[llength $space] != 1 || [llength $slave_segments] != 1 ||
    [llength $page_segments] != 1} {
    error "M08 real PS AXI space or two distinct AXI4-Lite slave segments missing"
}
# Vivado assigns the separate regions; no Linux MMIO permissions implied.
assign_bd_address -target_address_space $space [lindex $slave_segments 0]
assign_bd_address -target_address_space $space [lindex $page_segments 0]
validate_bd_design -force
# Do not accept a nominal-clock request alone: after genuine BD
# parameter propagation the PS, AXI slave clock, S_AXI and SmartConnect
# output must all report the SAME actual generated frequency.
foreach endpoint [list [pin_required ps/pl_clk0] [pin_required identity/aclk] \
                       [pin_required page/aclk] [intf_required identity/S_AXI] \
                       [intf_required page/S_AXI] [intf_required ctrl_sc/M00_AXI] \
                       [intf_required ctrl_sc/M01_AXI]] {
    set propagated_hz [string trim [get_property CONFIG.FREQ_HZ $endpoint]]
    if {![string is wideinteger -strict $propagated_hz] ||
        [expr {$propagated_hz+0}] != [expr {$ps_clock_hz+0}]} {
        error "M08 validated BD clock propagation disagrees with PS pl_clk0: $endpoint FREQ_HZ='$propagated_hz' expected '$ps_clock_hz'"
    }
}
puts "M08_GENUINE_AXI_CLOCK_PROPAGATION_MATCH_HZ=$ps_clock_hz"
save_bd_design
write_bd_tcl -force $design_export

# Re-query ACTUAL vendor assigned apertures after real validation.
proc unique_ps_aperture {space segment} {
    set found {}
    foreach candidate [get_bd_addr_segs -addressing -quiet -of_objects $segment] {
        if {[string match [format "%s/*" $space] "$candidate"]} {
            lappend found $candidate
        }
    }
    if {[llength $found] != 1} {
        error "M08 expected exactly one PS-visible aperture for $segment"
    }
    set address [lindex $found 0]
    set offset [string trim [get_property OFFSET $address]]
    set range [string trim [get_property RANGE $address]]
    if {![regexp {^0x[0-9A-Fa-f]+$} $offset] ||
        ![regexp {^0x[0-9A-Fa-f]+$} $range] ||
        [expr {$range + 0}] != 4096 ||
        [expr {$offset+0}] < 0 ||
        [expr {$offset + $range}] > 4294967296} {
        error "M08 PS address segment invalid or not exactly 4KiB: $address offset=$offset range=$range"
    }
    return [list $address $offset $range]
}
set identity_addr [unique_ps_aperture $space [lindex $slave_segments 0]]
set page_addr [unique_ps_aperture $space [lindex $page_segments 0]]
set identity_start [expr {[lindex $identity_addr 1]+0}]
set page_start [expr {[lindex $page_addr 1]+0}]
if {$identity_start == $page_start ||
    ($identity_start < $page_start+4096 && $page_start < $identity_start+4096)} {
    error "M08 identity and signed16 page PS address regions overlap"
}
puts "M08_PAGE_BD_DISTINCT_ID_AND_PAGE_4K_ADDRESS_SEGMENTS=1"

# Exactly two distinct externally mapped PL slaves; COMPUTE DISABLED in
# source wrapper. Vendor validation is not Linux address ownership.
set lines [list \
    "META|scope|M08_GENUINE_LOCAL_KV260_PS_TO_IDENTITY_AND_SAFE_PAGE_BD" \
    "META|part|$expected_part" \
    "META|vivado_version|$version" \
    "META|board_part|$kv260_board_part" \
    "META|ps_preset|YES" \
    "META|requested_clock_hz|$requested_clock_hz" \
    "META|actual_clock_hz|$ps_clock_hz" \
    "META|page_source|rtl/m08/m08_ps_page_safe_shell.sv" \
    "META|compute_enabled|NO" \
    "MASTER|[get_property NAME $master]|$space" \
    "SLAVE_IDENTITY|$slave|[lindex $slave_segments 0]" \
    "SLAVE_PAGE|$page_slave|[lindex $page_segments 0]" \
    "APERTURE_IDENTITY|[join $identity_addr |]" \
    "APERTURE_PAGE|[join $page_addr |]" \
    "META|validated_bd|YES" \
    "META|routed_implementation|NOT_RUN" \
    "META|bitstream|NOT_GENERATED" \
    "META|linux_mmio|NOT_ACCESSED" \
    "META|physical_ddr|NOT_ACCESSED" \
    "META|physical_kv260|NOT_PROGRAMMED"]
set o [open $report {WRONLY CREAT EXCL}]
puts $o [join $lines "\n"]
close $o
puts "M08_PAGE_GENUINE_VIVADO_BD_VALIDATED_NO_BITSTREAM_NO_BOARD"
