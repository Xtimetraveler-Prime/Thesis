# P02.4b five-logical-core / three-resident-context physical DDR-backed run.
if {$argc != 5} {
    error "usage: p02_4b_five_over_three.tcl <bit> <ltx> <vectors.tcl> <result.txt> <hw_server_url>"
}

set bit_file [file normalize [lindex $argv 0]]
set ltx_file [file normalize [lindex $argv 1]]
set vector_file [file normalize [lindex $argv 2]]
set result_file [file normalize [lindex $argv 3]]
set hw_server_url [lindex $argv 4]
foreach path [list $bit_file $ltx_file $vector_file] {
    if {![file exists $path]} { error "P02.4b input missing: $path" }
}
source $vector_file

proc p02b_parse_hex {raw} {
    set text [string trim $raw]
    regsub -all {_} $text "" text
    if {[regexp -nocase {^0x([0-9a-f]+)$} $text -> digits]} { return [expr "0x$digits"] }
    if {[regexp -nocase {^[0-9a-f]+$} $text]} { return [expr "0x$text"] }
    error "P02.4b cannot parse HEX VIO value '$raw'"
}

proc p02b_expect {label actual expected} {
    if {$actual != $expected} {
        error "P02.4b mismatch $label: actual=0x[format %X $actual] expected=0x[format %X $expected]"
    }
}

proc p02b_probe {vio direction port} {
    set wanted [string tolower $direction]
    set matches {}
    foreach probe [get_hw_probes -of_objects $vio] {
        if {[string tolower [get_property TYPE $probe]] eq $wanted && [get_property PROBE_PORT $probe] == $port} {
            lappend matches $probe
        }
    }
    if {[llength $matches] != 1} {
        error "P02.4b probe lookup failed direction=$direction port=$port matches=[llength $matches]"
    }
    return [lindex $matches 0]
}

proc p02b_format_hex_output {probe value} {
    set bits [get_property PROBE_PORT_BIT_COUNT $probe]
    set chars [expr {($bits + 3) / 4}]
    set text [string trim $value]
    regsub -all {_} $text "" text
    if {[regexp -nocase {^0x([0-9a-f]+)$} $text -> digits]} {
        set numeric [expr "0x$digits"]
        set digits [string toupper $digits]
    } elseif {[regexp {^[0-9]+$} $text]} {
        set numeric [expr {$text + 0}]
        set digits [format %X $numeric]
    } else {
        error "P02.4b cannot format VIO output '$value'"
    }
    if {$numeric < 0 || $numeric >= (1 << $bits)} {
        error "P02.4b VIO output out of range value=$value bits=$bits"
    }
    return "[string repeat 0 [expr {$chars - [string length $digits]}]]$digits"
}

proc p02b_p08_commit {settings} {
    global P02B_DISPATCH_VIO
    foreach {port value} $settings {
        set probe [p02b_probe $P02B_DISPATCH_VIO vio_output $port]
        set_property OUTPUT_VALUE [p02b_format_hex_output $probe $value] $probe
    }
    commit_hw_vio $P02B_DISPATCH_VIO
}

proc p02b_p08_input {port} {
    global P02B_DISPATCH_VIO
    refresh_hw_vio $P02B_DISPATCH_VIO
    return [p02b_parse_hex [get_property INPUT_VALUE [p02b_probe $P02B_DISPATCH_VIO vio_input $port]]]
}

proc p02b_wait_p08 {port expected timeout_ms label} {
    set deadline [expr {[clock milliseconds] + $timeout_ms}]
    set actual -1
    while {[clock milliseconds] <= $deadline} {
        set actual [p02b_p08_input $port]
        if {$actual == $expected} { return }
        after 10
    }
    error "P02.4b timeout waiting for $label expected=$expected actual=$actual"
}

proc p02b_host_write {slot bank addr value} {
    p02b_p08_commit [list 6 0 7 1 8 $slot 9 $bank 10 $addr 11 $value]
    p02b_p08_commit [list 6 1]
    p02b_wait_p08 21 1 2000 "host write ack slot=$slot bank=$bank addr=$addr"
    set err [p02b_p08_input 23]
    p02b_p08_commit [list 6 0]
    if {$err != 0} { error "P02.4b host write failed slot=$slot bank=$bank addr=$addr" }
}

