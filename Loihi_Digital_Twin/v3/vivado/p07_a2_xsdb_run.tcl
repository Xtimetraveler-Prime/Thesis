# One XSDB launch of the entire A53 autonomous P07-A2 image batch.
# XSDB MUST NOT dispatch individual cores, inject events, route or page.
if {$argc < 2 || $argc > 4} {
    error "usage: p07_a2_xsdb_run.tcl <candidate-elf> <mailbox-output> ?server? ?timeout-seconds?"
}
set elf [file normalize [lindex $argv 0]]
set output [file normalize [lindex $argv 1]]
set server "tcp:127.0.0.1:3121"
if {$argc >= 3} {set server [lindex $argv 2]}
set timeout 900
if {$argc == 4} {set timeout [lindex $argv 3]}
if {$timeout < 10 || $timeout > 7200} {error "P07-A2 timeout must be 10..7200"}
if {![file exists $elf]} {error "P07-A2 ELF missing"}
# The initial 2026-10-17 ELF built successfully but used the wrong
# trace timestep context. REFUSE its execution even if XSDB could load it.
if {[catch {exec grep -aFq "P07_A2_KV260_A53_FROZEN_TRACK_A_V1_TRACE_CONTEXT_FIX" $elf}]} {
    error "P07-A2 refusing stale pre-trace-fix ELF; rebuild from latest branch"
}
if {[file exists $output] || [file exists "$output.partial"]} {
    error "P07-A2 refusing to overwrite existing physical evidence output"
}
if {[file dirname $elf] eq [file dirname $output]} {
    puts "P07-A2 note: keep ELF and physical evidence artifacts independently immutable"
}
proc physical_target {} {
    foreach name {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$name\""}]} {return}
    }
    error "P07-A2 cannot select a physical DDR target"
}
connect -url $server
targets -set -filter {name =~ "Cortex-A53 #0"}
catch {stop}
catch {rst -processor}
dow $elf
puts "P07-A2 standalone A53 ELF downloaded; starting ONE autonomous batch"
con
set terminal 0
set polls $timeout
set scratch "$output.partial"
for {set i 0} {$i < $polls} {incr i} {
    after 1000
    physical_target
    file delete -force $scratch
    mrd -bin -file $scratch 0x43FF0000 16
    set fh [open $scratch rb]
    fconfigure $fh -translation binary -encoding binary
    set bytes [read $fh]
    close $fh
    if {[string length $bytes] == 64} {
        binary scan $bytes @8i terminal
        set terminal [expr {$terminal & 0xFFFFFFFF}]
        if {$terminal == 0x600D600D ||
            ($terminal & 0xFFFF0000) == 0xDEAD0000} {
            break
        }
    }
}
physical_target
file delete -force $output
mrd -bin -file $output 0x43FF0000 16384
targets -set -filter {name =~ "Cortex-A53 #0"}
catch {stop}
if {![file exists $output] || [file size $output] != 65536} {
    error "P07-A2 mailbox size mismatch"
}
puts [format "P07_A2_MAILBOX_STATUS=0x%08X" $terminal]
puts "P07_A2_MAILBOX=$output"
if {$i >= $polls} {
    puts "P07_A2_KV260_STATUS=TIMEOUT"
} elseif {$terminal == 0x600D600D} {
    puts "P07_A2_KV260_STATUS=TERMINAL_SUCCESS_UNVERIFIED_NUMERICS"
} else {
    puts "P07_A2_KV260_STATUS=TERMINAL_FAILURE_INSPECT_MAILBOX"
}
disconnect
