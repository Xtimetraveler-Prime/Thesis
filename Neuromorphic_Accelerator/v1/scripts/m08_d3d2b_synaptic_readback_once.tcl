# M08 D3.D.2B — ONE owner-armed physical four-neuron recurrent synapse test.
# JTAG ONLY: no PS-to-PL masters, SSH, Linux memory, DDR, flash or SD writes.
# Replaces D3.D.2A only via a separately accepted NEW native image.
# Exactly ONE program_hw_devices call. No automatic recovery/retry.
if {![info exists ::env(M08_D3D2B_ALLOW_PROGRAM)] ||
    $::env(M08_D3D2B_ALLOW_PROGRAM) ne "YES"} {
    error "Explicit M08_D3D2B_ALLOW_PROGRAM=YES required"
}
foreach var {M08_D3D2B_BIT M08_D3D2B_EXPECTED_SHA M08_D3D2B_VECTORS M08_D3D2B_RESULT} {
    if {![info exists ::env($var)] || [string trim $::env($var)] eq ""} {
        error "Missing accepted routed-synapse JTAG experiment variable: $var"
    }
}
if {![string match "2025.2*" [version -short]]} {
    error "Physical D3.D.2B requires Vivado 2025.2"
}
set bit [file normalize $::env(M08_D3D2B_BIT)]
set golden [file normalize $::env(M08_D3D2B_VECTORS)]
set result [file normalize $::env(M08_D3D2B_RESULT)]
set expected [string tolower $::env(M08_D3D2B_EXPECTED_SHA)]
set reviewed "dae1c4953826317854acd3c61d013b6fddec410a0450002fa13b3ab1f1650d14"
set native [file dirname [file dirname $bit]]
set hw [file dirname $result]
set base [file normalize [file join $::env(HOME) Thesis_Evidence M08]]
if {[file tail $bit] ne "m08_d3d2b_synaptic_lif_jtag_UNRELEASED.bit" ||
    ![regexp {^m08_d3d2b_synaptic_[A-Za-z0-9]+$} [file tail $native]] ||
    [file dirname $native] ne $base ||
    ![regexp {^m08_d3d2b_synaptic_HW_[A-Za-z0-9]+$} [file tail $hw]] ||
    [file dirname $hw] ne $base ||
    [file tail $result] ne "80_synaptic_parity_readback.txt" ||
    ![file isdirectory $hw] || [file exists $result]} {
    error "Noncanonical isolated owner synaptic candidate/HW evidence"
}
if {![file isfile $bit] || [file type $bit] ne "file" ||
    [file size $bit] != 7797847 ||
    $expected ne $reviewed ||
    $expected eq "3c213c1271f48106495203d008d7f46619f8f079549117e404fca11fd3179411" ||
    $expected eq "b071adcec0ba33077cdf70543d5cc9c354f6746bcc8138e8c741c41a3cbb1c8b"} {
    error "Old, missing or invalid new synapse-routed bitstream"
}
if {![file isfile $golden] || [file type $golden] ne "file" ||
    [file dirname $golden] ne $hw ||
    [file tail $golden] ne "10_m02_golden.txt" ||
    [file size $golden] > 12000 || [file size $golden] < 100} {
    error "Missing/unsafe dense+queued M02 synaptic golden"
}
set digest [string tolower [lindex [exec sha256sum -- $bit] 0]]
if {$digest ne $expected || $digest ne $reviewed} {
    error "Accepted routed native bitstream digest differs from reviewed original"
}
set f [open $golden RDONLY]
set lines [split [string trim [read $f]] "\n"]
close $f
if {[llength $lines] != 4 ||
    [lindex $lines 0] ne "# schema=m08-d3d2b-m02-routed-four-neuron-v1" ||
    [lindex $lines 1] ne "# independent_dense_vs_queued=PASS"} {
    error "New M02 routed four-neuron golden header invalid"
}
set seen {}
set rows {}
foreach line [lrange $lines 2 end] {
    set fields [split $line |]
    if {[llength $fields] != 104 ||
        ![regexp {^[a-z][a-z0-9_]+$} [lindex $fields 0]] ||
        [lindex $fields 0] in $seen ||
        [lindex $fields 3] ne "00000008"} {
        error "Incorrect four-neuron/routed-eight-edge fixture"
    }
    foreach word [lrange $fields 1 end] {
        if {![regexp {^[0-9A-F]{8}$} $word]} {
            error "Wrong 32-bit M02 golden word"
        }
    }
    lappend seen [lindex $fields 0]
    lappend rows $fields
}
if {$seen ne {chain_recurrent inhibition_half_decay}} {
    error "Unexpected physical synaptic test workload set"
}

