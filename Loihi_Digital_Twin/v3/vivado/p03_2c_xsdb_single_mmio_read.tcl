# Issue one physical 32-bit MMIO read for a P03.2c System ILA capture.
if {$argc < 1 || $argc > 2} {
    error "usage: p03_2c_xsdb_single_mmio_read.tcl <address> ?<xsdb_server_url>?"
}
set address [lindex $argv 0]
set server_url "tcp:127.0.0.1:3121"
if {$argc == 2} { set server_url [lindex $argv 1] }

proc p03_select_physical_target {} {
    foreach candidate {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$candidate\""} err]} {
            puts "P03_2C_ILA_READ_TARGET=$candidate"
            return
        }
        puts "P03_2C_ILA_INFO target $candidate unavailable: $err"
    }
    error "P03.2c ILA diagnostic could not select PSU/APU physical-memory target"
}

connect -url $server_url
p03_select_physical_target
puts "P03_2C_ILA_READ_ADDRESS=$address"
puts [mrd -force -size w $address 1]
disconnect
