#!/usr/bin/env python3
"""M08.4 exact new original owner-routed K26 image acceptance (READ ONLY).

The owner supplied the first-original native folder with 15/15 SHA receipts
and the actual four new-image vendor reports on 2026-11-20. This checker pins
the exact original bit, DRC/timing/clocks/native metadata and every DRC
instance, instead of borrowing older M32Q warning waivers. Only the BOUNDED
one-shot JTAG host-paged physical experiment can consume this authorization.

The methodology summary contains 5 unlocalized LUTAR-1 asynchronous-reset
advisories. The owner explicitly accepts remaining first physical test risk;
these warnings are disclosed, NOT claimed to have been independently traced.
No DDR/DMA, PS address probing, raw-event FIFO, async-event claim or HW I/O.
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
import m08_paged_m06_lif_native_review as native
import m08_d3c_jtag_bram_gate as vendor

OWNER="m08_paged_m06_lif_QFKpXlPW"
WRAPPER="m08_paged_m06_lif_jtag_wrapper"
BIT="bitstream_candidate/m08_paged_m06_lif_jtag_UNRELEASED.bit"
ORIGINAL={
    BIT:("6a4a71f255adcc79a4131401a3f75eb64f253d3431f5ad1babc0da48479f6494",7797842),
    "reports/20_route_drc.rpt":("2fd20b6a84cb803c4935b509b4bb5f32306ffb608067450e068d85a2284e92d4",9366),
    "reports/21_route_timing.rpt":("fcb73aca06ced0c7df7d2f9f6657e23375a2504a7a5c64461ec683a969c0e42c",80427),
    "reports/23_route_clocks.rpt":("e8330903e1ee569af95ef98fa1f072760b33b067a154fd89f3630244ea0a9ac0",2243),
    "reports/30_native_result.txt":("495a6468fd23fa2ab1558b793553025518753dddc0faece8d17c951a1894c88a",2211),
}
# The metadata size in the owner's Linux file can vary with final newline in
# summaries; the hash is authoritative for this text file.
DRC_PROFILE={
    "PDCN-1569":(3,"LUT equation term check"),
    "REQP-1857":(1,"RAMB18E2_writefirst_collision_advisory"),
    "REQP-1858":(2,"RAMB36E2_writefirst_collision_advisory"),
    "RTSTAT-10":(1,"No routable loads"),
}
VENDOR_DBG="dbg_hub/inst/BSCANID.u_xsdbm_id/"
VENDOR_AXI="m08_paged_m06_lif_jtag_i/jtag_axi/inst/jtag_axi_engine_u/"
LUT_PINS={
  1:("'A2'","temp_curid[31]_i_1","I0","'O5=(A3*A1)+(A3*(~A1)*(~A4))+((~A3))'"),
  2:("'A5'","temp_curid[31]_i_1","I1","'O5=(A3*A1)+(A3*(~A1)*(~A4))+((~A3))'"),
  3:("'A5'","id_state[0]_i_1","I0","'O6=(A6+~A6)*((A2))'"),
}
RAM_NAMES={
    ("REQP-1857",1):("rx_fifo_i","WIDE_PRIM18.ram"),
    ("REQP-1858",1):("rd_cmd_fifo_i","WIDE_PRIM36_NO_ECC.ram"),
    ("REQP-1858",2):("wr_cmd_fifo_i","WIDE_PRIM36_NO_ECC.ram"),
}
class Reject(ValueError):
    pass

def require(ok:bool,reason:str):
    if not ok: raise Reject(reason)

def original_bytes(run:Path,rel:str)->bytes:
    path=run/rel
    require(path.is_file() and not path.is_symlink(),"missing or symlink owner original "+rel)
    require(not any((run/p).is_symlink() for p in
                    (Path(rel).parents) if str(p)!="."),
            "symlink original evidence parent "+rel)
    data=path.read_bytes()
    expected_digest,expected_len=ORIGINAL[rel]
    require(sha256(data).hexdigest()==expected_digest,
            "original owner report or bit SHA changed: "+rel)
    if rel==BIT:
        require(len(data)==expected_len,"original new K26 bit length changed")
    return data

def inspect_drc(text:str)->dict:
    for term in ("Vivado v.2025.2 (lin64)","Command      : report_drc -file ",
                 "Design       : "+WRAPPER,"Device       : xck26-sfvc784-2LV-c",
                 "Design State : Fully Routed"):
        require(term in text,"original new-image DRC provenance missing: "+term)
    require(re.findall(r"(?m)^\s*Checks found:\s*(\d+)\s*$",text)==["7"],
            "expected exactly seven owner new-image DRC warnings")
    rows=re.findall(r"(?m)^\|\s*([A-Z]+-\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*(\d+)\s*\|$",text)
    require(len(rows)==4 and {(code,sev.strip(),desc.strip(),int(num))
            for code,sev,desc,num in rows}==
            {(code,"Warning",desc,count) for code,(count,desc) in DRC_PROFILE.items()},
            "unexpected original K26 DRC severity/class/count")
    heads=list(re.finditer(r"(?m)^([A-Z]+-\d+)#(\d+)\s+(Warning|Critical Warning|Error)\s*$",text))
    require(len(heads)==7,"new DRC warning details are missing or duplicated")
    found=Counter()
    for idx,h in enumerate(heads):
        code,number,severity=h.group(1),int(h.group(2)),h.group(3)
        require(code in DRC_PROFILE and severity=="Warning" and
                1<=number<=DRC_PROFILE[code][0],
                "nonvendor/fatal/new K26 warning instance")
        found[(code,number)]+=1
        section=text[h.end():heads[idx+1].start() if idx+1<len(heads) else len(text)]
        require(section.count("Related violations: <none>")==1 and
                DRC_PROFILE[code][1] in section,
                "original vendor DRC warning body changed")
        if code=="PDCN-1569":
            pin,cell,leaf,equation=LUT_PINS[number]
            require("Used physical LUT pin "+pin+" of cell "+VENDOR_DBG+
                    "SWITCH_N_EXT_BSCAN." in section and
                    cell+" (pin "+VENDOR_DBG+"SWITCH_N_EXT_BSCAN." in section and
                    "/"+leaf+") is not included in the LUT equation: "+equation in section,
                    "unexpected debug-hub LUT pin/equation warning")
            require(section.count("Used physical LUT pin ")==1,
                    "duplicate debug hub pin warning")
        elif code in ("REQP-1857","REQP-1858"):
            fifo,primitive=RAM_NAMES[code,number]
            require(section.count("BRAM (")==1 and
                    "BRAM ("+VENDOR_AXI+fifo+"/" in section and
                    primitive+")" in section and
                    "SDP mode with WRITE_FIRST write-mode" in section and
                    "address collisions" in section,
                    "new LIF memory or unexpected vendor BRAM collision advisory")
        else:
            require(code=="RTSTAT-10" and
                    re.search(r"(?m)^\s*39 net\(s\) have no routable loads\.",section) and
                    "(the first 15 of 37 listed)" in section,
                    "new original JTAG routing-load warning changed")
            m=re.search(r"problem bus\(es\) and/or net\(s\) are (.*?)\s*"
                        r"\(the first 15 of 37 listed\)",section,re.S)
            require(m is not None,"new vendor route-load sample missing")
            sampled=[x.strip() for x in m.group(1).split(",") if x.strip()]
            require(len(sampled)==15 and all(x.startswith((VENDOR_DBG,VENDOR_AXI))
                                             for x in sampled),
                    "new non-vendor unrouted net or different samples")
    require(found==Counter({(code,n):1 for code,(count,_) in DRC_PROFILE.items()
                            for n in range(1,count+1)}),
            "original seven vendor debug/JTAG warning instances differ")
    return {"original_drc_warning_instances":7,
            "original_drc_critical_warnings":0,"original_drc_errors":0,
            "owner_accepted_vendor_warning_classes":sorted(DRC_PROFILE)}

def inspect(run:Path)->dict:
    require(run.name==OWNER and
            run.parent==(Path.home()/"Thesis_Evidence"/"M08") and
            run.is_dir() and not run.is_symlink(),
            "only the original QFKpXlPW owner-native folder may be released")
    require(not (run/"reports").is_symlink() and
            not (run/"bitstream_candidate").is_symlink(),
            "symlinked owner-original report/image folder")
    first=native.inspect(run)  # SHA of all 15 originals AND current five sources
    require(first["original_15_sha_entries_verified"] and
            first["source_sha_current_exact"] and
            first["candidate_bitstream_sha256"]==ORIGINAL[BIT][0],
            "first-original native receipts or source did not verify")
    data={k:original_bytes(run,k) for k in ORIGINAL}
    meta_lines=data["reports/30_native_result.txt"].decode("ascii").splitlines()
    rows=[line.split("=",1) for line in meta_lines]
    require(all(len(r)==2 for r in rows) and len(dict(rows))==len(rows),
            "duplicate/malformed first-original K26 native metadata")
    metadata=dict(rows)
    expected={
        "schema":"m08-paged-m06-32-signed16-one-resident-offline-build-v1",
        "wrapper_top":WRAPPER,
        "neural_mode":"SIGNED16_32_NEURON_4_TICK_5_EDGE_PAGED_LIF",
        "logical_neuron_pages":"6","resident_neuron_pages":"1",
        "neuron_state_page_bytes":"256","physical_page_memory_banks":"1",
        "max_neurons_per_resident_bank":"6",
        "m06_original_edges":"5","m06_original_external_events":"17",
        "external_input_ingress":"HOST_COALESCED_NO_RAW_EVENT_FIFO_IN_THIS_IMAGE",
        "recurrent_delivery":"PL_COMPUTED_FROM_GLOBAL_PRIOR_SPIKE_HISTORY",
        "neural_page_dispatches_per_32x4_workload":"24",
        "physical_m06_hls_core":"NO","physical_m06_ddr":"NO",
        "kernel_owned_dma_buffer":"NO",
        "new_image_owner_drc_review":"REQUIRED",
        "physical_jtag_test_authorized":"NO",
        "hardware_bitstream_programmed":"NO",
        "hardware_neural_execution_proven":"NO",
        "vivado_version":"2025.2",
        "part":"xck26-sfvc784-2LV-c",
        "board_part":"xilinx.com:kv260_som:part0:1.4",
        "ps_to_pl_hpm":"DISABLED","jtag_axi":"ENABLED_PL",
        "ps_pl0_clock_request_hz":"100000000",
        "ps_pl0_runtime_clock_proven":"NO",
        "bram_map_base":"0xA0000000","bram_map_range":"0x00001000",
        "lif_base":"0xA0001000","lif_map_range":"0x00001000",
        "reset_mode":"FABRIC_POR_256_CYCLES","ps_reset_dependency":"NO",
        "fan_route":"TTC0_WAVEOUT2_TO_A12",
        "bitstream_size_bytes":str(ORIGINAL[BIT][1]),
    }
    for key,value in expected.items():
        require(metadata.get(key)==value,"original image metadata wrong: "+key)
    require((run/"02_vivado_exit.txt").read_text().strip()=="vivado_build_exit=0",
            "first-original Vivado return code not zero")
    log=(run/"00_vivado.log").read_text(encoding="utf-8",errors="replace")
    require("M08_PAGED_M06_NEURAL_OFFLINE_BITSTREAM_CREATED_OWNER_DRC_REVIEW_REQUIRED_NOT_PROGRAMMED" in log,
            "original first-route bit generation completion marker missing")
    require(not any(line.startswith(("ERROR:","CRITICAL WARNING:"))
                    for line in log.splitlines()),
            "original routed Vivado build had fatal/critical diagnostics")
    drc=inspect_drc(data["reports/20_route_drc.rpt"].decode("utf-8"))
    timing_data=data["reports/21_route_timing.rpt"].decode("utf-8")
    for term in ("Vivado v.2025.2 (lin64)","Design            : "+WRAPPER,
                 "Design State      : Routed",
                 "LUTAR-1  Warning   LUT drives async reset alert  5",
                 "0 pins that are not constrained for maximum delay",
                 "All user specified timing constraints are met."):
        require(term in timing_data,"first owner timing/methodology text changed: "+term)
    timing=vendor.inspect_timing(timing_data)
    require(timing["wns_ns"]==0.763 and timing["tns_ns"]==0.0 and
            timing["whs_ns"]==0.010 and timing["ths_ns"]==0.0,
            "first original slack differs from owner reviewed timing")
    summary=re.search(r"(?m)^\s*0\.763\s+0\.000\s+0\s+26211\s+0\.010\s+0\.000\s+0\s+26147\s+4\.238\s+0\.000\s+0\s+9082\s*$",timing_data)
    require(summary is not None,"original setup/hold/pulse-width endpoint count changed")
    clocks=data["reports/23_route_clocks.rpt"].decode("utf-8")
    require("Vivado v.2025.2 (lin64)" in clocks and
            "Design            : "+WRAPPER in clocks and
            "Design State      : Routed" in clocks and
            "xck26-sfvc784" in clocks and
            re.search(r"(?m)^clk_pl_0\s+10\.000\s+\{0\.000 5\.000\}\s+P\s+\{.*?/PLCLK\[0\]\}\s*$",clocks) and
            re.search(r"(?m)^clk_pl_1\s+10\.000\s+\{0\.000 5\.000\}\s+P\s+\{.*?/PLCLK\[1\]\}\s*$",clocks) and
            "INTERNAL_TCK  50.000" in clocks,
            "original PL0/PL1/debug clock does not match reviewed native report")
    return {
        "status":"M08_4_EXACT_FIRST_OWNER_NATIVE_NEW_IMAGE_ACCEPTED_BOUNDED_JTAG_ONLY",
        "image_specific_gate":"ACCEPTED",
        "original_15_sha_entries_verified":True,
        "source_sha_current_exact":True,
        "owner_bit_sha256":ORIGINAL[BIT][0],
        "owner_bit_bytes":ORIGINAL[BIT][1],
        "original_report_sha256":{k:v[0] for k,v in ORIGINAL.items()},
        **drc,**timing,
        "pulse_width_worst_ns":4.238,
        "methodology_LUTAR_1_async_reset_warnings":5,
        "methodology_warning_cells_untraced":True,
        "owner_explicitly_accepts_remaining_first_physical_risk":True,
        "JTAG_one_shot_programming_permitted_after_independent_preflight":True,
        "physical_programmed":False,
        "physical_neural_results_proven":False,
        "DDR_or_raw_event_fifo_proven":False,
    }

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir",type=Path,required=True)
    args=p.parse_args()
    try:
        result=inspect(args.run_dir)
        print(json.dumps(result,indent=2,sort_keys=True))
        print("M08_4_EXACT_FIRST_OWNER_NEW_IMAGE_REVIEWED_BOUNDED_JTAG_ALLOWED_WITH_PREFLIGHT")
        return 0
    except (Reject,native.Reject,vendor.Reject,ValueError,OSError,KeyError,UnicodeError) as exc:
        print("M08_4_EXACT_NATIVE_FIRST_IMAGE_REJECTED: "+str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
