# P07-A4.2c SYNTHETIC RAMP16 negative-gate only.
# INTENTIONALLY changes exactly ONE 32-bit reserved descriptor word
# AFTER accepted byte-exact original XSDB staging readbacks and before
# standalone A53 starts. Never use under Linux DDR ownership.
# Do not change any TRAIN/test staged source or accepted ELF/bitstream.
if {$argc != 4} {
    error "usage: p07_a4_xsdb_inject_descriptor_fault.tcl <synthetic-original-descriptor256> <before256-out> <after256-out> <xsdb-server>"
}
set original [file normalize [lindex $argv 0]]
set before [file normalize [lindex $argv 1]]
set after [file normalize [lindex $argv 2]]
set server [lindex $argv 3]
if {![file exists $original] || [file size $original]!=256 ||
    [file exists $before] || [file exists $after]} {
    error "P07-A4.2c negative: original header missing/wrong or output evidence exists"
}
set fh [open $original rb]
fconfigure $fh -translation binary -encoding binary
set reference [read $fh]
close $fh
if {[string range $reference 0 7] ne "P07A4P01" ||
    [string range $reference 144 147] ne [binary format H8 00000000]} {
    error "P07-A4.2c negative: descriptor is not an accepted zero-reserved A4 input"
}
connect -url $server
targets -set -filter {name =~ "Cortex-A53 #0"}
catch {stop}
set selected 0
foreach name {PSU APU} {
    if {![catch {targets -set -filter "name =~ \"$name\""}]} {
        set selected 1
        break
    }
}
if {!$selected} {error "P07-A4.2c negative: cannot select physical DDR target"}
# Before injection, require original 256-byte physical header EXACTLY
# matches immutable SHA-pinned on-disk staging file.
mrd -bin -file $before 0x43FE0000 64
set fb [open $before rb]
fconfigure $fb -translation binary -encoding binary
set beforeBytes [read $fb]
close $fb
if {$beforeBytes ne $reference} {
    error "P07-A4.2c negative: pre-fault physical descriptor mismatch"
}
# The reserved word at descriptor byte 144 = physical 0x43FE0090.
# It was zero. Make it 0x00000001, ONLY this one aligned 32-bit word.
mwr 0x43FE0090 0x00000001
mrd -bin -file $after 0x43FE0000 64
set fa [open $after rb]
fconfigure $fa -translation binary -encoding binary
set afterBytes [read $fa]
close $fa
set expected [string replace $beforeBytes 144 147 [binary format H8 01000000]]
if {$afterBytes ne $expected} {
    error "P07-A4.2c negative: descriptor physical mutation not EXACT one reserved word"
}
puts "P07_A4_2C_DESCRIPTOR_FAULT_ADDRESS=0x43FE0090"
puts "P07_A4_2C_DESCRIPTOR_ONE_WORD_PHYSICAL_FAULT_CONFIRMED=1"
puts "P07_A4_2C_NEGATIVE_A53_INFERENCE=NOT_STARTED"
disconnect
