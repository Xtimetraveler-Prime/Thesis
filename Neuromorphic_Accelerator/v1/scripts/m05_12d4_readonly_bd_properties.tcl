# D4.1b: ONLY read the immutable original D3 .xpr and saved BD.
# open_project -read_only; no save, validate, generate, synth, bitstream or HW.
if {[llength $argv] != 3} {
    error "Usage: -tclargs <ORIGINAL_D3_EVIDENCE_DIR> <NEW_REPORT_PATH> <EXPECTED_D4_OUTDIR>"
}
set original [file normalize [lindex $argv 0]]
set report [file normalize [lindex $argv 1]]
set out [file normalize [lindex $argv 2]]
if {![file isdirectory $original] || ![file isdirectory $out]} {
    error "original evidence and separate new D4 output must exist"
}
if {[file dirname $report] ne $out || [file exists $report]} {
    error "D4 probe cannot overwrite any pre-existing evidence or write into original"
}
set expected "neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
if {[file tail $original] ne $expected} {
    error "wrong original D3 evidence identity"
}
set xpr [file join $original 13_file_backed_project m05_d3_output_products.xpr]
set bdname m05_12d3_real_signed32_hls_six_control_address_candidate
set bd [file join $original 13_file_backed_project m05_d3_output_products.srcs sources_1 bd $bdname [format "%s.bd" $bdname]]
if {![file isfile $xpr] || ![file isfile $bd]} {
    error "original Vivado file-backed XPR and BD missing"
}
# AMD UG835: -read_only prevents saving changes to original .xpr.
open_project -read_only $xpr
set actual_bd [get_files -quiet $bd]
if {[llength $actual_bd] != 1 || [file normalize [lindex $actual_bd 0]] ne $bd} {
    error "original saved .bd is not one exact project file"
}
open_bd_design [lindex $actual_bd 0]
set f [open $report x]
puts $f "META|scope|M05_D4_1B_ORIGINAL_READ_ONLY_2025_2_BD_AXI_PROPERTIES"
puts $f "PROJECT|$xpr"
puts $f "BD|$bd"
foreach {name si mi} {ctrl_sc 1 6 mem_sc 4 1} {
    set cells [get_bd_cells -quiet $name]
    if {[llength $cells] != 1} {error "expected exact original SmartConnect cell $name"}
    foreach {key value} [list CONFIG.NUM_SI $si CONFIG.NUM_MI $mi] {
        if {[lsearch -exact [list_property [lindex $cells 0]] $key] < 0} {
            error "missing required genuine SmartConnect property $name/$key"
        }
        set got [string trim [get_property $key [lindex $cells 0]]]
        puts $f "CELL|$name|$key|$got"
        flush $f
        if {$got ne "$value"} {
            error "genuine original SmartConnect $name $key=$got, expected $value"
        }
    }
}
set props {
    CONFIG.PROTOCOL CONFIG.DATA_WIDTH CONFIG.ADDR_WIDTH CONFIG.ID_WIDTH
    CONFIG.AWUSER_WIDTH CONFIG.ARUSER_WIDTH CONFIG.WUSER_WIDTH
    CONFIG.BUSER_WIDTH CONFIG.RUSER_WIDTH
    CONFIG.MAX_BURST_LENGTH CONFIG.SUPPORTS_NARROW_BURST CONFIG.HAS_BURST
    CONFIG.HAS_WSTRB CONFIG.HAS_BRESP CONFIG.HAS_RRESP CONFIG.READ_WRITE_MODE
    CONFIG.NUM_READ_OUTSTANDING CONFIG.NUM_WRITE_OUTSTANDING
    CONFIG.HAS_CACHE CONFIG.HAS_LOCK CONFIG.HAS_PROT CONFIG.HAS_QOS
    CONFIG.HAS_REGION CONFIG.FREQ_HZ CONFIG.CLK_DOMAIN
}
set endpoints {
    ctrl_sc/S00_AXI ctrl_sc/M00_AXI ctrl_sc/M01_AXI
    ctrl_sc/M02_AXI ctrl_sc/M03_AXI ctrl_sc/M04_AXI ctrl_sc/M05_AXI
    dma_neurons/S_AXI_LITE dma_synapses/S_AXI_LITE
    dma_external/S_AXI_LITE dma_trace/S_AXI_LITE
    shell/s_axi hls/s_axi_control
    dma_neurons/M_AXI_MM2S mem_sc/S00_AXI
    dma_synapses/M_AXI_MM2S mem_sc/S01_AXI
    dma_external/M_AXI_MM2S mem_sc/S02_AXI
    dma_trace/M_AXI_S2MM mem_sc/S03_AXI
    mem_sc/M00_AXI ps/S_AXI_HP0_FPD
}
set widths [dict create \
    dma_neurons/M_AXI_MM2S 256 mem_sc/S00_AXI 256 \
    dma_synapses/M_AXI_MM2S 256 mem_sc/S01_AXI 256 \
    dma_external/M_AXI_MM2S 256 mem_sc/S02_AXI 256 \
    dma_trace/M_AXI_S2MM 256 mem_sc/S03_AXI 256 \
    mem_sc/M00_AXI 128 ps/S_AXI_HP0_FPD 128]
foreach endpoint $endpoints {
    set pins [get_bd_intf_pins -quiet $endpoint]
    if {[llength $pins] != 1} {error "expected exact original interface $endpoint"}
    set pin [lindex $pins 0]
    set nets [get_bd_intf_nets -quiet -of_objects $pin]
    if {[llength $nets] != 1} {
        error "expected exactly one original interface net on $endpoint"
    }
    puts $f "NET|$endpoint|[lindex $nets 0]"
    set existing [list_property $pin]
    foreach prop $props {
        set value "ABSENT"
        if {[lsearch -exact $existing $prop] >= 0} {
            set value [string trim [get_property $prop $pin]]
            if {$value eq ""} {set value "EMPTY"}
        }
        if {[string first "|" $value] >= 0 || [string first "\n" $value] >= 0} {
            error "unsafe multi-line/property delimiter on $endpoint $prop"
        }
        puts $f "IFACE|$endpoint|$prop|$value"
        if {$prop eq "CONFIG.DATA_WIDTH" && [dict exists $widths $endpoint]} {
            set required [dict get $widths $endpoint]
            if {$value ne "$required"} {
                error "genuine D3 interface width drift $endpoint: $value != $required"
            }
        }
    }
    flush $f
}
puts $f "META|physical_board|NOT_AUTHORIZED"
puts $f "META|generated_payload_field_map|NOT_PROVEN"
puts $f "META|simulation|NOT_RUN"
puts $f "META|synthesis|NOT_RUN"
puts $f "READ_ONLY_QUERY|PASS|Genuine_original_BD_properties_only"
close $f
close_project
puts "M05_D4_READ_ONLY_BD_PROPERTIES_PASS|NO_GENERATION_NO_SYNTHESIS_NO_BOARD"
