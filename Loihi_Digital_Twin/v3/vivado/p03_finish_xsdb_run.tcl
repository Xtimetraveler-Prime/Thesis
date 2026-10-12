# Launch unified P03 A53 ELF and passively poll DONE/ERROR mailbox.
# No host-owned page/route/barrier/dispatch decisions are made.
if {$argc < 2 || $argc > 4} {
    error "usage: p03_finish_xsdb_run.tcl <elf> <mailbox> ?server? ?timeout_s?"
}
set elf [file normalize [lindex $argv 0]]
set mailbox [file normalize [lindex $argv 1]]
set server "tcp:127.0.0.1:3121"
if {$argc >= 3} { set server [lindex $argv 2] }
set timeout_s 600
if {$argc == 4} { set timeout_s [lindex $argv 3] }
if {$timeout_s < 10 || $timeout_s > 3600} {
    error "P03 runtime timeout must be 10..3600 seconds"
}
if {![file exists $elf]} { error "P03 ELF missing: $elf" }
proc p03_psu_target {} {
    foreach name {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$name\""} e]} {
            puts "P03 result mailbox physical target: $name"
            return
        }
    }
    error "P03 PSU/APU physical target not available"
}
connect -url $server
targets -set -filter {name =~ "Cortex-A53 #0"}
catch {stop}
catch {rst -processor}
dow $elf
puts "PASS: P03 unified board-autonomous A53 ELF downloaded"
con
set result_word 0
set n 0
set tmp "$mailbox.poll"
set polls $timeout_s
while {$n < $polls} {
    after 1000
    p03_psu_target
    file delete -force $tmp
    mrd -bin -file $tmp 0x43FF0000 64
    set fh [open $tmp rb]
    fconfigure $fh -translation binary -encoding binary
    set raw [read $fh]
    close $fh
    if {[string length $raw] == 256} {
        binary scan $raw @8i result_word
        set result_word [expr {$result_word & 0xFFFFFFFF}]
        if {$result_word == 0x600D600D ||
            ($result_word & 0xFFFF0000) == 0xDEAD0000} {
            puts [format "P03 board-local terminal result=0x%08X after %d poll(s)" $result_word [expr {$n + 1}]]
            break
        }
    }
    incr n
}
file delete -force $mailbox
file rename -force $tmp $mailbox
if {![file exists $mailbox] || [file size $mailbox] != 256} {
    error "P03 physical result mailbox missing or incorrect size"
}
targets -set -filter {name =~ "Cortex-A53 #0"}
catch {stop}
if {$n >= $polls} {
    puts "FAIL: P03 A53 runtime did not produce terminal mailbox within timeout"
} else {
    puts "PASS: P03 A53 terminal mailbox captured after board-local execution"
}
puts "P03_RESULT_MAILBOX=$mailbox"
disconnect
