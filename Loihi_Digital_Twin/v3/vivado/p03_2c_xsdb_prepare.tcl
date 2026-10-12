# P03.2c provision one accepted context record and clear the result mailbox.
if {$argc < 1 || $argc > 2} {
    error "usage: p03_2c_xsdb_prepare.tcl <fixture_dir> ?<xsdb_server_url>?"
}

set fixture_dir [file normalize [lindex $argv 0]]
set server_url "tcp:127.0.0.1:3121"
if {$argc == 2} { set server_url [lindex $argv 1] }

proc p03_select_physical_target {} {
    foreach candidate {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$candidate\""} err]} {
            puts "P03.2c physical DDR access target: $candidate"
            return
        }
        puts "P03.2c INFO: physical target $candidate unavailable: $err"
    }
    error "P03.2c could not select PSU/APU physical-memory target"
}

proc p03_files_equal {left right} {
    set lf [open $left rb]
    set rf [open $right rb]
    fconfigure $lf -translation binary -encoding binary
    fconfigure $rf -translation binary -encoding binary
    set ldata [read $lf]
    set rdata [read $rf]
    close $lf
    close $rf
    return [expr {$ldata eq $rdata}]
}

set record [file join $fixture_dir core0_initial.bin]
set mailbox_zero [file join $fixture_dir mailbox_zero.bin]
foreach path [list $record $mailbox_zero] {
    if {![file exists $path]} { error "P03.2c fixture missing: $path" }
}
if {[file size $record] != 0x80000} {
    error "P03.2c context record must be exactly 512 KiB"
}
if {[file size $mailbox_zero] != 64} {
    error "P03.2c mailbox zero image must be exactly 64 bytes"
}

connect -url $server_url

set halted 0
for {set i 0} {$i < 4} {incr i} {
    set filter [format {name =~ "Cortex-A53 #%d"} $i]
    if {[catch {targets -set -filter $filter} select_error]} {
        puts "P03.2c INFO: Cortex-A53 #$i not visible: $select_error"
        continue
    }
    catch {stop}
    incr halted
}
if {$halted == 0} {
    error "P03.2c could not find any Cortex-A53 target"
}

p03_select_physical_target

set record_addr 0x40000000
set mailbox_addr 0x43FF0000

puts [format "P03.2c provisioning core0 backing record at 0x%08X" $record_addr]
dow -data $record $record_addr
set verify_record [file join $fixture_dir core0_physical_readback.bin]
file delete -force $verify_record
mrd -bin -file $verify_record $record_addr 131072
if {![p03_files_equal $record $verify_record]} {
    error "P03.2c core0 physical DDR readback mismatch"
}
file delete -force $verify_record

puts [format "P03.2c clearing result mailbox at 0x%08X" $mailbox_addr]
dow -data $mailbox_zero $mailbox_addr
set verify_mailbox [file join $fixture_dir mailbox_physical_readback.bin]
file delete -force $verify_mailbox
mrd -bin -file $verify_mailbox $mailbox_addr 16
if {![p03_files_equal $mailbox_zero $verify_mailbox]} {
    error "P03.2c mailbox clear readback mismatch"
}
file delete -force $verify_mailbox

puts "PASS: P03.2c backing record provisioned and mailbox cleared by physical readback"
disconnect
