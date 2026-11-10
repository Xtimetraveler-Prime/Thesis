# Standalone pure Tcl helper: locate the IP customization on disk, not by
# asking get_files -of_objects [get_ips], which can return an empty list for
# the newly created IP customization before generate_target in Vivado 2025.2.
# Sourceable and unit-testable with tclsh WITHOUT invoking any Vivado tools.
proc m06_g3_xci_path {project_root ipname} {
    if {![regexp {^m06_g3_(read|write)_dwc$} $ipname]} {
        error "M06 G3 unexpected AMD converter instance name: $ipname"
    }
    if {![file isdirectory $project_root]} {
        error "M06 G3 new scratch project missing: $project_root"
    }
    set xci [file join [file normalize $project_root] \
        "m06_g3_amd_dwc.srcs" "sources_1" "ip" $ipname "${ipname}.xci"]
    if {![file isfile $xci] || [file size $xci] <= 0} {
        error "M06 G3 expected genuine nonempty AMD IP .xci not found at: $xci"
    }
    # Return EXACT expected source path under the newly created project,
    # never a broad search that might accidentally find original D3 IP.
    return [file normalize $xci]
}
