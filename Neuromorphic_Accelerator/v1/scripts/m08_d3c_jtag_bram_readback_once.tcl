# M08 D3.C deliberate one-shot physical JTAG AXI->BRAM communication experiment.
# For LATER owner-run only AFTER genuinely accepted native Vivado .bit build.
# No PS AXI/HPM0, UART/SSH, DDR, firmware, flash, FPGA manager or Linux calls.
# Stages: verify exact native image hash -> program once -> JTAG AXI WRITE/READ
# four 32-bit words -> compare exact values -> PC-only evidence file.
if {![info exists ::env(M08_D3C_ALLOW_PROGRAM)] ||
    $::env(M08_D3C_ALLOW_PROGRAM) ne "YES"} {
    error "Physical programming requires explicit M08_D3C_ALLOW_PROGRAM=YES"
}
foreach name {M08_D3C_BIT M08_D3C_EXPECTED_SHA M08_D3C_RESULT} {
    if {![info exists ::env($name)] || [string trim $::env($name)] eq ""} {
        error "Required physical experiment input not set: $name"
    }
}
if {![string match "2025.2*" [version -short]]} {
    error "Physical experiment requires Vivado 2025.2"
}
set bit [file normalize $::env(M08_D3C_BIT)]
set expected [string tolower $::env(M08_D3C_EXPECTED_SHA)]
set result [file normalize $::env(M08_D3C_RESULT)]
if {[file tail $bit] ne "m08_d3c_jtag_bram_UNRELEASED.bit" ||
    ![regexp {^m08_d3c_jtag_link_[A-Za-z0-9]+$} [file tail [file dirname [file dirname $bit]]]]} {
    error "Not the newly generated D3C diagnostic image"
}
if {![regexp {^[0-9a-f]{64}$} $expected]} {
    error "Expected SHA256 syntax invalid"
}
if {![file isfile $bit] || [file size $bit] < 100000 ||
    [file size $bit] > 100000000} {
    error "Missing/implausible new JTAG BRAM image"
}
if {[file exists $result] || ![file isdirectory [file dirname $result]]} {
    error "Result must be a fresh file in a known PC evidence directory"
}
set digest [string tolower [lindex [exec sha256sum -- $bit] 0]]
if {$digest ne $expected ||
    $digest eq "a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b" ||
    $digest eq "07af9e26905fd72b4d6b5845cbb4e309ecbefa83745a7c371769648cd0bdd547"} {
    error "Wrong native candidate digest; FPGA unchanged"
}
set target_path "localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA"
set hw_open 0
set server_open 0
set tgt_open 0
puts "M08_D3C_HARDWARE_IMAGE_VERIFIED|$digest"
try {
    open_hw_manager
    set hw_open 1
    connect_hw_server -url localhost:3121
    set server_open 1
    set targets [get_hw_targets -quiet]
    if {[llength $targets] != 1 || [lindex $targets 0] ne $target_path} {
        error "Unexpected or ambiguous JTAG target"
    }
    current_hw_target [lindex $targets 0]
    open_hw_target
    set tgt_open 1
    set matched {}
    foreach d [get_hw_devices -quiet] {
        puts "M08_D3C_DEVICE|[get_property NAME $d]|[get_property PART $d]"
        if {[get_property NAME $d] eq "xck26_0" &&
            [regexp {^xck26($|-)} [get_property PART $d]]} {
            lappend matched $d
        }
    }
    if {[llength $matched] != 1} {
        error "Could not uniquely identify K26 FPGA, before programming"
    }
    set fpga [lindex $matched 0]
    current_hw_device $fpga
    set_property PROGRAM.FILE $bit $fpga
    puts "M08_D3C_PROGRAM_START"
    flush stdout
    # ONE actual JTAG programming call. Do not retry automatically.
    program_hw_devices $fpga
    puts "M08_D3C_PROGRAM_COMPLETED"
    flush stdout
    refresh_hw_device -update_hw_probes false $fpga
    set axis [get_hw_axis -quiet]
    if {[llength $axis] != 1} {
        error "JTAG-to-AXI debug master not discoverable after programming"
    }
    set axi [lindex $axis 0]
    puts "M08_D3C_AXI_MASTER_DISCOVERED|$axi"
    reset_hw_axi $axi
    # Four distinct nonzero data words, aligned inside a reserved 16-byte
    # BRAM window starting at A0000000. No Linux/MMIO/PS HPM accesses.
    set values {A5A55A5A 12345678 DEADBEEF 0BADF00D}
    set lines {}
    for {set i 0} {$i < 4} {incr i} {
        set addr [format %08X [expr {0xA0000000 + ($i * 4)}]]
        set word [lindex $values $i]
        set wt [create_hw_axi_txn d3c_write_$i $axi -type WRITE \
            -address $addr -len 1 -data $word]
        run_hw_axi $wt
        puts "M08_D3C_AXI_WRITE|$addr|$word"
    }
    for {set i 0} {$i < 4} {incr i} {
        set addr [format %08X [expr {0xA0000000 + ($i * 4)}]]
        set expected_word [lindex $values $i]
        set rt [create_hw_axi_txn d3c_read_$i $axi -type READ \
            -address $addr -len 1]
        run_hw_axi $rt
        set observed [string toupper [string map {_ "" " " ""} \
            [string trim [get_property DATA $rt]]]]
        puts "M08_D3C_AXI_READ|$addr|$observed"
        if {![regexp {^[0-9A-F]{8}$} $observed] ||
            $observed ne $expected_word} {
            error "BRAM AXI readback mismatch at $addr: expected $expected_word got $observed"
        }
        lappend lines "address=$addr expected=$expected_word observed=$observed PASS"
    }
    set fd [open $result {WRONLY CREAT EXCL}]
    puts $fd {schema=m08-d3c-jtag-bram-one-shot-readback-v1}
    puts $fd {result=FOUR_BRAMA_WORDS_WRITTEN_READ_AND_MATCHED}
    puts $fd "candidate_sha256=$digest"
    puts $fd "target=$target_path"
    puts $fd "device=[get_property NAME $fpga]"
    puts $fd "debug_axi=$axi"
    puts $fd {no_linux_ssh_or_ps_mmio_used=YES}
    puts $fd {neural_inference_tested=NO}
    foreach line $lines {puts $fd $line}
    close $fd
    puts "M08_D3C_FOUR_WORDS_READBACK_PASS_PC_RECEIPT=$result"
} finally {
    if {$tgt_open} {catch {close_hw_target}}
    if {$server_open} {catch {disconnect_hw_server}}
    if {$hw_open} {catch {close_hw_manager}}
}
