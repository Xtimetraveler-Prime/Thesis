#!/usr/bin/env python3
"""Stage separate file-backed Vivado BD product trial without altering passed Tcl."""
import argparse
import hashlib
from pathlib import Path
import sys
from m05_12d3_dma_memory_trial import derive as derive_dma

PRODUCT_BLOCK = r"""
# NEW offline project flow only. Do not synthesize, write a bitstream or use HW.
save_bd_design
set actual_bd [get_files -quiet *.bd]
if {[llength $actual_bd] != 1 || ![file isfile [lindex $actual_bd 0]]} {
    error "expected genuine saved file-backed .bd for output products"
}
set real_xpr [file join $output_project_dir m05_d3_output_products.xpr]
if {![file isfile $real_xpr]} {
    error "expected genuine file-backed .xpr before generate_target"
}
set wf [open $width_report_path w]
puts $wf "META|scope|OFFLINE_REAL_VIVADO_BD_OUTPUT_PRODUCTS_WIDTH_CONTRACT"
puts $wf "PROJECT|$real_xpr"
puts $wf "BD|[lindex $actual_bd 0]"
foreach {endpoint wanted} {
    dma_neurons/M_AXI_MM2S 256
    mem_sc/S00_AXI 256
    dma_synapses/M_AXI_MM2S 256
    mem_sc/S01_AXI 256
    dma_external/M_AXI_MM2S 256
    mem_sc/S02_AXI 256
    dma_trace/M_AXI_S2MM 256
    mem_sc/S03_AXI 256
    mem_sc/M00_AXI 128
    ps/S_AXI_HP0_FPD 128
} {
    set iface [require_intf $endpoint]
    if {[lsearch -exact [list_property $iface] CONFIG.DATA_WIDTH] < 0} {
        error "Vivado native AXI pin lacks CONFIG.DATA_WIDTH: $endpoint"
    }
    set actual [string trim [get_property CONFIG.DATA_WIDTH $iface]]
    puts "M05_D3_IP_OUTPUT_WIDTH_READBACK|$endpoint|$actual"
    puts $wf "WIDTH|$endpoint|$actual"
    flush $wf
    if {$actual ne "$wanted"} {
        error "genuine Vivado $endpoint width $actual != $wanted"
    }
}
puts "M05_D3_IP_OUTPUT_TARGET_BEGIN|[lindex $actual_bd 0]"
# AMD UG835: targets for an IP Integrator hierarchy must use the BD FILE,
# not individual get_ips subcores. Never suppress generate_target errors.
generate_target all $actual_bd
puts $wf "GENERATE_TARGET|all|PASS"
puts $wf "META|physical_board|NOT_AUTHORIZED"
puts $wf "META|synthesis|NOT_RUN"
puts $wf "META|converter_internals|NOT_PROVEN_BY_OUTPUT_PRODUCTS"
close $wf
puts "M05_D3_IP_OUTPUT_TARGET_PASS|GENUINE_FILE_BACKED_BD_PRODUCTS|WIDTH_ENDPOINTS=10|SYNTHESIS=NOT_RUN"
"""
OLD_SUCCESS = 'puts "PASS: M05.12d.3 explicit SIX control-banks and genuine full Vivado block design validation (NO IP GENERATION/BOARD/DDR)"'
NEW_SUCCESS = 'puts "PASS: M05.12d.3 file-backed Vivado BD/IP outputs generated and original DMA/full-BD passed (NO SYNTHESIS/BITSTREAM/BOARD)"'
def derive(source: str) -> str:
    text = derive_dma(source)
    old_create = "create_project -in_memory -part $part\n"
    old_close = 'puts $vf "VALIDATION|PASS|FULL_BD_VALIDATE_FORCE"\nclose $vf\nclose_project\n'
    old_arg = "set dma_memory_path [lindex $argv 8]\n"
    for anchor in (old_create, old_close, old_arg, OLD_SUCCESS, 'if {[llength $argv] != 9}'):
        if text.count(anchor) != 1:
            raise ValueError("original six-control+DMA Tcl structure changed: " + anchor[:75])
    text = text.replace('if {[llength $argv] != 9}', 'if {[llength $argv] != 11}', 1)
    text = text.replace(old_arg, old_arg +
        'set width_report_path [lindex $argv 9]\n'
        'set output_project_dir [lindex $argv 10]\n'
        'if {[file exists $output_project_dir]} {error "refuse existing Vivado project in owner evidence"}\n', 1)
    text = text.replace(old_create,
        "create_project m05_d3_output_products $output_project_dir -part $part\n", 1)
    text = text.replace(old_close,
        'puts $vf "VALIDATION|PASS|FULL_BD_VALIDATE_FORCE"\nclose $vf\n' +
        PRODUCT_BLOCK + "close_project\n", 1)
    text = text.replace(OLD_SUCCESS, NEW_SUCCESS, 1)
    return text

def stage(source: Path, target: Path, manifest: Path) -> None:
    if not source.is_file() or source.resolve() in (target.resolve(), manifest.resolve()):
        raise ValueError("original accepted Tcl missing or would be overwritten")
    if target.exists() or manifest.exists() or target.parent.resolve() != manifest.parent.resolve():
        raise ValueError("fresh co-located stage artifact files required")
    before = source.read_bytes()
    after = derive(before.decode("utf-8")).encode()
    with target.open("xb") as out:
        out.write(after)
    with manifest.open("x", encoding="utf-8") as out:
        out.write("META|scope|OFFLINE_FILE_BACKED_VIVADO_OUTPUT_TRIAL\n")
        out.write("ORIGINAL_SIX_CONTROL_SHA256|" + hashlib.sha256(before).hexdigest() + "\n")
        out.write("DERIVED_FILE_BACKED_SHA256|" + hashlib.sha256(after).hexdigest() + "\n")
        out.write("META|physical_board|NOT_AUTHORIZED\n")
        out.write("META|synthesis|NOT_RUN\n")
    if source.read_bytes() != before:
        raise RuntimeError("accepted source changed during staging")
    print("PASS: M05.12d.3 separate file-backed Vivado output trial staged without mutating owner-PASS Tcl")

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-tcl", required=True, type=Path)
    p.add_argument("--derived-tcl", required=True, type=Path)
    p.add_argument("--manifest", required=True, type=Path)
    a=p.parse_args()
    try: stage(a.base_tcl, a.derived_tcl, a.manifest)
    except (ValueError, UnicodeError, RuntimeError, OSError) as e:
        print(f"ERROR: file-backed offline BD candidate: {e}", file=sys.stderr)
        return 2
    return 0
if __name__=="__main__":
    raise SystemExit(main())
