#!/usr/bin/env python3
"""D3.D.2C owner FIRST new genuine Vivado evidence triage, NO BOARD.

Never accepts any new image automatically, even if DRC happens to be 0.
Reports original SHA, 12-file receipt and timing/provenance, then exits 2
until a separate exact owner image/source/hierarchy review is implemented.
NO D3.D.2B seven-warning inheritance. NO programming or source rewrite.
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
import m08_d3d2c_m06_gate as stage
import m08_d3c_jtag_bram_gate as d3c

BUILDER=ROOT/"scripts/m08_d3d2c_m06_build.tcl"
RTL=stage.RTL
POR=ROOT/"rtl/m08_d3c_fabric_por.v"
BIT_REL="bitstream_candidate/m08_d3d2c_m06_lif_jtag_UNRELEASED.bit"
FILES=(
    "00_vivado.log","01_vivado.jou","02_vivado_exit.txt",
    "reports/10_fan_a12.xdc","reports/11_fabric_por.v",
    "reports/12_synaptic_lif_axil.v","reports/20_route_drc.rpt",
    "reports/21_route_timing.rpt","reports/22_route_utilization.rpt",
    "reports/23_route_clocks.rpt","reports/30_native_result.txt",BIT_REL
)

class Reject(ValueError):
    pass

def check(value,msg):
    if not value:
        raise Reject(msg)

def read(path,limit=12000000):
    check(path.is_file() and not path.is_symlink(),"missing/symlink native file "+str(path))
    check(0<path.stat().st_size<=limit,"empty/oversize native file "+str(path))
    return path.read_bytes()

def inspect(folder:Path):
    stage.source()  # original D3.D.2B source must still be pinned
    check(folder.is_dir() and not folder.is_symlink() and
          folder.parent.name=="M08" and
          re.fullmatch(r"m08_d3d2c_m06_[A-Za-z0-9]+",folder.name) is not None,
          "not a unique new D3.D.2C owner native folder")
    receipt=read(folder/"99_evidence_sha256.txt",12000).decode("ascii").splitlines()
    check(len(receipt)==12,"expected exactly twelve original native SHA rows")
    for name,line in zip(FILES,receipt):
        match=re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_./-]+)",line)
        check(match is not None and match.group(2)==name,
              "original ledger name/order drift "+name)
        obj=folder/name
        check(not obj.parent.is_symlink(),"symlinked report/bitstream parent")
        actual=sha256(read(obj,100000000 if name==BIT_REL else 12000000)).hexdigest()
        check(actual==match.group(1),"original native file hash drift "+name)
    check(read(folder/"02_vivado_exit.txt",80).decode().strip()=="vivado_build_exit=0",
          "native Vivado execution failed; preserve first report")
    metadata=read(folder/"reports/30_native_result.txt",16000).decode().splitlines()
    fields=[x.split("=",1) for x in metadata]
    check(all(len(x)==2 for x in fields) and len(fields)==len(dict(fields)),
          "malformed native owner metadata")
    data=dict(fields)
    for key,value in {
        "schema":"m08-d3d2c-m06-32-offline-build-v1",
        "wrapper_top":"m08_d3d2c_m06_lif_jtag_wrapper",
        "neural_mode":"THIRTY_TWO_NEURON_M06_RECURRENT_3_4_SIGNED16",
        "decay_modes":"ZERO_HALF_ONE_THREE_QUARTERS",
        "physical_neurons":"32","physical_ticks":"4",
        "edge_capacity":"8","m06_original_edges":"5",
        "m06_original_external_events":"17",
        "external_event_coalescing":"HOST_PC_ONLY",
        "physical_m06_ddr":"NO",
        "part":"xck26-sfvc784-2LV-c",
        "ps_to_pl_hpm":"DISABLED",
        "ps_clock_dependency":"YES",
        "bram_map_base":"0xA0000000",
        "lif_base":"0xA0001000",
        "reset_mode":"FABRIC_POR_256_CYCLES",
        "hardware_bitstream_programmed":"NO",
        "hardware_neural_execution_proven":"NO",
    }.items():
        check(data.get(key)==value,"new native metadata mismatch "+key)
    for key,path,embedded in (
        ("lif_rtl_sha256",RTL,"reports/12_synaptic_lif_axil.v"),
        ("fabric_por_rtl_sha256",POR,"reports/11_fabric_por.v"),
    ):
        digest=sha256(read(path,100000)).hexdigest()
        check(data.get(key)==digest and
              sha256(read(folder/embedded,100000)).hexdigest()==digest,
              "routed source/provenance mismatch "+key)
    check(data.get("builder_sha256")==sha256(read(BUILDER,100000)).hexdigest(),
          "owner original Vivado builder mismatch")
    check(data.get("vivado_version","").startswith("2025.2"),
          "requires original Vivado 2025.2")
    bit=read(folder/BIT_REL,100000000)
    check(len(bit)>100000,"no plausible genuine new bitstream")
    bit_hash=sha256(bit).hexdigest()
    check(bit_hash != "dae1c4953826317854acd3c61d013b6fddec410a0450002fa13b3ab1f1650d14",
          "D3.D.2B image is NOT a 32-neuron candidate")
    log=read(folder/"00_vivado.log").decode(errors="replace")
    check("M08_D3D2C_NATIVE_TOP_WRAPPER_VALIDATED" in log and
          "M08_D3D2C_JTAG_BRAM_OFFLINE_BITSTREAM_CREATED_NOT_PROGRAMMED" in log,
          "real Vivado 32-neuron routing markers absent")
    check(not any(x.startswith(("ERROR:","CRITICAL WARNING:"))
                  for x in log.splitlines()),
          "native Vivado errors/critical warnings need manual review")
    drc=read(folder/"reports/20_route_drc.rpt",3000000).decode(errors="replace")
    hits=re.findall(r"(?m)^\s*Checks found:\s*(\d+)\s*$",drc)
    check(len(hits)==1,"original routed DRC count missing or ambiguous")
    try:
        timing=d3c.inspect_timing(read(
            folder/"reports/21_route_timing.rpt",3000000).decode(errors="replace"))
    except (d3c.Reject,ValueError) as exc:
        raise Reject("original timing is NOT accepted: "+str(exc)) from exc
    return {
        "status":"M08_D3D2C_FIRST_NATIVE_IMAGE_DRC_REVIEW_REQUIRED_NO_BOARD",
        "original_12_sha_entries_verified":True,
        "candidate_sha256":bit_hash,
        "candidate_bytes":len(bit),
        "original_drc_checks":int(hits[0]),
        "first_new_drc_report_sha256":sha256(drc.encode()).hexdigest(),
        "hardware_programmed":False,
        "new_image_approved_for_programming":False,
        **timing,
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir",type=Path,required=True)
    a=p.parse_args()
    try:
        print(json.dumps(inspect(a.run_dir),indent=2,sort_keys=True))
        print("M08_D3D2C_STOP_FIRST_IMAGE_NOT_AUTHORIZED",file=sys.stderr)
        return 2  # *mandatory*: first image requires separate original review
    except (Reject,ValueError,OSError,KeyError,UnicodeError) as exc:
        print("M08_D3D2C_NATIVE_REJECTED: "+str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
