# M05.12d.2c OFFLINE K26 Zynq UltraScale+ PS CONFIGURATION PROPERTY DISCOVERY.
# No board preset, no PS/DDR/clock changes, no IP property WRITES, no hardware.
# The M05.12d.2a owner catalog saw zero HP/HPC default interfaces and found
# no guessed "PCW" config keys. Discover ACTUAL Vivado 2025.2 CONFIG.PSU__ keys.
if {[llength $argv] != 1} {error "usage: <original-property-report-path>"}
set out [lindex $argv 0]
set part xck26-sfvc784-2LV-c
set scope UNCONFIGURED_K26_PS_PROPERTY_CATALOG_NO_PRESET_OR_DDR
create_project -in_memory -part $part
set_property source_mgmt_mode All [current_project]
set defs [get_ipdefs -all -quiet xilinx.com:ip:zynq_ultra_ps_e:*]
if {[llength $defs] < 1} {error "PS IP absent from offline K26 catalog"}
set def [lindex [lsort -dictionary $defs] end]
set vlnv [get_property VLNV $def]
if {![string match {xilinx.com:ip:zynq_ultra_ps_e:*} $vlnv]} {error "wrong PS IP"}
create_bd_design m05_12d2c_ps_property_catalog
set ps [create_bd_cell -type ip -vlnv $vlnv ps_catalog]
if {[llength $ps] != 1} {error "PS catalog IP creation failed"}
set keys {}
foreach prop [lsort -dictionary [list_property $ps]] {
    if {![regexp {^CONFIG\.(PSU__USE__|PSU__CRL_APB__PL0_REF_CTRL__|PSU__FPGA_PL0_ENABLE|PSU__MAXIGP|PSU__SAXIGP)} $prop]} {
        continue
    }
    set key [string range $prop 7 end]
    if {![regexp {^PSU__[A-Za-z0-9_]+$} $key]} {
        error "unserializable PS CONFIG property key '$key'"
    }
    lappend keys $key
}
if {[llength $keys] < 1 || [llength $keys] > 1024} {
    error "empty/oversized relevant PSU property inventory; do not infer PS enablement"
}
set observed [dict create]
set records {}
foreach key $keys {
    set raw [get_property "CONFIG.$key" $ps]
    if {[string length $raw] > 4096} {error "unreasonably long PS parameter $key"}
    if {$raw eq ""} {
        set encoded "~"
    } else {
        set encoded [binary encode base64 -maxlen 0 $raw]
    }
    dict set observed $key 1
    lappend records "PROP|$key|$encoded"
}
# Lookup probes explicitly show whether the actual keys exist in this IP.
# DO NOT assume GP numbering corresponds to exact HPM/HP port until verified.
set targets {
    PSU__USE__M_AXI_GP0 PSU__USE__M_AXI_GP1 PSU__USE__M_AXI_GP2
    PSU__USE__S_AXI_GP0 PSU__USE__S_AXI_GP1 PSU__USE__S_AXI_GP2
    PSU__USE__S_AXI_GP3 PSU__USE__S_AXI_GP4 PSU__USE__S_AXI_GP5
    PSU__USE__S_AXI_GP6 PSU__USE__IRQ0 PSU__USE__FABRIC__RST
    PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ
    PSU__FPGA_PL0_ENABLE
}
set meta [list "META|part|$part" "META|vlnv|$vlnv" "META|scope|$scope" \
    "META|source_mgmt_mode|[get_property source_mgmt_mode [current_project]]" \
    "META|property_count|[llength $keys]"]
foreach key $targets {
    set present [expr {[dict exists $observed $key] ? 1 : 0}]
    lappend meta "TARGET|$key|$present"
}
set f [open $out w]
foreach line $meta {puts $f $line}
foreach line $records {puts $f $line}
close $f
close_project
puts "PASS: M05.12d.2c offline K26 PS property names and values discovered (NO WRITE/PRESET/DDR)"
