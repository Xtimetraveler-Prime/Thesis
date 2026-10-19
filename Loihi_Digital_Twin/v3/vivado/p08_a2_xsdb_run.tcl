# P08-A2.1 isolated latency-only standalone Cortex-A53 candidate.
# One ELF launch for 16/128/10000 images; A53 fully owns every timestep.
# This is NOT a physical passing result unless the independent verifier passes.
if {$argc < 4 || $argc > 6} {
    error "usage: p08_a2_xsdb_run.tcl <P08-A2-elf> <journal-1MiB-out> <trace64KiB-out> <timing1MiB-out> ?server? ?timeout-seconds?"
}
# Explicit standalone bare-metal consent; this TCL can reset A53 and access
# reserved DDR. Never run while Linux owns this memory. A3 will supply a
# separate shell-level gate with provenance/readback checks.
if {![info exists ::env(P08_A2_CONFIRM_KV260_JTAG_ONLY)] ||
    $::env(P08_A2_CONFIRM_KV260_JTAG_ONLY) ne "YES" ||
    ![info exists ::env(P08_A2_CONFIRM_VALIDATION_ONLY)] ||
    $::env(P08_A2_CONFIRM_VALIDATION_ONLY) ne "YES"} {
    error "P08-A2 refuses hardware access without JTAG-only and validation-only consent"
}
set elf [file normalize [lindex $argv 0]]
set output [file normalize [lindex $argv 1]]
set trace [file normalize [lindex $argv 2]]
set timing [file normalize [lindex $argv 3]]
set server "tcp:127.0.0.1:3121"
if {$argc >= 5} {set server [lindex $argv 4]}
set timeout 3600
if {$argc == 6} {set timeout [lindex $argv 5]}
if {$timeout < 10 || $timeout > 28800} {
    error "P07-A4.2c timeout must be 10..28800s"
}
if {![file exists $elf]} {error "P08-A2.1 new standalone ELF missing"}
if {[catch {exec grep -aFq "P08_A2_1_LATENCY_ONLY_KV260_A53_CANDIDATE_V1" $elf}]} {
    error "P08-A2.1 refuses wrong/stale A53 ELF"
}
foreach name [list $output $trace $timing "$output.partial" "$timing.partial"] {
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
puts "P08-A2.1 latency candidate A53 ELF downloaded; starting ONE dataset run"
con
set terminal 0
set timing_status 0
set polls $timeout
set scratch "$output.partial"
set timing_scratch "$timing.partial"
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
        # P07 writes its terminal journal before P08 writes terminal
        # sidecar: do not halt the A53 on P07 success alone.
        if {$terminal == 0x600D600D} {
            file delete -force $timing_scratch
            mrd -bin -file $timing_scratch 0x43000000 16
            set tf [open $timing_scratch rb]
            fconfigure $tf -translation binary -encoding binary
            set raw [read $tf]
            close $tf
            if {[string length $raw] == 64} {
                binary scan $raw @16i timing_status
                set timing_status [expr {$timing_status & 0xFFFFFFFF}]
                if {$timing_status == 0x600D600D} {break}
            }
        } elseif {($terminal & 0xFFFF0000) == 0xDEAD0000} {
            break
        }
    }
}
physical_target_a4
file delete -force $scratch
file delete -force $timing_scratch
mrd -bin -file $output 0x42000000 262144
mrd -bin -file $trace 0x43FF0000 16384
mrd -bin -file $timing 0x43000000 262144
targets -set -filter {name =~ "Cortex-A53 #0"}
catch {stop}
if {![file exists $output] || [file size $output] != 1048576 ||
    ![file exists $trace] || [file size $trace] != 65536 ||
    ![file exists $timing] || [file size $timing] != 1048576} {
    error "P07-A4.2c full physical journal/selected trace capture size mismatch"
}
puts [format "P07_A4_2C_JOURNAL_STATUS=0x%08X" $terminal]
puts "P07_A4_2C_JOURNAL=$output"
puts "P07_A4_2C_TRACE=$trace"
puts "P08_A2_1_TIMING=$timing"
puts [format "P08_A2_1_TIMING_STATUS=0x%08X" $timing_status]
if {$i >= $polls} {
    puts "P08_A2_1_KV260_STATUS=TIMEOUT"
} elseif {$terminal == 0x600D600D && $timing_status == 0x600D600D} {
    puts "P08_A2_1_KV260_STATUS=TERMINAL_BOTH_SUCCESS_UNVERIFIED_NUMERICS"
} else {
    puts "P08_A2_1_KV260_STATUS=TERMINAL_FAILURE_INSPECT_JOURNAL_AND_TIMING"
}
disconnect
