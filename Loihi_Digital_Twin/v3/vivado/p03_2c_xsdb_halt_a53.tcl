# Halt visible Cortex-A53 cores before a P03.2c ILA-triggered physical MMIO read.
if {$argc > 1} {
    error "usage: p03_2c_xsdb_halt_a53.tcl ?<xsdb_server_url>?"
}
set server_url "tcp:127.0.0.1:3121"
if {$argc == 1} { set server_url [lindex $argv 0] }

connect -url $server_url
set halted 0
for {set i 0} {$i < 4} {incr i} {
    set filter [format {name =~ "Cortex-A53 #%d"} $i]
    if {[catch {targets -set -filter $filter}]} {
        continue
    }
    catch {stop}
    incr halted
}
if {$halted == 0} {
    error "P03.2c ILA diagnostic could not find any Cortex-A53 target"
}
puts "P03_2C_ILA_HALTED_A53_COUNT=$halted"
disconnect