proc p02b_host_read {slot bank addr} {
    p02b_p08_commit [list 6 0 7 0 8 $slot 9 $bank 10 $addr 11 0]
    p02b_p08_commit [list 6 1]
    p02b_wait_p08 21 1 2000 "host read ack slot=$slot bank=$bank addr=$addr"
    set valid [p02b_p08_input 22]
    set err [p02b_p08_input 23]
    set value [p02b_p08_input 24]
    p02b_p08_commit [list 6 0]
    if {$err != 0 || $valid != 1} {
        error "P02.4b host read failed slot=$slot bank=$bank addr=$addr valid=$valid error=$err"
    }
    return $value
}

proc p02b_verify_static_resident_image {core slot} {
    global P02B_EXPECT_CONFIG0 P02B_EXPECT_AXON_INDEX P02B_EXPECT_AXON_WORD
    global P02B_EXPECT_SYNAPSE0 P02B_EXPECT_ROUTE_DESC0 P02B_EXPECT_ROUTE0

    set config_actual [p02b_host_read $slot 0 0]
    set config_expected [p02b_parse_hex $P02B_EXPECT_CONFIG0($core)]
    p02b_expect "resident config core=$core slot=$slot" $config_actual $config_expected

    set axon_index $P02B_EXPECT_AXON_INDEX($core)
    set axon_actual [p02b_host_read $slot 2 $axon_index]
    set axon_expected [p02b_parse_hex $P02B_EXPECT_AXON_WORD($core)]
    p02b_expect "resident axon core=$core slot=$slot addr=$axon_index" $axon_actual $axon_expected

    set synapse_actual [p02b_host_read $slot 3 0]
    set synapse_expected [p02b_parse_hex $P02B_EXPECT_SYNAPSE0($core)]
    p02b_expect "resident synapse core=$core slot=$slot" $synapse_actual $synapse_expected

    set route_desc_actual [p02b_host_read $slot 4 0]
    set route_desc_expected [p02b_parse_hex $P02B_EXPECT_ROUTE_DESC0($core)]
    p02b_expect "resident route descriptor core=$core slot=$slot" $route_desc_actual $route_desc_expected

    set route_actual [p02b_host_read $slot 5 0]
    set route_expected [p02b_parse_hex $P02B_EXPECT_ROUTE0($core)]
    p02b_expect "resident route core=$core slot=$slot" $route_actual $route_expected

    puts "PASS: P02.4b resident static image verified logical_core=$core slot=$slot"
}

proc p02b_verify_initial_resident_image {core slot} {
    global P02B_EXPECT_INITIAL_STATE0
    p02b_verify_static_resident_image $core $slot

    set state_actual [p02b_host_read $slot 1 0]
    set state_expected [p02b_parse_hex $P02B_EXPECT_INITIAL_STATE0($core)]
    p02b_expect "initial resident state core=$core slot=$slot" $state_actual $state_expected

    puts "PASS: P02.4b initial resident image verified logical_core=$core slot=$slot"
}


proc p02b_page_input {port} {
    global P02B_PAGE_VIO
    refresh_hw_vio $P02B_PAGE_VIO
    set raw [get_property INPUT_VALUE [p02b_probe $P02B_PAGE_VIO vio_input $port]]
    return [expr {wide($raw)}]
}

proc p02b_page_commit {settings} {
    global P02B_PAGE_VIO
    foreach {port value} $settings {
        set probe [p02b_probe $P02B_PAGE_VIO vio_output $port]
        set_property OUTPUT_VALUE [expr {wide($value)}] $probe
    }
    commit_hw_vio $P02B_PAGE_VIO
}

