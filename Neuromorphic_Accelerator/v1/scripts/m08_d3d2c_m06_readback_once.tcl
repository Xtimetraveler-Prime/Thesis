# D3.D.2C: STAGED one-shot JTAG M06 32-neuron neural readback, NO APPROVED IMAGE.
# This Tcl cannot pass until NEW original owner DRC/timing/image hash reviewed,
# RELEASED_SHA below replaced with exact new approved SHA, and shell reviewer
# independently accepts the immutable original 12-file SHA ledger.
# NEVER reuse D3.D.2B image or waive its seven debug warnings.
set RELEASED_SHA "UNREVIEWED_M08_D3D2C_OWNER_IMAGE"
if {![regexp {^[a-f0-9]{64}$} $RELEASED_SHA]} {
    error "D3.D.2C HARD STOP: first owner native image NOT RELEASED"
}
if {![info exists ::env(M08_D3D2C_ALLOW_PROGRAM)] ||
    $::env(M08_D3D2C_ALLOW_PROGRAM) ne "YES"} {
    error "D3.D.2C owner explicit program authorization missing"
}
foreach key {M08_D3D2C_BIT M08_D3D2C_VECTORS M08_D3D2C_RESULT M08_D3D2C_EXPECTED_SHA} {
    if {![info exists ::env($key)] || [string trim $::env($key)] eq ""} {
        error "Missing exact staged physical input $key"
    }
}
if {![string match "2025.2*" [version -short]]} {
    error "Genuine Vivado 2025.2 required"
}
set bit [file normalize $::env(M08_D3D2C_BIT)]
set source [file normalize $::env(M08_D3D2C_VECTORS)]
set result [file normalize $::env(M08_D3D2C_RESULT)]
set digest [string tolower $::env(M08_D3D2C_EXPECTED_SHA)]
set base [file normalize [file join $::env(HOME) Thesis_Evidence M08]]
set native [file dirname [file dirname $bit]]
set hw [file dirname $result]
if {[file tail $bit] ne "m08_d3d2c_m06_lif_jtag_UNRELEASED.bit" ||
    ![regexp {^m08_d3d2c_m06_[A-Za-z0-9]+$} [file tail $native]] ||
    [file dirname $native] ne $base ||
    ![regexp {^m08_d3d2c_m06_HW_[A-Za-z0-9]+$} [file tail $hw]] ||
    [file dirname $hw] ne $base ||
    [file tail $source] ne "10_m06_32x4_golden.hex" ||
    [file dirname $source] ne $hw ||
    [file tail $result] ne "80_m06_32x4_hw_parity.txt" ||
    ![file isdirectory $hw] || [file exists $result]} {
    error "Noncanonical original owner native / isolated physical folder"
}
if {$digest ne $RELEASED_SHA || ![file isfile $bit] ||
    ![file isfile $source] || [file type $bit] ne "file" ||
    [file type $source] ne "file" ||
    [file size $bit] < 100000 || [file size $source] > 9000} {
    error "D3.D.2C is NOT an independently approved owner bitstream"
}
set real [string tolower [lindex [exec sha256sum -- $bit] 0]]
if {$real ne $RELEASED_SHA} {error "New bitstream differs from accepted first owner"}
set fh [open $source RDONLY]
set lines [split [string trim [read $fh]] "\n"]
close $fh
if {[llength $lines] != 579} {
    error "Wrong complete original M06 32x4 neural oracle words"
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
proc d2c_write {axi address data} {
    global txn_counter
    incr txn_counter
    set x [create_hw_axi_txn d2c_w_$txn_counter $axi -type WRITE -address $address -len 1 -data $data]
    run_hw_axi $x
}
proc d2c_read {axi address} {
    global txn_counter
    incr txn_counter
    set x [create_hw_axi_txn d2c_r_$txn_counter $axi -type READ -address $address -len 1]
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
puts "M08_D3D2C_ACCEPTED_IMAGE_HASH|$real"
puts "M08_D3D2C_M06_TRIPLE_ORACLE_579_WORDS_VERIFIED"
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
        puts "M08_D3D2C_DEVICE|[get_property NAME $d]|[get_property PART $d]"
        if {[get_property NAME $d] eq "xck26_0" &&
            [regexp {^xck26($|-)} [get_property PART $d]]} {lappend matches $d}
    }
    if {[llength $matches] != 1} {error "No unique K26 device; NO PROGRAM"}
    set fpga [lindex $matches 0]
    current_hw_device $fpga
    set_property PROGRAM.FILE $bit $fpga
    puts {M08_D3D2C_PROGRAM_START}
    flush stdout
    program_hw_devices $fpga
    puts {M08_D3D2C_PROGRAM_COMPLETED}
    refresh_hw_device -update_hw_probes false $fpga
    set axis [get_hw_axis -quiet]
    if {[llength $axis] != 1 || [lindex $axis 0] ne "hw_axi_1"} {
        error "Missing unique postprogram hw_axi_1"
    }
    set axi [lindex $axis 0]
    reset_hw_axi $axi
    d2c_write $axi A0000000 55AA22DD
    if {[d2c_read $axi A0000000] ne "55AA22DD"} {
        error "BRAM regression failed; no neural computation attempted"
    }
    puts {M08_D3D2C_BRAM_TRANSPORT_PASS}
    if {[d2c_read $axi A0001000] ne "4D33324E" ||
        [d2c_read $axi A0001004] ne "00040000"} {
        error "Wrong 32-neuron engine magic/version"
    }
    puts {M08_D3D2C_M32N_V4_IDENTITY_PASS}
    d2c_write $axi A000100C [lindex $lines 0]
    d2c_write $axi A0001010 [lindex $lines 1]
    d2c_write $axi A0001020 [lindex $lines 2]
    for {set n 0} {$n < 32} {incr n} {
        for {set j 0} {$j < 8} {incr j} {
            set address [format %08X [expr {0xA0001100+$n*32+$j*4}]]
            d2c_write $axi $address [lindex $lines [expr {3+$n*8+$j}]]
        }
    }
    # Only original five ACTIVE M06 edges; unused edge delay zero is illegal.
    for {set e 0} {$e < 5} {incr e} {
        for {set j 0} {$j < 4} {incr j} {
            set address [format %08X [expr {0xA0001500+$e*16+$j*4}]]
            d2c_write $axi $address [lindex $lines [expr {259+$e*4+$j}]]
        }
    }
    d2c_write $axi A0001014 00000001
    set completed 0
    for {set attempt 0} {$attempt < 30} {incr attempt} {
        set status [d2c_read $axi A0001008]
        if {$status eq "00000001"} {set completed 1; break}
        if {$status ne "00000002"} {error "M06 32-neuron invalid compute status"}
        after 10
    }
    if {!$completed} {error "M06 32-neuron compute timeout"}
    if {[d2c_read $axi A0001018] ne [lindex $lines 0] ||
        [d2c_read $axi A000101C] ne "00000001"} {
        error "M06 DONE nonce/count differs from accepted source"
    }
    set result_lines {}
    for {set n 0} {$n < 32} {incr n} {
        set voltages {}
        set synaptic {}
        set offset [expr {291+$n*9}]
        for {set j 0} {$j < 4} {incr j} {
            set addr [format %08X [expr {0xA0001900+$n*32+$j*4}]]
            set actual [d2c_read $axi $addr]
            if {$actual ne [lindex $lines [expr {$offset+$j}]]} {
                error "M06 physical voltage mismatch n=$n t=$j got=$actual"
            }
            lappend voltages $actual
            set saddr [format %08X [expr {0xA0001D00+($n*4+$j)*4}]]
            set actualsyn [d2c_read $axi $saddr]
            if {$actualsyn ne [lindex $lines [expr {$offset+5+$j}]]} {
                error "M06 physical delivered recurrent current mismatch n=$n t=$j got=$actualsyn"
            }
            lappend synaptic $actualsyn
        }
        set maskaddr [format %08X [expr {0xA0001900+$n*32+16}]]
        set mask [d2c_read $axi $maskaddr]
        if {$mask ne [lindex $lines [expr {$offset+4}]]} {
            error "M06 physical spike mask mismatch n=$n got=$mask"
        }
        lappend result_lines "neuron=$n voltages=[join $voltages ,] mask=$mask synaptic_currents=[join $synaptic ,]"
        puts "M08_D3D2C_M06_REAL_NEURON_PARITY|$n"
        flush stdout
    }
    set fh [open $result {WRONLY CREAT EXCL}]
    puts $fh {schema=m08-d3d2c-m06-32-neuron-hardware-v1}
    puts $fh {result=ONE_ORIGINAL_M06_32X4_RECURRENT_HARDWARE_PARITY}
    puts $fh "candidate_sha256=$real"
    puts $fh "target=$target_path"
    puts $fh {device=xck26_0}
    puts $fh {debug_axi=hw_axi_1}
    puts $fh {external_events_coalesced_on_host=YES}
    puts $fh {physical_ddr_m06_hls_verified=NO}
    foreach line $result_lines {puts $fh $line}
    close $fh
    puts {M08_D3D2C_PHYSICAL_M06_128_VOLTAGE_128_SPIKE_128_SYN_CURRENT_PASS}
} finally {
    if {$target_open} {catch {close_hw_target}}
    if {$server_open} {catch {disconnect_hw_server}}
    if {$hw_open} {catch {close_hw_manager}}
}
