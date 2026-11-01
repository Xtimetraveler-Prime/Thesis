# Dedicated P07-B.4m FULL 26-TICK original TRAIN A53 inference ONLY.
# Destructive: low DDR [0,0x00106B00), mailbox [0x43FF0000,0x43FF0100).
# PRECONDITIONS (enforced by calling PC Python orchestrator):
#   halted/discarded Linux, accepted P03 shell, all 27 original P02 DDR
#   contexts + 16KiB signed descriptor + 80KiB and 896KiB route tables +
#   original TRAIN ingress physically staged/read back IN SAME JTAG SESSION.
# This TCL has NO independent memory ownership proof. Operator approves the
# expanded 1,075,968-byte low DDR + firmware coexistence risk separately.
# NEVER use on live Linux. REBOOT after every attempted A53 download/run.
if {$argc != 5 || [lindex $argv 0] ne "B4M_FULL_26TICK_AFTER_SAME_SESSION_SIGNED_READBACK_APPROVED"} {
    error "B4m: usage <specific_approval> <exact_full_26tick_elf> <zero256> <fresh_mailbox_out> <local_xsdb>"
}
set elf [file normalize [lindex $argv 1]]
set zeros [file normalize [lindex $argv 2]]
set out [file normalize [lindex $argv 3]]
set server [lindex $argv 4]
if {![regexp {^tcp:(localhost|127[.]0[.]0[.]1):[0-9]{2,5}$} $server]} {
    error "B4m: only localhost XSDB permitted"
}
if {![file isfile $elf] || [file size $elf]<=106580 ||
    ![file isfile $zeros] || [file size $zeros]!=256 ||
    [file exists $out] || ![file isdirectory [file dirname $out]] ||
    [file exists "${out}.zero_readback"] || [file exists "${out}.poll"]} {
    error "B4m: incorrect ELF/zero-mailbox or pre-existing evidence path"
}
if {[catch {exec grep -aFq P07_B4M_A53_TRAIN_26_TICK_CANDIDATE_V1 $elf}]} {
    error "B4m: wrong A53 full 26-tick ELF identity"
}
set expected_sha ccbd8c531e5571f929e81613cfee71f54abf341c36412ebcfa7d98e2313e6b70
set actual_sha [lindex [exec sha256sum $elf] 0]
if {$actual_sha ne $expected_sha} {
    error "B4m: exact independently accepted ELF SHA mismatch"
}
proc b4m_binary_read {path} {
    set f [open $path rb]
    fconfigure $f -translation binary -encoding binary
    set data [read $f]
    close $f
    return $data
}
set blank [b4m_binary_read $zeros]
if {$blank ne [string repeat "\x00" 256]} {
    error "B4m: mailbox init requires EXACTLY 256 zero bytes"
}
proc b4m_physical_ps_only {} {
    foreach name {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$name\""}]} {
            return
        }
    }
    error "B4m: no physical PS target (reject CPU virtual address)"
}
proc b4m_halt_cpu0 {label} {
    targets -set -filter {name =~ "Cortex-A53 #0"}
    if {[catch {stop} err]} {
        if {[string trim $err] ne "Already stopped"} {
            error "B4m: A53 #0 $label halt failed: $err"
        }
        puts "P07_B4M_A53_0_${label}_ALREADY_STOPPED_CONFIRMED=1"
    } else {
        puts "P07_B4M_A53_0_${label}_STOP_COMMAND_PASS=1"
    }
}
set connected 0
set failed [catch {
    connect -url $server
    set connected 1
    b4m_halt_cpu0 PRE_RESET
    rst -processor
    b4m_physical_ps_only
    dow -data $zeros 0x43FF0000
    set zeroread "${out}.zero_readback"
    mrd -bin -file $zeroread 0x43FF0000 64
    if {[b4m_binary_read $zeroread] ne $blank} {
        error "B4m: 256B physical mailbox initialization readback failed"
    }
    puts "P07_B4M_256B_MAILBOX_ZERO_PHYSICAL_READBACK_PASS=1"
    targets -set -filter {name =~ "Cortex-A53 #0"}
    dow $elf
    puts "P07_B4M_A53_26TICK_ELF_DOWNLOADED=1"
    con
    set scratch "${out}.poll"
    set terminal 0
    # Original 26*27 dispatches with per-compartment real debug reads
    # and 702 DDR paging operations may take substantially longer than
    # accepted B4l 27-dispatch first-epoch 60-second observation. This
    # polling budget is bounded and never treats timeout as success.
    for {set attempt 0} {$attempt < 1800} {incr attempt} {
        after 1000
        b4m_physical_ps_only
        if {[file exists $scratch]} {file delete $scratch}
        mrd -bin -file $scratch 0x43FF0000 64
        set raw [b4m_binary_read $scratch]
        if {[string length $raw]!=256} {
            error "B4m: partial physical 256B mailbox capture"
        }
        binary scan $raw @252i word
        if {[expr {$word & 0xFFFFFFFF}]==0xC0DEF00D} {
            set terminal 1
            break
        }
    }
    if {![file exists $scratch]} {
        error "B4m: no genuine physical mailbox capture"
    }
    file rename $scratch $out
    b4m_halt_cpu0 POST_CAPTURE
    puts "P07_B4M_A53_MAILBOX_CAPTURED_256_BYTES=1"
    if {!$terminal} {
        error "B4m: bounded full 26-tick completion timeout; partial mailbox preserved; REBOOT"
    }
    puts "P07_B4M_A53_26TICK_TERMINAL_DONE_PHYSICALLY_OBSERVED=1"
} why]
if {$connected} {catch {disconnect}}
if {$failed} {
    puts "P07_B4M_A53_FULL_26TICK_ATTEMPT_FAILED_REBOOT_REQUIRED=1"
    error $why
}
puts "P07_B4M_A53_FULL_26TICK_MAILBOX_CAPTURE_READY_FOR_INDEPENDENT_VERIFIER=1"
puts "P07_B4M_A53_26TICK_REBOOT_REQUIRED=1"
