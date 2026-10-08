# P03.2c read-only physical MMIO diagnostic.
# This script intentionally issues no page, dispatch, or resident-memory writes.
if {$argc > 1} {
    error "usage: p03_2c_xsdb_mmio_diag.tcl ?<xsdb_server_url>?"
}

set server_url "tcp:127.0.0.1:3121"
if {$argc == 1} { set server_url [lindex $argv 0] }

proc p03_select_physical_target {} {
    foreach candidate {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$candidate\""} err]} {
            puts "P03_2C_MMIO_DIAG_TARGET=$candidate"
            return
        }
        puts "P03_2C_MMIO_DIAG_INFO target $candidate unavailable: $err"
    }
    error "P03.2c could not select PSU/APU physical-memory target"
}

connect -url $server_url

# Halt visible A53s so Linux cannot race the diagnostic, then switch away from
# the processor/MMU context and issue physical transactions through PSU/APU.
for {set i 0} {$i < 4} {incr i} {
    set filter [format {name =~ "Cortex-A53 #%d"} $i]
    if {![catch {targets -set -filter $filter}]} {
        catch {stop}
    }
}
p03_select_physical_target

puts "P03_2C_MMIO_DIAG_BEGIN"
puts [mrd -force -size w 0xA4000000 4]
puts "P03_2C_MMIO_DIAG_REPEAT"
puts [mrd -force -size w 0xA4000000 4]
puts "P03_2C_MMIO_DIAG_SINGLE_ID"
puts [mrd -force -size w 0xA4000000 1]
puts "P03_2C_MMIO_DIAG_SINGLE_VERSION"
puts [mrd -force -size w 0xA4000004 1]
puts "P03_2C_MMIO_DIAG_SINGLE_CAPABILITIES"
puts [mrd -force -size w 0xA4000008 1]
puts "P03_2C_MMIO_DIAG_SINGLE_GLOBAL_STATUS"
puts [mrd -force -size w 0xA400000C 1]
puts "P03_2C_MMIO_DIAG_END"

disconnect
