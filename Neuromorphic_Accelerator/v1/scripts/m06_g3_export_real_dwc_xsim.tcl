# M06 G3: probe REAL saved AMD dual-DWC IP simulation source dependencies.
# Read-only project. Export only standalone xsim scripts into a NEW evidence
# directory; NEVER execute those scripts here and NEVER edit original D3.
# Tclargs: <saved successful DWC evidence folder> <new export evidence folder>
if {[llength $argv] != 2} {
    error "M06 G3 requires real DWC owner folder and new export folder"
}
set dw [file normalize [lindex $argv 0]]
set out [file normalize [lindex $argv 1]]
if {![file isdirectory $dw] || ![file isdirectory $out] ||
    ![string match "m06_g3_real_amd_dwc_*" [file tail $dw]] ||
    ![string match "m06_g3_amd_sim_export_*" [file tail $out]]} {
    error "M06 G3 wrong original DWC owner evidence or NEW export folder"
}
if {![string match "*2025.2*" [version -short]]} {
    error "M06 G3 requires original Vivado 2025.2"
}
set xpr [file join $dw "new_scratch_project" "m06_g3_amd_dwc.xpr"]
if {![file isfile $xpr]} {
    error "original success evidence has no scratch Vivado project"
}
set exportroot [file join $out "exported_xsim_scripts"]
file mkdir $exportroot
# AMD UG835 open_project -read_only prevents saving changes to existing XCI.
open_project -read_only $xpr
if {[get_property PART [current_project]] ne "xck26-sfvc784-2LV-c"} {
    error "original AMD IP target part changed"
}
set fp [open [file join $out "02_genuine_dwc_sim_compile_order.tsv"] w]
puts $fp "original_vendor_simulation_files_only\tNOT_HLS_OR_SMARTCONNECT_CONNECTED"
set roles {{m06_g3_read_dwc READ_ONLY} {m06_g3_write_dwc WRITE_ONLY}}
foreach row $roles {
    lassign $row name role
    set ip [get_ips -quiet $name]
    if {[llength $ip] != 1} {
        close $fp
        error "saved original real AMD IP missing: $name"
    }
    foreach {property expect} [list CONFIG.PROTOCOL AXI4 \
      CONFIG.READ_WRITE_MODE $role CONFIG.ADDR_WIDTH 32 \
      CONFIG.SI_DATA_WIDTH 32 CONFIG.MI_DATA_WIDTH 256 \
      CONFIG.SI_ID_WIDTH 1] {
        if {![string equal -nocase [get_property $property $ip] $expect]} {
            close $fp
            error "saved original AMD converter parameter changed: $name $property"
        }
    }
    # After successful generate_target all, compile_order queries are
    # meaningful even though premature get_files -of_objects $ip was
    # empty immediately after create_ip in the first failed owner run.
    set files [get_files -compile_order sources -used_in simulation -of_objects $ip]
    puts $fp "ip_name\t$name"
    puts $fp "ip_mode\t$role"
    puts $fp "ip_sim_file_count\t[llength $files]"
    foreach f $files {
        set fname [file normalize $f]
        if {![file exists $fname]} {
            close $fp
            error "original AMD simulation dependency missing: $fname"
        }
        set typ [get_property FILE_TYPE $f]
        puts $fp "$name\t$typ\t$fname"
    }
    flush $fp
    # Official Vivado standalone XSim compile/elaboration source manifest.
    # Writes only into new OUT, not to the accepted original owner project.
    export_simulation -simulator xsim -of_objects $ip \
        -directory [file join $exportroot $name] \
        -absolute_path -force
}
puts $fp "original_amd_smartconnect_linked\tFALSE"
puts $fp "generated_hls_linked\tFALSE"
puts $fp "vendor_converter_xsim_run\tFALSE"
puts $fp "m06_complete\tFALSE"
close $fp
close_project
puts "M06_G3_REAL_AMD_DWC_XSIM_SOURCES_EXPORTED_NOT_CONNECTED_NOT_SIMULATED"
