# P02.4b dump all five final K26 DDR backing records.
if {$argc < 1 || $argc > 2} {
    error "usage: p02_4b_xsdb_dump.tcl <dump_dir> ?<xsdb_server_url>?"
}

set dump_dir [file normalize [lindex $argv 0]]
file mkdir $dump_dir
set server_url "tcp:127.0.0.1:3121"
if {$argc == 2} { set server_url [lindex $argv 1] }

proc p02b_select_physical_memory_target {} {
    # Processor targets execute memory commands through the processor and
    # therefore apply its MMU translation.  PSU/APU are non-processor DAP
    # targets and access the supplied DDR address physically.
    foreach candidate {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$candidate\""} err]} {
            puts "P02.4b physical DDR access target: $candidate"
            return $candidate
        }
        puts "P02.4b INFO: physical target $candidate unavailable: $err"
    }
    error "P02.4b could not select a non-processor PSU/APU target for physical DDR access"
}

connect -url $server_url
p02b_select_physical_memory_target

for {set core 0} {$core < 5} {incr core} {
    set path [file join $dump_dir [format "core%d_after.bin" $core]]
    file delete -force $path
    set addr [expr {0x40000000 + ($core * 0x80000)}]
    puts [format "P02.4b dumping logical_core=%d address=0x%08X" $core $addr]
    mrd -bin -file $path $addr 131072
    if {![file exists $path]} { error "P02.4b dump missing: $path" }
    if {[file size $path] != 0x80000} {
        error "P02.4b dump must be exactly 512 KiB: $path size=[file size $path]"
    }
}

puts "PASS: P02.4b five final DDR backing records dumped through physical PSU/APU target"
disconnect
