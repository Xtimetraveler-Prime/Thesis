# M08 D3.D.2E — STAGED ONLY; exact first-original DRC unreviewed.
# Exactly one explicit owner-authorized JTAG program AFTER exact owner
# image SHA/size, source, DRC, 100MHz timing and 12-file ledger are checked
# in the shell. This Tcl independently rechecks SHA, JTAG target, and input
# geometry. No second program or automatic retry; cooling/UART/recovery
# preflight flags are mandatory. NO PS MMIO, DDR, HLS or flash writes.
set UNRELEASED_SHA "2c443c3d80e86e5e9488b457110a45b0db96881016e9f87a5c801a72ec7527dc"
# No hardware operation permitted until the separate exact-native gate returns 0.
if {![regexp {^[a-f0-9]{64}$} $UNRELEASED_SHA]} {
    error "D3.D.2E HARD STOP: first owner native image NOT RELEASED"
}
if {![info exists ::env(M08_D3D2E_ALLOW_PROGRAM)] ||
    $::env(M08_D3D2E_ALLOW_PROGRAM) ne "YES" ||
    ![info exists ::env(M08_D3D2E_PREFLIGHT_CONFIRMED)] ||
    $::env(M08_D3D2E_PREFLIGHT_CONFIRMED) ne "YES"} {
    error "D3.D.2E explicit one-shot owner consent AND cooling/UART/JTAG/recovery preflight confirmation required"
}
foreach key {M08_D3D2E_BIT M08_D3D2E_VECTORS M08_D3D2E_RESULT M08_D3D2E_EXPECTED_SHA} {
    if {![info exists ::env($key)] || [string trim $::env($key)] eq ""} {
        error "Missing exact staged physical input $key"
    }
}
if {![string match "2025.2*" [version -short]]} {
    error "Genuine Vivado 2025.2 required"
}
set bit [file normalize $::env(M08_D3D2E_BIT)]
set source [file normalize $::env(M08_D3D2E_VECTORS)]
set result [file normalize $::env(M08_D3D2E_RESULT)]
set digest [string tolower $::env(M08_D3D2E_EXPECTED_SHA)]
set base [file normalize [file join $::env(HOME) Thesis_Evidence M08]]
set native [file dirname [file dirname $bit]]
set hw [file dirname $result]
if {[file tail $bit] ne "m08_d3d2e_queue_lif_jtag_UNRELEASED.bit" ||
    [file tail $native] ne "m08_d3d2e_queue_GFz0SbiC" ||
    [file dirname $native] ne $base ||
    ![regexp {^m08_d3d2e_queue_HW_[A-Za-z0-9]+$} [file tail $hw]] ||
    [file dirname $hw] ne $base ||
    [file tail $source] ne "10_m06_tickqueue_golden.hex" ||
    [file dirname $source] ne $hw ||
    [file tail $result] ne "80_m06_tickqueue_hw_parity.txt" ||
    ![file isdirectory $hw] || [file exists $result]} {
    error "Noncanonical original owner native / isolated physical folder"
}
if {$digest ne $UNRELEASED_SHA || ![file isfile $bit] ||
    ![file isfile $source] || [file type $bit] ne "file" ||
    [file type $source] ne "file" ||
    [file size $bit] != 7797844 || [file size $source] > 9000 ||
    [file size $source] < 100} {
    error "D3.D.2E is NOT an independently approved owner bitstream"
}
set real [string tolower [lindex [exec sha256sum -- $bit] 0]]
if {$real ne $UNRELEASED_SHA} {error "New bitstream differs from accepted first owner"}
set fh [open $source RDONLY]
set lines [split [string trim [read $fh]] "\n"]
close $fh
if {[llength $lines] != 630} {
    error "Wrong original M06 630-word 17 raw-event neural oracle"
}
foreach word $lines {
    if {![regexp {^[0-9A-F]{8}$} $word]} {
        error "Malformed M06 32-bit oracle value"
    }
}
if {[lindex $lines 0] ne "D2C00001" ||
    [lindex $lines 1] ne "00000003" ||
    [lindex $lines 2] ne "00000005"} {
    error "Unexpected original M06 golden nonce/3/4/5-edge identity"
}
proc d2e_write {axi address data} {
    global txn_counter
    incr txn_counter
    set x [create_hw_axi_txn d2e_w_$txn_counter $axi -type WRITE -address $address -len 1 -data $data]
    run_hw_axi $x
}
proc d2e_read {axi address} {
    global txn_counter
    incr txn_counter
    set x [create_hw_axi_txn d2e_r_$txn_counter $axi -type READ -address $address -len 1]
    run_hw_axi $x
    set actual [string toupper [string map {_ "" " " ""} [string trim [get_property DATA $x]]]]
    if {![regexp {^[0-9A-F]{8}$} $actual]} {
        error "JTAG readback malformed at $address: $actual"
    }
    return $actual
}
set txn_counter 0
set hw_open 0
set server_open 0
set target_open 0
set target_path "localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA"
puts "M08_D3D2E_ACCEPTED_IMAGE_HASH|$real"
puts "M08_D3D2E_M06_TRIPLE_ORACLE_630_WORDS_VERIFIED"
flush stdout
try {
    open_hw_manager
    set hw_open 1
    connect_hw_server -url localhost:3121
    set server_open 1
    set targets [get_hw_targets -quiet]
    if {[llength $targets] != 1 || [lindex $targets 0] ne $target_path} {
        error "Unexpected or ambiguous KV260 JTAG target; NO PROGRAM"
    }
    current_hw_target [lindex $targets 0]
    open_hw_target
    set target_open 1
    set matches {}
    foreach d [get_hw_devices -quiet] {
        puts "M08_D3D2E_DEVICE|[get_property NAME $d]|[get_property PART $d]"
        if {[get_property NAME $d] eq "xck26_0" &&
            [regexp {^xck26($|-)} [get_property PART $d]]} {lappend matches $d}
    }
    if {[llength $matches] != 1} {error "No unique K26 device; NO PROGRAM"}
    set fpga [lindex $matches 0]
    current_hw_device $fpga
    set_property PROGRAM.FILE $bit $fpga
    puts {M08_D3D2E_PROGRAM_START}
    flush stdout
    program_hw_devices $fpga
    puts {M08_D3D2E_PROGRAM_COMPLETED}
    flush stdout
    refresh_hw_device -update_hw_probes false $fpga
    set axis [get_hw_axis -quiet]
    if {[llength $axis] != 1 || [lindex $axis 0] ne "hw_axi_1"} {
        error "Missing unique postprogram hw_axi_1"
    }
    set axi [lindex $axis 0]
    puts "M08_D3D2E_AXI_MASTER|$axi"
    flush stdout
    reset_hw_axi $axi
    d2e_write $axi A0000000 55AA22DD
    if {[d2e_read $axi A0000000] ne "55AA22DD"} {
        error "BRAM regression failed; no neural computation attempted"
    }
    puts {M08_D3D2E_BRAM_TRANSPORT_PASS}
    if {[d2e_read $axi A0001000] ne "4D333251" ||
        [d2e_read $axi A0001004] ne "00060000"} {
        error "Wrong 32-neuron engine magic/version"
    }
    puts {M08_D3D2E_M32Q_V6_IDENTITY_PASS}
    d2e_write $axi A000100C [lindex $lines 0]
    d2e_write $axi A0001010 [lindex $lines 1]
    d2e_write $axi A0001020 [lindex $lines 2]
    for {set n 0} {$n < 32} {incr n} {
        # M32Q current buckets are READ-ONLY: write ONLY 4 LIF params.
        # Explicitly never write +4..+7: these MUST be service-generated.
        for {set j 0} {$j < 4} {incr j} {
            set address [format %08X [expr {0xA0001100+$n*32+$j*4}]]
            d2e_write $axi $address [lindex $lines [expr {3+$n*8+$j}]]
        }
    }
    # Only original five ACTIVE M06 edges; unused edge delay zero is illegal.
    for {set e 0} {$e < 5} {incr e} {
        for {set j 0} {$j < 4} {incr j} {
            set address [format %08X [expr {0xA0001500+$e*16+$j*4}]]
            d2e_write $axi $address [lindex $lines [expr {259+$e*4+$j}]]
        }
    }
    # Send ORIGINAL 17 distinct M06 tuples: fabric, not host, sums currents.
    for {set e 0} {$e < 17} {incr e} {
        d2e_write $axi A0001024 [lindex $lines [expr {579+3*$e}]]
        d2e_write $axi A0001028 [lindex $lines [expr {580+3*$e}]]
        d2e_write $axi A000102C [lindex $lines [expr {581+3*$e}]]
        d2e_write $axi A0001030 00000001
        if {[d2e_read $axi A0001034] ne [format %08X [expr {$e+1}]] ||
            [d2e_read $axi A0001044] ne [format %08X [expr {$e+1}]] ||
            [d2e_read $axi A000104C] ne "00000000" ||
            [d2e_read $axi A0001050] ne "00000000"} {
            error "M32Q enqueue count/depth or premature service mismatch e=$e"
        }
    }
    puts {M08_D3D2E_PHYSICAL_RAW_17_EVENT_PUSH_ACCEPTED}
    flush stdout
    if {[d2e_read $axi A0001048] ne "00000011"} {error "M32Q FIFO high-watermark !=17"}
    # All fabric input sums are still zero until an explicit service command.
    for {set n 0} {$n < 32} {incr n} {
        for {set j 0} {$j < 4} {incr j} {
            set a [format %08X [expr {0xA0001100+$n*32+16+$j*4}]]
            if {[d2e_read $axi $a] ne "00000000"} {
                error "M32Q live input prematurely changed n=$n t=$j"
            }
        }
    }
    puts {M08_D3D2E_ALL_128_LIVE_BUCKETS_ZERO_BEFORE_SERVICE}
    flush stdout
    set service_counts {}
    set serviced_total 0
    for {set t 0} {$t < 4} {incr t} {
        set num 0
        for {set e 0} {$e < 17} {incr e} {
            scan [lindex $lines [expr {580+3*$e}]] %x event_tick
            if {$event_tick == $t} {incr num}
        }
        d2e_write $axi A0001040 [format %08X $t]
        set complete 0
        for {set attempt 0} {$attempt < 30} {incr attempt} {
            scan [d2e_read $axi A0001054] %x state
            if {[expr {$state & 1}] == 0 &&
                [expr {($state >> 1) & 7}] == $t+1} {
                set complete 1
                break
            }
            after 10
        }
        if {!$complete} {error "M32Q queue SERVICE tick timeout t=$t"}
        incr serviced_total $num
        if {[d2e_read $axi A000104C] ne [format %08X $serviced_total] ||
            [d2e_read $axi A0001044] ne [format %08X [expr {17-$serviced_total}]] ||
            [d2e_read $axi A0001050] ne [format %08X [expr {(1<<($t+1))-1}]]} {
            error "M32Q serviced/depth/tick-mask mismatch t=$t"
        }
        d2e_write $axi A0001028 [format %08X $t]
        if {[d2e_read $axi A0001058] ne [format %08X $num]} {
            error "M32Q per-tick service count mismatch t=$t"
        }
        lappend service_counts $num
        puts "M08_D3D2E_TICK_SERVICE_PARITY|$t|$num"
        flush stdout
    }
    if {$serviced_total != 17 ||
        [d2e_read $axi A0001034] ne "00000011" ||
        [d2e_read $axi A0001044] ne "00000000" ||
        [d2e_read $axi A0001048] ne "00000011" ||
        [d2e_read $axi A000104C] ne "00000011" ||
        [d2e_read $axi A0001050] ne "0000000F"} {
        error "M32Q full FIFO service invariant failed"
    }
    puts {M08_D3D2E_QUEUE_17_ACCEPTED_17_SERVICED_ALL_FOUR_TICKS_PASS}
    flush stdout
    set current_rows {}
    for {set n 0} {$n < 32} {incr n} {
        set currents {}
        for {set j 0} {$j < 4} {incr j} {
            set address [format %08X [expr {0xA0001100+$n*32+16+$j*4}]]
            set actual [d2e_read $axi $address]
            set want [lindex $lines [expr {3+$n*8+4+$j}]]
            if {$actual ne $want} {
                error "M06 FABRIC event current mismatch n=$n t=$j got=$actual wanted=$want"
            }
            lappend currents $actual
        }
        lappend current_rows [join $currents ,]
        puts "M08_D3D2E_EVENT_BUCKET_PARITY|$n"
        flush stdout
    }
    puts {M08_D3D2E_PHYSICAL_ALL_128_FPGA_EVENT_BUCKET_SUMS_PASS}
    flush stdout
    d2e_write $axi A0001014 00000001
    set completed 0
    for {set attempt 0} {$attempt < 30} {incr attempt} {
        set status [d2e_read $axi A0001008]
        if {$status eq "00000001"} {set completed 1; break}
        if {$status ne "00000002"} {error "M06 32-neuron invalid compute status"}
        after 10
    }
    if {!$completed} {error "M06 32-neuron compute timeout"}
    if {[d2e_read $axi A0001018] ne [lindex $lines 0] ||
        [d2e_read $axi A000101C] ne "00000001"} {
        error "M06 DONE nonce/count differs from accepted source"
    }
    set result_lines {}
    for {set n 0} {$n < 32} {incr n} {
        set voltages {}
        set synaptic {}
        set offset [expr {291+$n*9}]
        for {set j 0} {$j < 4} {incr j} {
            set addr [format %08X [expr {0xA0001900+$n*32+$j*4}]]
            set actual [d2e_read $axi $addr]
            if {$actual ne [lindex $lines [expr {$offset+$j}]]} {
                error "M06 physical voltage mismatch n=$n t=$j got=$actual"
            }
            lappend voltages $actual
            set saddr [format %08X [expr {0xA0001D00+($n*4+$j)*4}]]
            set actualsyn [d2e_read $axi $saddr]
            if {$actualsyn ne [lindex $lines [expr {$offset+5+$j}]]} {
                error "M06 physical delivered recurrent current mismatch n=$n t=$j got=$actualsyn"
            }
            lappend synaptic $actualsyn
        }
        set maskaddr [format %08X [expr {0xA0001900+$n*32+16}]]
        set mask [d2e_read $axi $maskaddr]
        if {$mask ne [lindex $lines [expr {$offset+4}]]} {
            error "M06 physical spike mask mismatch n=$n got=$mask"
        }
        lappend result_lines "neuron=$n external_currents=[lindex $current_rows $n] voltages=[join $voltages ,] mask=$mask synaptic_currents=[join $synaptic ,]"
        puts "M08_D3D2E_M06_REAL_NEURON_PARITY|$n"
        flush stdout
    }
    set fh [open $result {WRONLY CREAT EXCL}]
    puts $fh {schema=m08-d3d2e-m06-32-neuron-17-queued-event-hardware-v1}
    puts $fh {result=ONE_ORIGINAL_M06_32X4_QUEUED_EVENT_SERVICE_AND_RECURRENT_HARDWARE_PARITY}
    puts $fh "candidate_sha256=$real"
    puts $fh "target=$target_path"
    puts $fh {device=xck26_0}
    puts $fh {debug_axi=hw_axi_1}
    puts $fh {external_events_coalesced_on_host=NO}
    puts $fh {event_ingress_transport=JTAG_AXI_LITE_FIFO_MAILBOX}
    puts $fh {event_push_count=17}
    puts $fh {hardware_event_bucket_sums_verified=128}
    puts $fh {live_buckets_zero_before_service_verified=128}
    puts $fh {fifo_event_accept_count=17}
    puts $fh {fifo_event_serviced_count=17}
    puts $fh {fifo_depth_after_all_services=0}
    puts $fh {fifo_high_watermark=17}
    puts $fh {tick_completion_mask=0000000F}
    for {set t 0} {$t < 4} {incr t} {
        puts $fh "per_tick_serviced_$t=[lindex $service_counts $t]"
    }
    puts $fh {physical_ddr_m06_hls_verified=NO}
    foreach line $result_lines {puts $fh $line}
    close $fh
    puts {M08_D3D2E_PHYSICAL_M06_128_EVENT_128_VOLTAGE_128_SPIKE_128_SYN_CURRENT_PASS}
} finally {
    if {$target_open} {catch {close_hw_target}}
    if {$server_open} {catch {disconnect_hw_server}}
    if {$hw_open} {catch {close_hw_manager}}
}
