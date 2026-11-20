#!/usr/bin/env python3
"""D3.D.2D FIRST-owner exact RAW17 M32E v5 native bitstream review, NO BOARD.

This reviewer pins ONLY the owner's first 2026-11-20 15:33 original Vivado
candidate, original 12-file manifest, original source/builders, exact full
DRC report SHA, all seven individual XSDB/JTAG warnings, routed timing and
bitstream SHA. No inheritance of D3.D.2C warning pins or prior image. No
board/JTAG, MMIO, DDR, HLS or performance claims; physical auditor separate.
"""
from __future__ import annotations
import argparse
from collections import Counter
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
ORIGINAL_OWNER_NATIVE_DIR="m08_d3d2d_event_DE6kQWvt"
OWNER_ORIGINAL_BIT_SHA="f50a156342eaf1173a3869b5316e4edc1d59662d9f0d687bcec600f7b0efdeab"
OWNER_ORIGINAL_BIT_BYTES=7797844
OWNER_ORIGINAL_DRC_SHA="f1cc7a7b72b7eeee85828a6c5f7cb75d56894a55a2143cfe4e0f1f6c8098ebee"
REVIEWED_JTAG_INSTANCE="m08_d3d2d_event_lif_jtag_i"
REVIEWED_DEBUG_PREFIX="dbg_hub/inst/BSCANID.u_xsdbm_id/SWITCH_N_EXT_BSCAN."
REVIEWED_DRC_PATH=(
    "/home/dna/Thesis_Evidence/M08/"+ORIGINAL_OWNER_NATIVE_DIR+
    "/reports/20_route_drc.rpt"
)
REVIEWED_RTSTAT_FIRST15=tuple(
    item.replace("m08_d3d_lif_jtag_i",REVIEWED_JTAG_INSTANCE)
    for item in vendor.D3D_RTSTAT10_REVIEWED_FIRST15
)
REVIEWED_LUT_PINS={
    1:("'A2'","bscan_switch/temp_curid[31]_i_1","I1",
       "'O5=(A5*A1)+(A5*(~A1)*(~A4))+((~A5))'"),
    2:("'A3'","bscan_switch/temp_curid[31]_i_1","I0",
       "'O5=(A5*A1)+(A5*(~A1)*(~A4))+((~A5))'"),
    3:("'A5'","id_state[0]_i_1","I0",
       "'O6=(A6+~A6)*((A4))'"),
}
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

check=require  # same fail-closed condition helper for exact DRC detail

def read(path:Path,limit=12_000_000):
    require(path.is_file() and not path.is_symlink(),"missing/symlink original native evidence "+str(path))
    require(0<path.stat().st_size<=limit,"empty/oversize native evidence "+str(path))
    return path.read_bytes()

def inspect_reviewed_drc(report: str) -> dict:
    """Classify only all 7 first-owner XSDB/JTAG warnings and printed 15 paths.

    39 unroutable nets/37 listed; Vivado printed only first 15, so this
    intentionally does NOT claim the other 22 listed names were reviewed.
    The separate SHA256 check pins the entire original report byte-for-byte.
    """
    review="M08_D3D2D_NEW_DRC_REVIEW_REQUIRED: "
    for snippet in (
        "Vivado v.2025.2 (lin64)",
        "Date         : Fri Nov 20 15:32:35 2026",
        "Command      : report_drc -file "+REVIEWED_DRC_PATH,
        "Design       : m08_d3d2d_event_lif_jtag_wrapper",
        "Device       : xck26-sfvc784-2LV-c",
        "Design State : Fully Routed",
    ):
        check(snippet in report,review+"native report provenance changed")
    count=re.findall(r"(?m)^\s*Checks found:\s*(\d+)\s*$",report)
    check(count==["7"],review+"original DRC count not exactly seven")
    rows=re.findall(
        r"(?m)^\|\s*([A-Z]+-\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(\d+)\s*\|\s*$",
        report)
    check(len(rows)==4 and len({r[0] for r in rows})==4,
          review+"summary rows missing, duplicated or unreviewed")
    found={code:(int(num),description.strip()) for code,sev,description,num in rows
           if sev.strip()=="Warning"}
    check(found==vendor.VENDOR_DRC_PROFILE and
          all(sev.strip()=="Warning" for _,sev,_,_ in rows) and
          sum(int(num) for _,_,_,num in rows)==7,
          review+"rule severity/count/description changed")
    details=list(re.finditer(
        r"(?m)^([A-Z]+-\d+)#(\d+)\s+(Warning|Critical Warning|Error)\s*$",
        report))
    check(len(details)==7,review+"exact seven detailed warnings not present")
    counts=Counter()
    seen=set()
    for i,m in enumerate(details):
        code,ordinal,severity=m.group(1),int(m.group(2)),m.group(3)
        check(code in found and severity=="Warning" and
              (code,ordinal) not in seen,
              review+"critical/error/unknown/duplicate detailed warning")
        seen.add((code,ordinal))
        counts[code]+=1
        end=details[i+1].start() if i+1<len(details) else len(report)
        body=report[m.end():end]
        check(body.count("Related violations: <none>")==1 and
              vendor.VENDOR_DRC_PROFILE[code][1] in body,
              review+"vendor warning body or related violations changed")
        if code=="PDCN-1569":
            check(ordinal in REVIEWED_LUT_PINS,review+"new debug LUT ordinal")
            phys,suffix,endpoint,equation=REVIEWED_LUT_PINS[ordinal]
            cell=REVIEWED_DEBUG_PREFIX+suffix
            expected=(
                f"Used physical LUT pin {phys} of cell {cell} "
                f"(pin {cell}/{endpoint}) is not included in the LUT equation: "
                +equation
            )
            check(expected in body and
                  body.count("of cell ")==1 and body.count("(pin ")==1 and
                  body.count("is not included in the LUT equation: ")==1,
                  review+"debug LUT physical pin, hierarchy or equation changed")
        elif code in ("REQP-1857","REQP-1858"):
            expected_fifos={
                ("REQP-1857",1):("rx_fifo_i","WIDE_PRIM18.ram"),
                ("REQP-1858",1):("rd_cmd_fifo_i","WIDE_PRIM36_NO_ECC.ram"),
                ("REQP-1858",2):("wr_cmd_fifo_i","WIDE_PRIM36_NO_ECC.ram"),
            }
            target=expected_fifos.get((code,ordinal))
            prefix=("BRAM ("+REVIEWED_JTAG_INSTANCE+
                    "/jtag_axi/inst/jtag_axi_engine_u/")
            check(target is not None and body.count("BRAM (")==1 and
                  body.count(prefix+target[0]+"/")==1 and
                  body.count(target[1]+")")==1 and
                  "SDP mode with WRITE_FIRST write-mode" in body and
                  "address collisions" in body,
                  review+"unexpected JTAG AXI FIFO hierarchy, BRAM or collision")
        elif code=="RTSTAT-10":
            check(ordinal==1 and re.search(
                r"(?m)^\s*39 net\(s\) have no routable loads\.",body) and
                "(the first 15 of 37 listed)" in body,
                review+"RTSTAT total/list/sample size changed")
            m2=re.search(
                r"problem bus\(es\) and/or net\(s\) are (.*?)\s*"
                r"\(the first 15 of 37 listed\)",body,re.S)
            check(m2 is not None,review+"RTSTAT 15 printed paths absent")
            sampled=tuple(x.strip() for x in m2.group(1).split(",") if x.strip())
            check(sampled==REVIEWED_RTSTAT_FIRST15,
                  review+"RTSTAT printed paths include new/non-vendor net")
    for code,(expected_count,_) in vendor.VENDOR_DRC_PROFILE.items():
        check(counts[code]==expected_count and
              {ordinal for rule,ordinal in seen if rule==code}==
              set(range(1,expected_count+1)),
              review+"missing or reordered vendor warning ordinal")
    return {
        "original_drc_checks":7,
        "vendor_drc_warnings":7,
        "drc_review_status":"EXACT_OWNER_D3D2D_SEVEN_VENDOR_DEBUG_JTAG_WARNINGS",
        "rtstat_total_unroutable":39,
        "rtstat_listed_count":37,
        "rtstat_sampled_paths":15,
    }


