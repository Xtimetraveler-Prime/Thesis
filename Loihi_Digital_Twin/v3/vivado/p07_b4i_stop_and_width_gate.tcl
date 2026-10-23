# P07-B.4i takeover: halt #0, halt or observe powered-down #1..#3, then
# measure static FPD/LPD selectors. Dedicated disposable Linux session ONLY.
# No PS/PL writes, no DDR or PL MMIO, no resume. Reboot after use.
# Unexpected stop failures must NOT be swallowed; no core wakeup is attempted.
if {$argc != 2 || [lindex $argv 0] ne "DEDICATED_DISCARD_LINUX_APPROVED"} {
    error "usage: <DEDICATED_DISCARD_LINUX_APPROVED> <local_xsdb_url>"
}
set server [lindex $argv 1]
if {![regexp {^tcp:(localhost|127[.]0[.]0[.]1):[0-9]{2,5}$} $server]} {
    error "P07-B.4i only allows localhost XSDB server"
}
proc b4i_width_read {label address expected} {
    set response [mrd -force -size w $address 1]
    if {![regexp -nocase {^[[:xdigit:]]+:[[:space:]]+([[:xdigit:]]{8})} [string trim $response] _ raw]} {
        error "P07-B.4i unexpected physical register read $label: $response"
    }
    scan $raw %x value
    puts [format "P03_2C_PS_%s_AXIFS_RAW=0x%08X" $label $value]
    set selector [expr {($value >> 8) & 3}]
    set width [lindex {32 64 128 RESERVED} $selector]
    puts "P03_2C_PS_${label}_HPM0_WIDTH_BITS=$width"
    if {$value != $expected || $selector != 2} {
        error "P07-B.4i $label raw 0x[format %08X $value] != historical 128-bit raw 0x[format %08X $expected]; NO-GO"
    }
}
set connected 0
set status [catch {
    connect -url $server
    set connected 1
    set primary_reset_pending 0
    for {set i 0} {$i < 4} {incr i} {
        set name [format "Cortex-A53 #%d" $i]
        if {[catch {targets -set -filter "name =~ \"$name\""} target_error]} {
            error "P07-B.4i could not select $name: $target_error"
        }
        # Track A's accepted scripts tolerate a failed stop before an
        # explicitly authorized processor reset. Unlike Track A, we never
        # silently accept a powered-down primary: first observe the exact
        # message on up to three attempts, then defer a bounded A53 #0
        # processor-reset recovery until AFTER both PS widths pass.
        # No Linux cpuidle settings, PSU init or PS width writes.
        set stopped 0
        set secondary_down 0
        for {set attempt 1} {$attempt <= 3} {incr attempt} {
            if {![catch {stop} stop_error]} {
                set stopped 1
                break
            }
            if {[string trim $stop_error] eq "The core is powered down"} {
                if {$i > 0} {
                    set secondary_down 1
                    break
                }
                if {$attempt < 3} {
                    puts "P07_B4I_A53_0_TRANSIENT_POWER_DOWN_RETRY=$attempt"
                    after 200
                    continue
                }
                set primary_reset_pending 1
                puts "P07_B4I_A53_0_EXACT_POWER_DOWN_RESET_PENDING=1"
                break
            }
            if {$i == 0 && [string trim $stop_error] eq "Already stopped"} {
                puts "P07_B4I_A53_0_ALREADY_STOPPED_CONFIRMED=1"
                set stopped 2
                break
            }
            error "P07-B.4i stop failed for $name: $stop_error"
        }
        if {$secondary_down} {
            puts "P07_B4I_A53_${i}_POWERED_DOWN_OBSERVED=1"
        } elseif {$stopped == 2 && $i == 0} {
            # Exact "Already stopped" was emitted above. No duplicate marker.
        } elseif {$stopped == 1} {
            puts "P07_B4I_A53_${i}_STOP_COMMAND_PASS=1"
        } elseif {$i == 0 && $primary_reset_pending} {
            # The primary is NOT yet admitted. PS width must pass before
            # the approved Track-A-derived processor reset is even attempted.
        } else {
            error "P07-B.4i no positively observed stopped or powered-down state for $name"
        }
    }
    set physical ""
    foreach target_name {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$target_name\""}]} {
            set physical $target_name
            break
        }
    }
    if {$physical eq ""} {error "P07-B.4i missing PSU/APU register target"}
    puts "P07_B4I_PS_WIDTH_TARGET=$physical"
    b4i_width_read FPD 0xFD615000 0x00000A00
    b4i_width_read LPD 0xFF419000 0x00000200
    if {$primary_reset_pending} {
        # Accepted Track A launches used 'rst -processor' on the selected
        # A53 #0 before 'dow'. Use that SAME processor-local reset, but
        # demand a confirmed stopped primary BEFORE PL/DDR/ELF work.
        # Reset success alone is not evidence that CPU0 can be debugged.
        targets -set -filter {name =~ "Cortex-A53 #0"}
        if {[catch {rst -processor} reset_error]} {
            error "P07-B.4i stop failed for Cortex-A53 #0: Track A processor reset failed: $reset_error"
        }
        if {[catch {stop} check_error]} {
            if {[string trim $check_error] ne "Already stopped"} {
                error "P07-B.4i stop failed for Cortex-A53 #0: post-reset halt verification failed: $check_error"
            }
        }
        puts "P07_B4I_A53_0_TRACK_A_RESET_HALT_CONFIRMED=1"
    }
    puts "P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1"
} reason]
if {$connected} {catch {disconnect}}
if {$status} {
    puts "P07_B4I_STOP_WIDTH_GATE_FAIL_REBOOT_REQUIRED=1"
    error $reason
}
puts "P07_B4I_DISCARD_PREVIOUS_LINUX_AND_REBOOT_AFTER_TEST=1"
