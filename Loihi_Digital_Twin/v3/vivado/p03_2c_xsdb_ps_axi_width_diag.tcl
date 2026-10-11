# P03.2c READ-ONLY PS HPM0 width diagnostic. No register writes or resets.
# AMD UG1087: FPD_SLCR.afi_fs @ 0xFD615000 dw_ss0_sel[9:8]
#             LPD_SLCR.afi_fs @ 0xFF419000 dw_ss2_sel[9:8]
# Encodings: 0=32-bit, 1=64-bit, 2=128-bit, 3=reserved.
if {$argc > 1} {
    error "usage: p03_2c_xsdb_ps_axi_width_diag.tcl ?<xsdb_server_url>?"
}
set server_url "tcp:127.0.0.1:3121"
if {$argc == 1} { set server_url [lindex $argv 0] }

proc p03_width_label {selection} {
    switch -- $selection {
        0 { return "32" }
        1 { return "64" }
        2 { return "128" }
        default { return "RESERVED" }
    }
}

proc p03_physical_read32 {address} {
    set output [mrd -force -size w $address 1]
    puts "P03_2C_PS_WIDTH_MRD=$output"
    if {![regexp -nocase {^[[:xdigit:]]+:[[:space:]]+([[:xdigit:]]{8})} [string trim $output] _ value_hex]} {
        error "P03.2c could not parse PS width register read at $address: $output"
    }
    scan $value_hex %x value
    return $value
}

connect -url $server_url

# Keep Linux from launching concurrent PL transactions while inspecting
# static PS configuration. No MMIO control writes are issued.
for {set i 0} {$i < 4} {incr i} {
    set filter [format {name =~ "Cortex-A53 #%d"} $i]
    if {![catch {targets -set -filter $filter}]} {
        catch {stop}
    }
}

set selected ""
foreach target_name {PSU APU} {
    if {![catch {targets -set -filter "name =~ \"$target_name\""} err]} {
        set selected $target_name
        break
    }
    puts "P03_2C_PS_WIDTH_TARGET_INFO=$target_name:$err"
}
if {$selected eq ""} {
    error "P03.2c could not select PSU/APU physical-register target"
}
puts "P03_2C_PS_WIDTH_TARGET=$selected"

set fpd_raw [p03_physical_read32 0xFD615000]
set lpd_raw [p03_physical_read32 0xFF419000]
set fpd_sel [expr {($fpd_raw >> 8) & 3}]
set lpd_sel [expr {($lpd_raw >> 8) & 3}]
set fpd_width [p03_width_label $fpd_sel]
set lpd_width [p03_width_label $lpd_sel]

puts [format "P03_2C_PS_FPD_AXIFS_RAW=0x%08X" $fpd_raw]
puts "P03_2C_PS_FPD_HPM0_WIDTH_BITS=$fpd_width"
puts [format "P03_2C_PS_LPD_AXIFS_RAW=0x%08X" $lpd_raw]
puts "P03_2C_PS_LPD_HPM0_WIDTH_BITS=$lpd_width"
puts "P03_2C_PL_EXPECTED_HPM0_WIDTH_BITS=32"

foreach {master bits} [list FPD $fpd_width LPD $lpd_width] {
    if {$bits eq "32"} {
        puts "PASS: P03.2c $master PS HPM0 width matches 32-bit PL interface."
    } else {
        puts "P03_2C_PS_WIDTH_MISMATCH_$master=1"
        puts "WARNING: P03.2c $master PS HPM0 width=$bits, but PL expects 32 bits."
    }
}
puts "PASS: P03.2c read-only PS AXI width diagnostic complete; no PS registers written."
puts "IMPORTANT: static AXI width registers must be set during PS boot/reset initialization, NOT modified in a running system."
puts "IMPORTANT: A53 processors were halted; reboot KV260 after the diagnostic."
disconnect
