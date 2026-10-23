# P07-B.4l physical B3 scheduler first-epoch ELF launcher, SAME dedicated JTAG session
# as successful 27-core [0x40000000,0x40D80000) DDR staging AND\n# SHA-checked original 16KiB P02/B1.2 bindings at 0x43FC0000.
# DELIBERATELY DESTRUCTIVE to low DDR [0,ELF LOAD end) and 256B mailbox.
# No live-Linux operation. Do not reuse after halted session; reboot.
if {$argc != 5 || [lindex $argv 0] ne "B4L_B3_FIRST_EPOCH_AFTER_27_DDR_AND_BINDINGS_APPROVED"} {
    error "usage: <B4L_B3_FIRST_EPOCH_AFTER_27_DDR_AND_BINDINGS_APPROVED> <paging_elf> <zero256> <new_mailbox_out> <local_server>"
}
set elf [file normalize [lindex $argv 1]]
set zeros [file normalize [lindex $argv 2]]
set out [file normalize [lindex $argv 3]]
set server [lindex $argv 4]
if {![regexp {^tcp:(localhost|127[.]0[.]0[.]1):[0-9]{2,5}$} $server]} {
    error "B4l: localhost XSDB server only"
}
if {![file isfile $elf] || ![file isfile $zeros] ||
        [file size $zeros]!=256 || [file exists $out]} {
    error "B4l: ELF, 256-byte zeros or new mailbox path missing/invalid"
}
if {[catch {exec grep -aFq P07_B4L_A53_B3_ONE_EPOCH_V1 $elf}]} {
    error "B4l: distinct B3 first-epoch ELF identity missing"
}
set f [open $zeros rb]
fconfigure $f -translation binary -encoding binary
set blank [read $f]
close $f
if {$blank ne [string repeat "\x00" 256]} {
    error "B4l: zero mailbox input must contain EXACT 256 zero bytes"
}
proc b4l_ps_memory_target {} {
    foreach name {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$name\""}]} {
            return
        }
    }
    error "B4l physical non-CPU target unavailable"
}
proc b4l_halt_a53_primary {label} {
    targets -set -filter {name =~ "Cortex-A53 #0"}
    if {[catch {stop} err]} {
        if {[string trim $err] ne "Already stopped"} {
            error "B4l A53 #0 $label halted-state failure: $err"
        }
        puts "P07_B4L_A53_0_${label}_ALREADY_STOPPED_CONFIRMED=1"
    } else {
        puts "P07_B4L_A53_0_${label}_STOP_COMMAND_PASS=1"
    }
}
set connected 0
set failed [catch {
    connect -url $server
    set connected 1
    b4l_halt_a53_primary PRE_RESET
    rst -processor
    b4l_ps_memory_target
    dow -data $zeros 0x43FF0000
    set check "${out}.zero_readback"
    if {[file exists $check]} {error "B4l: zero-readback output already exists"}
    mrd -bin -file $check 0x43FF0000 64
    set f [open $check rb]
    fconfigure $f -translation binary -encoding binary
    set read_back [read $f]
    close $f
    if {$read_back ne $blank} {error "B4l: 256B physical mailbox zero readback mismatch"}
    targets -set -filter {name =~ "Cortex-A53 #0"}
    dow $elf
    puts "P07_B4L_B3_A53_EPOCH_ELF_DOWNLOADED=1"
    con
    set scratch "${out}.poll"
    set done 0
    for {set attempt 0} {$attempt < 60} {incr attempt} {
        after 1000
        b4l_ps_memory_target
        if {[file exists $scratch]} {file delete $scratch}
        mrd -bin -file $scratch 0x43FF0000 64
        set f [open $scratch rb]
        fconfigure $f -translation binary -encoding binary
        set data [read $f]
        close $f
        if {[string length $data]==256} {
            binary scan $data @252i last
            set last [expr {$last & 0xFFFFFFFF}]
            if {$last==0xC0DEF00D} {
                set done 1
                break
            }
        }
    }
    if {![file exists $scratch]} {error "B4l: B3 first-epoch mailbox unreadable"}
    file rename $scratch $out
    b4l_halt_a53_primary POST_CAPTURE
    if {!$done} {error "B4l: B3 first-epoch ELF completion timeout; preserve partial mailbox"}
    puts "P07_B4L_B3_A53_EPOCH_MAILBOX_CAPTURED_256_BYTES=1"
} why]
if {$connected} {catch {disconnect}}
if {$failed} {
    puts "P07_B4L_B3_A53_EPOCH_ATTEMPT_FAILED_REBOOT_REQUIRED=1"
    error $why
}
puts "P07_B4L_B3_A53_EPOCH_CAPTURE_READY_FOR_INDEPENDENT_VERIFIER=1"
puts "P07_B4L_B3_REBOOT_REQUIRED=1"
