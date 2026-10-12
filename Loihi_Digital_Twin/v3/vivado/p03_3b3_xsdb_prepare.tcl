# P03.3b3 provision one accepted context record and clear the result mailbox.
if {$argc < 1 || $argc > 2} {
    error "usage: p03_3b3_xsdb_prepare.tcl <fixture_dir> ?<xsdb_server_url>?"
}

set fixture_dir [file normalize [lindex $argv 0]]
set server_url "tcp:127.0.0.1:3121"
if {$argc == 2} { set server_url [lindex $argv 1] }

proc p03_select_physical_target {} {
    foreach candidate {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$candidate\""} err]} {
            puts "P03.3b3 physical DDR access target: $candidate"
            return
        }
        puts "P03.3b3 INFO: physical target $candidate unavailable: $err"
    }
    error "P03.3b3 could not select PSU/APU physical-memory target"
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

set mailbox_zero [file join $fixture_dir mailbox_zero.bin]
set records [list \
    [list [file join $fixture_dir core0_initial.bin] 0x40000000] \
    [list [file join $fixture_dir core1_initial.bin] 0x40080000] \
]
foreach pair $records {
    set p [lindex $pair 0]
    if {![file exists $p] || [file size $p] != 0x80000} {
        error "P03.3b3 two-core context must exist and contain 512 KiB: $p"
    }
}
if {![file exists $mailbox_zero] || [file size $mailbox_zero] != 128} {
    error "P03.3b3 mailbox zero image must be exactly 128 bytes"
}

connect -url $server_url

set halted 0
for {set i 0} {$i < 4} {incr i} {
    set filter [format {name =~ "Cortex-A53 #%d"} $i]
    if {[catch {targets -set -filter $filter} select_error]} {
        puts "P03.3b3 INFO: Cortex-A53 #$i not visible: $select_error"
        continue
    }
    catch {stop}
    incr halted
}
if {$halted == 0} {
    error "P03.3b3 could not find any Cortex-A53 target"
}
p03_select_physical_target

foreach pair $records {
    set record [lindex $pair 0]
    set record_addr [lindex $pair 1]
    puts [format "P03.3b3 provisioning backing record %s at 0x%08X" $record $record_addr]
    dow -data $record $record_addr
    set verify_record [file join $fixture_dir [format "record_%08X_readback.bin" $record_addr]]
    file delete -force $verify_record
    mrd -bin -file $verify_record $record_addr 131072
    if {![p03_files_equal $record $verify_record]} {
        error "P03.3b3 physical DDR backing record mismatch: $record"
    }
    file delete -force $verify_record
}
set mailbox_addr 0x43FF0000
puts [format "P03.3b3 clearing 128-byte mailbox at 0x%08X" $mailbox_addr]
dow -data $mailbox_zero $mailbox_addr
set verify_mailbox [file join $fixture_dir mailbox_physical_readback.bin]
file delete -force $verify_mailbox
mrd -bin -file $verify_mailbox $mailbox_addr 32
if {![p03_files_equal $mailbox_zero $verify_mailbox]} {
    error "P03.3b3 physical mailbox clear mismatch"
}
file delete -force $verify_mailbox
puts "PASS: P03.3b3 two 512KiB backing records and 128-byte mailbox physically verified"
disconnect
