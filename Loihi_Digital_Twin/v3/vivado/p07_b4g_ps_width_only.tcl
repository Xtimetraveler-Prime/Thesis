# P07-B.4g2 PS-ONLY width evidence after a controlled NORMAL board reboot.
# NO PS->PL MMIO accesses, no DDR, no CPU stop/reset, no PS/PL writes.
# Distinguishes the previous accepted 128-bit PS boot selection from
# physical 64-bit selection observed on 2026-10-21 (FPD raw=0x00002560).
# Do NOT run immediately after an earlier AXI/AP timeout: recover first.
if {$argc < 1 || $argc > 2} {
    error "usage: p07_b4g_ps_width_only.tcl READ_ONLY_OPERATOR_APPROVED ?tcp:127.0.0.1:3121?"
}
if {[lindex $argv 0] ne "READ_ONLY_OPERATOR_APPROVED"} {
    error "explicit PS-only probe operator acknowledgment required"
}
set url "tcp:127.0.0.1:3121"
if {$argc == 2} {set url [lindex $argv 1]}
if {![regexp {^tcp:(127[.]0[.]0[.]1|localhost):[0-9]{2,5}$} $url]} {
    error "PS-only diagnostic requires localhost XSDB server"
}

proc p07_b4g_psread {label address} {
    set data [mrd -force -value -size w $address 1]
    if {[llength $data] != 1} {
        error "unexpected PS register response count for $label"
    }
    set hex [lindex $data 0]
    if {![regexp -nocase {^(0x)?[0-9a-f]{1,8}$} $hex]} {
        error "invalid PS register hex word: $label"
    }
    scan $hex %x val
    puts [format "P07_B4G_PS_ONLY_%s_RAW=0x%08X" $label $val]
    set sel [expr {($val >> 8) & 3}]
    switch -- $sel {
        0 {set bits 32}
        1 {set bits 64}
        2 {set bits 128}
        default {set bits RESERVED}
    }
    puts [format "P07_B4G_PS_ONLY_%s_WIDTH_BITS=%s" $label $bits]
    return $sel
}

set connected 0
set rc [catch {
    connect -url $url
    set connected 1
    set target ""
    foreach type {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$type\""} ignored]} {
            set target $type
            break
        }
    }
    if {$target eq ""} {
        error "PSU/APU physical access unavailable"
    }
    puts "P07_B4G_PS_ONLY_TARGET=$target"
    set fpd [p07_b4g_psread FPD_HPM0 0xFD615000]
    set lpd [p07_b4g_psread LPD_HPM0 0xFF419000]
    # Report either selector without treating an unsupported width as a
    # valid PS-PL shell configuration. This script NEVER reads PL MMIO.
    if {$fpd != 2} {
        puts "P07_B4G_PS_ONLY_FPD128_MISMATCH=1"
    }
    if {$lpd != 2} {
        puts "P07_B4G_PS_ONLY_LPD128_MISMATCH=1"
    }
    puts "P07_B4G_PS_ONLY_TWO_PS_REGISTERS_READ=1"
} why]
if {$connected} {
    catch {disconnect}
}
if {$rc} {
    puts "P07_B4G_PS_ONLY_FAIL=1"
    puts "P07_B4G_A53_ELF_DOWNLOAD_AUTHORIZED=0"
    error "P07-B.4g PS-only read failed: $why"
}
puts "P07_B4G_PS_ONLY_DONE_NO_PL_READ=1"
puts "P07_B4G_A53_ELF_DOWNLOAD_AUTHORIZED=0"
puts "P07_B4G_PHYSICAL_INFERENCE_AUTHORIZED=0"
