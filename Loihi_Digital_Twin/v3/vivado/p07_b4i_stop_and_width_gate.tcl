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
    for {set i 0} {$i < 4} {incr i} {
        set name [format "Cortex-A53 #%d" $i]
        if {[catch {targets -set -filter "name =~ \"$name\""} target_error]} {
            error "P07-B.4i could not select $name: $target_error"
        }
        # CPU0 can briefly enter a Linux/PSCI deep-idle power state.
        # Retry ONLY the exact powered-down response for CPU0, up to
        # three stop attempts. A powered-down CPU0 is NEVER accepted
        # as halted; the firmware must not be launched without STOP_PASS.
        # No wake, reset, register writes, or bypasses are permitted here.
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
                error "P07-B.4i stop failed for $name: The core is powered down after 3 attempts; NO-GO. Reboot KV260; verify CPU0 is online and disable CPU0 deep cpuidle before the next dedicated JTAG session"
            }
            error "P07-B.4i stop failed for $name: $stop_error"
        }
        if {$secondary_down} {
            puts "P07_B4I_A53_${i}_POWERED_DOWN_OBSERVED=1"
        } elseif {$stopped} {
            puts "P07_B4I_A53_${i}_STOP_COMMAND_PASS=1"
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
    puts "P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1"
} reason]
if {$connected} {catch {disconnect}}
if {$status} {
    puts "P07_B4I_STOP_WIDTH_GATE_FAIL_REBOOT_REQUIRED=1"
    error $reason
}
puts "P07_B4I_DISCARD_PREVIOUS_LINUX_AND_REBOOT_AFTER_TEST=1"