proc p02b_page_transfer {page_out mutable_only slot record_base label} {
    global P02B_PAGE_INS P02B_PAGE_OUTS P02B_PAGE_VIO

    # Port-B ownership must be fully released by the debug path before paging.
    p02b_wait_p08 20 0 2000 "debug idle before page $label"

    set completed_before [p02b_page_input 4]
    set read_before [p02b_page_input 9]
    set write_before [p02b_page_input 10]
    set axi_before [p02b_page_input 11]

    p02b_page_commit [list 0 0 1 $page_out 2 $mutable_only 3 $slot 4 $record_base]
    p02b_page_commit [list 0 1]
    after 10
    p02b_page_commit [list 0 0]

    set complete 0
    for {set poll 0} {$poll < 3000} {incr poll} {
        refresh_hw_vio $P02B_PAGE_VIO
        foreach err_port {6 7 8 12 13} {
            set value [expr {wide([get_property INPUT_VALUE [p02b_probe $P02B_PAGE_VIO vio_input $err_port]])}]
            if {$value != 0} { error "P02.4b $label page error port=$err_port" }
        }
        if {[p02b_page_input 4] > $completed_before} {
            set complete 1
            break
        }
        after 10
    }
    if {!$complete} { error "P02.4b $label page transfer timeout" }
    p02b_expect "$label start_blocked" [p02b_page_input 2] 0

    set bytes [p02b_page_input 3]
    set read_after [p02b_page_input 9]
    set write_after [p02b_page_input 10]
    set axi_after [p02b_page_input 11]

    if {!$page_out} {
        set expected_bytes 438272
        set expected_read 1712
        set expected_write 0
        incr P02B_PAGE_INS
    } else {
        if {!$mutable_only} { error "P02.4b runtime only permits mutable-only page-out" }
        set expected_bytes 106496
        set expected_read 0
        set expected_write 416
        incr P02B_PAGE_OUTS
    }
    p02b_expect "$label semantic bytes" $bytes $expected_bytes
    p02b_expect "$label read bursts" [expr {$read_after - $read_before}] $expected_read
    p02b_expect "$label write bursts" [expr {$write_after - $write_before}] $expected_write
    p02b_expect "$label AXI bytes" [expr {$axi_after - $axi_before}] $expected_bytes
}

proc p02b_ensure_resident {core} {
    global P02B_RECORD_BASE
    global P02B_SLOT_CORE P02B_SLOT_DIRTY P02B_VICTIM_CURSOR
    global P02B_EVICTIONS P02B_PAGE_HITS

    for {set slot 0} {$slot < 3} {incr slot} {
        if {$P02B_SLOT_CORE($slot) == $core} {
            incr P02B_PAGE_HITS
            return $slot
        }
    }

    set slot $P02B_VICTIM_CURSOR
    set evicted $P02B_SLOT_CORE($slot)
    if {$evicted >= 0} {
        incr P02B_EVICTIONS
        if {$P02B_SLOT_DIRTY($slot)} {
            set label [format "evict_core%d_slot%d" $evicted $slot]
            p02b_page_transfer 1 1 $slot $P02B_RECORD_BASE($evicted) $label
            set P02B_SLOT_DIRTY($slot) 0
        }
    }

    set label [format "load_core%d_slot%d" $core $slot]
    p02b_page_transfer 0 0 $slot $P02B_RECORD_BASE($core) $label
    set P02B_SLOT_CORE($slot) $core
    set P02B_SLOT_DIRTY($slot) 0
    p02b_verify_static_resident_image $core $slot
    set P02B_VICTIM_CURSOR [expr {($P02B_VICTIM_CURSOR + 1) % 3}]
    return $slot
}

proc p02b_decode_packet {word} {
    return [list         [expr {($word >> 61) & 1}]         [expr {$word & 0x7F}]         [expr {($word >> 7) & 0xFFF}]         [expr {($word >> 19) & 0x3FF}]         [expr {($word >> 29) & 0xFFFFFFFF}]]
}

proc p02b_metadata {core event_count} {
    global P02B_COMPARTMENT_COUNT P02B_SYNAPSE_COUNT P02B_ROUTE_COUNT
    return [expr {
        $core |
        ($P02B_COMPARTMENT_COUNT($core) << 7) |
        ($P02B_SYNAPSE_COUNT($core) << 18) |
        ($P02B_ROUTE_COUNT($core) << 34) |
        ($event_count << 47)
    }]
}

