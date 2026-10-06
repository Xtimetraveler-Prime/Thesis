# P02.4b provision five authoritative logical-context records into K26 DDR.
if {$argc < 1 || $argc > 2} {
    error "usage: p02_4b_xsdb_prepare.tcl <fixture_dir> ?<xsdb_server_url>?"
}

set fixture_dir [file normalize [lindex $argv 0]]
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

set halted 0
for {set i 0} {$i < 4} {incr i} {
    set filter [format {name =~ "Cortex-A53 #%d"} $i]
    if {[catch {targets -set -filter $filter} select_error]} {
        puts "P02.4b INFO: Cortex-A53 #$i not visible: $select_error"
        continue
    }
    if {[catch {stop} stop_error]} {
        puts "P02.4b INFO: stop Cortex-A53 #$i returned: $stop_error"
    }
    incr halted
}
if {$halted == 0} {
    error "P02.4b could not find any Cortex-A53 target"
}
p02b_select_physical_memory_target

for {set core 0} {$core < 5} {incr core} {
    set path [file join $fixture_dir [format "core%d_initial.bin" $core]]
    if {![file exists $path]} { error "P02.4b fixture missing: $path" }
    if {[file size $path] != 0x80000} {
        error "P02.4b fixture must be exactly 512 KiB: $path"
    }
    set addr [expr {0x40000000 + ($core * 0x80000)}]
    puts [format "P02.4b provisioning logical_core=%d address=0x%08X" $core $addr]
    dow -data $path $addr
    verify -data $path $addr
}

puts "PASS: P02.4b five authoritative DDR backing records provisioned and verified through physical PSU/APU target"
disconnect
