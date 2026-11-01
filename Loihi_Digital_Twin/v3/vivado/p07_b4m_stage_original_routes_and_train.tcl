# P07-B.4m dedicated physical ORIGINAL route/TRAIN staging and readback only.
# Preconditions: dedicated halted A53/Linux discarded, accepted PS128,
# P03 shell, 27 contexts and original 16 KiB descriptor staged/read back.
# NEVER launch A53; REBOOT after any physical attempt.
if {$argc != 6 || [lindex $argv 0] ne "B4M_ORIGINAL_TRAIN_ROUTE_AND_FRAME_DDR_OVERWRITE_APPROVED"} {
    error "B4m: <approval> <outputs80k> <inputs896k> <trainframe> <readbackdir> <localhost_xsdb>"
}
set outputs [file normalize [lindex $argv 1]]
set inputs [file normalize [lindex $argv 2]]
set frame [file normalize [lindex $argv 3]]
set destination [file normalize [lindex $argv 4]]
set server [lindex $argv 5]
if {![regexp {^tcp:(localhost|127[.]0[.]0[.]1):[0-9]{2,5}$} $server]} {
    error "B4m: local XSDB server required"
}
if {![file isdirectory $destination] || [llength [glob -nocomplain -directory $destination *]]} {
    error "B4m: fresh empty readback directory required"
}
if {![file isfile $outputs] || [file size $outputs]!=81920 ||
    ![file isfile $inputs] || [file size $inputs]!=917504 ||
    ![file isfile $frame] || [file size $frame]<128 ||
    [file size $frame]>917504 || [file size $frame]%4!=0} {
    error "B4m: missing original signed byte-exact or 4-byte-aligned TRAIN input"
}
proc b4m_data {path} {
    set f [open $path rb]
    fconfigure $f -translation binary -encoding binary
    set d [read $f]
    close $f
    return $d
}
set source_paths [list $outputs $inputs $frame]
set addresses {0x43FC4000 0x41000000 0x41100000}
set names {output_routes_80k_physical.bin input_routes_896k_physical.bin original_TRAIN_ingress_physical.bin}
set magics {B4MROUT1 B4MING01 P06B13I1}
for {set i 0} {$i < 3} {incr i} {
    set in [lindex $source_paths $i]
    set out [file join $destination [lindex $names $i]]
    if {[file exists $out] || [string range [b4m_data $in] 0 7] ne [lindex $magics $i]} {
        error "B4m: original signed file header or readback destination mismatch"
    }
}
if {[expr {0x43FC4000+81920}]>0x43FE0000 ||
    [expr {0x41000000+917504}]>0x41100000 ||
    [expr {0x41100000+[file size $frame]}]>0x411E0000} {
    error "B4m: external routing data exceeds reserved physical DDR spans"
}
proc b4m_psu_only {} {
    foreach name {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$name\""}]} {
            puts "P07_B4M_PHYSICAL_DDR_TARGET=$name"
            return
        }
    }
    error "B4m: physical PSU/APU target unavailable; refuse virtual memory writes"
}
set connected 0
set rc [catch {
    connect -url $server
    set connected 1
    b4m_psu_only
    for {set i 0} {$i < 3} {incr i} {
        set in [lindex $source_paths $i]
        set addr [lindex $addresses $i]
        set out [file join $destination [lindex $names $i]]
        set bytes [file size $in]
        puts [format "P07_B4M_DDR_STAGE_%d_ADDR=%s_BYTES=%d" $i $addr $bytes]
        dow -data $in $addr
        mrd -bin -file $out $addr [expr {$bytes/4}]
        if {![file isfile $out] || [file size $out]!=$bytes ||
            [b4m_data $out] ne [b4m_data $in]} {
            error "B4m: original route/frame byte mismatch at physical address $addr"
        }
        puts [format "P07_B4M_DDR_STAGE_%d_BYTE_EXACT_PASS=1" $i]
    }
    puts "P07_B4M_ORIGINAL_ROUTES_AND_TRAIN_3_DDR_READBACK_PASS=1"
} err]
if {$connected} {catch {disconnect}}
if {$rc} {
    puts "P07_B4M_PHYSICAL_STAGING_ATTEMPT_FAIL_REBOOT_REQUIRED=1"
    error $err
}
puts "P07_B4M_PHYSICAL_STAGING_PASS_REBOOT_REQUIRED=1"
