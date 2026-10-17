# P07-A4.2c candidate persistent A53 physical staging.
# Dedicated bare-metal JTAG 0x40000000..0x43FFFFFF DDR owner ONLY.
# No official t10k source access and NO neural dispatch from host.
if {$argc < 4 || $argc > 5} {
    error "usage: p07_a4_xsdb_prepare.tcl <frozen-master> <validation-stage-dir> <trace-zero64k> <readback-dir> ?server?"
}
set master [file normalize [lindex $argv 0]]
set stage [file normalize [lindex $argv 1]]
set tracezero [file normalize [lindex $argv 2]]
set out [file normalize [lindex $argv 3]]
set server "tcp:127.0.0.1:3121"
if {$argc == 5} {set server [lindex $argv 4]}
set desc [file join $stage p07_a4_descriptor_256.bin]
set mapping [file join $stage p07_a4_mapping_1568.bin]
set pixels [file join $stage p07_a4_pixels_raw.bin]
set journal [file join $stage p07_a4_journal_initial_1m.bin]
set files [list [list $master 0x43F00000 524288]                 [list $pixels 0x41000000 -1]                 [list $desc 0x43FE0000 256]                 [list $mapping 0x43FE0100 1568]                 [list $journal 0x42000000 1048576]                 [list $tracezero 0x43FF0000 65536]]
foreach item $files {
    lassign $item file base expected
    if {![file exists $file] || [file size $file] <= 0 ||
        [file size $file] % 4 != 0} {
        error "P07-A4.2c missing/unaligned staging file $file"
    }
    if {$expected >= 0 && [file size $file] != $expected} {
        error "P07-A4.2c bad staging file length $file"
    }
}
if {[file size $pixels] > 7840000 || [file size $pixels] < 784 ||
    [file size $pixels] % 784 != 0} {
    error "P07-A4.2c validation raw pixels invalid size"
}
if {[lindex [exec sha256sum $master] 0] ne
    "9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955"} {
    error "P07-A4.2c immutable trained DDR image differs from acceptance"
}
file mkdir $out
proc p07_a4_physical_target {} {
    foreach name {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$name\""}]} {
            return
        }
    }
    error "P07-A4.2c physical PSU/APU target unavailable"
}
proc p07_a4_equal {left right} {
    set f [open $left rb]
    set g [open $right rb]
    fconfigure $f -translation binary -encoding binary
    fconfigure $g -translation binary -encoding binary
    set ok [expr {[read $f] eq [read $g]}]
    close $f
    close $g
    return $ok
}
connect -url $server
targets -set -filter {name =~ "Cortex-A53 #0"}
catch {stop}
p07_a4_physical_target
foreach item $files {
    lassign $item file base expected
    set size [file size $file]
    set dump [file join $out [format "readback_%08X.bin" $base]]
    if {[file exists $dump]} {
        error "P07-A4.2c refusing overwrite of staging readback"
    }
    puts [format "P07-A4.2c staging 0x%08X (%d bytes)" $base $size]
    dow -data $file $base
    mrd -bin -file $dump $base [expr {$size / 4}]
    if {![p07_a4_equal $file $dump]} {
        error "P07-A4.2c byte-exact staged DDR readback mismatch"
    }
}
puts "P07_A4_2C_XSDB_PROVISION_PASS=1"
puts "P07_A4_2C_KV260_INFERENCE=NOT_RUN"
disconnect
