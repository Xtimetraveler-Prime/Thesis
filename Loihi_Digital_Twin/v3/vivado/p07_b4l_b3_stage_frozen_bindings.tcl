# B4l same-session static 16KiB frozen B2.4 registrations provisioning.
# NEVER operate under live Linux. Caller must have successfully verified
# original 27x512KiB P02 DDR staging in THIS JTAG session.
# Physical data only to accepted [0x43FC0000,0x43FC4000); no A53 MMU.
if {$argc != 4 || [lindex $argv 0] ne "B4L_FROZEN_BINDING_16K_OVERWRITE_APPROVED"} {
    error "usage: <B4L_FROZEN_BINDING_16K_OVERWRITE_APPROVED> <original_bindings16k> <new_readback16k> <local_xsdb>"
}
set input [file normalize [lindex $argv 1]]
set out [file normalize [lindex $argv 2]]
set server [lindex $argv 3]
if {![regexp {^tcp:(localhost|127[.]0[.]0[.]1):[0-9]{2,5}$} $server]} {
    error "B4l B3: XSDB must be local"
}
if {![file isfile $input] || [file size $input]!=16384 ||
        [file exists $out] || ![file isdirectory [file dirname $out]]} {
    error "B4l B3: original fixed 16KiB input/new readback path invalid"
}
set f [open $input rb]
fconfigure $f -translation binary -encoding binary
set expected [read $f]
close $f
if {[string length $expected]!=16384 ||
        [string range $expected 0 7] ne "B4BIND01"} {
    error "B4l B3: frozen binary descriptor magic/length invalid"
}
proc b4l_b3_psu_only {} {
    foreach name {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$name\""}]} {
            puts "P07_B4L_B3_DESCRIPTOR_PHYSICAL_TARGET=$name"
            return
        }
    }
    error "B4l B3: physical PSU/APU target missing; refuse A53/MMU access"
}
set connected 0
set rc [catch {
    connect -url $server
    set connected 1
    b4l_b3_psu_only
    dow -data $input 0x43FC0000
    mrd -bin -file $out 0x43FC0000 4096
    if {![file isfile $out] || [file size $out]!=16384} {
        error "B4l B3: real 16KiB readback missing/truncated"
    }
    set f [open $out rb]
    fconfigure $f -translation binary -encoding binary
    set got [read $f]
    close $f
    if {$got ne $expected} {
        error "B4l B3: real descriptor differs byte for byte from authenticated frozen source"
    }
    puts "P07_B4L_B3_FROZEN_DESCRIPTOR_16K_PHYSICAL_READBACK_TCL_PASS=1"
} why]
if {$connected} {catch {disconnect}}
if {$rc} {
    puts "P07_B4L_B3_DESCRIPTOR_BOARD_ATTEMPT_FAIL_REBOOT_REQUIRED=1"
    error $why
}
puts "P07_B4L_B3_DESCRIPTOR_STAGE_DONE_REBOOT_REQUIRED=1"
