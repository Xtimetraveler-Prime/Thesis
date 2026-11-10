# M06 G3: query REAL saved AMD dual-DWC IP SIMULATION SOURCE DEPENDENCIES.
# Genuine owner Vivado 2025.2 returned an authoritative, ordered 13-file
# list for the read converter, but its separate export simulation operation
# failed internally with "expected boolean value but got empty string".
# Record only the successful get_files -compile_order result for BOTH IPs.
# Open the project READ ONLY. Never mutate original XCI, run XSim or use JTAG.
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
    # AMD UG835: this exact original query succeeded on the user's
    # first real read-only 2025.2 run. The separate Vivado export command
    # then crashed with an empty-Boolean internal error. Do NOT invoke it.
    set files [get_files -compile_order sources -used_in simulation -of_objects $ip]
    if {[llength $files] < 2} {
        close $fp
        error "genuine AMD simulation compile-order is missing or incomplete: $name"
    }
    set project_root [file normalize [file join $dw "new_scratch_project"]]
    set wrapper_found 0
    set headers_found 0
    set seen {}
    puts $fp "ip_name\t$name"
    puts $fp "ip_mode\t$role"
    puts $fp "ip_sim_file_count\t[llength $files]"
    foreach f $files {
        set fname [file normalize $f]
        if {![file isfile $fname] || [file size $fname] <= 0} {
            close $fp
            error "original AMD simulation dependency missing/empty: $fname"
        }
        if {[string first "${project_root}/" $fname] != 0} {
            close $fp
            error "AMD simulation source escaped authenticated scratch project: $fname"
        }
        if {[lsearch -exact $seen $fname] >= 0} {
            close $fp
            error "duplicate AMD simulation source path: $fname"
        }
        lappend seen $fname
        set typ [get_property FILE_TYPE $f]
        if {$typ ni {"Verilog" "SystemVerilog" "VHDL" "Verilog Header"}} {
            close $fp
            error "unknown AMD source type: $name $typ"
        }
        if {[file tail $fname] eq "${name}.v" && $typ eq "Verilog"} {
            set wrapper_found 1
        }
        if {$typ eq "Verilog Header"} {set headers_found 1}
        puts $fp "$name\t$typ\t$fname"
    }
    if {!$wrapper_found || !$headers_found} {
        close $fp
        error "original AMD SIM wrapper or required header absent: $name"
    }
    flush $fp
}
puts $fp "original_amd_smartconnect_linked\tFALSE"
puts $fp "generated_hls_linked\tFALSE"
puts $fp "vendor_converter_xsim_run\tFALSE"
puts $fp "m06_complete\tFALSE"
close $fp
close_project
puts "M06_G3_REAL_AMD_DWC_SIM_COMPILE_ORDER_RECORDED_NOT_CONNECTED_NOT_SIMULATED"