proc p02b_dispatch {timestep core slot event_bank event_count} {
    global P02B_EXPECT_EVENT_COUNT P02B_EXPECT_STATE P02B_EXPECT_SPIKES P02B_EXPECT_PACKETS
    global P02B_SLOT_DIRTY P02B_DISPATCHES

    set key "$timestep,$core"
    p02b_expect "event count t=$timestep core=$core" $event_count $P02B_EXPECT_EVENT_COUNT($key)

    p02b_wait_p08 20 0 2000 "debug idle before dispatch t=$timestep core=$core"
    set dispatch_before [p02b_p08_input 8]
    set metadata [p02b_metadata $core $event_count]
    p02b_p08_commit [list 2 $slot 3 $metadata 4 $timestep 5 $event_bank 0 0]
    p02b_p08_commit [list 0 1]
    after 1
    p02b_p08_commit [list 0 0]
    p02b_wait_p08 8 [expr {$dispatch_before + 1}] 30000 "dispatch t=$timestep core=$core"

    p02b_expect "active slot" [p02b_p08_input 3] $slot
    p02b_expect "active logical core" [p02b_p08_input 4] $core
    p02b_expect "event bank" [p02b_p08_input 5] $event_bank
    p02b_expect "latched status" [p02b_p08_input 7] 0
    foreach port {11 12 13 26 27} {
        p02b_expect "dispatch error port=$port" [p02b_p08_input $port] 0
    }

    p02b_expect "spike count" [p02b_p08_input 17] $P02B_EXPECT_SPIKES($key)
    set expected_packets $P02B_EXPECT_PACKETS($key)
    set packet_count [p02b_p08_input 6]
    p02b_expect "packet count" $packet_count [llength $expected_packets]

    set actual_packets {}
    for {set addr 0} {$addr < $packet_count} {incr addr} {
        set actual [p02b_host_read $slot 8 $addr]
        set expected [p02b_parse_hex [lindex $expected_packets $addr]]
        p02b_expect "packet t=$timestep core=$core addr=$addr" $actual $expected
        lappend actual_packets $actual
    }

    set actual_state [p02b_host_read $slot 1 0]
    set expected_state [p02b_parse_hex $P02B_EXPECT_STATE($key)]
    p02b_expect "state t=$timestep core=$core" $actual_state $expected_state

    set P02B_SLOT_DIRTY($slot) 1
    incr P02B_DISPATCHES
    return $actual_packets
}

open_hw_manager
connect_hw_server -url $hw_server_url
open_hw_target

set P02B_DEVICE ""
foreach device [get_hw_devices] {
    set name [string tolower [get_property NAME $device]]
    set part ""
    catch {set part [string tolower [get_property PART $device]]}
    if {[string match "*xck26*" $name] || [string match "*xczu5*" $name] ||
        [string match "*xck26*" $part] || [string match "*xczu5*" $part]} {
        set P02B_DEVICE $device
        break
    }
}
if {$P02B_DEVICE eq ""} { error "P02.4b could not identify K26 device" }
current_hw_device $P02B_DEVICE
refresh_hw_device $P02B_DEVICE

set_property PROGRAM.FILE $bit_file $P02B_DEVICE
set_property PROBES.FILE $ltx_file $P02B_DEVICE
catch {set_property FULL_PROBES.FILE $ltx_file $P02B_DEVICE}
program_hw_devices $P02B_DEVICE
refresh_hw_device $P02B_DEVICE

set P02B_DISPATCH_VIO ""
set P02B_PAGE_VIO ""
foreach vio [get_hw_vios -of_objects $P02B_DEVICE] {
    set cell ""
    set name ""
    catch {set cell [get_property CELL_NAME $vio]}
    catch {set name [get_property NAME $vio]}
    if {[string match "*vio_p08*" $cell] || [string match "*vio_p08*" $name]} { set P02B_DISPATCH_VIO $vio }
    if {[string match "*vio_p02_page*" $cell] || [string match "*vio_p02_page*" $name]} { set P02B_PAGE_VIO $vio }
}
if {$P02B_DISPATCH_VIO eq ""} { error "P02.4b could not find vio_p08" }
if {$P02B_PAGE_VIO eq ""} { error "P02.4b could not find vio_p02_page" }

