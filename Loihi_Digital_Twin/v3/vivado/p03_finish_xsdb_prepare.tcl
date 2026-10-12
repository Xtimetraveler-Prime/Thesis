# P03 final: provision frozen P02.4b five-core DDR + 256B manifest/mailbox.
# All accesses are physical via nonprocessor PSU/APU. No algorithmic control.
if {$argc < 1 || $argc > 2} {
    error "usage: p03_finish_xsdb_prepare.tcl <fixture-dir> ?server-url?"
}
set dir [file normalize [lindex $argv 0]]
set server "tcp:127.0.0.1:3121"
if {$argc == 2} { set server [lindex $argv 1] }

proc p03_physical_target {} {
    foreach name {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$name\""} e]} {
            puts "P03 physical DDR target: $name"
            return
        }
    }
    error "P03: PSU/APU physical DDR target unavailable"
}
proc p03_equal_files {a b} {
    set x [open $a rb]
    set y [open $b rb]
    fconfigure $x -translation binary -encoding binary
    fconfigure $y -translation binary -encoding binary
    set same [expr {[read $x] eq [read $y]}]
    close $x
    close $y
    return $same
}
set files {}
for {set core 0} {$core < 5} {incr core} {
    set file [file join $dir [format "core%d_initial.bin" $core]]
    if {![file exists $file] || [file size $file] != 0x80000} {
        error "P03 missing/incorrect 512 KiB core record: $file"
    }
    lappend files [list $file [expr {0x40000000+$core*0x80000}] 131072]
}
set cfg [file join $dir p03_run_config.bin]
set zero [file join $dir mailbox_zero.bin]
foreach file [list $cfg $zero] {
    if {![file exists $file] || [file size $file] != 256} {
        error "P03 expected exactly 256 bytes in $file"
    }
}
lappend files [list $cfg 0x43FE0000 64]
lappend files [list $zero 0x43FF0000 64]

connect -url $server
set halted 0
for {set core 0} {$core < 4} {incr core} {
    if {![catch {targets -set -filter [format {name =~ "Cortex-A53 #%d"} $core]}]} {
        catch {stop}
        incr halted
    }
}
if {$halted == 0} { error "P03: no Cortex-A53 target to halt" }
p03_physical_target
foreach entry $files {
    lassign $entry file addr words
    puts [format "P03 provisioning physical 0x%08X from %s" $addr $file]
    dow -data $file $addr
    set check [file join $dir [format "p03_readback_%08X.bin" $addr]]
    file delete -force $check
    mrd -bin -file $check $addr $words
    if {![p03_equal_files $file $check]} {
        error [format "P03 provisioning byte mismatch at 0x%08X" $addr]
    }
    file delete -force $check
}
puts "PASS: P03 five DDR records, 256B launch manifest and 256B mailbox provisioned/read back"
disconnect
