# M05 D4.3: original Vivado 2025.2 project simulation MODEL DISCOVERY ONLY.
# No launch_simulation, export_simulation, generate_target, synthesis or board.
# IMPORTANT: Simulator FILE LIST != compiled model != AXI protocol PASS.
if {[llength $argv] != 3} {
    error "Usage: -tclargs <ORIGINAL_D3_DIR> <NEW_OUTFILE> <NEW_EVIDENCE_DIR>"
}
set original [file normalize [lindex $argv 0]]
set output [file normalize [lindex $argv 1]]
set outdir [file normalize [lindex $argv 2]]
if {![file isdirectory $original] || ![file isdirectory $outdir]} {
    error "missing D3 and new D4 owner evidence directories"
}
if {[file tail $original] ne "neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"} {
    error "genuine exact accepted D3 owner evidence required"
}
if {[file dirname $output] ne $outdir || [file exists $output]} {
    error "new unique report path required; never overwrite original"
}
set xpr [file join $original 13_file_backed_project m05_d3_output_products.xpr]
set bdname m05_12d3_real_signed32_hls_six_control_address_candidate
set bd [file join $original 13_file_backed_project m05_d3_output_products.srcs sources_1 bd $bdname [format "%s.bd" $bdname]]
if {![file isfile $xpr] || ![file isfile $bd]} {
    error "original saved XPR and BD missing"
}
open_project -read_only $xpr
set exactbd [get_files -quiet $bd]
if {[llength $exactbd] != 1 || [file normalize [lindex $exactbd 0]] ne $bd} {
    error "original saved BD does not belong to exact read-only project"
}
open_bd_design [lindex $exactbd 0]
foreach cell {ctrl_sc mem_sc} {
    if {[llength [get_bd_cells -quiet $cell]] != 1} {
        error "original SmartConnect $cell unavailable"
    }
}
set f [open $output {WRONLY CREAT EXCL}]
puts $f "META|scope|M05_D4_ORIGINAL_SIM_MODEL_FEASIBILITY_ONLY"
puts $f "PROJECT|$xpr"
puts $f "BD|$bd"
set sim [get_filesets -quiet sim_1]
if {[llength $sim] != 1} {
    puts $f "SIMFILESET|MISSING"
    puts $f "SIMCOMPILE|UNAVAILABLE"
} else {
    puts $f "SIMFILESET|PRESENT"
    foreach key {TOP TARGET_SIMULATOR} {
        set available [list_property $sim]
        set value "ABSENT"
        if {[lsearch -exact $available $key] >= 0} {
            set value [string trim [get_property $key $sim]]
            if {$value eq ""} {set value "EMPTY"}
        }
        puts $f "SIMPROP|$key|$value"
    }
    if {[catch {get_files -compile_order sources -used_in simulation -of_objects $sim} compile_text]} {
        puts $f "SIMCOMPILE|QUERY_ERROR"
        puts $f "SIMERROR|[string map [list "\n" " " "|" "/"] $compile_text]"
    } else {
        puts $f "SIMCOMPILE|QUERY_OK"
        set mem_count 0
        set all_count 0
        foreach file $compile_text {
            incr all_count
            set path [string trim $file]
            if {[string first "|" $path] >= 0 || [string first "\n" $path] >= 0} {
                error "unexpected path delimiter in original simulation compile order"
            }
            if {[string first "mem_sc" [string tolower $path]] >= 0} {
                incr mem_count
                puts $f "MEM_SIM_FILE|$path"
            }
        }
        puts $f "SIMCOMPILE_COUNT|$all_count"
        puts $f "MEM_COMPILE_COUNT|$mem_count"
    }
}
set src_count 0
set mem_src_count 0
foreach file [get_files -all -quiet] {
    incr src_count
    set path [string trim $file]
    if {[string first "|" $path] >= 0 || [string first "\n" $path] >= 0} {
        error "unexpected original project source path delimiter"
    }
    if {[string first "mem_sc" [string tolower $path]] >= 0} {
        incr mem_src_count
        puts $f "MEM_PROJECT_FILE|$path"
    }
}
puts $f "PROJECT_FILE_COUNT|$src_count"
puts $f "MEM_PROJECT_COUNT|$mem_src_count"
puts $f "META|simulation|NOT_RUN"
puts $f "META|generated_model_compile|NOT_RUN"
puts $f "META|byte_scoreboard|NOT_RUN"
puts $f "META|physical_board|NOT_AUTHORIZED"
puts $f "SIM_MODEL_DISCOVERY|COMPLETE|SIMULATOR_FUNCTIONAL_PROOF_BLOCKED"
close $f
close_project
puts "M05_D4_SIM_MODEL_DISCOVERY_COMPLETE|ORIGINAL_READ_ONLY|NO_XSIM_NO_BOARD"
