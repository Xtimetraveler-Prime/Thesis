# P07-B.5.3 experimental new RAW-trace A53 26-tick launcher.
# Executed ONLY by p07_b5_raw_physical_capture.py with explicit new approvals
# AFTER original 27x512KiB + signed 16K + 80K + 896K + TRAIN ingress
# were physically read back in the SAME dedicated JTAG session.
# NOT approved by Vitis compiler/offline admission or old B4m V3 approvals.
# DESTRUCTIVE: Linux ownership, A53 low DDR [0,0x00107BC0),
# new mailbox [0x43FF0100,0x43FF0200), trace [0x42000000,0x420CD280).
# Unproven boot firmware and trace DDR ownership MUST be accepted separately.
# ALWAYS cold power-cycle after EVERY attempt, never resume halted Linux.
set TOKEN "B5_RAW_A53_NEW_DDR_TRACE_AND_MAILBOX_EXPLICITLY_APPROVED"
set EXPECTED_SHA "0e018a9cabf45b7e65a366b9e21df0cc90cb5b072053cac8c19d2f601be1d2cf"
if {$argc != 6 || [lindex $argv 0] ne $TOKEN} {
    error "B5 RAW: require exact operator contract token, ELF, 256-zero, mailbox path, trace path, local XSDB"
}
set elf [file normalize [lindex $argv 1]]
set zero [file normalize [lindex $argv 2]]
set mailbox [file normalize [lindex $argv 3]]
set trace [file normalize [lindex $argv 4]]
set server [lindex $argv 5]
if {![regexp {^tcp:(localhost|127[.]0[.]0[.]1):[0-9]{2,5}$} $server]} {
    error "B5 RAW: localhost XSDB only"
}
if {[file tail $elf] ne "p07_b5_raw_trace_v1.elf" ||
    ![file isfile $elf] || [file size $elf]<100000 ||
    ![file isfile $zero] || [file size $zero]!=256 ||
    [file exists $mailbox] || [file exists $trace] ||
    [file exists "${mailbox}.zero_readback"] || [file exists "${mailbox}.poll"] ||
    ![file isdirectory [file dirname $mailbox]] ||
    ![file isdirectory [file dirname $trace]]} {
    error "B5 RAW: ELF/zero input or evidence path not fresh/valid"
}
if {[catch {exec grep -aFq P07_B5_A53_TRAIN_RAW_TRACE_DIAGNOSTIC_V1 $elf}]} {
    error "B5 RAW: distinct A53 firmware identity missing"
}
if {[lindex [exec sha256sum $elf] 0] ne $EXPECTED_SHA} {
    error "B5 RAW: actual ELF SHA not pinned to operator-admitted artifact"
}
foreach old {P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V3
             P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V2
             P07_B4M_A53_TRAIN_26_TICK_CANDIDATE_V1} {
    if {![catch {exec grep -aFq $old $elf}]} {
        error "B5 RAW: legacy V3/V2/V1 firmware identity survived"
    }
}
proc b5_read {p} {
    set f [open $p rb]
    fconfigure $f -translation binary -encoding binary
    set data [read $f]
    close $f
    return $data
}
if {[b5_read $zero] ne [string repeat "\x00" 256]} {
    error "B5 RAW: only EXACT 256 all-zero mailbox initialization allowed"
}
proc b5_ps_only {} {
    foreach target {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$target\""}]} {return}
    }
    error "B5 RAW: missing physical PSU/APU target"
}
proc b5_stop_cpu0 {label} {
    targets -set -filter {name =~ "Cortex-A53 #0"}
    if {[catch {stop} message]} {
        if {[string trim $message] ne "Already stopped"} {
            error "B5 RAW: A53 halt ${label} failed: $message"
        }
    }
    puts "P07_B5_RAW_A53_${label}_STOPPED=1"
}
set connected 0
set failed [catch {
    connect -url $server
    set connected 1
    b5_stop_cpu0 PRE_RESET
    rst -processor
    b5_ps_only
    dow -data $zero 0x43FF0100
    mrd -bin -file "${mailbox}.zero_readback" 0x43FF0100 64
    if {[b5_read "${mailbox}.zero_readback"] ne [b5_read $zero]} {
        error "B5 RAW: physical 256B B5 mailbox zero readback mismatch"
    }
    puts "P07_B5_RAW_NEW_256B_MAILBOX_ZERO_PHYSICAL_READBACK_PASS=1"
    targets -set -filter {name =~ "Cortex-A53 #0"}
    dow $elf
    puts "P07_B5_RAW_NEW_A53_ELF_DOWNLOADED=1"
    con
    set poll "${mailbox}.poll"
    set terminal 0
    for {set attempt 0} {$attempt<1800} {incr attempt} {
        after 1000
        b5_ps_only
        if {[file exists $poll]} {file delete $poll}
        mrd -bin -file $poll 0x43FF0100 64
        set msg [b5_read $poll]
        if {[string length $msg]!=256} {
            error "B5 RAW: physical mailbox truncated"
        }
        binary scan $msg @252i done
        if {[expr {$done & 0xFFFFFFFF}]==0xC0DEF00D} {
            set terminal 1
            break
        }
    }
    if {![file exists $poll]} {error "B5 RAW: no physical mailbox captured"}
    file rename $poll $mailbox
    b5_stop_cpu0 POST_CAPTURE
    puts "P07_B5_RAW_NEW_256B_PHYSICAL_MAILBOX_CAPTURED=1"
    if {!$terminal} {error "B5 RAW: bounded 26-tick timeout; REBOOT"}
    puts "P07_B5_RAW_NEW_A53_TERMINAL_DONE_PHYSICALLY_OBSERVED=1"
    set raw_mailbox [b5_read $mailbox]
    binary scan $raw_mailbox i* words
    if {[llength $words]!=64 ||
        ([lindex $words 0] & 0xFFFFFFFF)!=0x42355331 ||
        ([lindex $words 2] & 0xFFFFFFFF)!=0x600D600D ||
        ([lindex $words 47] & 0xFFFFFFFF)!=0x42354331 ||
        ([lindex $words 51] & 0xFFFFFFFF)!=26260 ||
        ([lindex $words 52] & 0xFFFFFFFF)!=210080 ||
        ([lindex $words 53] & 0xFFFFFFFF)!=0x42000000 ||
        ([lindex $words 54] & 0xFFFFFFFF)!=0x420CD280 ||
        ([lindex $words 55] & 0xFFFFFFFF)!=0 ||
        ([lindex $words 56] & 0xFFFFFFFF)!=1} {
        error "B5 RAW: terminal mailbox is not a genuine successful complete raw capture; REBOOT"
    }
    puts "P07_B5_RAW_NEW_COMPLETE_CAPTURE_RECEIPT_PHYSICAL_PASS=1"
    # Memory readback is via real PSU/APU physical debug access ONLY.
    # Chunk to bound XSDB binary-read payload sizes and check every chunk.
    set destination [open $trace {WRONLY CREAT EXCL}]
    fconfigure $destination -translation binary -encoding binary
    set ok 0
    set rc [catch {
        set total 210080
        for {set offset 0} {$offset<$total} {incr offset 4096} {
            set words [expr {min(4096,$total-$offset)}]
            set address [format {0x%08X} [expr {0x42000000+4*$offset}]]
            set chunk "${trace}.chunk"
            if {[file exists $chunk]} {file delete $chunk}
            b5_ps_only
            mrd -bin -file $chunk $address $words
            set raw [b5_read $chunk]
            if {[string length $raw]!=4*$words} {
                error "B5 RAW: wrong real physical trace chunk length"
            }
            puts -nonewline $destination $raw
            file delete $chunk
        }
        set ok 1
    } reason]
    close $destination
    if {$rc || !$ok || [file size $trace]!=840320} {
        error "B5 RAW: incomplete physical sidecar, no parity accepted: $reason"
    }
    puts "P07_B5_RAW_840320_BYTE_PSU_PHYSICAL_TRACE_READBACK_CAPTURED=1"
} reason]
if {$connected} {catch {disconnect}}
if {$failed} {
    puts "P07_B5_RAW_PHYSICAL_ATTEMPT_FAILED_REBOOT_REQUIRED=1"
    error $reason
}
puts "P07_B5_RAW_PHYSICAL_MAILBOX_AND_TRACE_READY_FOR_INDEPENDENT_VERIFY=1"
puts "P07_B5_RAW_A53_COLD_POWER_CYCLE_REQUIRED=1"
