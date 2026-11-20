# M08 D3.D.2A — ONE owner-armed physical KV260 four-neuron JTAG test.
# New exact, separately accepted D3.D.2A bitstream. DO NOT reuse D3.D.1.
# JTAG AXI only. No SSH, Linux, PS AXI MMIO, DDR, SD, flash or xmutil.
# PC writes neuron params/external currents. FPGA must compute and return
# EVERY neuron/tick voltage and spike (two independent M02 oracle fixtures).
# No retry or second program_hw_devices call on any outcome.

if {![info exists ::env(M08_D3D2A_ALLOW_PROGRAM)] ||
    $::env(M08_D3D2A_ALLOW_PROGRAM) ne "YES"} {
    error "Explicit M08_D3D2A_ALLOW_PROGRAM=YES required"
}
foreach env_name {M08_D3D2A_BIT M08_D3D2A_EXPECTED_SHA M08_D3D2A_RESULT M08_D3D2A_VECTORS} {
    if {![info exists ::env($env_name)] ||
        [string trim $::env($env_name)] eq ""} {
        error "Missing D3.D.2A single-attempt input: $env_name"
    }
}
if {![string match "2025.2*" [version -short]]} {
    error "Four-neuron physical test requires Vivado 2025.2"
}
set bit [file normalize $::env(M08_D3D2A_BIT)]
set result [file normalize $::env(M08_D3D2A_RESULT)]
set golden [file normalize $::env(M08_D3D2A_VECTORS)]
set expected [string tolower $::env(M08_D3D2A_EXPECTED_SHA)]
set reviewed "3c213c1271f48106495203d008d7f46619f8f079549117e404fca11fd3179411"
set native [file dirname [file dirname $bit]]
set hw [file dirname $result]
set evidence_base [file normalize [file join $::env(HOME) Thesis_Evidence M08]]
if {[file tail $bit] ne "m08_d3d2a_four_lif_jtag_UNRELEASED.bit" ||
    ![regexp {^m08_d3d2a_four_[A-Za-z0-9]+$} [file tail $native]] ||
    [file dirname $native] ne $evidence_base ||
    ![regexp {^m08_d3d2a_four_HW_[A-Za-z0-9]+$} [file tail $hw]] ||
    [file dirname $hw] ne $evidence_base ||
    [file tail $result] ne "80_neural_parity_readback.txt"} {
    error "Noncanonical original native/physical D3.D.2A evidence paths"
}
if {![file isfile $bit] || [file type $bit] ne "file" ||
    [file size $bit] != 7797843 || $expected ne $reviewed} {
    error "New four-neuron bitstream not the unique reviewed candidate"
}
if {![file isfile $golden] || [file type $golden] ne "file" ||
    [file size $golden] < 50 || [file size $golden] > 12000 ||
    [file dirname $golden] ne $hw ||
    [file tail $golden] ne "10_m02_golden.txt" ||
    ![file isdirectory $hw] ||
    [file exists $result]} {
    error "Missing/mutated result/golden evidence destination"
}
set digest [string tolower [lindex [exec sha256sum -- $bit] 0]]
if {$digest ne $reviewed} {
    error "Native bitstream sha does not equal reviewed original owner SHA256"
}

set f [open $golden RDONLY]
set goldens [split [string trim [read $f]] "\n"]
close $f
if {[llength $goldens] != 4 ||
    [lindex $goldens 0] ne "# schema=m08-d3d2a-m02-four-neuron-v1" ||
    [lindex $goldens 1] ne "# independent_dense_vs_queued=PASS"} {
    error "D3.D.2A M02 dense/event comparison headers missing"
}
set rows {}
set seen {}
foreach row [lrange $goldens 2 end] {
    set fields [split $row |]
    if {[llength $fields] != 55 ||
        ![regexp {^[a-z][a-z0-9_]+$} [lindex $fields 0]] ||
        [lindex $fields 0] in $seen} {
        error "Four-neuron M02 fixture dimensions/name/uniqueness invalid"
    }
    foreach word [lrange $fields 1 end] {
        if {![regexp {^[0-9A-F]{8}$} $word]} {
            error "Invalid 32-bit golden input/output word"
        }
    }
    lappend seen [lindex $fields 0]
    lappend rows $fields
}
if {$seen ne {independent_half_decay independent_unit_decay}} {
    error "Unexpected D3.D.2A physical workload names or order"
}

