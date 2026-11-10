# M06 G3 new, scratch-only ORIGINAL Vivado 2025.2 AMD width-IP generator.
# Invocation: vivado -mode batch -source this.tcl -tclargs <NEW evidence dir>
# This NEVER imports or edits the original D3 SmartConnect project, invokes
# implementation, programs any device, allocates PS memory or accesses JTAG.
if {[llength $argv] != 1} {
    error "G3 requires exactly one newly created evidence-directory argument"
}
set out [file normalize [lindex $argv 0]]
if {![file isdirectory $out]} {
    error "G3 evidence directory does not exist"
}
# Safe pure-Tcl path resolver: use the actual new project .xci file,
# NOT get_files -of_objects $ip (empty in owner's real Vivado run).
source [file join [file dirname [file normalize [info script]]] "m06_g3_xci_path.tcl"]
set tool_version [version -short]
if {![string match "*2025.2*" $tool_version]} {
    error "G3 requires original Vivado 2025.2, got $tool_version"
}
set part "xck26-sfvc784-2LV-c"
set fw [open [file join $out "02_amd_dwc_configuration.tsv"] w]
puts $fw "status\tORIGINAL_AMD_IP_GENERATED_NOT_CONNECTED"
puts $fw "tool_version\t$tool_version"
puts $fw "part\t$part"

# Vivado new scratch project. -force never touches an existing original
# D3 source because the Bash runner allocates a unique evidence directory.
set prj [file join $out "new_scratch_project"]
if {[file exists $prj]} {
    close $fw
    error "refuse to overwrite prior scratch IP project"
}
create_project m06_g3_amd_dwc $prj -part $part
set_property target_language Verilog [current_project]

set devices {
    {m06_g3_read_dwc READ_ONLY}
    {m06_g3_write_dwc WRITE_ONLY}
}
foreach pair $devices {
    lassign $pair ipname role
    create_ip -name axi_dwidth_converter -vendor xilinx.com \
        -library ip -module_name $ipname
    set ip [get_ips -quiet $ipname]
    if {[llength $ip] != 1} {
        close $fw
        error "real AMD axi_dwidth_converter IP unavailable: $ipname"
    }
    # CONFIG names are the AMD PG059 core parameter keys; fail loudly
    # if the installed 2025.2 IP does not expose these names or values.
    set required [list \
        CONFIG.PROTOCOL AXI4 \
        CONFIG.READ_WRITE_MODE $role \
        CONFIG.ADDR_WIDTH 32 \
        CONFIG.SI_DATA_WIDTH 32 \
        CONFIG.MI_DATA_WIDTH 256 \
        CONFIG.SI_ID_WIDTH 1 \
        CONFIG.FIFO_MODE 0]
    foreach {key value} $required {
        if {[lsearch -exact [list_property $ip] $key] < 0} {
            close $fw
            error "AMD 2025.2 IP $ipname has no required property $key"
        }
    }
    set property_dict {}
    foreach {key value} $required {
        lappend property_dict $key $value
    }
    set_property -dict $property_dict $ip
    # Read AFTER customization; a silent IP parameter reset is a failure.
    foreach {key value} $required {
        set actual [get_property $key $ip]
        puts $fw "$ipname.$key\t$actual"
        if {![string equal -nocase "$actual" "$value"]} {
            close $fw
            error "AMD IP readback mismatch $ipname $key: wanted $value got $actual"
        }
    }
    flush $fw
    # The owner's real Vivado 2025.2 run created the IP object and
    # accepted every property, but get_files -of_objects $ip returned
    # an empty list. The XCI customization is a FILE under this NEW
    # project's .srcs/sources_1/ip/<instance>/<instance>.xci tree;
    # verify that actual nonempty file, never silently trust a missing
    # Tcl IP->file relationship or search the original immutable D3.
    set ip_xci [m06_g3_xci_path $prj $ipname]
    puts $fw "$ipname.xci_source_path\t$ip_xci"
    flush $fw
    generate_target all $ip
    export_ip_user_files -of_objects $ip -no_script -force
    # The output products contain the original Vivado simulation model,
    # but have not been run against generated HLS or original SmartConnect.
}
puts $fw "ip_count\t2"
puts $fw "original_smartconnect_connected\tFALSE"
puts $fw "generated_hls_connected\tFALSE"
puts $fw "physical_DDR\tNOT_ACCESSED"
puts $fw "m06_complete\tFALSE"
close $fw
puts "M06_G3_REAL_AMD_DWC_IP_GENERATED_NOT_CONNECTED"
close_project
