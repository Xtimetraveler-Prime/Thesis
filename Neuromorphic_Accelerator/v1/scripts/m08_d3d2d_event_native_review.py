#!/usr/bin/env python3
"""D3.D.2D FIRST new owner-native RAW-EVENT image triage. READ ONLY, NO BOARD.

Not a bitstream approval. Even a clean first owner route/timing/DRC and
complete SHA receipt ALWAYS yield exit code 2 with "NEW_DRC_REVIEW_REQUIRED".
The original D3.D.2C seven vendor warnings/image are NEVER inherited.
Separate owner-exact new bitstream/DRC/clock/hierarchy signoff is mandatory
before any guarded new physical programming command can be developed.
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
import m08_d3d2d_event_gate as gate
import m08_d3c_jtag_bram_gate as vendor

BUILDER=ROOT/"scripts/m08_d3d2d_event_build.tcl"
POR=ROOT/"rtl/m08_d3c_fabric_por.v"
BIT="bitstream_candidate/m08_d3d2d_event_lif_jtag_UNRELEASED.bit"
FILES=(
    "00_vivado.log","01_vivado.jou","02_vivado_exit.txt",
    "reports/10_fan_a12.xdc","reports/11_fabric_por.v",
    "reports/12_synaptic_lif_axil.v","reports/20_route_drc.rpt",
    "reports/21_route_timing.rpt","reports/22_route_utilization.rpt",
    "reports/23_route_clocks.rpt","reports/30_native_result.txt",BIT
)

class Reject(ValueError):
    pass

def require(ok,why):
    if not ok:
        raise Reject(why)

def read(path:Path,limit=12_000_000):
    require(path.is_file() and not path.is_symlink(),"missing/symlink original native evidence "+str(path))
    require(0<path.stat().st_size<=limit,"empty/oversize native evidence "+str(path))
    return path.read_bytes()

def inspect(run:Path)->dict:
    gate.source()
    require(run.is_dir() and not run.is_symlink() and run.parent.name=="M08" and
            re.fullmatch(r"m08_d3d2d_event_[A-Za-z0-9]+",run.name) is not None,
            "noncanonical new raw event owner original native evidence folder")
    receipt=read(run/"99_evidence_sha256.txt",12000).decode("ascii").splitlines()
    require(len(receipt)==12,"expected twelve original SHA receipt rows")
    for name,row in zip(FILES,receipt):
        m=re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_./-]+)",row)
        require(m is not None and m.group(2)==name,
                "incorrect original native SHA name/order "+name)
        path=run/name
        require(not path.parent.is_symlink(),"symlinked native evidence directory")
        digest=sha256(read(path,100_000_000 if name==BIT else 12_000_000)).hexdigest()
        require(digest==m.group(1),"original native byte changed "+name)
    require(read(run/"02_vivado_exit.txt",80).decode().strip()=="vivado_build_exit=0",
            "original Vivado build returned nonzero, preserve evidence")
    report=read(run/"reports/30_native_result.txt",15000).decode().splitlines()
    parts=[v.split("=",1) for v in report]
    require(all(len(x)==2 for x in parts) and len(dict(parts))==len(parts),
            "malformed/duplicate original native metadata")
    data=dict(parts)
    expected={
        "schema":"m08-d3d2d-raw-events-32-offline-build-v1",
        "wrapper_top":"m08_d3d2d_event_lif_jtag_wrapper",
        "neural_mode":"THIRTY_TWO_NEURON_M06_RAW_17_EVENT_INGRESS_3_4_SIGNED16",
        "decay_modes":"ZERO_HALF_ONE_THREE_QUARTERS",
        "physical_neurons":"32","physical_ticks":"4",
        "edge_capacity":"8","m06_original_edges":"5",
        "m06_original_external_events":"17",
        "external_event_coalescing":"FPGA_AXI_LITE_EVENT_PUSH",
        "event_mailbox_capacity":"64",
        "m06_original_individual_external_events":"17",
        "hardware_signed_event_accumulation":"YES",
        "physical_event_stream_dma":"NO",
        "physical_m06_ddr":"NO",
        "part":"xck26-sfvc784-2LV-c",
        "ps_to_pl_hpm":"DISABLED",
        "jtag_axi":"ENABLED_PL","ps_pl0_clock_request_hz":"100000000",
        "ps_pl0_runtime_clock_proven":"NO",
        "bram_map_base":"0xA0000000",
        "lif_base":"0xA0001000",
        "bram_map_range":"0x00001000",
        "lif_map_range":"0x00001000",
        "reset_mode":"FABRIC_POR_256_CYCLES",
        "ps_reset_dependency":"NO","ps_clock_dependency":"YES",
        "fan_route":"TTC0_WAVEOUT2_TO_A12",
        "hardware_bitstream_programmed":"NO",
        "hardware_neural_execution_proven":"NO",
    }
    for key,value in expected.items():
        require(data.get(key)==value,"new native raw-event metadata mismatch "+key)
    for key,source,receipt_path in (
        ("lif_rtl_sha256",gate.RTL,"reports/12_synaptic_lif_axil.v"),
        ("fabric_por_rtl_sha256",POR,"reports/11_fabric_por.v"),
    ):
        digest=sha256(read(source,100000)).hexdigest()
        require(data.get(key)==digest and
                sha256(read(run/receipt_path,100000)).hexdigest()==digest,
                "raw event native source/embedded code SHA drift "+key)
    require(data.get("builder_sha256")==sha256(read(BUILDER,100000)).hexdigest(),
            "native raw-event Vivado builder SHA changed")
    require(data.get("vivado_version","").startswith("2025.2"),
            "genuine 2025.2 Vivado required")
    b=read(run/BIT,100_000_000)
    bit_sha=sha256(b).hexdigest()
    require(len(b)>100000 and str(len(b))==data.get("bitstream_size_bytes"),
            "new candidate bitstream size/hash inconsistent")
    require(bit_sha not in (
        "244d304a44af6b1eda1943c18e7b5a3bed302cae2308c28a11944ede7eadf932",
        "dae1c4953826317854acd3c61d013b6fddec410a0450002fa13b3ab1f1650d14",
    ),"old already physically accepted bitstream cannot substitute M32E")
    log=read(run/"00_vivado.log").decode(errors="replace")
    require("M08_D3D2D_NATIVE_TOP_WRAPPER_VALIDATED|m08_d3d2d_event_lif_jtag_wrapper" in log and
            "M08_D3D2D_JTAG_BRAM_OFFLINE_BITSTREAM_CREATED_NOT_PROGRAMMED" in log,
            "native new wrapper or bitstream marker missing")
    require(not any(x.startswith(("ERROR:","CRITICAL WARNING:")) for x in log.splitlines()),
            "original Vivado critical warning/error requires new diagnosis")
    drc_raw=read(run/"reports/20_route_drc.rpt",3_000_000)
    drc=drc_raw.decode(errors="replace")
    counts=re.findall(r"(?m)^\s*Checks found:\s*(\d+)\s*$",drc)
    require(len(counts)==1,"original DRC count missing/ambiguous")
    try:
        timing=vendor.inspect_timing(read(
            run/"reports/21_route_timing.rpt",3_000_000).decode(errors="replace"))
    except (vendor.Reject,ValueError) as exc:
        raise Reject("new original native timing NOT accepted: "+str(exc)) from exc
    # Always require a fresh human first-image DRC review EVEN with positive
    # timing; this tool NEVER returns physical authorization.
    return dict(
        status="M08_D3D2D_FIRST_NEW_NATIVE_DRC_REVIEW_REQUIRED_NO_BOARD",
        original_12_sha_entries_verified=True,
        candidate_path=str(run/BIT),
        candidate_sha256=bit_sha,
        candidate_bytes=len(b),
        original_drc_checks=int(counts[0]),
        original_drc_sha256=sha256(drc_raw).hexdigest(),
        physical_authorized=False, physical_programmed=False,
        raw_event_ingress_physically_verified=False,
        **timing)

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir",type=Path,required=True)
    args=p.parse_args()
    try:
        print(json.dumps(inspect(args.run_dir),indent=2,sort_keys=True))
        print("M08_D3D2D_FIRST_IMAGE_REVIEW_HARD_STOP_NO_BOARD",file=sys.stderr)
        return 2
    except (Reject,ValueError,OSError,KeyError,UnicodeError) as exc:
        print("M08_D3D2D_NATIVE_PC_REJECTED: "+str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
