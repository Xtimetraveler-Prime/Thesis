# P08-B4.2 full1024 DESTRUCTIVE A53 JTAG run; only after physically verified
# SAME-SESSION 6 signed DDR transfers / accepted P03 / halted Linux.
# Result is structural only until independently checked all1024 scalar.
# REBOOT KV260 after ANY attempt. NEVER resume stopped Linux.
if {$argc != 6 ||
    [lindex $argv 0] ne "P08_B4_FULL1024_AFTER_SIX_SIGNED_PHYSICAL_READBACK_RISK_APPROVED"} {
    error "P08-B4.2: <approval> <pinned B4 original full1024 ELF> <zeros256> <zeros262144> <NEW capture dir> <local XSDB>"
}
set elf [file normalize [lindex $argv 1]]
set zeros256 [file normalize [lindex $argv 2]]
set zeros262144 [file normalize [lindex $argv 3]]
set out [file normalize [lindex $argv 4]]
set server [lindex $argv 5]
if {![regexp {^tcp:(localhost|127[.]0[.]0[.]1):[0-9]{2,5}$} $server]} {
    error "P08-B4.2: localhost XSDB only"
}
if {![file isfile $elf] || [file tail $elf] ne "p08_b4_original_full1024.elf" ||
    ![file isfile $zeros256] || [file size $zeros256]!=256 ||
    ![file isfile $zeros262144] || [file size $zeros262144]!=262144 ||
    ![file isdirectory $out] ||
    [llength [glob -nocomplain -directory $out *]]!=0} {
    error "P08-B4.2: exact B4 original full1024 ELF, two zero sentinels and fresh physical capture dir required"
}
proc pilot_read {file} {
    set f [open $file rb]
    fconfigure $f -translation binary -encoding binary
    set result [read $f]
    close $f
    return $result
}
if {[pilot_read $zeros256] ne [string repeat "\x00" 256] ||
    [pilot_read $zeros262144] ne [string repeat "\x00" 262144]} {
    error "P08-B4.2: exact all-zero mailbox/journal/timer sentinels required"
}
if {[catch {exec grep -aFq P08_B2_3_ORIGINAL_27CORE_1024_IMAGE_ONLY_A53_V1 $elf}] ||
    [catch {exec grep -aFq P08_B4_FULL1024_TERMINAL_DONE=1 $elf}]} {
    error "P08-B4.2: wrong A53 image-only ELF identity or 1024 terminal marker"
}
set pin 0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1
if {[lindex [exec sha256sum $elf] 0] ne $pin} {
    error "P08-B4.2: operator genuine full1024 ELF SHA differs"
}
proc pilot_psu {} {
    foreach name {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$name\""}]} {
            return
        }
    }
    error "P08-B4.2: no physical PSU/APU target, refuse CPU/MMU access"
}
proc pilot_halt_cpu {label} {
    targets -set -filter {name =~ "Cortex-A53 #0"}
    if {[catch {stop} why]} {
        if {[string trim $why] ne "Already stopped"} {
            error "P08-B4.2: A53 #0 $label halt failure: $why"
        }
    }
    puts "P08_B4_FULL1024_A53_STOP_CONFIRMED=1"
}
# A53 firmware writes 0xC0DEF00D for EVERY mailbox message, including
# startup and intermediate image progress. DONE BY ITSELF IS NOT SUCCESS.
# Strict classifier is pure Tcl and separately unit-tested without JTAG.
proc pilot_mailbox_classify {raw} {
    if {[string length $raw]!=256} {return INVALID}
    if {[binary scan $raw i64 words]!=1 || [llength $words]!=64} {
        return INVALID
    }
    set magic [expr {[lindex $words 0] & 0xFFFFFFFF}]
    set version [expr {[lindex $words 1] & 0xFFFFFFFF}]
    set status [expr {[lindex $words 2] & 0xFFFFFFFF}]
    set index [expr {[lindex $words 3] & 0xFFFFFFFF}]
    set fault [expr {[lindex $words 4] & 0xFFFFFFFF}]
    set completed [expr {[lindex $words 5] & 0xFFFFFFFF}]
    set done [expr {[lindex $words 63] & 0xFFFFFFFF}]
    if {$done != 0xC0DEF00D} {return INCOMPLETE}
    if {$magic != 0x50384232 || $version != 1} {return INVALID}
    if {$status == 0xC0DE0000} {
        # Startup reports ordinal=-1 and 0 complete; after each image,
        # ordinal and completed count advance together. NONE is terminal.
        if {$fault != 0 || $completed>1024 ||
            !($completed==0 && $index==0xFFFFFFFF) &&
            !($completed>0 && $index==$completed-1)} {
            return INVALID
        }
        return PROGRESS
    }
    if {$status == 0x600D0823} {
        if {$index!=1023 || $fault!=0 || $completed!=1024} {
            return INVALID
        }
        return SUCCESS
    }
    if {$status == 0xDEAD0823} {return FAILURE}
    return INVALID
}
set connected 0
set failed [catch {
    connect -url $server
    set connected 1
    pilot_halt_cpu PRE_RESET
    rst -processor
    pilot_psu
    foreach {src start count label} [list \
        $zeros256 0x43FF0200 64 mailbox_zero_physical.bin \
        $zeros262144 0x42200000 65536 journal_zero_physical.bin \
        $zeros262144 0x42300000 65536 timing_zero_physical.bin] {
        set target [file join $out $label]
        dow -data $src $start
        mrd -bin -file $target $start $count
        if {[pilot_read $target] ne [pilot_read $src]} {
            error "P08-B4.2: real PSU initial zero readback failed: $label"
        }
        puts "P08_B4_FULL1024_RESULT_REGION_ZERO_PHYSICAL_READBACK_PASS=1"
    }
    targets -set -filter {name =~ "Cortex-A53 #0"}
    dow $elf
    puts "P08_B4_FULL1024_EXACT_OPERATOR_SHA_PINNED_ELF_DOWNLOADED=1"
    con
    set mailbox [file join $out mailbox_terminal_physical.bin]
    set scratch [file join $out mailbox_poll.tmp]
    set terminal 0
    set terminal_state INCOMPLETE
    set previous_completed 0
    # Original 27-core pager + 26 ticks + 1010 neural trace each image
    # may be slow. Fixed bounded observation, never accept a timeout.
    for {set attempt 0} {$attempt < 172800} {incr attempt} {
        after 1000
        pilot_psu
        if {[file exists $scratch]} {file delete $scratch}
        mrd -bin -file $scratch 0x43FF0200 64
        set raw [pilot_read $scratch]
        if {[string length $raw]!=256} {
            error "P08-B4.2: partial physical mailbox"
        }
        set state [pilot_mailbox_classify $raw]
        if {$state eq "PROGRESS"} {
            binary scan $raw i64 progress
            set completed [expr {[lindex $progress 5] & 0xFFFFFFFF}]
            if {$completed<$previous_completed} {
                error "P08-B4.2: original image-completed count moved backward"
            }
            set previous_completed $completed
            continue
        }
        if {$state eq "INCOMPLETE"} {continue}
        if {$state eq "INVALID"} {
            error "P08-B4.2: malformed/unknown authentic mailbox state"
        }
        if {$state eq "SUCCESS" || $state eq "FAILURE"} {
            set terminal 1
            set terminal_state $state
            break
        }
    }
    if {![file exists $scratch]} {
        error "P08-B4.2: no physically observed terminal mailbox"
    }
    file rename $scratch $mailbox
    pilot_halt_cpu POST_CAPTURE
    puts "P08_B4_FULL1024_PHYSICAL_TERMINAL_MAILBOX_CAPTURED_256B=1"
    pilot_psu
    mrd -bin -file [file join $out journal1024_physical.bin] 0x42200000 65536
    mrd -bin -file [file join $out timing1024_physical.bin] 0x42300000 65536
    if {![file isfile [file join $out journal1024_physical.bin]] ||
        [file size [file join $out journal1024_physical.bin]]!=262144 ||
        ![file isfile [file join $out timing1024_physical.bin]] ||
        [file size [file join $out timing1024_physical.bin]]!=262144} {
        error "P08-B4.2: missing 1024x256B complete physical neural/timing receipts"
    }
    puts "P08_B4_FULL1024_REAL_1024_JOURNAL_AND_TIMING_SIDECARS_PHYSICAL_CAPTURED=1"
    if {!$terminal} {
        error "P08-B4.2: timed out. Partial physical evidence preserved. REBOOT."
    }
    if {$terminal_state eq "FAILURE"} {
        error "P08-B4.2: real A53 reported a TERMINAL FAILURE. Original fault mailbox and partial sidecars preserved; REBOOT."
    }
    if {$terminal_state ne "SUCCESS"} {
        error "P08-B4.2: not a genuine 1024/1024 terminal success."
    }
    set data [pilot_read $mailbox]
    binary scan $data i64 words
    foreach {i expect} {0 0x50384232 1 1 2 0x600D0823 3 1023 4 0 5 1024 63 0xC0DEF00D} {
        if {[expr {[lindex $words $i] & 0xFFFFFFFF}] != $expect} {
            error "P08-B4.2: observed physical terminal is NOT strict full1024 PASS"
        }
    }
    puts "P08_B4_FULL1024_EXACT_1024_FRAME_HARDWARE_TERMINAL_OBSERVED=1"
} reason]
if {$connected} {catch {disconnect}}
if {$failed} {
    puts "P08_B4_FULL1024_JTAG_ATTEMPT_FAILED_REBOOT_REQUIRED=1"
    error $reason
}
puts "P08_B4_FULL1024_PHYSICAL_CAPTURE_PENDING_INDEPENDENT_SCALAR_VERIFICATION=1"
puts "P08_B4_FULL1024_REBOOT_REQUIRED=1"
