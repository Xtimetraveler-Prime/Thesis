#!/usr/bin/env python3
"""EXACT first-original D3.D.2E M32Q native image acceptance; READ ONLY.

Owner supplied full original seven-warning DRC, bit SHA, timing and clock
summaries on 2026-11-20. Check original 12-file SHA receipt, *current source*
and exact image, every original warning, true route slack and clock constraints.
This program NEVER opens JTAG or programs a board. Physical owner preflight
and explicit one-shot consent are still separate.
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
import m08_d3d2e_queue_native_review as first
import m08_d3d2e_queue_gate as source_gate
import m08_d3c_jtag_bram_gate as vendor

OWNER_NATIVE_DIR="m08_d3d2e_queue_GFz0SbiC"
OWNER_BIT_SHA="2c443c3d80e86e5e9488b457110a45b0db96881016e9f87a5c801a72ec7527dc"
OWNER_BIT_BYTES=7797844
OWNER_DRC_SHA="3c4c1d8bd304dc71eb4f21bddee7a9c35cbf2053857a805c097bc2e96f0157c6"
OWNER_TIMING_SHA="cdeaf520fbbb944de4148cecca290651125c3009a2375966ee2b5d17f584c59f"
OWNER_CLOCKS_SHA="836479b2faf87c71df2f50b9b19128d4b6ba7e9ac6dd72a41a6f42383ae43820"
WRAPPER="m08_d3d2e_queue_lif_jtag_wrapper"
JTAG_ROOT="m08_d3d2e_queue_lif_jtag_i/jtag_axi/inst/jtag_axi_engine_u/"
DEBUG_ROOT="dbg_hub/inst/BSCANID.u_xsdbm_id/"
DEBUG_SWITCH=DEBUG_ROOT+"SWITCH_N_EXT_BSCAN."
DRC_PATH="/home/dna/Thesis_Evidence/M08/"+OWNER_NATIVE_DIR+"/reports/20_route_drc.rpt"
PROFILE={
    "PDCN-1569":(3,"LUT equation term check"),
    "REQP-1857":(1,"RAMB18E2_writefirst_collision_advisory"),
    "REQP-1858":(2,"RAMB36E2_writefirst_collision_advisory"),
    "RTSTAT-10":(1,"No routable loads"),
}
LUTS={
    1:("'A1'","bscan_switch/temp_curid[31]_i_1","I0",
       "'O5=(A5*A3)+(A5*(~A3)*(~A4))+((~A5))'"),
    2:("'A2'","bscan_switch/temp_curid[31]_i_1","I1",
       "'O5=(A5*A3)+(A5*(~A3)*(~A4))+((~A5))'"),
    3:("'A3'","id_state[0]_i_1","I0",
       "'O6=(A6+~A6)*((A1))'"),
}
RAM_FIFOS={
    ("REQP-1857",1):("rx_fifo_i","WIDE_PRIM18.ram"),
    ("REQP-1858",1):("rd_cmd_fifo_i","WIDE_PRIM36_NO_ECC.ram"),
    ("REQP-1858",2):("wr_cmd_fifo_i","WIDE_PRIM36_NO_ECC.ram"),
}
RF_SUFFIX="/inst_fifo_gen/gconvfifo.rf/grf.rf/gntv_or_sync_fifo.gl0.rd/gr1.gr1_int.rfwft/"
RTSTAT_SAMPLE=(
    DEBUG_ROOT+"CORE_XSDB.UUT_MASTER/U_ICON_INTERFACE/U_CMD1/ctl_reg_en_2[1]",
    DEBUG_ROOT+"CORE_XSDB.UUT_MASTER/U_ICON_INTERFACE/U_CMD6_RD/U_RD_FIFO/SUBCORE_FIFO.xsdbm_v3_0_5_rdfifo_inst"+RF_SUFFIX+"aempty_fwft_i",
    DEBUG_ROOT+"CORE_XSDB.UUT_MASTER/U_ICON_INTERFACE/U_CMD7_CTL/ctl_reg[2:0]",
    DEBUG_ROOT+"CORE_XSDB.UUT_MASTER/U_ICON_INTERFACE/U_CMD7_CTL/ctl_reg_en_2[1]",
    DEBUG_SWITCH+"bscan_inst/TMS",
    DEBUG_SWITCH+"bscan_switch/m_bscan_capture[0]",
    DEBUG_SWITCH+"bscan_switch/m_bscan_drck[0]",
    JTAG_ROOT+"rd_cmd_fifo_i"+RF_SUFFIX+"aempty_fwft_i",
    JTAG_ROOT+"rd_cmd_fifo_i"+RF_SUFFIX+"empty_fwft_i",
    JTAG_ROOT+"rx_fifo_i"+RF_SUFFIX+"aempty_fwft_i",
    JTAG_ROOT+"rx_fifo_i"+RF_SUFFIX+"empty_fwft_i",
    JTAG_ROOT+"tx_fifo_i"+RF_SUFFIX+"aempty_fwft_i",
    JTAG_ROOT+"tx_fifo_i"+RF_SUFFIX+"empty_fwft_i",
    JTAG_ROOT+"wr_cmd_fifo_i"+RF_SUFFIX+"aempty_fwft_i",
    JTAG_ROOT+"wr_cmd_fifo_i"+RF_SUFFIX+"empty_fwft_i",
)

class Reject(ValueError):
    pass

def require(ok: bool, reason: str) -> None:
    if not ok:
        raise Reject(reason)

def read(p: Path, limit: int=12_000_000) -> bytes:
    require(p.is_file() and not p.is_symlink(),"missing/symlink exact native original "+str(p))
    require(0 < p.stat().st_size <= limit,"empty/oversize exact native original "+str(p))
    return p.read_bytes()

def inspect_drc(report: str) -> dict:
    """Classify exactly the seven individually reviewed first-original warnings.

    Original report SHA is separately required in inspect(); the XSDB and
    JTAG/AXI advisory classification does NOT prove collision-free RAM traffic.
    """
    for term in (
        "Vivado v.2025.2 (lin64)",
        "Date         : Fri Nov 20 16:34:33 2026",
        "Command      : report_drc -file "+DRC_PATH,
        "Design       : "+WRAPPER,
        "Device       : xck26-sfvc784-2LV-c",
        "Design State : Fully Routed",
    ):
        require(term in report,"original D3.D.2E DRC provenance changed: "+term)
    require(re.findall(r"(?m)^\s*Checks found:\s*(\d+)\s*$",report)==["7"],
            "first original routed DRC must have exactly seven checks")
    rows=re.findall(r"(?m)^\|\s*([A-Z]+-\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*(\d+)\s*\|$",report)
    require(len(rows)==4 and
            {(code,sev.strip(),description.strip(),int(num))
             for code,sev,description,num in rows}==
            {(code,"Warning",description,count)
             for code,(count,description) in PROFILE.items()},
            "new/altered warning class, severity or count")
    heads=list(re.finditer(r"(?m)^([A-Z]+-\d+)#(\d+)\s+(Warning|Critical Warning|Error)\s*$",report))
    require(len(heads)==7,"unreviewed/duplicated/missing DRC warning details")
    found=Counter()
    for i,m in enumerate(heads):
        code,num,sev=m.group(1),int(m.group(2)),m.group(3)
        require(code in PROFILE and sev=="Warning" and
                1<=num<=PROFILE[code][0],
                "unreviewed DRC warning severity/ordinal/hierarchy")
        found[(code,num)]+=1
        body=report[m.end():heads[i+1].start() if i+1<len(heads) else len(report)]
        require(body.count("Related violations: <none>")==1 and
                PROFILE[code][1] in body,
                "DRC warning body/related violations changed")
        if code=="PDCN-1569":
            pin,suffix,endpoint,equation=LUTS[num]
            cell=DEBUG_SWITCH+suffix
            expected=(f"Used physical LUT pin {pin} of cell {cell} "
                      f"(pin {cell}/{endpoint}) is not included in the LUT equation: "
                      +equation)
            require(expected in body and body.count("of cell ")==1 and
                    body.count("is not included in the LUT equation: ")==1,
                    "new M32Q LUT pin, equation or owner debug hierarchy")
        elif code in ("REQP-1857","REQP-1858"):
            fifo,primitive=RAM_FIFOS[(code,num)]
            require(body.count("BRAM (")==1 and
                    body.count("BRAM ("+JTAG_ROOT+fifo+"/")==1 and
                    body.count(primitive+")")==1 and
                    "SDP mode with WRITE_FIRST write-mode" in body and
                    "address collisions" in body,
                    "new non-vendor BRAM/collision warning instance")
        else:
            require(code=="RTSTAT-10" and num==1 and
                    re.search(r"(?m)^\s*39 net\(s\) have no routable loads\.",body) and
                    "(the first 15 of 37 listed)" in body,
                    "RTSTAT count/sample changed")
            m2=re.search(r"problem bus\(es\) and/or net\(s\) are (.*?)\s*"
                         r"\(the first 15 of 37 listed\)",body,re.S)
            require(m2 is not None,"missing original 15 RTSTAT printed net paths")
            sample=tuple(p.strip() for p in m2.group(1).split(",") if p.strip())
            require(sample==RTSTAT_SAMPLE,
                    "RTSTAT sampled net path differs from original reviewed vendor-only 15")
    require(found==Counter({(code,i):1 for code,(n,_) in PROFILE.items()
                             for i in range(1,n+1)}),
            "original seven individual vendor warning instances differ")
    return {"original_drc_checks":7,"reviewed_vendor_warnings":7,
            "rtstat_no_routable_loads":39,"rtstat_sampled_vendor_paths":15,
            "drc_review_status":"EXACT_D3D2E_FIRST_ORIGINAL_SEVEN_VENDOR_DEBUG_JTAG_WARNINGS"}

def inspect(run: Path) -> dict:
    # IMPORTANT: no JTAG, no owner-original mutations, no source substitution.
    require(run.name==OWNER_NATIVE_DIR and
            run.parent==Path.home()/"Thesis_Evidence"/"M08" and
            not run.is_symlink(),"not the exact first original owner M32Q candidate")
    require(not (run/"reports").is_symlink() and
            not (run/"bitstream_candidate").is_symlink(),
            "symlinked owner native evidence subdirectory")
    try:
        first_result=first.inspect(run)  # verifies original 12 receipts + current builder/RTL/POR
        source_gate.source()            # original M02/M03 neural and queue source identity
    except (first.Reject,source_gate.Reject) as exc:
        raise Reject("first original SHA/source check failed: "+str(exc)) from exc
    require(first_result.get("sha_ledger_rows_verified")==12,
            "first original 12 SHA receipts missing")
    bit=read(run/first.BIT,100_000_000)
    bit_digest=sha256(bit).hexdigest()
    require(bit_digest==OWNER_BIT_SHA and len(bit)==OWNER_BIT_BYTES and
            first_result["new_original_candidate_sha256"]==bit_digest,
            "not the first owner original M32Q bitstream")
    d=read(run/"reports/20_route_drc.rpt",3_000_000)
    t=read(run/"reports/21_route_timing.rpt",3_000_000)
    c=read(run/"reports/23_route_clocks.rpt",3_000_000)
    require(sha256(d).hexdigest()==OWNER_DRC_SHA,"first-original DRC SHA mismatch")
    require(sha256(t).hexdigest()==OWNER_TIMING_SHA,"first-original timing SHA mismatch")
    require(sha256(c).hexdigest()==OWNER_CLOCKS_SHA,"first-original clock SHA mismatch")
    reviewed=inspect_drc(d.decode("utf-8"))
    try:
        timing=vendor.inspect_timing(t.decode("utf-8"))
    except (vendor.Reject,ValueError) as exc:
        raise Reject("new owner routed timing has no accepted 100MHz closure: "+str(exc)) from exc
    require(timing["wns_ns"]==1.844 and timing["tns_ns"]==0.0 and
            timing["whs_ns"]==0.010 and timing["ths_ns"]==0.0,
            "first-original timing numbers differ from owner reported 100MHz route")
    clocks=c.decode("utf-8")
    require("Design            : "+WRAPPER in clocks and
            "Design State      : Routed" in clocks and
            "xck26-sfvc784" in clocks and
            re.search(r"(?m)^clk_pl_0\s+10\.000\s+\{0\.000 5\.000\}\s+P\s+\{.*?/PLCLK\[0\]\}\s*$",clocks) and
            re.search(r"(?m)^clk_pl_1\s+10\.000\s+\{0\.000 5\.000\}\s+P\s+\{.*?/PLCLK\[1\]\}\s*$",clocks) and
            "INTERNAL_TCK  50.000" in clocks,
            "first-original PL0/PL1/debug clock report not accepted")
    original_log=read(run/"00_vivado.log")
    require(b"M08_D3D2E_JTAG_BRAM_OFFLINE_BITSTREAM_CREATED_NOT_PROGRAMMED" in original_log,
            "original first Vivado build-success marker absent")
    require(not any(line.startswith((b"ERROR:",b"CRITICAL WARNING:"))
                    for line in original_log.splitlines()),
            "original Vivado log has fatal error/critical warning")
    metadata=dict(line.split("=",1) for line in
                  read(run/"reports/30_native_result.txt",15000).decode("ascii").splitlines())
    expected_meta={
        "board_part":"xilinx.com:kv260_som:part0:1.4",
        "neural_mode":"THIRTY_TWO_NEURON_M06_TICK_QUEUED_17_EVENT_SERVICE_3_4_SIGNED16",
        "decay_modes":"ZERO_HALF_ONE_THREE_QUARTERS",
        "m06_original_individual_external_events":"17",
        "external_event_coalescing":"FPGA_FIFO_TICK_SERVICE_ONLY",
        "event_service_clock":"PS_REQUESTED_PL0_100MHZ",
        "hardware_signed_event_accumulation":"AFTER_TICK_SERVICE",
        "edge_capacity":"8",
        "jtag_axi":"ENABLED_PL",
        "bram_map_range":"0x00001000","lif_map_range":"0x00001000",
        "bram_depth_words":"1024","bram_width_bits":"32",
        "bram_controller_derived_depth":"1024","test_window_bytes":"4096",
        "fan_route":"TTC0_WAVEOUT2_TO_A12",
        "ps_reset_dependency":"NO",
        "linux_management_compatibility":"NOT_PROVEN",
        "hardware_jtag_axil_readback_proven":"NO",
        "hardware_lif_readback_proven":"NO",
    }
    for key,value in expected_meta.items():
        require(metadata.get(key)==value,"first-original M32Q metadata differs: "+key)
    return dict(
        status="M08_D3D2E_EXACT_OWNER_NATIVE_TICKQUEUE_IMAGE_ACCEPTED_NO_BOARD",
        image_specific_gate="ACCEPTED",
        candidate_sha256=bit_digest,
        candidate_bytes=len(bit),
        original_12_sha_entries_verified=True,
        original_drc_sha256=OWNER_DRC_SHA,
        original_timing_sha256=OWNER_TIMING_SHA,
        original_clock_sha256=OWNER_CLOCKS_SHA,
        physical_programmed=False,
        physical_neural_parity_verified=False,
        fifo_service_physically_verified=False,
        async_clock_or_streaming_proven=False,
        **reviewed, **timing
    )

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir",type=Path,required=True)
    a=parser.parse_args()
    try:
        result=inspect(a.run_dir)
        print(json.dumps(result,sort_keys=True,indent=2))
        print("M08_D3D2E_EXACT_OWNER_FIRST_ORIGINAL_NATIVE_IMAGE_ACCEPTED_NO_BOARD")
        return 0
    except (Reject,first.Reject,source_gate.Reject,ValueError,OSError,UnicodeError,KeyError) as exc:
        print("M08_D3D2E_EXACT_NATIVE_REVIEW_REJECTED: "+str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
