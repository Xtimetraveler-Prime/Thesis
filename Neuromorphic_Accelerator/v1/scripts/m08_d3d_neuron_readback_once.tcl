# M08 D3.D.1 — one explicitly owner-authorized physical LIF/JTAG experiment.
# REQUIRES fresh D3.D native Vivado image, not the old D3.C BRAM echo image.
# This TCL does not use Linux/SSH, MMIO, DDR, PS AXI masters, flash, or xmutil.
# JTAG writes parameters and external currents. FPGA itself computes 4 LIF
# ticks and returns a voltage/spike trace. Compare ALL results with an exact
# separately generated M02 dense+event reference fixture BEFORE success.
if {![info exists ::env(M08_D3D_ALLOW_PROGRAM)] ||
    $::env(M08_D3D_ALLOW_PROGRAM) ne "YES"} {
    error "Explicit M08_D3D_ALLOW_PROGRAM=YES required for new physical image"
}
foreach env_name {M08_D3D_BIT M08_D3D_EXPECTED_SHA M08_D3D_RESULT M08_D3D_VECTORS} {
    if {![info exists ::env($env_name)] ||
        [string trim $::env($env_name)] eq ""} {
        error "Missing bounded physical experiment input: $env_name"
    }
}
if {![string match "2025.2*" [version -short]]} {
    error "Physical D3.D neuron experiment requires Vivado 2025.2"
}
set bit [file normalize $::env(M08_D3D_BIT)]
set result [file normalize $::env(M08_D3D_RESULT)]
set golden [file normalize $::env(M08_D3D_VECTORS)]
set expected [string tolower $::env(M08_D3D_EXPECTED_SHA)]
if {[file tail $bit] ne "m08_d3d_lif_jtag_UNRELEASED.bit" ||
    ![regexp {^m08_d3d_neuron_[A-Za-z0-9]+$} [file tail [file dirname [file dirname $bit]]]]} {
    error "Expected new, correctly named native D3.D neural image only"
}
if {![regexp {^[0-9a-f]{64}$} $expected] || ![file isfile $bit] ||
    [file type $bit] ne "file" || [file size $bit] < 100000 ||
    [file size $bit] > 100000000} {
    error "Invalid, noncanonical or implausible neuron bitstream"
}
if {[file exists $result] || ![file isdirectory [file dirname $result]] ||
    ![file isfile $golden] || [file type $golden] ne "file" ||
    [file size $golden] < 40 || [file size $golden] > 10000} {
    error "Unsafe/missing PC golden vectors or result receipt destination"
}
set digest [string tolower [lindex [exec sha256sum -- $bit] 0]]
if {$digest ne $expected ||
    $digest eq "87e04662b038ded01bd020141c541a33d62370df02bdeaacdad695b17c9d00a1" ||
    $digest eq "51c090b95069fc4fd5b9d79f3cbbf45aea222d6ac484569aabe115877df098ea"} {
    error "New D3.D compute bitstream SHA mismatch or old BRAM-only image"
}
set stream [open $golden RDONLY]
set fixture_lines [split [string trim [read $stream]] "\n"]
close $stream
if {[llength $fixture_lines] != 6 ||
    [lindex $fixture_lines 0] ne "# schema=m08-d3d-m02-golden-v1" ||
    [lindex $fixture_lines 1] ne "# independent_dense_vs_event=PASS"} {
    error "M02 signed16 golden schema/count or independent oracle marker incorrect"
}
set golden_rows {}
set fixture_seen {}
foreach line [lrange $fixture_lines 2 end] {
    set fields [split $line |]
    if {[llength $fields] != 16 ||
        ![regexp {^[a-z][a-z0-9_]+$} [lindex $fields 0]] ||
        [lindex $fields 0] in $fixture_seen} {
        error "Malformed/duplicate M02 golden fixture"
    }
    foreach word [lrange $fields 1 end] {
        if {![regexp {^[0-9A-F]{8}$} $word]} {
            error "Malformed 32-bit fixture hex word"
        }
    }
    lappend fixture_seen [lindex $fields 0]
    lappend golden_rows $fields
}
if {[llength $golden_rows] != 4} {error "Expected exactly four M02 fixture rows"}
set target_path "localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA"
set hw_open 0
set server_open 0
set tgt_open 0
set txn_counter 0
proc d3d_write {axi addr word} {
    global txn_counter
    incr txn_counter
    set t [create_hw_axi_txn d3d_w_$txn_counter $axi -type WRITE \
        -address $addr -len 1 -data $word]
    run_hw_axi $t
}
proc d3d_read {axi addr} {
    global txn_counter
    incr txn_counter
    set t [create_hw_axi_txn d3d_r_$txn_counter $axi -type READ \
        -address $addr -len 1]
    run_hw_axi $t
    set observed [string toupper [string map {_ "" " " ""} \
        [string trim [get_property DATA $t]]]]
    if {![regexp {^[0-9A-F]{8}$} $observed]} {
        error "Invalid AXI 32-bit readback for $addr: $observed"
    }
    return $observed
}
puts "M08_D3D_NEW_NEURAL_IMAGE_VERIFIED|$digest"
puts "M08_D3D_M02_FIXTURES_VERIFIED|[llength $golden_rows]"
try {
    open_hw_manager
    set hw_open 1
    connect_hw_server -url localhost:3121
    set server_open 1
    set targets [get_hw_targets -quiet]
    if {[llength $targets] != 1 || [lindex $targets 0] ne $target_path} {
        error "JTAG target changed or ambiguous; no programming"
    }
    current_hw_target [lindex $targets 0]
    open_hw_target
    set tgt_open 1
    set matched {}
    foreach d [get_hw_devices -quiet] {
        puts "M08_D3D_DEVICE|[get_property NAME $d]|[get_property PART $d]"
        if {[get_property NAME $d] eq "xck26_0" &&
            [regexp {^xck26($|-)} [get_property PART $d]]} {
            lappend matched $d
        }
    }
    if {[llength $matched] != 1} {
        error "K26 JTAG device unavailable before programming"
    }
    set fpga [lindex $matched 0]
    current_hw_device $fpga
    set_property PROGRAM.FILE $bit $fpga
    puts {M08_D3D_PROGRAM_START}
    flush stdout
    program_hw_devices $fpga
    puts {M08_D3D_PROGRAM_COMPLETED}
    flush stdout
    refresh_hw_device -update_hw_probes false $fpga
    set axes [get_hw_axis -quiet]
    if {[llength $axes] != 1} {
        error "Expected exactly one working JTAG AXI core in new D3.D bitstream"
    }
    set axi [lindex $axes 0]
    puts "M08_D3D_AXI_MASTER|$axi"
    reset_hw_axi $axi

    # Retain a single bounded old-path BRAM echo to separate debug transport
    # failure from newly integrated AXI-Lite neuron peripheral failure.
    d3d_write $axi A0000000 55AA22DD
    if {[d3d_read $axi A0000000] ne "55AA22DD"} {
        error "Existing JTAG/BRAM transport regression; neuron not attempted"
    }
    puts {M08_D3D_BRAM_TRANSPORT_REGRESSION_PASS}

    if {[d3d_read $axi A0001000] ne "4D384C46" ||
        [d3d_read $axi A0001004] ne "00010000"} {
        error "New LIF peripheral magic/version not identified"
    }
    set result_lines {}
    set run_sequence 0
    foreach row $golden_rows {
        incr run_sequence
        set name [lindex $row 0]
        set nonce [lindex $row 1]
        set input_words [lrange $row 1 10]
        set expected_voltages [lrange $row 11 14]
        set expected_mask [lindex $row 15]
        set write_addrs {A000100C A0001010 A0001014 A0001018 A000101C \
                         A0001020 A0001024 A0001028 A000102C A0001030}
        foreach addr $write_addrs word $input_words {
            d3d_write $axi $addr $word
        }
        d3d_write $axi A0001034 00000001
        set status [d3d_read $axi A0001008]
        if {$status ne "00000001"} {
            error "LIF compute not DONE/idle for $name: $status"
        }
        if {[d3d_read $axi A0001038] ne $nonce} {
            error "LIF stale/incorrect completed nonce for $name"
        }
        set observed_mask [d3d_read $axi A000103C]
        if {$observed_mask ne $expected_mask} {
            error "LIF spike trace mismatch $name: got $observed_mask expected $expected_mask"
        }
        set observed_voltage {}
        foreach addr {A0001040 A0001044 A0001048 A000104C} {
            lappend observed_voltage [d3d_read $axi $addr]
        }
        if {$observed_voltage ne $expected_voltages} {
            error "Hardware M02 membrane trace mismatch $name: got $observed_voltage expected $expected_voltages"
        }
        set count [d3d_read $axi A0001050]
        set expected_count [format %08X $run_sequence]
        if {$count ne $expected_count} {
            error "LIF hardware run counter mismatch: got $count expected $expected_count"
        }
        lappend result_lines "fixture=$name nonce=$nonce voltages=[join $observed_voltage ,] spike_mask=$observed_mask hardware=PASS"
        puts "M08_D3D_HW_NEURAL_M02_PARITY_PASS|$name|$observed_mask"
        flush stdout
    }
    set fd [open $result {WRONLY CREAT EXCL}]
    puts $fd {schema=m08-d3d-hardware-lif4-ticks-v1}
    puts $fd {result=FOUR_HARDWARE_NEURON_FIXTURES_MATCHED_M02}
    puts $fd "candidate_sha256=$digest"
    puts $fd "target=$target_path"
    puts $fd "device=[get_property NAME $fpga]"
    puts $fd "debug_axi=$axi"
    puts $fd {neural_execution_tested=YES_SINGLE_NEURON_FOUR_TICKS}
    puts $fd {no_ps_axi_ddr_ssh_used=YES}
    puts $fd {reset_mode=FABRIC_POR_256_CYCLES}
    puts $fd {ps_clock_dependency=YES}
    puts $fd {synapse_routing_tested=NO}
    puts $fd {full_m06_paging_tested=NO}
    foreach line $result_lines {puts $fd $line}
    close $fd
    puts "M08_D3D_PHYSICAL_NEURAL_RESULT_PC_RECEIPT=$result"
} finally {
    if {$tgt_open} {catch {close_hw_target}}
    if {$server_open} {catch {disconnect_hw_server}}
    if {$hw_open} {catch {close_hw_manager}}
}
