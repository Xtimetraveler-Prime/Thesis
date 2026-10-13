# P05.1 triangle: read all five authoritative DDR records after A53 has halted.
if {$argc < 1 || $argc > 2} {
    error "usage: p05_1_triangle_dump.tcl <dump-dir> ?server-url?"
}
set out [file normalize [lindex $argv 0]]
set server "tcp:127.0.0.1:3121"
if {$argc == 2} { set server [lindex $argv 1] }
file mkdir $out
connect -url $server
set found 0
foreach name {PSU APU} {
    if {![catch {targets -set -filter "name =~ \"$name\""}]} {
        puts "P05.1 triangle final-dump physical target: $name"
        set found 1
        break
    }
}
if {!$found} { error "P05 triangle cannot dump physical DDR via PSU/APU" }
for {set core 0} {$core < 3} {incr core} {
    set addr [expr {0x40000000+$core*0x80000}]
    set file [file join $out [format "core%d_after.bin" $core]]
    file delete -force $file
    mrd -bin -file $file $addr 131072
    if {![file exists $file] || [file size $file] != 0x80000} {
        error "P05.1 triangle DDR core $core wrong size"
    }
    puts [format "P05.1 triangle physical DDR core=%d addr=0x%08X bytes=%d" $core $addr [file size $file]]
}
puts "PASS: P05.1 three triangle authoritative DDR records captured from KV260"
disconnect
