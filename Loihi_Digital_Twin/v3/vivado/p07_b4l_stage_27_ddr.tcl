# P07-B.4l: standalone dedicated JTAG-only 27-core P02 DDR staging.
# This intentionally overwrites [0x40000000,0x40D80000) while Linux is
# discarded. Requires prior strict A53 stop/FPD128 gate, and original P03 PL.
# Does NOT run an ELF, page contexts into URAM, or dispatch inference.
if {$argc != 4 || [lindex $argv 0] ne "DEDICATED_27_DDR_OVERWRITE_APPROVED"} {
    error "usage: <DEDICATED_27_DDR_OVERWRITE_APPROVED> <27_input_dir> <new_readback_dir> <local_xsdb_url>"
}
set source [file normalize [lindex $argv 1]]
set out [file normalize [lindex $argv 2]]
set server [lindex $argv 3]
if {![regexp {^tcp:(localhost|127[.]0[.]0[.]1):[0-9]{2,5}$} $server]} {
    error "P07-B.4l: localhost XSDB server only"
}
if {![file isdirectory $source] || ![file isdirectory $out]} {
    error "P07-B.4l: source/readback directories must preexist"
}
set inputs {}
set dumps {}
for {set i 0} {$i < 27} {incr i} {
    set input [file join $source [format "core_%03d_stage_512k.bin" $i]]
    set output [file join $out [format "core_%03d_physical_readback_512k.bin" $i]]
    if {![file isfile $input] || [file size $input] != 0x80000 || [file exists $output]} {
        error "P07-B.4l: missing/malformed input or existing readback for core $i"
    }
    lappend inputs $input
    lappend dumps $output
}
# Fail before connecting if there is any other existing readback file.
if {[llength [glob -nocomplain -directory $out *]] != 0} {
    error "P07-B.4l: readback directory must be empty"
}
proc b4l_file_equal {a b} {
    set af [open $a rb]
    set bf [open $b rb]
    fconfigure $af -translation binary -encoding binary
    fconfigure $bf -translation binary -encoding binary
    set equal [expr {[read $af] eq [read $bf]}]
    close $af
    close $bf
    return $equal
}
proc b4l_physical_ddr_target {} {
    foreach target_name {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$target_name\""}]} {
            puts "P07_B4L_PHYSICAL_DDR_TARGET=$target_name"
            return
        }
    }
    error "P07-B.4l: PSU/APU physical target unavailable; refuse CPU/MMU address translation"
}
set connected 0
set rc [catch {
    connect -url $server
    set connected 1
    b4l_physical_ddr_target
    for {set i 0} {$i < 27} {incr i} {
        set addr [expr {0x40000000 + $i * 0x80000}]
        set path [lindex $inputs $i]
        set output [lindex $dumps $i]
        puts [format "P07_B4L_STAGE_CORE=%d ADDRESS=0x%08X BYTES=524288" $i $addr]
        # Only fixed source size and fixed physical addresses; NEVER use
        # the A53 core/MMU target for DDR provisioning.
        dow -data $path $addr
        mrd -bin -file $output $addr 131072
        if {![file isfile $output] || [file size $output] != 0x80000 ||
            ![b4l_file_equal $path $output]} {
            error "P07-B.4l: physical byte readback mismatch on core $i"
        }
        puts "P07_B4L_CORE_${i}_512K_PHYSICAL_READBACK_PASS=1"
    }
    puts "P07_B4L_ALL_27_DDR_CORE_READBACK_TCL_PASS=1"
} err]
if {$connected} {catch {disconnect}}
if {$rc} {
    puts "P07_B4L_DDR_STAGE_FAILED_REBOOT_REQUIRED=1"
    error $err
}
puts "P07_B4L_DDR_STAGE_TCL_DONE_REBOOT_REQUIRED=1"
