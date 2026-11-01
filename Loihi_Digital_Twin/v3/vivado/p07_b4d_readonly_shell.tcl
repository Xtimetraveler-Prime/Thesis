# P07-B.4d READ-ONLY PS/PL shell snapshot. Operator-triggered ONLY.
# Unlike accepted P03_2c_xsdb_ps_axi_width_diag.tcl, this does not stop
# any Cortex-A53 processor: no reset, halt, dow, PL programming or writes.
# Invoking XSDB still requires explicit ownership/board approval.
if {$argc > 1} {
    error "usage: p07_b4d_readonly_shell.tcl ?<xsdb_server_url>?"
}
set url "tcp:127.0.0.1:3121"
if {$argc == 1} {set url [lindex $argv 0]}

proc p07_b4d_read32 {label address} {
    set raw [mrd -force -size w $address 1]
    if {![regexp -nocase {^[[:xdigit:]]+:[[:space:]]+([[:xdigit:]]{8})} [string trim $raw] match hex]} {
        error "P07-B.4d failed to parse read-only $label at $address: $raw"
    }
    scan $hex %x integer
    puts [format "P07_B4D_%s=0x%08X" $label $integer]
    return $integer
}

connect -url $url
set selected ""
foreach candidate {PSU APU} {
    if {![catch {targets -set -filter "name =~ \"$candidate\""} why]} {
        set selected $candidate
        break
    }
}
if {$selected eq ""} {
    error "P07-B.4d unable to access read-only PSU/APU memory target"
}
puts "P07_B4D_PHYSICAL_TARGET=$selected"
set fpd [p07_b4d_read32 FPD_RAW 0xFD615000]
set ident [p07_b4d_read32 P03_ID 0xA4000000]
set version [p07_b4d_read32 P03_VERSION 0xA4000004]
set caps [p07_b4d_read32 P03_CAPABILITIES 0xA4000008]
set status [p07_b4d_read32 P03_GLOBAL_STATUS 0xA400000C]
set pending [p07_b4d_read32 P03_PAGE_PENDING 0xA4000054]
if {(($fpd >> 8) & 3) != 2 || $ident != 0x4C543302 ||
    $version != 0x00010000 || $caps != 0x0001031F ||
    $status != 0 || $pending != 0} {
    puts "P07_B4D_READONLY_PS_PL_SNAPSHOT_FAIL=1"
    error "P07-B.4d read-only shell mismatch, no physical acceptance"
}
puts "P07_B4D_READONLY_PS_PL_SNAPSHOT_PASS=1"
puts "P07_B4D_INFERENCE_AUTHORIZED=0"
disconnect