foreach probe [get_hw_probes -of_objects $P02B_DISPATCH_VIO] {
    set type [string tolower [get_property TYPE $probe]]
    if {$type eq "vio_input"} { set_property INPUT_VALUE_RADIX HEX $probe }
    if {$type eq "vio_output"} { set_property OUTPUT_VALUE_RADIX HEX $probe }
}
foreach probe [get_hw_probes -of_objects $P02B_PAGE_VIO] {
    set type [string tolower [get_property TYPE $probe]]
    if {$type eq "vio_input"} { set_property INPUT_VALUE_RADIX UNSIGNED $probe }
    if {$type eq "vio_output"} { set_property OUTPUT_VALUE_RADIX UNSIGNED $probe }
}

reset_hw_vio_outputs $P02B_DISPATCH_VIO
reset_hw_vio_outputs $P02B_PAGE_VIO
refresh_hw_vio -update_output_values $P02B_DISPATCH_VIO
refresh_hw_vio -update_output_values $P02B_PAGE_VIO

p02b_p08_commit [list 1 1]
after 20
p02b_p08_commit [list 1 0]
after 20
p02b_expect "resetn released" [p02b_p08_input 28] 1

array set P02B_SLOT_CORE {0 -1 1 -1 2 -1}
array set P02B_SLOT_DIRTY {0 0 1 0 2 0}
set P02B_VICTIM_CURSOR 0
set P02B_PAGE_INS 0
set P02B_PAGE_OUTS 0
set P02B_EVICTIONS 0
set P02B_PAGE_HITS 0
set P02B_DISPATCHES 0
set P02B_ROUTED_PACKETS 0
set P02B_BARRIERS 0
array set P02B_EVENT_COUNT {}
for {set core 0} {$core < 5} {incr core} {
    set P02B_EVENT_COUNT($core,0) 0
    set P02B_EVENT_COUNT($core,1) 0
}

for {set slot 0} {$slot < 3} {incr slot} {
    set core [lindex $P02B_INITIAL_RESIDENCY $slot]
    set label [format "initial_core%d_slot%d" $core $slot]
    p02b_page_transfer 0 0 $slot $P02B_RECORD_BASE($core) $label
    set P02B_SLOT_CORE($slot) $core
    p02b_verify_initial_resident_image $core $slot
}
puts "PASS: P02.4b initial residency logical={0 1 2} physical_slots=3"

for {set timestep 0} {$timestep < $P02B_TIMESTEPS} {incr timestep} {
    set current_bank [expr {$timestep & 1}]
    set next_bank [expr {1 - $current_bank}]
    set routed_words {}

    foreach core $P02B_SERVICE_ORDER {
        set slot [p02b_ensure_resident $core]

        set addr $P02B_EVENT_COUNT($core,$current_bank)
        set event_bank_id [expr {$current_bank ? 9 : 6}]
        p02b_host_write $slot $event_bank_id $addr $P02B_EXTERNAL_AXON($core)
        set event_readback [p02b_host_read $slot $event_bank_id $addr]
        p02b_expect "external event readback t=$timestep core=$core slot=$slot"             $event_readback $P02B_EXTERNAL_AXON($core)
        incr P02B_EVENT_COUNT($core,$current_bank)
        set P02B_SLOT_DIRTY($slot) 1

        set packets [p02b_dispatch $timestep $core $slot $current_bank $P02B_EVENT_COUNT($core,$current_bank)]
        foreach word $packets { lappend routed_words $word }
        set P02B_EVENT_COUNT($core,$current_bank) 0
    }

    foreach word $routed_words {
        lassign [p02b_decode_packet $word] valid dest axon source target
        p02b_expect "packet valid t=$timestep" $valid 1
        p02b_expect "packet target t=$timestep" $target [expr {$timestep + 1}]
        if {$dest < 0 || $dest >= 5} { error "P02.4b packet destination core out of range: $dest" }

        set slot [p02b_ensure_resident $dest]
        set addr $P02B_EVENT_COUNT($dest,$next_bank)
        if {$addr >= 4096} { error "P02.4b next-event overflow core=$dest" }
        set next_bank_id [expr {$next_bank ? 9 : 6}]
        p02b_host_write $slot $next_bank_id $addr $axon
        incr P02B_EVENT_COUNT($dest,$next_bank)
        set P02B_SLOT_DIRTY($slot) 1
        incr P02B_ROUTED_PACKETS
    }

    for {set core 0} {$core < 5} {incr core} {
        if {$timestep + 1 < $P02B_TIMESTEPS} {
            set key "[expr {$timestep + 1}],$core"
            set expected_next [expr {$P02B_EXPECT_EVENT_COUNT($key) - 1}]
        } else {
            set expected_next [llength $P02B_FINAL_NEXT_EVENTS($core)]
        }
        p02b_expect "next event count t=$timestep core=$core" $P02B_EVENT_COUNT($core,$next_bank) $expected_next
    }

    incr P02B_BARRIERS
    puts "PASS: P02.4b barrier timestep=$timestep dispatches=$P02B_DISPATCHES routed_packets=$P02B_ROUTED_PACKETS"
}

