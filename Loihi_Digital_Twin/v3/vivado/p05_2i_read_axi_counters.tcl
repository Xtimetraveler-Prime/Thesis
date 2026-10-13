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
if {[file exists $witness] || [file exists "$witness.second"]} {
    error "P05.2i never overwrites previously captured physical counter evidence"
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
mrd -bin -file $witness 0xA4000044 4
if {![file exists $witness] || [file size $witness] != 16} {
    error "P05.2i physical PL counter register read did not return four 32-bit words"
}
mrd -bin -file "$witness.second" 0xA4000044 4
if {![file exists "$witness.second"] || [file size "$witness.second"] != 16} {
    error "P05.2i second physical PL AXI counter snapshot incomplete"
}
set a [open $witness rb]
fconfigure $a -translation binary -encoding binary
set first [read $a]
close $a
set b [open "$witness.second" rb]
fconfigure $b -translation binary -encoding binary
set second [read $b]
close $b
if {$first ne $second} {
    error "P05.2i hardware page AXI counters changed AFTER A53 terminal; unstable snapshot"
}
file delete -force "$witness.second"
binary scan $first i4 values
set readb [expr {[lindex $values 0] & 0xFFFFFFFF}]
set writeb [expr {[lindex $values 1] & 0xFFFFFFFF}]
set lo [expr {[lindex $values 2] & 0xFFFFFFFF}]
set hi [expr {[lindex $values 3] & 0xFFFFFFFF}]
set bytes [expr {($hi << 32) | $lo}]
puts "P05_2I_PL_HARDWARE_AXI_READ_BURSTS=$readb"
puts "P05_2I_PL_HARDWARE_AXI_WRITE_BURSTS=$writeb"
puts "P05_2I_PL_HARDWARE_AXI_SUCCESSFUL_BYTES=$bytes"
puts "PASS: P05.2i four live PL AXI page-counter words read-only captured twice and identical"
puts "P05_2I_HW_COUNTER_WITNESS=$witness"
disconnect
