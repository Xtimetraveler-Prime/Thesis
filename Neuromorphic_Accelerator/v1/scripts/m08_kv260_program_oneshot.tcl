# M08.2b guarded one-shot K26 programming; adapted from proven Loihi
# P08.4.3b Vivado Hardware Manager sequence, NOT Loihi VIO/.ltx.
# NO PS reset, AXI, fan, firmware, SD/QSPI/flash or retry.
if {[llength $argv] != 2} {
    error "usage: m08_kv260_program_oneshot.tcl <original-bit> <fresh-result>"
}
if {![info exists ::env(M08_ALLOW_PROGRAM)] || $::env(M08_ALLOW_PROGRAM) ne "YES"} {
    error "explicit M08_ALLOW_PROGRAM=YES required"
}
if {![info exists ::env(M08_APPROVED_MODE)] || $::env(M08_APPROVED_MODE) ne "ISOLATED_JTAG"} {
    error "M08_APPROVED_MODE=ISOLATED_JTAG required; never overwrite Linux-managed PL"
}
if {![string match "2025.2*" [version -short]]} {
    error "M08 requires genuine Vivado 2025.2"
}
set bit_file [file normalize [lindex $argv 0]]
set result_file [file normalize [lindex $argv 1]]
if {![file exists $bit_file] || ![file isfile $bit_file] || [file size $bit_file] != 7797831} {
    error "M08 original bitstream missing or wrong exact size"
}
if {[file exists $result_file] || ![file isdirectory [file dirname $result_file]]} {
    error "M08 result must be fresh under an existing evidence directory"
}
set expected_sha "170da137f315a6f53c345c416808c5203e866b8772acb6b7e69265fe38d31bbf"
set found_sha [string tolower [lindex [exec sha256sum -- $bit_file] 0]]
if {$found_sha ne $expected_sha} {
    error "M08 original bitstream SHA256 mismatch; FPGA unchanged"
}
# Cable identity already established by original owner JTAG evidence.
# A changed cable must trigger a fresh operator review, NEVER fallback.
set expected_target "localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA"
set manager_open 0
set server_open 0
set target_open 0
try {
    open_hw_manager
    set manager_open 1
    connect_hw_server -url localhost:3121
    set server_open 1
    set targets [get_hw_targets -quiet]
    if {[llength $targets] != 1 || [lindex $targets 0] ne $expected_target} {
        error "M08 physical target changed or ambiguous; no programming"
    }
    current_hw_target [lindex $targets 0]
    open_hw_target
    set target_open 1
    set selected {}
    foreach d [get_hw_devices -quiet] {
        set name [string trim [get_property NAME $d]]
        set part [string trim [get_property PART $d]]
        puts "M08_DEVICE_OBSERVED|$name|$part"
        if {$name eq "xck26_0" && [regexp {^xck26($|-)} $part]} {
            lappend selected $d
        }
    }
    if {[llength $selected] != 1} {
        error "M08 no unique xck26_0 with xck26 part; arm_dap_1 is NOT FPGA"
    }
    set fpga [lindex $selected 0]
    if {[get_property NAME $fpga] ne "xck26_0"} {
        error "M08 FPGA identity changed before programming"
    }
    puts "M08_PROGRAM_PREFLIGHT_OK|$expected_target|xck26_0|$found_sha"
    current_hw_device $fpga
    refresh_hw_device -update_hw_probes false $fpga
    set_property PROGRAM.FILE $bit_file $fpga
    # Exactly one actual PL programming call; failures are never retried.
    program_hw_devices $fpga
    refresh_hw_device $fpga
    set out [open $result_file {WRONLY CREAT EXCL}]
    puts $out "schema=m08-2b-one-shot-jtag-program-v1"
    puts $out "result=PROGRAMMED_ONLY_NO_PS_AXI_PROOF"
    puts $out "hardware_target=$expected_target"
    puts $out "device=xck26_0"
    puts $out "part=[get_property PART $fpga]"
    puts $out "vivado_version=[version -short]"
    puts $out "bitstream_sha256=$found_sha"
    puts $out "bitstream_bytes=[file size $bit_file]"
    puts $out "no_ps_axi_verified=1"
    close $out
    puts "M08_JTAG_PROGRAMMED_BITSTREAM_NO_PS_AXI_READBACK"
} finally {
    if {$target_open} { catch {close_hw_target} }
    if {$server_open} { catch {disconnect_hw_server} }
    if {$manager_open} { catch {close_hw_manager} }
}
