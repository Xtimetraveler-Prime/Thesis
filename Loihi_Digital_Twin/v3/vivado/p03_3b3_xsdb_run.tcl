# P03.3b3 download/run standalone A53 smoke ELF and dump result mailbox.
if {$argc < 2 || $argc > 3} {
    error "usage: p03_3b3_xsdb_run.tcl <elf> <mailbox_dump> ?<xsdb_server_url>?"
}

set elf [file normalize [lindex $argv 0]]
set mailbox_dump [file normalize [lindex $argv 1]]
set server_url "tcp:127.0.0.1:3121"
if {$argc == 3} { set server_url [lindex $argv 2] }

if {![file exists $elf]} { error "P03.3b3 ELF missing: $elf" }

proc p03_select_physical_target {} {
    foreach candidate {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$candidate\""} err]} {
            puts "P03.3b3 physical mailbox target: $candidate"
            return
        }
        puts "P03.3b3 INFO: physical target $candidate unavailable: $err"
    }
    error "P03.3b3 could not select PSU/APU physical-memory target"
}

connect -url $server_url

targets -set -filter {name =~ "Cortex-A53 #0"}
catch {stop}
catch {rst -processor}
dow $elf
puts "PASS: P03.3b3 standalone ELF downloaded to Cortex-A53 #0"
con

# The physical operations complete in milliseconds; allow generous startup
# margin for the standalone CRT/BSP and JTAG-controlled run.
after 3000

p03_select_physical_target
file delete -force $mailbox_dump
mrd -bin -file $mailbox_dump 0x43FF0000 32
if {![file exists $mailbox_dump] || [file size $mailbox_dump] != 128} {
    error "P03.3b3 mailbox dump missing or wrong size"
}

targets -set -filter {name =~ "Cortex-A53 #0"}
catch {stop}

puts "PASS: P03.3b3 A53 smoke executed and 128-byte mailbox dumped"
disconnect
