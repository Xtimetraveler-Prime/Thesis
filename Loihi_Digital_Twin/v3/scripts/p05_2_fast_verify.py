#!/usr/bin/env python3
"""P05.2b physical FAST/no-checkpoint equivalence verifier.

The independent model and the already-accepted P05.1 diagnostic
physical output must have identical final full-record SHA256 to
new physical fast-mode DDR dumps. All dynamic neural inputs, per-core
context, accepted routing and operational counts remain unchanged.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT=Path(__file__).resolve().parents[1]
SRC=str(ROOT/"src")
if SRC in sys.path:sys.path.remove(SRC)
sys.path.insert(0,SRC)


def load(name:str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P05R=load("p05_2b_mailbox",ROOT/"scripts/p05_1_verify.py")
TRI=load("p05_2b_oracle",ROOT/"scripts/p05_1_triangle_fixture.py")
PROFILE="p05-2-fast-no-checkpoints-triangle-v1"


def verify(mailbox:Path,folder:Path)->bool:
    try:
        raw=mailbox.read_bytes()
        if len(raw)!=256:raise ValueError("P05R mailbox length must be 256")
        r=struct.unpack("<64I",raw)
        data=dict(zip(P05R.FIELDS,r))
        artifacts=folder/"p05_artifacts"
        golden=folder/"triangle_golden"
        gate=json.loads((folder/"p05_2_fast_gate.json").read_text())
        model=json.loads((golden/"manifest.json").read_text())
        diag_gate=json.loads((folder/"triangle_gate.json").read_text())
        info=json.loads((artifacts/"p05_manifest.json").read_text())
        fast_spec=json.loads((folder/"p05_2_fast_spec.json").read_text())
        diag_spec=json.loads((folder/"triangle_spec.json").read_text())
        head=(artifacts/"p05_header.bin").read_bytes()
        payload=(artifacts/"p05_payload.bin").read_bytes()
        diag_head=(folder/"p05_diag_reference_header.bin").read_bytes()
        diag_payload=(folder/"p05_diag_reference_payload.bin").read_bytes()
        h=struct.unpack("<64I",head)
        dh=struct.unpack("<64I",diag_head)
        if (gate["profile"],gate["neural_reference_profile"])!=(
            PROFILE,TRI.PROFILE):
            raise ValueError("incorrect fast-mode profile identity")
        if (h[0],h[1],h[2],h[3],h[4],h[5],
            h[6],h[13],h[14],h[20])!=(
            0x47353050,1,256,0,5,3,3,15,0,15):
            raise ValueError("P05 fast descriptor is not no-checkpoint triangle")
        if (dh[0],dh[1],dh[3],dh[4],dh[5],dh[13],dh[14])!=(
            0x47353050,1,1,5,3,15,15):
            raise ValueError("diagnostic reference descriptor drift")
        if h[12]!=len(payload) or h[12]>0xE0000:
            raise ValueError("fast payload size invalid")
        if h[22]!=zlib.crc32(payload) or (
            h[23]!=zlib.crc32(head[:92]+bytes(4)+head[96:])):
            raise ValueError("fast header/payload CRC mismatch")
        if dh[22]!=zlib.crc32(diag_payload) or (
            dh[23]!=zlib.crc32(diag_head[:92]+bytes(4)+diag_head[96:])):
            raise ValueError("diagnostic ABI reference CRC mismatch")
        if (h[17],h[18])!=(dh[17],dh[18]) or payload!=diag_payload[:dh[18]]:
            raise ValueError("fast mode differs in exact core/event payload bytes")
        if any(fast_spec[k]!=diag_spec[k] for k in (
            "schema","timesteps","slot_count","cores","events"
        )) or (fast_spec["mode"]!="fast" or fast_spec["checkpoints"]!=[]
                or diag_spec["mode"]!="diagnostic"
                or len(diag_spec["checkpoints"])!=15):
            raise ValueError("fast and diagnostic neural stimuli differ")
        if (info["header_sha256"]!=hashlib.sha256(head).hexdigest() or
            info["payload_sha256"]!=hashlib.sha256(payload).hexdigest() or
            info["input_spec_sha256"]!=hashlib.sha256(
                (folder/"p05_2_fast_spec.json").read_bytes()).hexdigest()):
            raise ValueError("fast generated manifest sha drift")
        if (gate["fast_header_sha256"]!=info["header_sha256"] or
            gate["fast_payload_sha256"]!=info["payload_sha256"] or
            gate["fast_spec_sha256"]!=info["input_spec_sha256"] or
            gate["frozen_diagnostic_reference_header_sha256"]!=
                hashlib.sha256(diag_head).hexdigest() or
            gate["frozen_diagnostic_reference_payload_sha256"]!=
                hashlib.sha256(diag_payload).hexdigest()):
            raise ValueError("fast/diagnostic staged SHA identity drift")
        if (model["logical_core_ids"],model["dispatch_count"],
            model["expected_packet_count_total"])!=([0,1,2],15,12):
            raise ValueError("original independent neural oracle changed")
        if (diag_gate["oracle_trace_sha256"]!=model["trace_fingerprint"] or
            gate["reference_golden_trace_sha256"]!=model["trace_fingerprint"]):
            raise ValueError("independent model trace identity drift")
        for core in range(3):
            record=(artifacts/f"core{core}_initial.bin").read_bytes()
            original=(golden/f"core{core}_initial.bin").read_bytes()
            if len(record)!=0x80000 or record!=original:
                raise ValueError(f"fast core {core} neural record changed")
            row=struct.unpack_from("<8I",payload,core*32)
            if (row[0]!=core or row[4]!=zlib.crc32(record) or
                row[5]!=10+core):
                raise ValueError(f"fast core {core} descriptor mismatch")
        for idx in range(15):
            row=struct.unpack_from("<4I",payload,h[17]+idx*16)
            if row!=(idx//3,idx%3,10+idx%3,0):
                raise ValueError(f"fast external input {idx} not model stimulus")
        assert gate["expected_checkpoints"]==0
        assert gate["accepted_prior_physical_final_ddr_sha256"]
    except (OSError,ValueError,AssertionError,KeyError,TypeError,struct.error) as e:
        print("FAIL: P05.2 fast evidence admission: "+str(e),file=sys.stderr)
        return False

    want={
        "magic":0x52353050,"version":1,
        "result":0x600D600D,"error":0,
        "steps":5,"completed_steps":5,"cores":3,"slots":3,
        "phase":18,"fault":0,"fault_phase":0,
        "dispatches":15,"packets":12,"barriers":5,
        "initial_ins":3,"replacement_ins":0,"runtime_outs":0,
        "final_outs":3,"evictions":0,"hits":15,
        "hw_id":0x4C543302,"hw_caps":0x0001031F,
        "hw_dispatches":15,"hw_pages":6,
        "hw_last_page_bytes":106496,"hw_status":0,
        "hw_pending_bytes":0,"resident_deliveries":12,
        "inputs_consumed":15,"checkpoints_passed":0,
        "failed_step":0,"failed_core":0,"failed_class":0,
        "expected_crc":0,"observed_crc":0,
        "header_crc":h[23],"payload_crc":h[22],
        "diagnostic_mode":0,"expected_events":15,
        "expected_checks":0,"expected_dispatches":15,
        "diag_flags":0,"last_page_error":0,
    }
    errors=[]
    for k,v in want.items():
        if data[k]!=v:
            errors.append(f"{k}: actual 0x{data[k]:08X} expected 0x{v:08X}")
    if r[60:]!=(0,0,0,0):
        errors.append("reserved mailbox words nonzero")
    for k in ("cntfrq_hz","hw_read_bursts","hw_write_bursts"):
        if data[k]==0:errors.append(k+" unexpectedly zero")
    for lo,hi in (
        ("pl_dispatch_lo","pl_dispatch_hi"),
        ("pl_page_lo","pl_page_hi"),
        ("ps_infer_lo","ps_infer_hi"),
    ):
        if data[lo]|data[hi]==0:
            errors.append(lo+" / "+hi+" unexpectedly zero")
    records=None
    ddr_error=None
    try:
        oracle=TRI.oracle_module()
        records=oracle.verify(golden,folder/"final_ddr")
        accepted=gate["accepted_prior_physical_final_ddr_sha256"]
        for cid in (0,1,2):
            observed=records["records"][str(cid)]["sha256"]
            if observed!=accepted[str(cid)]:
                errors.append(
                    f"core {cid} fast mode final SHA differs from accepted"
                    f" diagnostic physical P05.1: {observed} vs {accepted[str(cid)]}"
                )
    except (OSError,AssertionError,ValueError) as e:
        ddr_error=str(e)
    if errors or ddr_error:
        for e in errors:print("FAIL: P05.2 fast mailbox/data "+e,file=sys.stderr)
        if ddr_error:
            print("P05_2_FAST_FINAL_DDR_COMPARISON=FAIL: "+ddr_error,file=sys.stderr)
        else:
            print("P05_2_FAST_FINAL_DDR_COMPARISON=PASS (mailbox or historical SHA still failed)",file=sys.stderr)
        if data["result"]!=0x600D600D:
            print("P05_2_FAST_FAILURE="+json.dumps({
                k:data[k] for k in (
                    "result","error","phase","fault","fault_phase",
                    "dispatches","packets","barriers","resident_deliveries",
                    "inputs_consumed","checkpoints_passed",
                )
            },sort_keys=True),file=sys.stderr)
        return False
    print(
        "PASS: P05.2 fast/no-checkpoint A53 triangle "
        "timesteps=5 dispatches=15 packets=12 "
        "resident_deliveries=12 barriers=5 events=15 checkpoints=0"
    )
    print("PASS: P05.2 fast mode three final 512KiB DDR records byte-exact to BOTH independent Python oracle and earlier physical diagnostic-mode KV260 SHA256s")
    print("P05_2_FAST_METADATA="+json.dumps({
        "model_trace_sha256":model["trace_fingerprint"],
        "header_crc32":f"0x{h[23]:08X}",
        "payload_crc32":f"0x{h[22]:08X}",
        "diag_observations":0,
        "record_sha256":{
            str(k):records["records"][str(k)]["sha256"]
            for k in range(3)
        },
        "pl_dispatch_cycles":data["pl_dispatch_lo"]|(
            data["pl_dispatch_hi"]<<32),
        "ps_inference_ticks":data["ps_infer_lo"]|(
            data["ps_infer_hi"]<<32),
        "timing_note":"Timing is only exploratory, not calibrated throughput or benchmark energy",
    },sort_keys=True))
    return True


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mailbox",required=True,type=Path)
    ap.add_argument("--directory",required=True,type=Path)
    args=ap.parse_args()
    return 0 if verify(args.mailbox,args.directory) else 1


if __name__=="__main__":
    raise SystemExit(main())
