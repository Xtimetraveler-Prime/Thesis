#!/usr/bin/env python3
"""Independent READ-ONLY M08.4 first-original KV260 paged neural receipt audit.

This audits the original immutable JTAG source/log/oracle/physical word
capture. It is NEVER a substitute for earlier new-image DRC/timing release.
The 512 comparisons comprise 128 HOST-coalesced input checks plus 384
fabric-computed voltage, spike and recurrent-current observations.
NO real DDR, DMA, on-fabric raw event FIFO or asynchronous clocks proved.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_paged_m06_lif_fixture as oracle
import m08_paged_m06_lif_native_review as native
import m08_paged_m06_lif_exact_native_accept as first_image

NAMES=(
    "00_executed_source.tcl",
    "01_jtag_paged_m06.log",
    "02_jtag_paged_m06.jou",
    "03_exit.txt",
    "10_edge_config_input.hex",
    *(f"11_neural_page_{p}_input.hex" for p in range(6)),
    "20_independent_512_oracle_ONLY.hex",
    "80_physical_paged_neural_parity.txt",
)
EXPECTED_BIT_SHA="6a4a71f255adcc79a4131401a3f75eb64f253d3431f5ad1babc0da48479f6494"
OBS=re.compile(
    r"^tick=(\d+) page=(\d+) neuron=(\d+) "
    r"input=([0-9A-F]{8}) voltage=([0-9A-F]{8}) "
    r"mask=([0-9A-F]{8}) recurrent=([0-9A-F]{8})$"
)
class Reject(ValueError):
    pass

def require(value:bool,reason:str):
    if not value:
        raise Reject(reason)

def read(path:Path,limit:int=15_000_000)->bytes:
    require(path.is_file() and not path.is_symlink() and
            0 < path.stat().st_size <=limit,
            "missing, symlink or oversized original physical file "+str(path))
    return path.read_bytes()

def inspect(native_dir:Path,hw_dir:Path)->dict:
    require(native_dir.name=="m08_paged_m06_lif_QFKpXlPW" and
            native_dir.parent==(Path.home()/"Thesis_Evidence/M08"),
            "wrong original native image")
    original=first_image.inspect(native_dir)
    require(original["image_specific_gate"]=="ACCEPTED" and
            original["owner_bit_sha256"]==EXPECTED_BIT_SHA,
            "first owner native image must have an independently accepted exact-source DRC/timing/clock gate")
    require(hw_dir.is_dir() and not hw_dir.is_symlink() and
            hw_dir.parent==(Path.home()/"Thesis_Evidence/M08") and
            re.fullmatch(r"m08_paged_m06_lif_HW_[A-Za-z0-9]+",hw_dir.name),
            "noncanonical original hardware evidence")
    receipt=read(hw_dir/"99_evidence_sha256.txt",10_000).decode("ascii").splitlines()
    require(len(receipt)==len(NAMES),
            "expected 13 complete original hardware SHA receipt rows")
    checked={}
    for line in receipt:
        require(re.fullmatch(r"[0-9a-f]{64}  .+",line) is not None,
                "malformed owner SHA row")
        want,name=line.split("  ",1)
        require(name in NAMES and name not in checked,
                "unrecognized or duplicated first original hardware receipt")
        actual=read(hw_dir/name)
        require(sha256(actual).hexdigest()==want,
                "original physical file was altered: "+name)
        checked[name]=actual
    require(set(checked)==set(NAMES),"original hardware ledger incomplete")
    require(checked["00_executed_source.tcl"]==
            read(ROOT/"scripts/m08_paged_m06_lif_physical_once.tcl"),
            "owner executed Tcl must be exact source with no drift")
    require(checked["03_exit.txt"].decode("ascii").strip()=="vivado_physical_exit=0",
            "original JTAG process did not exit successfully")
    fixture={
        "10_edge_config_input.hex":oracle.edge_words(),
        **{f"11_neural_page_{p}_input.hex":oracle.neural_words(p) for p in range(6)},
        "20_independent_512_oracle_ONLY.hex":oracle.golden_words(),
    }
    for name,words in fixture.items():
        expected="".join(f"{x:08X}\n" for x in words).encode("ascii")
        require(checked[name]==expected,"original neural input or comparison-only oracle mismatch: "+name)
    log=checked["01_jtag_paged_m06.log"].decode("utf-8",errors="replace")
    lines=log.splitlines()
    # Vivado batch mode ECHOES executed Tcl as comment-prefixed source lines
    # (e.g. '# puts "M08_4_NEW_IMAGE_PROGRAM_ONCE_START"') in the same
    # original log as the actual stdout line. Substring counting therefore
    # double-counts even an EXACTLY ONE-program successful original run.
    # Count ONLY complete standalone event lines. No receipt rewrite, JTAG
    # replay or original source mutation is appropriate for this audit bug.
    ordered=[
        "M08_4_ORIGINAL_BIT_SHA|"+EXPECTED_BIT_SHA,
        "M08_4_SEPARATE_6_INPUT_PAGES_AND_512_ONLY_EXTERNAL_GOLDEN_PRECHECK_PASS",
        "M08_4_NEW_IMAGE_PROGRAM_ONCE_START",
        "M08_4_NEW_IMAGE_PROGRAM_ONCE_COMPLETE",
        "M08_4_PHYSICAL_EDGE_PAGE_CONFIGURED_5",
    ]
    for t in range(4):
        ordered.extend(
            f"M08_4_PHYSICAL_256B_LOAD_COMPUTE_FULL_DIRTY_SAVE|{t}|{p}"
            for p in range(6)
        )
        ordered.append(f"M08_4_PHYSICAL_ORDERED_TICK_BARRIER|{t}")
    ordered.append(
        "M08_4_PHYSICAL_128_HOST_CURRENTS_384_FABRIC_COMPUTED_24_PAGES_ONE_BANK_PASS"
    )
    marker_positions=[]
    for marker in ordered:
        positions=[i for i,line in enumerate(lines) if line==marker]
        require(len(positions)==1,
                "missing or duplicate original standalone physical JTAG marker "+marker)
        marker_positions.append(positions[0])
    require(marker_positions==sorted(marker_positions) and
            len(set(marker_positions))==len(marker_positions),
            "first original JTAG markers out of physical execution order")
    body=checked["80_physical_paged_neural_parity.txt"].decode("ascii").splitlines()
    expected_head=(
        "result=ONE_NEW_ORIGINAL_SIGNED16_32X4_ONE_RESIDENT_SIX_PAGE_PHYSICAL_PARITY",
        "owner_bit_sha256="+EXPECTED_BIT_SHA,
        "genuine_kv260_jtag_program_count=1",
        "external_raw_events=17",
        "external_ingress=HOST_COALESCED_NOT_RAW_EVENT_FIFO",
        "independently_checked_host_input_currents=128",
        "independently_checked_fabric_voltages=128",
        "independently_checked_fabric_spike_decisions=128",
        "independently_checked_fabric_recurrent_currents=128",
        "real_page_load_compute_dirty_save_dispatches=24",
        "real_resident_neuron_banks=1",
        "physical_ps_pl_ddr=NO",
    )
    require(tuple(body[:len(expected_head)])==expected_head,
            "first original result metadata mismatched expected safety scope")
    records=body[len(expected_head):]
    require(len(records)==128,"physical neural result must have exactly 128 computed records")
    golden=oracle.golden_words()
    expected_masks=[0]*32
    idx=0
    for t in range(4):
        for p in range(6):
            for loc in range(2 if p==5 else 6):
                n=p*6+loc
                match=OBS.fullmatch(records[idx])
                require(match is not None,"malformed physical neural row "+str(idx))
                observed=[int(x,16) for x in match.groups()[3:]]
                off=t*128+n*4
                expected_masks[n] |= ((golden[off+2]&1)<<t)
                expected=[golden[off],golden[off+1],expected_masks[n],golden[off+3]]
                require(tuple(map(int,match.groups()[:3]))==(t,p,n) and
                        observed==expected,
                        "independent M02/M03 physical neural parity mismatch "+str((t,p,n)))
                idx+=1
    require(any(mask for mask in expected_masks) and
            any(golden[t*128+n*4+3] for t in range(4) for n in range(32)),
            "original workload must exercise true spike and synaptic recurrence")
    return {
        "status":"M08_4_FIRST_ORIGINAL_PHYSICAL_ONE_RESIDENT_6PAGES_128HOST_384PL_NUMERICAL_PASS_REVIEW_REQUIRED",
        "native_original_bit_sha256":EXPECTED_BIT_SHA,
        "original_native_15_SHA_files_checked":True,
        "original_physical_sha_files_checked":len(NAMES),
        "original_single_JTAG_program_marker":True,
        "physical_256_byte_page_dispatches_saved":24,
        "ordered_tick_barriers":4,
        "independent_host_coalesced_input_checks":128,
        "independent_physical_pl_computed_checks":384,
        "total_exact_numerical_comparisons":512,
        "physical_ddr":False,
        "new_image_hardware_owner_release_already_required":True,
        "owner_final_M08_4_acceptance_review_pending":True,
    }

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native-dir",type=Path,required=True)
    p.add_argument("--hw-dir",type=Path,required=True)
    args=p.parse_args()
    try:
        print(json.dumps(inspect(args.native_dir,args.hw_dir),indent=2,sort_keys=True))
        return 0
    except (Reject,native.Reject,first_image.Reject,oracle.Reject,ValueError,OSError,UnicodeError) as exc:
        print("M08_4_FIRST_HW_RECEIPT_REJECTED: "+str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
