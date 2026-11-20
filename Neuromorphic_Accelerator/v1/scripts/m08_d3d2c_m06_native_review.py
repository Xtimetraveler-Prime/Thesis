#!/usr/bin/env python3
"""D3.D.2C FIRST owner-original EXACT native 32-neuron Vivado gate, NO BOARD.

Reviewed solely the first successful original 2026-11-20 12:31 MST owner
image m08_d3d2c_m06_MN2pwduB and its seven EXACT vendor/debug DRC warnings.
Other original images, edited results, new warning cells/pins, negative timing
or altered RTL/builders all fail closed. Not a blanket warning waiver.
Does not program JTAG, touch Linux/PS MMIO, or establish physical M06 parity.
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
import m08_d3d2c_m06_gate as stage
import m08_d3c_jtag_bram_gate as d3c

BUILDER=ROOT/"scripts/m08_d3d2c_m06_build.tcl"
RTL=stage.RTL
POR=ROOT/"rtl/m08_d3c_fabric_por.v"
BIT_REL="bitstream_candidate/m08_d3d2c_m06_lif_jtag_UNRELEASED.bit"
# Exact owner-original new 32-neuron candidate, NOT inherited from D3.D.2B.
ORIGINAL_OWNER_NATIVE_DIR="m08_d3d2c_m06_MN2pwduB"
OWNER_ORIGINAL_BIT_SHA="244d304a44af6b1eda1943c18e7b5a3bed302cae2308c28a11944ede7eadf932"
OWNER_ORIGINAL_BIT_BYTES=7797842
OWNER_ORIGINAL_DRC_SHA="7c273c8160811e7242c15418d174ae31fc6ddfee7d4850b7748d2facbe3e9fe3"
OWNER_ORIGINAL_RTL_SHA="27b40475d75592d06f45bc5d66205e4a93e1684195c2965031ad32eb4c77ad04"
OWNER_ORIGINAL_BUILDER_SHA="e4c95944c11881b741d92215be161dd00e3ab1b89d96e34c32a14b4acec8ca6d"
OWNER_ORIGINAL_POR_SHA="56dffdb178772296c7d751d75654aff8be44885939f752a9200ad1f961373fb2"
REVIEWED_JTAG_INSTANCE="m08_d3d2c_m06_lif_jtag_i"
REVIEWED_DEBUG_PREFIX="dbg_hub/inst/BSCANID.u_xsdbm_id/SWITCH_N_EXT_BSCAN."
REVIEWED_DRC_PATH=(
    "/home/dna/Thesis_Evidence/M08/"+ORIGINAL_OWNER_NATIVE_DIR+
    "/reports/20_route_drc.rpt"
)
REVIEWED_RTSTAT_FIRST15=tuple(
    item.replace("m08_d3d_lif_jtag_i",REVIEWED_JTAG_INSTANCE)
    for item in d3c.D3D_RTSTAT10_REVIEWED_FIRST15
)
REVIEWED_LUT_PINS={
    1:("'A1'","bscan_switch/temp_curid[31]_i_1","I0",
       "'O5=(A3*A4)+(A3*(~A4)*(~A5))+((~A3))'"),
    2:("'A2'","bscan_switch/temp_curid[31]_i_1","I1",
       "'O5=(A3*A4)+(A3*(~A4)*(~A5))+((~A3))'"),
    3:("'A5'","id_state[0]_i_1","I0",
       "'O6=(A6+~A6)*((A1))'"),
}
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

def inspect_reviewed_drc(report: str) -> dict:
    """Classify only all 7 first-owner XSDB/JTAG warnings and printed 15 paths.

    39 unroutable nets/37 listed; Vivado printed only first 15, so this
    intentionally does NOT claim the other 22 listed names were reviewed.
    The separate SHA256 check pins the entire original report byte-for-byte.
    """
    review="M08_D3D2C_NEW_DRC_REVIEW_REQUIRED: "
    for snippet in (
        "Vivado v.2025.2 (lin64)",
        "Date         : Fri Nov 20 12:31:10 2026",
        "Command      : report_drc -file "+REVIEWED_DRC_PATH,
        "Design       : m08_d3d2c_m06_lif_jtag_wrapper",
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
    check(found==d3c.VENDOR_DRC_PROFILE and
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
              d3c.VENDOR_DRC_PROFILE[code][1] in body,
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
    for code,(expected_count,_) in d3c.VENDOR_DRC_PROFILE.items():
        check(counts[code]==expected_count and
              {ordinal for rule,ordinal in seen if rule==code}==
              set(range(1,expected_count+1)),
              review+"missing or reordered vendor warning ordinal")
    return {
        "original_drc_checks":7,
        "vendor_drc_warnings":7,
        "drc_review_status":"EXACT_OWNER_D3D2C_SEVEN_VENDOR_DEBUG_JTAG_WARNINGS",
        "rtstat_total_unroutable":39,
        "rtstat_listed_count":37,
        "rtstat_sampled_paths":15,
    }


def inspect(folder:Path):
    stage.source()  # original D3.D.2B source must still be pinned
    check(folder.is_dir() and not folder.is_symlink() and
          folder.parent.name=="M08" and
          folder.name==ORIGINAL_OWNER_NATIVE_DIR,
          "not immutable first owner D3.D.2C accepted native folder")
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
        "ps_reset_dependency":"NO",
        "jtag_axi":"ENABLED_PL",
        "ps_pl0_clock_request_hz":"100000000",
        "ps_pl0_runtime_clock_proven":"NO",
        "board_part":"xilinx.com:kv260_som:part0:1.4",
        "linux_management_compatibility":"NOT_PROVEN",
        "bram_map_base":"0xA0000000",
        "lif_base":"0xA0001000",
        "bram_map_range":"0x00001000",
        "lif_map_range":"0x00001000",
        "bram_controller_derived_depth":"1024",
        "bram_depth_words":"1024",
        "bram_width_bits":"32",
        "test_window_bytes":"4096",
        "fan_route":"TTC0_WAVEOUT2_TO_A12",
        "reset_mode":"FABRIC_POR_256_CYCLES",
        "hardware_bitstream_programmed":"NO",
        "hardware_neural_execution_proven":"NO",
        "hardware_jtag_axil_readback_proven":"NO",
        "hardware_lif_readback_proven":"NO",
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
    for key,pinned in (
        ("builder_sha256",OWNER_ORIGINAL_BUILDER_SHA),
        ("lif_rtl_sha256",OWNER_ORIGINAL_RTL_SHA),
        ("fabric_por_rtl_sha256",OWNER_ORIGINAL_POR_SHA),
    ):
        check(data.get(key)==pinned,
              "reviewed original owner source pin changed: "+key)
    check(data.get("builder_sha256")==sha256(read(BUILDER,100000)).hexdigest(),
          "owner original Vivado builder mismatch")
    check(data.get("vivado_version","").startswith("2025.2"),
          "requires original Vivado 2025.2")
    bit=read(folder/BIT_REL,100000000)
    check(len(bit)==OWNER_ORIGINAL_BIT_BYTES and
          data.get("bitstream_size_bytes")==str(OWNER_ORIGINAL_BIT_BYTES),
          "owner original candidate bitstream size differs")
    bit_hash=sha256(bit).hexdigest()
    check(bit_hash==OWNER_ORIGINAL_BIT_SHA,
          "owner original 32-neuron candidate image SHA256 mismatch")
    check(bit_hash != "dae1c4953826317854acd3c61d013b6fddec410a0450002fa13b3ab1f1650d14",
          "D3.D.2B image is NOT a 32-neuron candidate")
    log=read(folder/"00_vivado.log").decode(errors="replace")
    check("M08_D3D2C_NATIVE_TOP_WRAPPER_VALIDATED|m08_d3d2c_m06_lif_jtag_wrapper" in log and
          "M08_D3D2C_JTAG_BRAM_OFFLINE_BITSTREAM_CREATED_NOT_PROGRAMMED" in log,
          "real Vivado 32-neuron routing markers absent")
    check(not any(x.startswith(("ERROR:","CRITICAL WARNING:"))
                  for x in log.splitlines()),
          "native Vivado errors/critical warnings need manual review")
    original_drc_bytes=read(folder/"reports/20_route_drc.rpt",3000000)
    check(sha256(original_drc_bytes).hexdigest()==OWNER_ORIGINAL_DRC_SHA,
          "original owner DRC report not byte-identical to reviewed seven advisories")
    drc=inspect_reviewed_drc(original_drc_bytes.decode("utf-8"))
    try:
        timing=d3c.inspect_timing(read(
            folder/"reports/21_route_timing.rpt",3000000).decode(errors="replace"))
    except (d3c.Reject,ValueError) as exc:
        raise Reject("original timing is NOT accepted: "+str(exc)) from exc
    check(timing["wns_ns"]==2.675 and timing["tns_ns"]==0.0 and
          timing["whs_ns"]==0.010 and timing["ths_ns"]==0.0,
          "original routed timing summary no longer matches owner-reviewed candidate")
    return {
        "status":"M08_D3D2C_EXACT_OWNER_NATIVE_M06_32_IMAGE_ACCEPTED_NO_BOARD",
        "original_12_sha_entries_verified":True,
        "candidate_path":str((folder/BIT_REL).resolve()),
        "candidate_sha256":bit_hash,
        "candidate_bytes":len(bit),
        "first_new_drc_report_sha256":OWNER_ORIGINAL_DRC_SHA,
        "hardware_programmed":False,
        "native_image_reviewed":True,
        "physical_programming_authorized":False,
        "physical_32_neuron_m02_parity_verified":False,
        **drc,**timing,
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir",type=Path,required=True)
    a=p.parse_args()
    try:
        print(json.dumps(inspect(a.run_dir),indent=2,sort_keys=True))
        print("M08_D3D2C_EXACT_OWNER_NATIVE_M06_32_IMAGE_ACCEPTED_NO_BOARD")
        return 0  # read-only native acceptance, NEVER a physical board result
    except (Reject,ValueError,OSError,KeyError,UnicodeError) as exc:
        print("M08_D3D2C_NATIVE_REJECTED: "+str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