for {set slot 0} {$slot < 3} {incr slot} {
    set core $P02B_SLOT_CORE($slot)
    if {$core >= 0 && $P02B_SLOT_DIRTY($slot)} {
        set label [format "final_flush_core%d_slot%d" $core $slot]
        p02b_page_transfer 1 1 $slot $P02B_RECORD_BASE($core) $label
        set P02B_SLOT_DIRTY($slot) 0
    }
}

p02b_expect "completed dispatches" [p02b_p08_input 8] 35
p02b_expect "barrier count" $P02B_BARRIERS $P02B_TIMESTEPS
if {$P02B_EVICTIONS <= 0} { error "P02.4b did not exercise any resident eviction" }

set page_completed [p02b_page_input 4]
set read_bursts [p02b_page_input 9]
set write_bursts [p02b_page_input 10]
set axi_bytes [p02b_page_input 11]
set pending [p02b_page_input 14]
set expected_page_completed [expr {$P02B_PAGE_INS + $P02B_PAGE_OUTS}]
set expected_read_bursts [expr {$P02B_PAGE_INS * 1712}]
set expected_write_bursts [expr {$P02B_PAGE_OUTS * 416}]
set expected_axi_bytes [expr {($expected_read_bursts + $expected_write_bursts) * 256}]

p02b_expect "page transfer count" $page_completed $expected_page_completed
p02b_expect "aggregate read bursts" $read_bursts $expected_read_bursts
p02b_expect "aggregate write bursts" $write_bursts $expected_write_bursts
p02b_expect "aggregate AXI bytes" $axi_bytes $expected_axi_bytes
p02b_expect "pending write bytes" $pending 0

set result [open $result_file w]
puts $result "schema=p02-4b-five-over-three-physical-v1"
puts $result "logical_core_count=5"
puts $result "resident_context_count=3"
puts $result "physical_engine_count=1"
puts $result "timesteps=$P02B_TIMESTEPS"
puts $result "completed_dispatches=$P02B_DISPATCHES"
puts $result "barriers=$P02B_BARRIERS"
puts $result "routed_packets=$P02B_ROUTED_PACKETS"
puts $result "page_ins=$P02B_PAGE_INS"
puts $result "page_outs=$P02B_PAGE_OUTS"
puts $result "evictions=$P02B_EVICTIONS"
puts $result "page_hits=$P02B_PAGE_HITS"
puts $result "axi_read_bursts=$read_bursts"
puts $result "axi_write_bursts=$write_bursts"
puts $result "axi_bytes=$axi_bytes"
puts $result "authoritative_backing=k26-ddr"
puts $result "result=PASS"
close $result

puts "P02_4B_DISPATCHES=$P02B_DISPATCHES"
puts "P02_4B_BARRIERS=$P02B_BARRIERS"
puts "P02_4B_ROUTED_PACKETS=$P02B_ROUTED_PACKETS"
puts "P02_4B_PAGE_INS=$P02B_PAGE_INS"
puts "P02_4B_PAGE_OUTS=$P02B_PAGE_OUTS"
puts "P02_4B_EVICTIONS=$P02B_EVICTIONS"
puts "P02_4B_PAGE_HITS=$P02B_PAGE_HITS"
puts "P02_4B_AXI_READ_BURSTS=$read_bursts"
puts "P02_4B_AXI_WRITE_BURSTS=$write_bursts"
puts "P02_4B_AXI_BYTES=$axi_bytes"
puts "PASS: P02.4b five-over-three physical execution completed with K26 DDR authoritative"

close_hw_manager
