# M08.4 SOURCE-STAGED physical one-shot candidate (NOT RELEASED).
# NEVER run this Tcl standalone. The outer shell MUST first pass a newly
# independent exact-image native DRC/timing/clock/SHA gate, active cooling,
# UART, stock rollback, exclusive JTAG and explicit one-shot owner consent.
# JTAG AXI PL ONLY; NOT PS /dev/mem, OS DDR, DMA, flash or SD writes.
# Original first failed/succeeded owner evidence directories remain immutable.
set ORIGINAL_SHA "6a4a71f255adcc79a4131401a3f75eb64f253d3431f5ad1babc0da48479f6494"
set ORIGINAL_OWNER "m08_paged_m06_lif_QFKpXlPW"
foreach key {M08_4_BIT M08_4_NATIVE M08_4_HW M08_4_EXPECTED_SHA M08_4_PROGRAM_ONCE M08_4_PREFLIGHT_CONFIRMED M08_4_IMAGE_RELEASE} {
    if {![info exists ::env($key)] || [string trim $::env($key)] eq ""} {
        error "M08.4 physical source NOT RELEASED, missing required exact-image/preflight input $key"
    }
}
foreach key {M08_4_PROGRAM_ONCE M08_4_PREFLIGHT_CONFIRMED M08_4_IMAGE_RELEASE} {
    if {$::env($key) ne "YES"} {
        error "M08.4 physical STOP: no exact-image release/preflight/owner one-shot consent"
    }
}
if {![string match "2025.2*" [version -short]]} {
    error "Genuine Vivado 2025.2 required"
}
set homebase [file normalize [file join $::env(HOME) Thesis_Evidence M08]]
set native [file normalize $::env(M08_4_NATIVE)]
set hwdir [file normalize $::env(M08_4_HW)]
set bit [file normalize $::env(M08_4_BIT)]
if {[file dirname $native] ne $homebase ||
    [file tail $native] ne $ORIGINAL_OWNER ||
    [file dirname $hwdir] ne $homebase ||
    ![regexp {^m08_paged_m06_lif_HW_[A-Za-z0-9]+$} [file tail $hwdir]] ||
    $bit ne [file join $native bitstream_candidate m08_paged_m06_lif_jtag_UNRELEASED.bit] ||
    ![file isdirectory $native] || ![file isdirectory $hwdir] ||
    [file exists [file join $hwdir 80_physical_paged_neural_parity.txt]]} {
    error "M08.4 physical STOP: noncanonical new owner native/image/evidence path"
}
if {![file isfile $bit] || [file type $bit] ne "file" ||
    [string tolower $::env(M08_4_EXPECTED_SHA)] ne $ORIGINAL_SHA ||
    [string tolower [lindex [exec sha256sum -- $bit] 0]] ne $ORIGINAL_SHA} {
    error "M08.4 physical STOP: first original image digest mismatch"
}
# All inputs are separate HOST-owned persistent neural pages. Goldens are
# comparison-only and MUST NEVER be staged as compute-facing neuron words.
proc m08_load_words {path count} {
    if {![file isfile $path] || [file type $path] ne "file" ||
        [file size $path] > 20000} {
        error "Missing/invalid original comparison or input file $path"
    }
    set fd [open $path RDONLY]
    set lines [split [string trim [read $fd]] "\n"]
    close $fd
    if {[llength $lines] != $count} {error "wrong word count $path"}
    foreach word $lines {
        if {![regexp {^[0-9A-F]{8}$} $word]} {
            error "untrusted 32-bit hex input from $path"
        }
    }
    return $lines
}
set edge_words [m08_load_words [file join $hwdir 10_edge_config_input.hex] 64]
for {set p 0} {$p<6} {incr p} {
    set backing($p) [m08_load_words [file join $hwdir 11_neural_page_${p}_input.hex] 64]
    if {[lindex $backing($p) 60] ne "4D364E46" ||
        [scan [lindex $backing($p) 61] %x] != $p ||
        [scan [lindex $backing($p) 62] %x] != [expr {$p==5?2:6}] ||
        [lindex $backing($p) 63] ne "00000000"} {
        error "input-only neuron page wrong ID/geometry: $p"
    }
}
if {[lindex $edge_words 60] ne "4D364547" ||
    [lindex $edge_words 61] ne "FFFFFFFF" ||
    [lindex $edge_words 62] ne "00000005"} {
    error "M06 edge setup input identity drift"
}
set golden [m08_load_words [file join $hwdir 20_independent_512_oracle_ONLY.hex] 512]
array set masks {}
for {set n 0} {$n<32} {incr n} {set masks($n) 0}
set verified_inputs 0
set verified_voltages 0
set verified_spikes 0
set verified_syn 0
set saved_pages 0
set txn_counter 0
proc m08_w {axi addr data} {
    global txn_counter
    incr txn_counter
    set x [create_hw_axi_txn m084_w_$txn_counter $axi -type WRITE -address $addr -len 1 -data $data]
    run_hw_axi $x
}
proc m08_r {axi addr} {
    global txn_counter
    incr txn_counter
    set x [create_hw_axi_txn m084_r_$txn_counter $axi -type READ -address $addr -len 1]
    run_hw_axi $x
    set result [string toupper [string map {_ "" " " ""} [string trim [get_property DATA $x]]]]
    if {![regexp {^[0-9A-F]{8}$} $result]} {
        error "M08.4 malformed physical AXI read $addr: $result"
    }
    return $result
}
proc m08_expect {axi addr want} {
    set actual [m08_r $axi $addr]
    if {$actual ne $want} {
        error "M08.4 physical mismatch addr=$addr expected=$want actual=$actual"
    }
    return $actual
}
proc m08_stage {axi logical words} {
    m08_w $axi A0001010 [format %08X $logical]
    m08_w $axi A0001014 00000001
    m08_expect $axi A000101C 00000000
    for {set j 0} {$j<64} {incr j} {
        set a [format %08X [expr {0xA0001100+4*$j}]]
        m08_w $axi $a [lindex $words $j]
    }
    m08_expect $axi A000101C 00000100
    for {set j 0} {$j<64} {incr j} {
        set a [format %08X [expr {0xA0001100+4*$j}]]
        m08_expect $axi $a [lindex $words $j]
    }
    m08_w $axi A0001014 00000002
    m08_expect $axi A000100C 00000012
    m08_expect $axi A0001018 [format %08X $logical]
}
proc m08_dispatch {axi} {
    m08_w $axi A0001014 00000004
    set complete 0
    for {set tries 0} {$tries<200} {incr tries} {
        set status [m08_r $axi A000100C]
        if {$status eq "00000034"} {
            set complete 1
            break
        }
        scan $status %x status_int
        if {($status_int & 0x108) != 0} {
            error "M08.4 sticky fault/poison in page compute: $status"
        }
    }
    if {!$complete} {error "M08.4 bounded page compute timeout; no auto-retry"}
}
set hw_open 0
set server_open 0
set target_open 0
set target_path "localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA"
puts "M08_4_ORIGINAL_BIT_SHA|$ORIGINAL_SHA"
puts "M08_4_SEPARATE_6_INPUT_PAGES_AND_512_ONLY_EXTERNAL_GOLDEN_PRECHECK_PASS"
flush stdout
try {
    open_hw_manager
    set hw_open 1
    connect_hw_server -url localhost:3121
    set server_open 1
    set targets [get_hw_targets -quiet]
    if {[llength $targets]!=1 || [lindex $targets 0] ne $target_path} {
        error "M08.4 ambiguous/unexpected K26 JTAG target, NOT programming"
    }
    current_hw_target [lindex $targets 0]
    open_hw_target
    set target_open 1
    set devices {}
    foreach dev [get_hw_devices -quiet] {
        if {[get_property NAME $dev] eq "xck26_0" &&
            [regexp {^xck26($|-)} [get_property PART $dev]]} {
            lappend devices $dev
        }
    }
    if {[llength $devices] != 1} {
        error "M08.4 expected exactly one K26 xck26_0: NOT programming"
    }
    set fpga [lindex $devices 0]
    current_hw_device $fpga
    set_property PROGRAM.FILE $bit $fpga
    puts "M08_4_NEW_IMAGE_PROGRAM_ONCE_START"
    flush stdout
    program_hw_devices $fpga
    puts "M08_4_NEW_IMAGE_PROGRAM_ONCE_COMPLETE"
    flush stdout
    refresh_hw_device -update_hw_probes false $fpga
    set axilist [get_hw_axis -quiet]
    if {[llength $axilist]!=1 || [lindex $axilist 0] ne "hw_axi_1"} {
        error "M08.4 no uniquely recognized JTAG hw_axi_1 after programming"
    }
    set axi [lindex $axilist 0]
    reset_hw_axi $axi
    # A distinct 4KiB on-fabric scratch BRAM -- no PS or DDR addresses.
    m08_w $axi A0000000 55AA22DD
    m08_expect $axi A0000000 55AA22DD
    m08_expect $axi A0001000 4D303850
    m08_expect $axi A0001004 00020002
    m08_expect $axi A0001008 00000001
    m08_stage $axi 4294967295 $edge_words
    m08_dispatch $axi
    for {set j 0} {$j<64} {incr j} {
        set a [format %08X [expr {0xA0001100+4*$j}]]
        m08_expect $axi $a [lindex $edge_words $j]
    }
    m08_w $axi A0001014 00000008
    m08_expect $axi A000100C 00000012
    puts "M08_4_PHYSICAL_EDGE_PAGE_CONFIGURED_5"
    flush stdout
    set observations {}
    for {set tick 0} {$tick<4} {incr tick} {
        for {set page 0} {$page<6} {incr page} {
            set count [expr {$page==5?2:6}]
            lset backing($page) 63 [format %08X $tick]
            # Compare host-coalesced input current against independent fixture
            # before loading: NOT a claim of raw event fabric ingress.
            for {set local 0} {$local<$count} {incr local} {
                set neuron [expr {$page*6+$local}]
                set off [expr {$tick*128+$neuron*4}]
                set idx [expr {$local*10+4+$tick}]
                if {[lindex $backing($page) $idx] ne [lindex $golden $off]} {
                    error "M08.4 independent external-current input mismatch tick=$tick neuron=$neuron"
                }
                incr verified_inputs
            }
            m08_stage $axi $page $backing($page)
            m08_dispatch $axi
            # Compare EVERY post-compute fabric word BEFORE hardware SAVE.
            # Persist ACTUAL readback as host backing for next tick/eviction.
            for {set j 0} {$j<64} {incr j} {
                set address [format %08X [expr {0xA0001100+4*$j}]]
                set want [lindex $backing($page) $j]
                if {$j<$count*10} {
                    set local [expr {$j/10}]
                    set field [expr {$j%10}]
                    set neuron [expr {$page*6+$local}]
                    set off [expr {$tick*128+$neuron*4}]
                    if {$field==0} {
                        set want [lindex $golden [expr {$off+1}]]
                        incr verified_voltages
                    } elseif {$field==8} {
                        set fired [expr {[scan [lindex $golden [expr {$off+2}]] %x] & 1}]
                        set masks($neuron) [expr {$masks($neuron) | ($fired << $tick)}]
                        set want [format %08X $masks($neuron)]
                        incr verified_spikes
                    } elseif {$field==9} {
                        set want [lindex $golden [expr {$off+3}]]
                        incr verified_syn
                    }
                }
                set actual [m08_expect $axi $address $want]
                lset backing($page) $j $actual
                if {$j<$count*10 && ($j%10)==9} {
                    set local [expr {$j/10}]
                    set neuron [expr {$page*6+$local}]
                    set off [expr {$tick*128+$neuron*4}]
                    lappend observations "tick=$tick page=$page neuron=$neuron input=[lindex $golden $off] voltage=[lindex $backing($page) [expr {$local*10}]] mask=[lindex $backing($page) [expr {$local*10+8}]] recurrent=$actual"
                }
            }
            m08_w $axi A0001014 00000008
            m08_expect $axi A000100C 00000012
            incr saved_pages
            puts "M08_4_PHYSICAL_256B_LOAD_COMPUTE_FULL_DIRTY_SAVE|$tick|$page"
            flush stdout
        }
        puts "M08_4_PHYSICAL_ORDERED_TICK_BARRIER|$tick"
        flush stdout
    }
    if {$saved_pages!=24 || $verified_inputs!=128 ||
        $verified_voltages!=128 || $verified_spikes!=128 ||
        $verified_syn!=128 || [llength $observations]!=128} {
        error "M08.4 original physical comparison count mismatch"
    }
    set out [file join $hwdir 80_physical_paged_neural_parity.txt]
    set fd [open $out {WRONLY CREAT EXCL}]
    puts $fd {result=ONE_NEW_ORIGINAL_SIGNED16_32X4_ONE_RESIDENT_SIX_PAGE_PHYSICAL_PARITY}
    puts $fd "owner_bit_sha256=$ORIGINAL_SHA"
    puts $fd {genuine_kv260_jtag_program_count=1}
    puts $fd {external_raw_events=17}
    puts $fd {external_ingress=HOST_COALESCED_NOT_RAW_EVENT_FIFO}
    puts $fd {independently_checked_host_input_currents=128}
    puts $fd {independently_checked_fabric_voltages=128}
    puts $fd {independently_checked_fabric_spike_decisions=128}
    puts $fd {independently_checked_fabric_recurrent_currents=128}
    puts $fd {real_page_load_compute_dirty_save_dispatches=24}
    puts $fd {real_resident_neuron_banks=1}
    puts $fd {physical_ps_pl_ddr=NO}
    foreach row $observations {puts $fd $row}
    close $fd
    puts "M08_4_PHYSICAL_128_HOST_CURRENTS_384_FABRIC_COMPUTED_24_PAGES_ONE_BANK_PASS"
    flush stdout
} finally {
    if {$target_open} {catch {close_hw_target}}
    if {$server_open} {catch {disconnect_hw_server}}
    if {$hw_open} {catch {close_hw_manager}}
}
