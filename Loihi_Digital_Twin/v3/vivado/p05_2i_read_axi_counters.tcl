# P05.2i READ-ONLY physical PL page AXI success counters after A53 has halted.
# The four contiguous MMIO words are read via existing PSU/APU DAP.
# 0xA4000044 completed READ burst transactions
# 0xA4000048 completed WRITE burst transactions
# 0xA400004C total bytes moved [31:0]
# 0xA4000050 total bytes moved [63:32].
#
# Do NOT alter any register, reset PL or reboot before capturing this witness.
# If this debugger-side PSU/APU target cannot reach PS->PL MMIO, fail CLOSED
# and retain the original untouched physical P05.2h outputs for investigation.
if {$argc < 1 || $argc > 2} {
    error "usage: p05_2i_read_axi_counters.tcl <physical-evidence-dir> ?XSDB-url?"
}
set out [file normalize [lindex $argv 0]]
set server "tcp:127.0.0.1:3121"
if {$argc == 2} {set server [lindex $argv 1]}
if {![file exists [file join $out p05_a53_result.bin]] ||
    ![file exists [file join $out final_ddr core0_after.bin]]} {
    error "P05.2i requires original finalized A53 and DDR evidence first"
}
set witness [file join $out p05_2i_axi_witness.bin]
set first_file "$witness.first"
set second_file "$witness.second"
# A previous (unforced) XSDB mrd can create an EMPTY witness before the
# memory-map guard rejects the address. Retain that original failed
# artifact separately; NEVER overwrite any nonempty captured witness.
if {[file exists $witness]} {
    if {[file size $witness] != 0} {
        error "P05.2i never overwrites nonempty physical AXI evidence"
    }
    set blocked "$witness.original_unforced_block.bin"
    if {[file exists $blocked]} {
        error "P05.2i previous blocked-mrd artifact already archived"
    }
    file rename -- $witness $blocked
    puts "P05_2I_ORIGINAL_BLOCKED_MRD_ARCHIVE=$blocked"
}
if {[file exists $first_file] || [file exists $second_file]} {
    error "P05.2i prior partial AXI counter read exists; do not overwrite evidence"
}
connect -url $server
set found 0
foreach target {PSU APU} {
    if {![catch {targets -set -filter "name =~ \"$target\""}]} {
        puts "P05_2I_PHYSICAL_PL_MMIO_TARGET=$target"
        set found 1
        break
    }
}
if {!$found} {error "P05.2i no nonprocessor PSU/APU memory access target"}
# The A53 is already halted by accepted P03_finish_xsdb_run.tcl.
# Two identical passive reads provide a stable terminal counter snapshot.
# AMD UG1725 / UG1400 mrd -force: override debugger SOFTWARE memory
# map validation. This never changes PS/PL hardware XMPU/XPPU policy,
# issues NO writes, and cannot overcome a truly blocked AXI path.
# The accepted A53 had just used the SAME PS->PL 0xA4000000 window.
mrd -force -bin -file $first_file 0xA4000044 4
if {![file exists $first_file] || [file size $first_file] != 16} {
    error "P05.2i forced PL read did not produce four actual MMIO words"
}
mrd -force -bin -file $second_file 0xA4000044 4
if {![file exists $second_file] || [file size $second_file] != 16} {
    error "P05.2i second forced PL AXI read incomplete"
}
set a [open $first_file rb]
fconfigure $a -translation binary -encoding binary
set first [read $a]
close $a
set b [open $second_file rb]
fconfigure $b -translation binary -encoding binary
set second [read $b]
close $b
if {$first ne $second} {
    error "P05.2i hardware page AXI counters changed AFTER A53 terminal; unstable snapshot"
}
binary scan $first i4 values
set readb [expr {[lindex $values 0] & 0xFFFFFFFF}]
set writeb [expr {[lindex $values 1] & 0xFFFFFFFF}]
set lo [expr {[lindex $values 2] & 0xFFFFFFFF}]
set hi [expr {[lindex $values 3] & 0xFFFFFFFF}]
set bytes [expr {($hi << 32) | $lo}]
# Promote physical evidence ONLY after two stable reads have completed.
file rename -- $first_file $witness
file delete -- $second_file
puts "P05_2I_PL_HARDWARE_AXI_READ_BURSTS=$readb"
puts "P05_2I_PL_HARDWARE_AXI_WRITE_BURSTS=$writeb"
puts "P05_2I_PL_HARDWARE_AXI_SUCCESSFUL_BYTES=$bytes"
puts "PASS: P05.2i four live PL AXI page-counter words read-only captured twice and identical"
puts "P05_2I_HW_COUNTER_WITNESS=$witness"
disconnect
