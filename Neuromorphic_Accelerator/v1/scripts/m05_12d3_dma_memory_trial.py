#!/usr/bin/env python3
"""Generate a NEW offline DMA-memory trial without editing owner-validated Tcl.

Only the 9th evidence output argument and one documented AMD UG835 AXI-MM
address block are added. The generated Tcl is evidence, not approved RTL,
DDR ownership, a Vivado PASS, or permission to access a physical device.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import sys

PRE = 'if {[llength $argv] != 8} {error "usage:'
ARG = 'set annotated_top [lindex $argv 7]\n'
ANCHOR = '# Full, genuine Vivado block-design validation. Capture status separately:\n'
MARKER = "M05_D3_DMA_HP0_OFFLINE_MAPPING_PASS"
MEMORY_TCL = r"""
# Original owner-verified six PS control segments have already read back.
# Distinct OFFLINE-only stage: four DMA masters -> real PS HP0 DDR_LOW.
# Never assign invented DDR base/range or claim PS/Linux DMA buffer ownership.
# Genuine owner log identified these exact two PS slave segment instances.
set hp0_ddr [get_bd_addr_segs -quiet /ps/SAXIGP2/HP0_DDR_LOW]
set hp0_ocm [get_bd_addr_segs -quiet /ps/SAXIGP2/HP0_LPS_OCM]
if {[llength $hp0_ddr] != 1 || [llength $hp0_ocm] != 1} {
    error "expected exactly one genuine HP0 DDR_LOW and one LPS_OCM slave segment"
}
set mf [open $dma_memory_path w]
puts $mf "META|scope|OFFLINE_VIVADO_DMA_HP0_DDR_LOW_MAPPING_OCM_EXCLUDED"
puts $mf "SLAVE|DDR_LOW|$hp0_ddr"
puts $mf "SLAVE|OCM|$hp0_ocm"
foreach {bank endpoint expected_space} {
    dma_neurons dma_neurons/M_AXI_MM2S /dma_neurons/Data_MM2S
    dma_synapses dma_synapses/M_AXI_MM2S /dma_synapses/Data_MM2S
    dma_external dma_external/M_AXI_MM2S /dma_external/Data_MM2S
    dma_trace dma_trace/M_AXI_S2MM /dma_trace/Data_S2MM
} {
    set master_port [require_intf $endpoint]
    if {[string toupper [get_property MODE $master_port]] ne "MASTER"} {
        error "DMA memory interface $endpoint is not a genuine MASTER"
    }
    set dma_space [get_bd_addr_spaces -quiet -of_objects $master_port]
    if {[llength $dma_space] != 1 || "$dma_space" ne "$expected_space"} {
        error "DMA $bank master address space not exact: $dma_space"
    }
    if {[llength [get_bd_addr_segs -quiet -of_objects $dma_space]] != 0} {
        error "DMA $bank unexpectedly pre-mapped before isolated memory trial"
    }
    # AMD UG835: -target_address_space ensures no implicit assignment to
    # the PS control or another DMA master. Vivado determines actual range.
    assign_bd_address -target_address_space $dma_space $hp0_ddr
    set ddr_matches {}
    foreach candidate [get_bd_addr_segs -addressing -quiet -of_objects $hp0_ddr] {
        if {[string match [format "%s/*" $dma_space] "$candidate"]} {
            lappend ddr_matches $candidate
        }
    }
    if {[llength $ddr_matches] != 1} {
        error "DMA $bank lacks one authentic DDR_LOW master segment"
    }
    set ddr_master [lindex $ddr_matches 0]
    set reverse [get_bd_addr_segs -quiet -of_objects $ddr_master]
    if {[llength $reverse] != 1 || "$reverse" ne "$hp0_ddr"} {
        error "DMA $bank DDR_LOW master does not reverse to real PS slave"
    }
    set ddr_offset [string trim [get_property OFFSET $ddr_master]]
    set ddr_range [string trim [get_property RANGE $ddr_master]]
    if {![regexp {^0x[0-9A-Fa-f]+$} $ddr_offset] ||
        ![regexp {^0x[0-9A-Fa-f]+$} $ddr_range] ||
        [expr {$ddr_range + 0}] <= 0 ||
        [expr {$ddr_offset + 0}] < 0 ||
        [expr {$ddr_offset + $ddr_range}] > 4294967296} {
        error "actual DMA $bank DDR_LOW range not representable by 32-bit address"
    }
    # OCM is NOT authorized for DMA: exclude rather than map it accessible.
    exclude_bd_addr_seg -target_address_space $dma_space $hp0_ocm
    # Query the EXCLUDED master segment directly in this exact DMA space.
    # Using plain -addressing on the slave can omit excluded segments;
    # AMD UG835 documents -excluded -of_objects <master address space>.
    set excluded [get_bd_addr_segs -excluded -quiet -of_objects $dma_space]
    if {[llength $excluded] != 1 || [lsearch -exact $excluded $ddr_master] >= 0} {
        error "DMA $bank must have exactly one excluded OCM master and nonexcluded DDR"
    }
    set ocm_master [lindex $excluded 0]
    set ocm_reverse [get_bd_addr_segs -quiet -of_objects $ocm_master]
    if {[llength $ocm_reverse] != 1 || "$ocm_reverse" ne "$hp0_ocm"} {
        error "excluded OCM master not linked to authentic HP0 OCM slave"
    }
    # Genuine owner 2025.2 run mapped HP0 DDR_LOW (2 GiB at zero) and
    # successfully EXCLUDED OCM, then this old check falsely required both
    # objects in the PLAIN query. Excluded segments have their own query.
    # AMD UG835 distinguishes -addressed (accessible) and -excluded. Prove
    # exactly one accessible DDR and exactly one excluded OCM; additionally
    # reject any unexpected entries in the ordinary space listing. That
    # ordinary list is allowed to OMIT the excluded OCM object.
    set addressed [get_bd_addr_segs -addressed -quiet -of_objects $dma_space]
    set all_masters [get_bd_addr_segs -quiet -of_objects $dma_space]
    puts "M05_D3_DMA_HP0_SEGMENT_SET_QUERY|$bank|SPACE=$dma_space|ADDRESSED=$addressed|EXCLUDED=$excluded|PLAIN=$all_masters|DDR=$ddr_master|OCM=$ocm_master"
    if {[llength $addressed] != 1 || [lindex $addressed 0] ne "$ddr_master"} {
        error "DMA $bank accessible segments are not EXACTLY the authentic HP0 DDR_LOW master"
    }
    if {[llength $excluded] != 1 || [lindex $excluded 0] ne "$ocm_master"} {
        error "DMA $bank excluded segments are not EXACTLY the authentic HP0 OCM master"
    }
    if {[llength $all_masters] < 1 || [llength $all_masters] > 2 ||
        [lsearch -exact $all_masters $ddr_master] < 0} {
        error "DMA $bank plain master listing lost DDR or has unexpected count; inspect ADDRESSED/EXCLUDED diagnostic"
    }
    foreach candidate $all_masters {
        if {$candidate ne "$ddr_master" && $candidate ne "$ocm_master"} {
            error "DMA $bank has an unexpected plain master segment $candidate"
        }
    }
    puts "M05_D3_DMA_HP0_DDR_READBACK|$bank|$dma_space|$ddr_master|OFFSET=$ddr_offset|RANGE=$ddr_range"
    puts "M05_D3_DMA_HP0_OCM_EXCLUDED|$bank|$dma_space|$ocm_master"
    puts $mf "DDR|$bank|$hp0_ddr|$dma_space|$ddr_master|$ddr_offset|$ddr_range"
    puts $mf "OCM_EXCLUDED|$bank|$hp0_ocm|$dma_space|$ocm_master"
    flush $mf
}
puts $mf "META|dma_address_width|32"
puts $mf "META|physical_ddr|NOT_AUTHORIZED"
puts $mf "META|generated_smartconnect_width_adapter|NOT_YET_PROVEN"
close $mf
puts "M05_D3_DMA_HP0_OFFLINE_MAPPING_PASS|DDR_LOW_MAPPED=4|OCM_EXCLUDED=4|GENERATED_WIDTH_ADAPTER=UNPROVEN"