set target_path "localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA"
set hw_open 0
set server_open 0
set tgt_open 0
set txn_counter 0
proc d2a_write {axi addr word} {
    global txn_counter
    incr txn_counter
    set t [create_hw_axi_txn d2a_w_$txn_counter $axi -type WRITE \
        -address $addr -len 1 -data $word]
    run_hw_axi $t
}
proc d2a_read {axi addr} {
    global txn_counter
    incr txn_counter
    set t [create_hw_axi_txn d2a_r_$txn_counter $axi -type READ \
        -address $addr -len 1]
    run_hw_axi $t
    set value [string toupper [string map {_ "" " " ""} \
        [string trim [get_property DATA $t]]]]
    if {![regexp {^[0-9A-F]{8}$} $value]} {
        error "AXI readback is not an exact 32-bit word: $addr got $value"
    }
    return $value
}
puts "M08_D3D2A_IMAGE_HASH_VERIFIED|$digest"
puts "M08_D3D2A_GOLDEN_FOUR_NEURON_FIXTURES_VERIFIED|[llength $rows]"
flush stdout

try {
    open_hw_manager
    set hw_open 1
    connect_hw_server -url localhost:3121
    set server_open 1
    set targets [get_hw_targets -quiet]
    if {[llength $targets] != 1 ||
        [lindex $targets 0] ne $target_path} {
        error "Unexpected/ambiguous K26 JTAG target — NO PROGRAM"
    }
    current_hw_target [lindex $targets 0]
    open_hw_target
    set tgt_open 1
    set matches {}
    foreach device [get_hw_devices -quiet] {
        puts "M08_D3D2A_DEVICE|[get_property NAME $device]|[get_property PART $device]"
        if {[get_property NAME $device] eq "xck26_0" &&
            [regexp {^xck26($|-)} [get_property PART $device]]} {
            lappend matches $device
        }
    }
    if {[llength $matches] != 1} {
        error "No unique reviewed physical xck26_0 target"
    }
    set fpga [lindex $matches 0]
    current_hw_device $fpga
    set_property PROGRAM.FILE $bit $fpga
    puts {M08_D3D2A_PROGRAM_START}
    flush stdout
    program_hw_devices $fpga
    puts {M08_D3D2A_PROGRAM_COMPLETED}
    flush stdout
    refresh_hw_device -update_hw_probes false $fpga
    set axes [get_hw_axis -quiet]
    if {[llength $axes] != 1} {
        error "Expected exactly one JTAG AXI master in four-neuron image"
    }
    set axi [lindex $axes 0]
    if {$axi ne "hw_axi_1"} {
        error "Wrong JTAG AXI master: $axi"
    }
    puts "M08_D3D2A_AXI_MASTER|$axi"
    reset_hw_axi $axi

    d2a_write $axi A0000000 55AA22DD
    if {[d2a_read $axi A0000000] ne "55AA22DD"} {
        error "BRAM transport regression before neural test"
    }
    puts {M08_D3D2A_BRAM_TRANSPORT_REGRESSION_PASS}
    if {[d2a_read $axi A0001000] ne "4D344C46" ||
        [d2a_read $axi A0001004] ne "00020000"} {
        error "Wrong new four-neuron LIF magic/version"
    }
    puts {M08_D3D2A_FOUR_NEURON_LIF_IDENTITY_PASS}

    set result_lines {}
    set run_seq 0
    foreach fields $rows {
        incr run_seq
        set name [lindex $fields 0]
        set nonce [lindex $fields 1]
        set decay [lindex $fields 2]
        d2a_write $axi A000100C $nonce
        d2a_write $axi A0001010 $decay
        # Inputs 3..34 = four neurons * (initial,bias,threshold,
        # reset, four external signed32 currents). Hardware computes results.
        for {set n 0} {$n < 4} {incr n} {
            for {set j 0} {$j < 8} {incr j} {
                set idx [expr {3+$n*8+$j}]
                set addr [format %08X [expr {0xA0001040+$n*32+$j*4}]]
                d2a_write $axi $addr [lindex $fields $idx]
            }
        }
        d2a_write $axi A0001014 00000001

        # Bound the status poll; never retry START or reprogram on failure.
        set completed 0
        for {set attempt 0} {$attempt < 16} {incr attempt} {
            set status [d2a_read $axi A0001008]
            if {$status eq "00000001"} {
                set completed 1
                break
            }
            if {$status ne "00000002"} {
                error "Four-neuron status invalid for $name: $status"
            }
            after 10
        }
        if {!$completed} {error "Four-neuron DONE timeout for $name"}
        if {[d2a_read $axi A0001018] ne $nonce} {
            error "Four-neuron stale/mismatched completed nonce for $name"
        }
        set count [d2a_read $axi A000101C]
        if {$count ne [format %08X $run_seq]} {
            error "Four-neuron run count mismatch for $name: $count"
        }

        set voltages {}
        set spike_masks {}
        for {set n 0} {$n < 4} {incr n} {
            set neuron_volts {}
            set base [expr {0xA0001100+$n*32}]
            for {set j 0} {$j < 4} {incr j} {
                set addr [format %08X [expr {$base+$j*4}]]
                set actual [d2a_read $axi $addr]
                set expected_v [lindex $fields [expr {35+$n*5+$j}]]
                if {$actual ne $expected_v} {
                    error "REAL FPGA voltage mismatch $name neuron=$n tick=$j got=$actual want=$expected_v"
                }
                lappend neuron_volts $actual
            }
            set mask_addr [format %08X [expr {$base+16}]]
            set mask [d2a_read $axi $mask_addr]
            set expected_mask [lindex $fields [expr {35+$n*5+4}]]
            if {$mask ne $expected_mask} {
                error "REAL FPGA spikes mismatch $name neuron=$n got=$mask want=$expected_mask"
            }
            lappend voltages [join $neuron_volts ,]
            lappend spike_masks $mask
        }
        lappend result_lines "fixture=$name nonce=$nonce decay=$decay voltages=[join $voltages \;] spike_masks=[join $spike_masks ,] hardware=PASS"
        puts "M08_D3D2A_HW_FOUR_NEURON_M02_PARITY_PASS|$name|[join $spike_masks ,]"
        flush stdout
    }
    set fd [open $result {WRONLY CREAT EXCL}]
    puts $fd {schema=m08-d3d2a-hardware-four-neurons-four-ticks-v1}
    puts $fd {result=TWO_HARDWARE_FOUR_NEURON_FIXTURES_MATCHED_M02}
    puts $fd "candidate_sha256=$digest"
    puts $fd "target=$target_path"
    puts $fd "device=[get_property NAME $fpga]"
    puts $fd "debug_axi=$axi"
    puts $fd {neural_execution_tested=YES_FOUR_NEURONS_FOUR_TICKS_TWO_CASES}
    puts $fd {no_ps_axi_ddr_ssh_used=YES}
    puts $fd {reset_mode=FABRIC_POR_256_CYCLES}
    puts $fd {ps_clock_dependency=YES}
    puts $fd {synapse_routing_tested=NO}
    puts $fd {full_m06_paging_tested=NO}
    foreach line $result_lines {puts $fd $line}
    close $fd
    puts "M08_D3D2A_HW_RESULT_PC_RECEIPT=$result"
} finally {
    if {$tgt_open} {catch {close_hw_target}}
    if {$server_open} {catch {disconnect_hw_server}}
    if {$hw_open} {catch {close_hw_manager}}
}