def inspect(run:Path)->dict:
    gate.source()
    require(run.is_dir() and not run.is_symlink() and run.parent.name=="M08" and
            run.name==ORIGINAL_OWNER_NATIVE_DIR,
            "not immutable first owner D3.D.2D exact original native folder")
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
    # Owner source/build/bit provenance and readback limitations remain pinned.
    for key in ("hardware_jtag_axil_readback_proven","hardware_lif_readback_proven"):
        require(data.get(key)=="NO","original new prephysical metadata drift "+key)
    require(data.get("linux_management_compatibility")=="NOT_PROVEN",
            "new raw-event Linux management compatibility not established")
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
    require(len(b)==OWNER_ORIGINAL_BIT_BYTES and
            str(len(b))==data.get("bitstream_size_bytes") and
            bit_sha==OWNER_ORIGINAL_BIT_SHA,
            "owner-original accepted M32E bitstream size/SHA differs")
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
    require(sha256(drc_raw).hexdigest()==OWNER_ORIGINAL_DRC_SHA,
            "owner original raw-event DRC report changed from exact reviewed bytes")
    drc=inspect_reviewed_drc(drc_raw.decode("utf-8"))
    try:
        timing=vendor.inspect_timing(read(
            run/"reports/21_route_timing.rpt",3_000_000).decode(errors="replace"))
    except (vendor.Reject,ValueError) as exc:
        raise Reject("new original native timing NOT accepted: "+str(exc)) from exc
    require(timing["wns_ns"]==2.136 and timing["tns_ns"]==0.0 and
            timing["whs_ns"]==0.010 and timing["ths_ns"]==0.0,
            "original D3.D.2D routed timing summary changed from reviewed candidate")
    # Original SHA+full DRC+exact source+timing acceptance is NOT board parity.
    return dict(
        status="M08_D3D2D_EXACT_OWNER_NATIVE_RAW17_IMAGE_ACCEPTED_NO_BOARD",
        original_12_sha_entries_verified=True,
        candidate_path=str(run/BIT),
        candidate_sha256=bit_sha,
        candidate_bytes=len(b),
        original_drc_sha256=OWNER_ORIGINAL_DRC_SHA,
        native_image_reviewed=True,
        physical_programmed=False,
        raw_event_ingress_physically_verified=False,
        **drc,**timing)

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir",type=Path,required=True)
    args=p.parse_args()
    try:
        print(json.dumps(inspect(args.run_dir),indent=2,sort_keys=True))
        print("M08_D3D2D_EXACT_OWNER_NATIVE_RAW17_IMAGE_ACCEPTED_NO_BOARD")
        return 0  # native read-only only; no physical programming executed
    except (Reject,ValueError,OSError,KeyError,UnicodeError) as exc:
        print("M08_D3D2D_NATIVE_PC_REJECTED: "+str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
