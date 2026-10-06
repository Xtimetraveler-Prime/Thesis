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

    set verify_path [file join $fixture_dir [format "core%d_physical_readback.bin" $core]]
    file delete -force $verify_path
    mrd -bin -file $verify_path $addr 131072
    if {![file exists $verify_path]} {
        error "P02.4b physical readback missing: $verify_path"
    }
    if {[file size $verify_path] != 0x80000} {
        error "P02.4b physical readback size mismatch: $verify_path size=[file size $verify_path]"
    }
    if {![p02_binary_files_equal $path $verify_path]} {
        error "P02.4b physical DDR readback mismatch for logical core $core"
    }
    file delete -force $verify_path
}

puts "PASS: P02.4b five authoritative DDR backing records provisioned and byte-verified by physical readback"
disconnect
