# P07-B.4g OPTIONAL non-halting, read-only live PS/PL snapshot.
# XSDB 2025.2 mrd -value returns a Tcl list of values; do not parse console
# display text. Never stop/reset/program any CPU, PL, DDR, or run A53 ELF.
#
# Operator must knowingly invoke this script with the exact opt-in marker:
#   xsdb vivado/p07_b4g_readonly_shell.tcl READ_ONLY_OPERATOR_APPROVED
# Optional XSDB hw_server URL is second argument.
if {$argc < 1 || $argc > 2} {
    error "P07-B.4g usage: <READ_ONLY_OPERATOR_APPROVED> ?<xsdb_server_url>?"
}
if {[lindex $argv 0] ne "READ_ONLY_OPERATOR_APPROVED"} {
    error "P07-B.4g explicit operator acknowledgment is mandatory"
}
set server_url "tcp:127.0.0.1:3121"
if {$argc == 2} {
    set server_url [lindex $argv 1]
}
# Never allow a script from this file to connect to arbitrary remote servers
# by accident. Use local hardware server forwarded explicitly by operator.
if {![regexp {^tcp:(127[.]0[.]0[.]1|localhost):[0-9]{2,5}$} $server_url]} {
    error "P07-B.4g requires local XSDB server URL only"
}

proc p07_b4g_read32 {label address} {
    # AMD UG1725 XSDB 2025.2: -value returns a Tcl list rather than a
    # formatted console string; this is not a PS register write.
    set words [mrd -force -value -size w $address 1]
    if {[llength $words] != 1} {
        error "P07-B.4g read $label yielded [llength $words] words, expected one"
    }
    set word [lindex $words 0]
    if {![regexp -nocase {^(0x)?[0-9a-f]{1,8}$} $word]} {
        error "P07-B.4g malformed $label 32-bit word: $word"
    }
    scan $word %x numeric
    if {$numeric < 0 || $numeric > 0xFFFFFFFF} {
        error "P07-B.4g out-of-range $label"
    }
    puts [format "P07_B4G_%s=0x%08X" $label $numeric]
    return $numeric
}

set connected 0
set rc [catch {
    connect -url $server_url
    set connected 1
    set physical ""
    # Select PS memory access target rather than any Cortex-A53 execution
    # context; no A53 targets are stopped, examined or resumed.
    foreach candidate {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$candidate\""} msg]} {
            set physical $candidate
            break
        }
    }
    if {$physical eq ""} {
        error "no accessible PSU/APU memory target, fail without CPU action"
    }
    puts "P07_B4G_PHYSICAL_TARGET=$physical"
    set fpd     [p07_b4g_read32 FPD_RAW 0xFD615000]
    set ident   [p07_b4g_read32 P03_ID 0xA4000000]
    set version [p07_b4g_read32 P03_VERSION 0xA4000004]
    set caps    [p07_b4g_read32 P03_CAPABILITIES 0xA4000008]
    set status  [p07_b4g_read32 P03_GLOBAL_STATUS 0xA400000C]
    set pending [p07_b4g_read32 P03_PAGE_PENDING 0xA4000054]
    if {(($fpd >> 8) & 3) != 2} {
        error "FPD width selector differs from accepted FPD128"
    }
    if {$ident != 0x4C543302 || $version != 0x00010000 ||
        $caps != 0x0001031F} {
        error "live P03 shell ID/version/capabilities differ"
    }
    if {$status != 0 || $pending != 0} {
        error "live P03 shell not quiescent"
    }
    puts "P07_B4G_READONLY_PS_PL_SNAPSHOT_PASS=1"
} why]
if {$connected} {
    # Disconnect on failure as well as PASS. No reset, stop, con or writes.
    catch {disconnect}
}
if {$rc} {
    puts "P07_B4G_READONLY_PS_PL_SNAPSHOT_FAIL=1"
    puts "P07_B4G_INFERENCE_AUTHORIZED=0"
    error "P07-B.4g no physical acceptance: $why"
}
puts "P07_B4G_INFERENCE_AUTHORIZED=0"
puts "P07_B4G_A53_ELF_DOWNLOAD_AUTHORIZED=0"
