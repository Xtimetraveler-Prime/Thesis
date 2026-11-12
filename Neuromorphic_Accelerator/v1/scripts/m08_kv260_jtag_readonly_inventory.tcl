# M08.2b FIRST PHYSICAL TARGET INVENTORY — READ ONLY.
# Vivado 2025.2 PC Hardware Manager connection + device enumeration ONLY.
# NO program_hw_devices, JTAG reset, firmware load, PS memory access,
# clock/reset alteration, or SD/QSPI/flash operations.
# Do not infer that a seen device is ready for PS AXI register access.
if {[llength $argv] != 1} {
    error "usage: m08_kv260_jtag_readonly_inventory.tcl <NEW-absolute-report-file>"
}
set report [file normalize [lindex $argv 0]]
if {[file exists $report] || ![file isdirectory [file dirname $report]]} {
    error "M08 requires a fresh report path inside an existing evidence folder"
}
set fout [open $report {WRONLY CREAT EXCL}]
proc m08_report {text} {
    global fout
    puts $fout $text
    flush $fout
    puts $text
}
m08_report "M08_KV260_JTAG_INVENTORY_READ_ONLY_NO_PROGRAMMING"
m08_report "META|vivado_version|[version -short]"
if {![string match "2025.2*" [version -short]]} {
    error "M08 JTAG inventory requires Vivado 2025.2"
}
open_hw
connect_hw_server -url localhost:3121
set targets [get_hw_targets -quiet]
m08_report "META|target_count|[llength $targets]"
foreach target $targets {
    m08_report "JTAG_TARGET|$target"
}
if {[llength $targets] != 1} {
    error "M08 no unique JTAG target; select the K26 cable manually from original report before any programming"
}
set target [lindex $targets 0]
current_hw_target $target
open_hw_target
set devices [get_hw_devices -quiet]
m08_report "META|device_count|[llength $devices]"
foreach device $devices {
    set name [string trim [get_property -quiet NAME $device]]
    set part [string trim [get_property -quiet PART $device]]
    m08_report "JTAG_DEVICE|$name|$part"
}
if {[llength $devices] == 0} {
    error "M08 JTAG target opened but has no enumerated hardware devices"
}
m08_report "M08_JTAG_ENUMERATED_ONLY_NO_BOARD_CONFIGURATION_CHANGE"
close_hw_target
disconnect_hw_server
close_hw
close $fout