"""
def derive(original: str) -> str:
    if any(original.count(a) != 1 for a in (PRE, ARG, ANCHOR)):
        raise ValueError("six-bank baseline changed: refusing unreviewed injection")
    if MARKER in original or "set dma_memory_path " in original:
        raise ValueError("six-bank baseline already modified for memory; refuse nesting")
    return (original.replace(PRE, 'if {[llength $argv] != 9} {error "usage:', 1)
            .replace(ARG, ARG + 'set dma_memory_path [lindex $argv 8]\n', 1)
            .replace(ANCHOR, MEMORY_TCL + ANCHOR, 1))

def stage(original: Path, derived: Path, manifest: Path) -> None:
    if not original.is_file() or original.resolve() in (derived.resolve(), manifest.resolve()):
        raise ValueError("read-only authentic six-bank Tcl missing or would be overwritten")
    if derived.exists() or manifest.exists() or derived.parent.resolve() != manifest.parent.resolve():
        raise ValueError("use unused derived Tcl/manifest paths within same evidence directory")
    before = original.read_bytes()
    after = derive(before.decode("utf-8")).encode("utf-8")
    with derived.open("xb") as f:
        f.write(after)
    with manifest.open("x", encoding="utf-8") as f:
        f.write("META|scope|OFFLINE_D3_DMA_HP0_DERIVED_SOURCE_TRIAL\n")
        f.write("ORIGINAL_TCL_SHA256|" + hashlib.sha256(before).hexdigest() + "\n")
        f.write("DERIVED_TCL_SHA256|" + hashlib.sha256(after).hexdigest() + "\n")
        f.write("CHANGES|9TH_REPORT_ARG_AND_ONE_DMA_HP0_ADDRESS_BLOCK_ONLY\n")
        f.write("META|physical_ddr|NOT_AUTHORIZED\n")
        f.write("META|generated_smartconnect_width_adapter|NOT_YET_PROVEN\n")
    if original.read_bytes() != before:
        raise RuntimeError("original accepted Tcl changed while staging")
    print("PASS: M05.12d.3 isolated DMA HP0 memory trial staged (original six-bank Tcl untouched, NO BOARD)")

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-tcl", required=True, type=Path)
    p.add_argument("--derived-tcl", required=True, type=Path)
    p.add_argument("--manifest", required=True, type=Path)
    a = p.parse_args()
    try:
        stage(a.base_tcl, a.derived_tcl, a.manifest)
    except (OSError, ValueError, UnicodeError, RuntimeError) as e:
        print(f"ERROR: M05.12d.3 DMA-memory trial staging: {e}", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
