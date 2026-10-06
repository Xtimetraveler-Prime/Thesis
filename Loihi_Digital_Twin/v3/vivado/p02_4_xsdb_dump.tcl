# P02.4 physical DDR dump through XSDB.
if {$argc < 1 || $argc > 2} {
    error "usage: p02_4_xsdb_dump.tcl <dump_dir> ?<xsdb_server_url>?"
}

set dump_dir [file normalize [lindex $argv 0]]
file mkdir $dump_dir
set server_url "tcp:127.0.0.1:3121"
if {$argc == 2} { set server_url [lindex $argv 1] }

set source_dump [file join $dump_dir source_after.bin]
set full_dump [file join $dump_dir full_after.bin]
set mutable_dump [file join $dump_dir mutable_after.bin]
foreach f [list $source_dump $full_dump $mutable_dump] {
    file delete -force $f
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

connect -url $server_url
p02_select_physical_memory_target

# 0x80000 bytes / 4 bytes per default word = 131072 words.
mrd -bin -file $source_dump 0x40000000 131072
mrd -bin -file $full_dump 0x43F00000 131072
mrd -bin -file $mutable_dump 0x43F80000 131072

foreach f [list $source_dump $full_dump $mutable_dump] {
    if {![file exists $f]} { error "P02.4 expected DDR dump missing: $f" }
    if {[file size $f] != 0x80000} {
        error "P02.4 DDR dump must be exactly 512 KiB: $f size=[file size $f]"
    }
}

puts "PASS: P02.4 DDR source/full/mutable records dumped for comparison"
disconnect
