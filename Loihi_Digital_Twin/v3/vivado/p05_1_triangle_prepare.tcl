# P05.1 physical three-core spiking resident triangle: provision P05G v1 deployment.
# All DDR via nonprocessor PSU/APU; never route/dispatch by XSDB.
# Explicitly limited to 0..2 / 5 steps for the FIRST independent probe.
if {$argc < 1 || $argc > 2} {
    error "usage: p05_1_xsdb_prepare.tcl <probe-dir> ?server-url?"
}
set root [file normalize [lindex $argv 0]]
set server "tcp:127.0.0.1:3121"
if {$argc == 2} {set server [lindex $argv 1]}
set artifact [file join $root p05_artifacts]
set fixture [file join $root triangle_golden]
set files {}

proc p05_physical {} {
    foreach target {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$target\""}]} {
            puts "P05.1 physical DDR target: $target"
            return
        }
    }
    error "P05.1: no physical PSU/APU target"
}
proc p05_equal {a b} {
    set x [open $a rb]; set y [open $b rb]
    fconfigure $x -translation binary -encoding binary
    fconfigure $y -translation binary -encoding binary
    set ok [expr {[read $x] eq [read $y]}]
    close $x;close $y
    return $ok
}
for {set core 0} {$core < 3} {incr core} {
    set path [file join $artifact [format "core%d_initial.bin" $core]]
    set frozen [file join $fixture [format "core%d_initial.bin" $core]]
    if {![file exists $path] || [file size $path] != 0x80000 ||
        ![file exists $frozen] || ![p05_equal $path $frozen]} {
        error "P05.1 requires triangle-model-identical 512KiB initial DDR core $core"
    }
    lappend files [list $path [expr {0x40000000+$core*0x80000}] 131072]
}
set payload [file join $artifact p05_payload.bin]
set header [file join $artifact p05_header.bin]
set zero [file join $root p05_mailbox_zero.bin]
if {![file exists $payload] || [file size $payload] == 0 ||
    [file size $payload] > 0xE0000 || [file size $payload] % 4 != 0} {
    error "P05.1 payload size/alignment invalid"
}
if {![file exists $header] || [file size $header] != 256 ||
    ![file exists $zero] || [file size $zero] != 256} {
    error "P05.1 requires exact 256B header and zero mailbox"
}
lappend files [list $payload 0x43F00000 [expr {[file size $payload] / 4}]]
lappend files [list $header 0x43FE0000 64]
lappend files [list $zero 0x43FF0000 64]
connect -url $server
set stopped 0
for {set core 0} {$core < 4} {incr core} {
    if {![catch {targets -set -filter [format {name =~ "Cortex-A53 #%d"} $core]}]} {
        catch {stop}
        incr stopped
    }
}
if {$stopped == 0} {error "P05.1: no Cortex-A53 was found to stop"}
p05_physical
foreach entry $files {
    lassign $entry file addr words
    puts [format "P05.1 provisioning 0x%08X bytes=%d" $addr [file size $file]]
    dow -data $file $addr
    set check [file join $root [format "readback_%08X.bin" $addr]]
    file delete -force $check
    mrd -bin -file $check $addr $words
    if {![p05_equal $file $check]} {
        error [format "P05.1 physical DDR readback mismatch 0x%08X" $addr]
    }
    file delete -force $check
}
puts "PASS: P05.1 three triangle records, P05G payload/header and zero result mailbox provisioned/read back"
disconnect
