# P07-B.4i dedicated JTAG-only mailbox pilot, derived from accepted P03/P07-A.
# DESTRUCTIVE: stops/resets A53 #0, downloads ELF, overwrites 64 DDR bytes.
# NEVER use on a Linux-owned board. Driver must independently gate this call.
if {$argc != 5 || [lindex $argv 0] ne "DEDICATED_A53_DDR_OWNER_VERIFIED"} {
    error "usage: <DEDICATED_A53_DDR_OWNER_VERIFIED> <ELF> <zeros64> <mailbox_out> <xsdb_url>"
}
set elf [file normalize [lindex $argv 1]]
set zeros [file normalize [lindex $argv 2]]
set output [file normalize [lindex $argv 3]]
set server [lindex $argv 4]
if {![regexp {^tcp:(localhost|127[.]0[.]0[.]1):[0-9]{2,5}$} $server]} {
    error "P07-B.4i local hw_server only"
}
if {![file isfile $elf] || ![file isfile $zeros] ||
    [file size $zeros] != 64 || [file exists $output]} {
    error "P07-B.4i ELF/zero-mailbox inputs or new output invalid"
}
set input [open $zeros rb]
fconfigure $input -translation binary -encoding binary
set blank [read $input]
close $input
if {$blank ne [string repeat "\x00" 64]} {
    error "P07-B.4i requires EXACT 64 zero bytes"
}
if {[catch {exec grep -aFq P07_B4I_A53_MAILBOX_FPD128_PROBE_V1 $elf}]} {
    error "P07-B.4i refuse wrong or stale ELF"
}
proc b4i_ps_target {} {
    foreach candidate {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$candidate\""}]} {
            return
        }
    }
    error "P07-B.4i no physical DDR target"
}
set connected 0
set result [catch {
    connect -url $server
    set connected 1
    targets -set -filter {name =~ "Cortex-A53 #0"}
    stop
    rst -processor
    b4i_ps_target
    dow -data $zeros 0x43FF0000
    set before "\${output}.zero_readback"
    if {[file exists $before]} {error "zero readback already exists"}
    mrd -bin -file $before 0x43FF0000 16
    set f [open $before rb]
    fconfigure $f -translation binary -encoding binary
    set observed [read $f]
    close $f
    if {$observed ne $blank} {error "B4i zero-mailbox byte readback FAIL"}
    targets -set -filter {name =~ "Cortex-A53 #0"}
    dow $elf
    puts "P07_B4I_A53_DOWNLOADED=1"
    con
    set scratch "\${output}.poll"
    set complete 0
    for {set i 0} {$i < 30} {incr i} {
        after 1000
        b4i_ps_target
        if {[file exists $scratch]} {file delete $scratch}
        mrd -bin -file $scratch 0x43FF0000 16
        set fh [open $scratch rb]
        fconfigure $fh -translation binary -encoding binary
        set bytes [read $fh]
        close $fh
        if {[string length $bytes] == 64} {
            binary scan $bytes @60i done
            set done [expr {$done & 0xFFFFFFFF}]
            if {$done == 0xC0DEF00D} {
                set complete 1
                break
            }
        }
    }
    if {![file exists $scratch]} {
        error "P07-B.4i result mailbox was never readable"
    }
    file rename $scratch $output
    targets -set -filter {name =~ "Cortex-A53 #0"}
    stop
    if {!$complete} {error "P07-B.4i completion timeout; inspect mailbox"}
    puts "P07_B4I_MAILBOX_CAPTURED_64_BYTES=1"
    puts "P07_B4I_A53_INFERENCE_DISPATCHED=0"
} why]
if {$connected} {catch {disconnect}}
if {$result} {
    puts "P07_B4I_BOARD_ATTEMPT_FAIL_REBOOT_REQUIRED=1"
    error "P07-B.4i: $why"
}
puts "P07_B4I_BOARD_CAPTURE_READY_FOR_INDEPENDENT_VERIFIER=1"
puts "P07_B4I_REBOOT_REQUIRED=1"
