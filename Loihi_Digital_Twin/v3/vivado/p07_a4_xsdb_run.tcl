# P07-A4.2c candidate persistent standalone Cortex-A53 runtime.
# One ELF launch for 16/128/10000 images; A53 fully owns every timestep.
# This is NOT a physical passing result unless the independent verifier passes.
if {$argc < 3 || $argc > 5} {
    error "usage: p07_a4_xsdb_run.tcl <new-A4-elf> <journal-1MiB-out> <trace64KiB-out> ?server? ?timeout-seconds?"
}
set elf [file normalize [lindex $argv 0]]
set output [file normalize [lindex $argv 1]]
set trace [file normalize [lindex $argv 2]]
set server "tcp:127.0.0.1:3121"
if {$argc >= 4} {set server [lindex $argv 3]}
set timeout 3600
if {$argc == 5} {set timeout [lindex $argv 4]}
if {$timeout < 10 || $timeout > 28800} {
    error "P07-A4.2c timeout must be 10..28800s"
}
if {![file exists $elf]} {error "P07-A4.2c new standalone ELF missing"}
if {[catch {exec grep -aFq "P07_A4_2B_PERSISTENT_KV260_A53_FROZEN_TRACK_A_V1" $elf}]} {
    error "P07-A4.2c refuse wrong/stale A53 ELF (A2 ELF is NOT persistent)"
}
foreach name [list $output $trace "$output.partial"] {
    if {[file exists $name]} {
        error "P07-A4.2c refusing overwrite of existing physical evidence"
    }
}
proc physical_target_a4 {} {
    foreach name {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$name\""}]} {return}
    }
    error "P07-A4.2c cannot select physical DDR target"
}
connect -url $server
targets -set -filter {name =~ "Cortex-A53 #0"}
catch {stop}
catch {rst -processor}
dow $elf
puts "P07-A4.2c standalone persistent A53 ELF downloaded; starting ONE dataset run"
con
set terminal 0
set polls $timeout
set scratch "$output.partial"
for {set i 0} {$i < $polls} {incr i} {
    after 1000
    physical_target_a4
    file delete -force $scratch
    # Header status lives at byte 16; read 64-byte status prefix.
    mrd -bin -file $scratch 0x42000000 16
    set fh [open $scratch rb]
    fconfigure $fh -translation binary -encoding binary
    set bytes [read $fh]
    close $fh
    if {[string length $bytes] == 64} {
        binary scan $bytes @16i terminal
        set terminal [expr {$terminal & 0xFFFFFFFF}]
        if {$terminal == 0x600D600D ||
            ($terminal & 0xFFFF0000) == 0xDEAD0000} {
            break
        }
    }
}
physical_target_a4
file delete -force $scratch
mrd -bin -file $output 0x42000000 262144
mrd -bin -file $trace 0x43FF0000 16384
targets -set -filter {name =~ "Cortex-A53 #0"}
catch {stop}
if {![file exists $output] || [file size $output] != 1048576 ||
    ![file exists $trace] || [file size $trace] != 65536} {
    error "P07-A4.2c full physical journal/selected trace capture size mismatch"
}
puts [format "P07_A4_2C_JOURNAL_STATUS=0x%08X" $terminal]
puts "P07_A4_2C_JOURNAL=$output"
puts "P07_A4_2C_TRACE=$trace"
if {$i >= $polls} {
    puts "P07_A4_2C_KV260_STATUS=TIMEOUT"
} elseif {$terminal == 0x600D600D} {
    puts "P07_A4_2C_KV260_STATUS=TERMINAL_SUCCESS_UNVERIFIED_NUMERICS"
} else {
    puts "P07_A4_2C_KV260_STATUS=TERMINAL_FAILURE_INSPECT_JOURNAL"
}
disconnect
