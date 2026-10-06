# P02.4 physical DDR fixture provisioning through XSDB.
#
# The board must have booted far enough for PS DDR to be initialized.  This
# script halts all visible Cortex-A53 cores before touching the project-reserved
# 0x4000_0000..0x43FF_FFFF backing window, so Linux cannot allocate or modify
# that memory while the paging experiment runs.
if {$argc < 1 || $argc > 2} {
    error "usage: p02_4_xsdb_prepare.tcl <fixture_dir> ?<xsdb_server_url>?"
}

set fixture_dir [file normalize [lindex $argv 0]]
set server_url "tcp:127.0.0.1:3121"
if {$argc == 2} { set server_url [lindex $argv 1] }

set source_file [file join $fixture_dir source_core0.bin]
set full_file [file join $fixture_dir full_scratch_core126.bin]
set mutable_file [file join $fixture_dir mutable_scratch_core127.bin]
foreach f [list $source_file $full_file $mutable_file] {
    if {![file exists $f]} { error "P02.4 fixture file missing: $f" }
    if {[file size $f] != 0x80000} {
        error "P02.4 fixture file must be exactly 512 KiB: $f"
    }
}

proc p02_select_physical_memory_target {} {
    foreach candidate {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$candidate\""} err]} {
            puts "P02.4 physical DDR access target: $candidate"
            return $candidate
        }
        puts "P02.4 INFO: physical target $candidate unavailable: $err"
    }
    error "P02.4 could not select a non-processor PSU/APU target for physical DDR access"
}

proc p02_binary_files_equal {left right} {
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

connect -url $server_url

set halted 0
for {set i 0} {$i < 4} {incr i} {
    set filter [format {name =~ "Cortex-A53 #%d"} $i]
    if {[catch {targets -set -filter $filter} select_error]} {
        puts "P02.4 INFO: Cortex-A53 #$i not visible: $select_error"
        continue
    }
    if {[catch {stop} stop_error]} {
        puts "P02.4 INFO: stop Cortex-A53 #$i returned: $stop_error"
    }
    incr halted
}
if {$halted == 0} {
    error "P02.4 could not find any Cortex-A53 target. DDR must be initialized and the APU visible."
}

p02_select_physical_memory_target

puts "P02.4 provisioning source record at 0x40000000"
dow -data $source_file 0x40000000
set source_verify [file join $fixture_dir "source_physical_readback.bin"]
file delete -force $source_verify
mrd -bin -file $source_verify 0x40000000 131072
if {![p02_binary_files_equal $source_file $source_verify]} {
    error "P02.4 physical source DDR readback mismatch"
}
file delete -force $source_verify

puts "P02.4 provisioning full-roundtrip scratch at 0x43F00000"
dow -data $full_file 0x43F00000
set full_verify [file join $fixture_dir "full_physical_readback.bin"]
file delete -force $full_verify
mrd -bin -file $full_verify 0x43F00000 131072
if {![p02_binary_files_equal $full_file $full_verify]} {
    error "P02.4 physical full-scratch DDR readback mismatch"
}
file delete -force $full_verify

puts "P02.4 provisioning mutable-roundtrip scratch at 0x43F80000"
dow -data $mutable_file 0x43F80000
set mutable_verify [file join $fixture_dir "mutable_physical_readback.bin"]
file delete -force $mutable_verify
mrd -bin -file $mutable_verify 0x43F80000 131072
if {![p02_binary_files_equal $mutable_file $mutable_verify]} {
    error "P02.4 physical mutable-scratch DDR readback mismatch"
}
file delete -force $mutable_verify

puts "PASS: P02.4 DDR fixtures provisioned and byte-verified by physical readback with A53 cores halted"
disconnect
