# P03.2c read-only physical MMIO diagnostic.
# This script intentionally issues no page, dispatch, or resident-memory writes.
if {$argc > 1} {
    error "usage: p03_2c_xsdb_mmio_diag.tcl ?<xsdb_server_url>?"
}

set server_url "tcp:127.0.0.1:3121"
if {$argc == 1} { set server_url [lindex $argv 0] }

connect -url $server_url

targets -set -filter {name =~ "Cortex-A53 #0"}
catch {stop}

puts "P03_2C_MMIO_DIAG_TARGET=Cortex-A53 #0"
puts "P03_2C_MMIO_DIAG_BEGIN"
mrd 0xA4000000 4
puts "P03_2C_MMIO_DIAG_REPEAT"
mrd 0xA4000000 4
puts "P03_2C_MMIO_DIAG_SINGLE_ID"
mrd 0xA4000000 1
puts "P03_2C_MMIO_DIAG_SINGLE_VERSION"
mrd 0xA4000004 1
puts "P03_2C_MMIO_DIAG_SINGLE_CAPABILITIES"
mrd 0xA4000008 1
puts "P03_2C_MMIO_DIAG_SINGLE_GLOBAL_STATUS"
mrd 0xA400000C 1
puts "P03_2C_MMIO_DIAG_END"

disconnect
