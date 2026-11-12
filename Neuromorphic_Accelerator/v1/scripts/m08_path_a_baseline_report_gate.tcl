# M08.2b Path A — pure Tcl exact-line baseline acceptance gate.
# Intentionally no Vivado commands, board calls, or file mutations.
# Standalone source can be regression-tested with tclsh, before native Vivado.
proc m08_path_a_check_baseline_readback {path} {
    if {![file isfile $path]} {
        error "M08 Path A original baseline readback report missing: $path"
    }
    set input [open $path r]
    set lines [split [string trimright [read $input] "\n"] "\n"]
    close $input
    foreach marker {
        META|scope|M08_GENUINE_LOCAL_KV260_PS_TO_IDENTITY_AND_SAFE_PAGE_BD
        META|compute_enabled|NO
        META|validated_bd|YES
        META|routed_implementation|NOT_RUN
        META|bitstream|NOT_GENERATED
        META|linux_mmio|NOT_ACCESSED
        META|physical_kv260|NOT_PROGRAMMED
    } {
        if {[llength [lsearch -all -exact $lines $marker]] != 1} {
            error "M08 Path A original baseline report missing or duplicate exact line: $marker"
        }
    }
    set id_lines [lsearch -all -inline -glob $lines {APERTURE_IDENTITY|*}]
    set page_lines [lsearch -all -inline -glob $lines {APERTURE_PAGE|*}]
    if {[llength $id_lines] != 1 || [llength $page_lines] != 1} {
        error "M08 Path A requires original TWO uniquely mapped PS apertures"
    }
    puts "M08_PATH_A_ORIGINAL_DUAL_AXI_REPORT_EXACT_SCOPE_OK"
    return 1
}