set target_path "localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA"
set hw_open 0
set server_open 0
set target_open 0
set txn_counter 0
proc d2b_write {axi address data} {
    global txn_counter
    incr txn_counter
    set txn [create_hw_axi_txn d2b_w_$txn_counter $axi -type WRITE \
        -address $address -len 1 -data $data]
    run_hw_axi $txn
}
proc d2b_read {axi address} {
    global txn_counter
    incr txn_counter
    set txn [create_hw_axi_txn d2b_r_$txn_counter $axi -type READ \
        -address $address -len 1]
    run_hw_axi $txn
    set observed [string toupper [string map {_ "" " " ""} \
        [string trim [get_property DATA $txn]]]]
    if {![regexp {^[0-9A-F]{8}$} $observed]} {
        error "JTAG AXI invalid 32-bit readback at $address: $observed"
    }
    return $observed
}

puts "M08_D3D2B_IMAGE_HASH_VERIFIED|$digest"
puts "M08_D3D2B_M02_ROUTING_FIXTURES_VERIFIED|[llength $rows]"
flush stdout
try {
    open_hw_manager
    set hw_open 1
    connect_hw_server -url localhost:3121
    set server_open 1
    set targets [get_hw_targets -quiet]
    if {[llength $targets] != 1 || [lindex $targets 0] ne $target_path} {
        error "Unexpected/ambiguous KV260 JTAG target; NO PROGRAM"
    }
    current_hw_target [lindex $targets 0]
    open_hw_target
    set target_open 1
    set matches {}
    foreach device [get_hw_devices -quiet] {
        puts "M08_D3D2B_DEVICE|[get_property NAME $device]|[get_property PART $device]"
        if {[get_property NAME $device] eq "xck26_0" &&
            [regexp {^xck26($|-)} [get_property PART $device]]} {
            lappend matches $device
        }
    }
    if {[llength $matches] != 1} {
        error "Cannot uniquely identify xck26_0"
    }
    set fpga [lindex $matches 0]
    current_hw_device $fpga
    set_property PROGRAM.FILE $bit $fpga
    puts {M08_D3D2B_PROGRAM_START}
    flush stdout
    program_hw_devices $fpga
    puts {M08_D3D2B_PROGRAM_COMPLETED}
    flush stdout
    refresh_hw_device -update_hw_probes false $fpga
    set axis [get_hw_axis -quiet]
    if {[llength $axis] != 1 || [lindex $axis 0] ne "hw_axi_1"} {
        error "No unique expected hw_axi_1 after new FPGA programming"
    }
    set axi [lindex $axis 0]
    puts "M08_D3D2B_AXI_MASTER|$axi"
    reset_hw_axi $axi

    d2b_write $axi A0000000 55AA22DD
    if {[d2b_read $axi A0000000] ne "55AA22DD"} {
        error "BRAM communication failed; synapse compute not attempted"
    }
    puts {M08_D3D2B_BRAM_TRANSPORT_PASS}
    if {[d2b_read $axi A0001000] ne "4D34534E" ||
        [d2b_read $axi A0001004] ne "00030000"} {
        error "New synapse-engine magic/version identification failed"
    }
    puts {M08_D3D2B_ROUTED_SYNAPSE_IDENTITY_PASS}

    set result_lines {}
    set sequence 0
    foreach fields $rows {
        incr sequence
        set name [lindex $fields 0]
        set nonce [lindex $fields 1]
        set mode [lindex $fields 2]
        set edge_count [lindex $fields 3]
        d2b_write $axi A000100C $nonce
        d2b_write $axi A0001010 $mode
        d2b_write $axi A0001020 $edge_count
        # Four neuron parameter blocks, then eight synaptic edge blocks.
        # These words contain ONLY params, external inputs and edges.
        for {set n 0} {$n < 4} {incr n} {
            for {set j 0} {$j < 8} {incr j} {
                set address [format %08X [expr {0xA0001040+$n*32+$j*4}]]
                d2b_write $axi $address [lindex $fields [expr {4+$n*8+$j}]]
            }
        }
        for {set e 0} {$e < 8} {incr e} {
            for {set j 0} {$j < 4} {incr j} {
                set address [format %08X [expr {0xA0001200+$e*16+$j*4}]]
                d2b_write $axi $address [lindex $fields [expr {36+$e*4+$j}]]
            }
        }
        d2b_write $axi A0001014 00000001
        set completed 0
        for {set attempt 0} {$attempt < 16} {incr attempt} {
            set status [d2b_read $axi A0001008]
            if {$status eq "00000001"} {
                set completed 1
                break
            }
            if {$status ne "00000002"} {
                error "Synaptic network has invalid busy/status word for $name: $status"
            }
            after 10
        }
        if {!$completed} {error "Four-neuron routed compute DONE timeout: $name"}
        if {[d2b_read $axi A0001018] ne $nonce} {
            error "Recurrent engine result nonce mismatched: $name"
        }
        if {[d2b_read $axi A000101C] ne [format %08X $sequence]} {
            error "Recurrent engine run count not sequential: $name"
        }
        set voltages {}
        set spike_masks {}
        set synaptic_currents {}
        for {set n 0} {$n < 4} {incr n} {
            set v_words {}
            set s_words {}
            for {set j 0} {$j < 4} {incr j} {
                set vaddr [format %08X [expr {0xA0001100+$n*32+$j*4}]]
                set saddr [format %08X [expr {0xA0001300+$n*16+$j*4}]]
                set actual_v [d2b_read $axi $vaddr]
                set actual_s [d2b_read $axi $saddr]
                set offset [expr {68+$n*9}]
                set expected_v [lindex $fields [expr {$offset+$j}]]
                set expected_s [lindex $fields [expr {$offset+5+$j}]]
                if {$actual_v ne $expected_v} {
                    error "M02 physical voltage mismatch $name neuron=$n tick=$j got=$actual_v want=$expected_v"
                }
                if {$actual_s ne $expected_s} {
                    error "M02 physical SYNAPSE ROUTING mismatch $name neuron=$n tick=$j got=$actual_s want=$expected_s"
                }
                lappend v_words $actual_v
                lappend s_words $actual_s
            }
            set maddr [format %08X [expr {0xA0001100+$n*32+16}]]
            set actual_m [d2b_read $axi $maddr]
            set expected_m [lindex $fields [expr {68+$n*9+4}]]
            if {$actual_m ne $expected_m} {
                error "M02 physical spike mask mismatch $name neuron=$n got=$actual_m want=$expected_m"
            }
            lappend voltages [join $v_words ,]
            lappend synaptic_currents [join $s_words ,]
            lappend spike_masks $actual_m
        }
        lappend result_lines "fixture=$name nonce=$nonce decay=$mode voltages=[join $voltages \;] spike_masks=[join $spike_masks ,] synaptic_currents=[join $synaptic_currents \;] hardware=PASS"
        puts "M08_D3D2B_HW_M02_RECURRENT_SYNAPSE_PARITY_PASS|$name|[join $spike_masks ,]"
        flush stdout
    }
    set fd [open $result {WRONLY CREAT EXCL}]
    puts $fd {schema=m08-d3d2b-hw-recurrent-four-neurons-v1}
    puts $fd {result=TWO_FOUR_NEURON_RECURRENT_SYNAPSE_FIXTURES_MATCHED_M02}
    puts $fd "candidate_sha256=$digest"
    puts $fd "target=$target_path"
    puts $fd {device=xck26_0}
    puts $fd "debug_axi=$axi"
    puts $fd {synaptic_execution_tested=YES_8_EDGES_4_NEURONS_4_TICKS}
    puts $fd {no_ps_axi_ddr_ssh_used=YES}
    puts $fd {reset_mode=FABRIC_POR_256_CYCLES}
    puts $fd {ps_clock_dependency=YES}
    puts $fd {full_m06_paging_tested=NO}
    foreach line $result_lines {puts $fd $line}
    close $fd
    puts "M08_D3D2B_PHYSICAL_ROUTED_RESULT_PC_RECEIPT=$result"
} finally {
    if {$target_open} {catch {close_hw_target}}
    if {$server_open} {catch {disconnect_hw_server}}
    if {$hw_open} {catch {close_hw_manager}}
}
