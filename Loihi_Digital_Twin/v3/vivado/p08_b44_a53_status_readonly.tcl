# P08-B44 DIAGNOSTIC ONLY: read XSDB target inventory after a FULL board
# power cycle and NORMAL serial boot. No CPU selection, stop, reset,
# resume, memory access, register access, software download, PL programming
# or hardware mutation. This is a READ-ONLY JTAG OBSERVATION, different
# from the PC-only mailbox monitor (which never connects to hardware).
#
# Diagnostic results NEVER constitute safe A53 takeover or 128bit PS
# width acceptance. In particular "External debug access is disabled"
# is NOT a proof of halted or powered-down CPU and MUST NOT be
# reclassified as admissible in original P07-B4i safety gate.
if {$argc != 1} {
    error "P08-B44 read-only A53 target status usage: <tcp:127.0.0.1:3121>"
}
set server [lindex $argv 0]
if {![regexp {^tcp:(localhost|127[.]0[.]0[.]1):[0-9]{2,5}$} $server]} {
    error "P08-B44 read-only A53 target inventory requires localhost hardware server"
}
set connected 0
set status [catch {
    connect -url $server
    set connected 1
    puts "P08_B44_READONLY_JTAG_TARGET_OBSERVATION_CONNECTED=1"
    puts "P08_B44_READONLY_JTAG_TARGETS_BEGIN"
    puts [targets]
    puts "P08_B44_READONLY_JTAG_TARGETS_END"
    puts "P08_B44_READONLY_JTAG_CHAIN_BEGIN"
    puts [jtag targets]
    puts "P08_B44_READONLY_JTAG_CHAIN_END"
} reason]
if {$connected} {catch {disconnect}}
if {$status} {
    puts "P08_B44_READONLY_TARGET_DIAGNOSTIC_NO_GO=1"
    error $reason
}
puts "P08_B44_READONLY_TARGET_OBSERVATION_ONLY=1"
puts "P08_B44_HALTED_OR_POWERED_DOWN_ALL_A53_PROVEN=0"
puts "P08_B44_NEW_PROFILE_PHYSICAL_JTAG_AUTHORIZED=0"
puts "P08_B44_ORIGINAL_P07_CORE_STOP_GATE_UNCHANGED=1"
