# M06: ORIGINAL Vivado 2025.2 memory IP simulator BFM port contract capture.
# PURPOSE: construct one real vendor functional transaction test; NOT warnings.
# Original saved XPR and BD are READ ONLY. No generate_target or simulation.
if {[llength $argv] != 2} {
    error "usage: -tclargs <accepted_original_D3_directory> <new_report_path>"
}
set original [file normalize [lindex $argv 0]]
set report [file normalize [lindex $argv 1]]
if {[file tail $original] ne "neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"} {
    error "requires exact accepted original D3 project"
}
set xp [file join $original 13_file_backed_project m05_d3_output_products.xpr]
set design m05_12d3_real_signed32_hls_six_control_address_candidate
set bp [file join $original 13_file_backed_project m05_d3_output_products.srcs sources_1 bd $design [format "%s.bd" $design]]
if {![file isfile $xp] || ![file isfile $bp]} {
    error "original file-backed XPR and BD missing"
}
if {[file exists $report] || ![file isdirectory [file dirname $report]]} {
    error "report must be new exclusive file in existing output folder"
}
set out [open $report {WRONLY CREAT EXCL}]
puts $out "META|purpose|M06_ORIGINAL_VENDOR_XSIM_BFM_PORT_CONTRACT_NOT_WARNINGS"
puts $out "SOURCE_XPR|$xp"
puts $out "SOURCE_BD|$bp"
open_project -read_only $xp
set original_bd [get_files -quiet $bp]
if {[llength $original_bd] != 1} {
    error "original saved BD not uniquely registered"
}
open_bd_design [lindex $original_bd 0]
if {[llength [get_bd_cells -quiet mem_sc]] != 1 ||
    [llength [get_bd_cells -quiet ps]] != 1} {
    error "original mem_sc and ps missing; cannot construct vendor BFM"
}
set ip [get_bd_cells mem_sc]
puts $out "MEM_IP_VLNV|[get_property VLNV $ip]"
foreach key {CONFIG.NUM_SI CONFIG.NUM_MI} {
    set value "NOT_EXPOSED"
    if {[lsearch -exact [list_property $ip] $key] >= 0} {
        set value [get_property $key $ip]
    }
    puts $out "MEM_IP_PROPERTY|$key|$value"
}
set interfaces {
    mem_sc/S00_AXI 256
    mem_sc/S01_AXI 256
    mem_sc/S02_AXI 256
    mem_sc/S03_AXI 256
    mem_sc/M00_AXI 128
    ps/S_AXI_HP0_FPD 128
}
foreach {name expected_width} $interfaces {
    set pin [get_bd_intf_pins -quiet $name]
    if {[llength $pin] != 1} {
        error "original AXI endpoint missing: $name"
    }
    puts $out "ENDPOINT|$name"
    set available [list_property $pin]
    foreach key {
        CONFIG.PROTOCOL CONFIG.DATA_WIDTH CONFIG.ADDR_WIDTH
        CONFIG.ID_WIDTH CONFIG.AWUSER_WIDTH CONFIG.ARUSER_WIDTH
        CONFIG.WUSER_WIDTH CONFIG.RUSER_WIDTH CONFIG.BUSER_WIDTH
        CONFIG.MAX_BURST_LENGTH CONFIG.HAS_BURST
        CONFIG.SUPPORTS_NARROW_BURST CONFIG.READ_WRITE_MODE
    } {
        set value "NOT_EXPOSED_BY_ORIGINAL"
        if {[lsearch -exact $available $key] >= 0} {
            set value [string trim [get_property $key $pin]]
        }
        puts $out "ENDPOINT_PROPERTY|$name|$key|$value"
    }
    if {[lsearch -exact $available CONFIG.DATA_WIDTH] < 0 ||
        [get_property CONFIG.DATA_WIDTH $pin] ne "$expected_width"} {
        error "original endpoint $name no longer matches expected $expected_width-bit"
    }
}
foreach pinname {mem_sc/aclk mem_sc/aresetn} {
    if {[llength [get_bd_pins -quiet $pinname]] != 1} {
        error "missing original IP $pinname"
    }
    puts $out "CLOCK_RESET_PORT|$pinname|PRESENT"
}
set sim [get_filesets -quiet sim_1]
if {[llength $sim] != 1} {
    puts $out "SIM_FILESET|UNAVAILABLE"
} else {
    puts $out "SIM_FILESET|PRESENT"
    set props [list_property $sim]
    foreach key {TOP TARGET_SIMULATOR} {
        set value "NOT_EXPOSED"
        if {[lsearch -exact $props $key] >= 0} {
            set value [get_property $key $sim]
        }
        puts $out "SIM_PROPERTY|$key|$value"
    }
}
if {[catch {get_files -compile_order sources -used_in simulation} compiled]} {
    puts $out "SIM_QUERY|ERROR|[string map [list "\n" " " "|" "/"] $compiled]"
} else {
    puts $out "SIM_QUERY|OK|[llength $compiled]"
    foreach sf $compiled {
        puts $out "SIM_SOURCE|$sf"
    }
}
set project_sources [get_files -all -quiet]
puts $out "PROJECT_FILE_COUNT|[llength $project_sources]"
foreach sf $project_sources {
    if {[string first "mem_sc" [string tolower $sf]] >= 0} {
        puts $out "MEM_PROJECT_SOURCE|$sf"
    }
}
puts $out "SIMULATOR_FUNCTIONAL_TRIAL|NOT_EXECUTED"
puts $out "GENERATE_TARGET|NOT_EXECUTED"
puts $out "PHYSICAL_BOARD|NOT_AUTHORIZED"
puts $out "RESULT|ORIGINAL_PORTS_CAPTURED_FOR_ONE_VENDOR_FUNCTIONAL_XSIM_TRIAL"
close $out
close_project
puts "M06_EXACT_ORIGINAL_MEM_SC_PORTS_CAPTURED|READ_ONLY_NO_XSIM_NO_BOARD"
