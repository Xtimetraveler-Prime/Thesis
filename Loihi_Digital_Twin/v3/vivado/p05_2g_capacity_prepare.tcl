# P05.2g physical one-core 4096/4097 event-bank boundary regression: provision P05G v1 deployment.
# All DDR via nonprocessor PSU/APU; never route/dispatch by XSDB.
# Explicitly limited to core0, one timestep and one physical slot.
if {$argc < 1 || $argc > 2} {
    error "usage: p05_2g_capacity_prepare.tcl <probe-dir> ?server-url?"
}
set root [file normalize [lindex $argv 0]]
set server "tcp:127.0.0.1:3121"
if {$argc == 2} {set server [lindex $argv 1]}
set artifact [file join $root p05_artifacts]
set fixture [file join $root capacity_golden]
set files {}

proc p05_physical {} {
    foreach target {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$target\""}]} {
            puts "P05.2g physical DDR target: $target"
            return
        }
    }
    error "P05.2g: no physical PSU/APU target"
}
proc p05_equal {a b} {
    set x [open $a rb]; set y [open $b rb]
    fconfigure $x -translation binary -encoding binary
    fconfigure $y -translation binary -encoding binary
    set ok [expr {[read $x] eq [read $y]}]
    close $x;close $y
    return $ok
}
for {set core 0} {$core < 1} {incr core} {
    set path [file join $artifact [format "core%d_initial.bin" $core]]
    set frozen [file join $fixture [format "core%d_initial.bin" $core]]
    if {![file exists $path] || [file size $path] != 0x80000 ||
        ![file exists $frozen] || ![p05_equal $path $frozen]} {
        error "P05.2g requires independent-capacity-model-identical 512KiB initial DDR core $core"
    }
    lappend files [list $path [expr {0x40000000+$core*0x80000}] 131072]
}
set payload [file join $artifact p05_payload.bin]
set header [file join $artifact p05_header.bin]
set zero [file join $root p05_mailbox_zero.bin]
if {![file exists $payload] || [file size $payload] == 0 ||
    [file size $payload] > 0xE0000 || [file size $payload] % 4 != 0} {
    error "P05.2g payload size/alignment invalid"
}
if {![file exists $header] || [file size $header] != 256 ||
    ![file exists $zero] || [file size $zero] != 256} {
    error "P05.2g requires exact 256B header and zero mailbox"
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
if {$stopped == 0} {error "P05.2g: no Cortex-A53 was found to stop"}
p05_physical
foreach entry $files {
    lassign $entry file addr words
    puts [format "P05.2g provisioning 0x%08X bytes=%d" $addr [file size $file]]
    dow -data $file $addr
    set check [file join $root [format "readback_%08X.bin" $addr]]
    file delete -force $check
    mrd -bin -file $check $addr $words
    if {![p05_equal $file $check]} {
        error [format "P05.2g physical DDR readback mismatch 0x%08X" $addr]
    }
    file delete -force $check
}
puts "PASS: P05.2g one initial record, P05G payload/header and zero result mailbox provisioned/read back"
disconnect
