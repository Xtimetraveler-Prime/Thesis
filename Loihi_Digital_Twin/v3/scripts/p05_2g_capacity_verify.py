#!/usr/bin/env python3
"""Strict P05.2g actual-KV260 4096-event success / 4097-event fail-closed verifier."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import zlib

ROOT=Path(__file__).resolve().parents[1]
SRC=str(ROOT/"src")
if SRC in sys.path:sys.path.remove(SRC)
sys.path.insert(0,SRC)
from p05_2g_capacity_fixture import full_model,digest,CAPACITY,OVER,AXON
from p05_2_composite_fixture import load
P05R=load("p05_2g_mailbox",ROOT/"scripts/p05_1_verify.py")
FIELDS=P05R.FIELDS

def physical_files(root:Path):
    mb=root/"p05_a53_result.bin"
    if not mb.exists() or len(mb.read_bytes())!=256:
        raise ValueError("missing real 256B A53 P05R terminal")
    d=dict(zip(FIELDS,struct.unpack("<64I",mb.read_bytes())))
    if tuple(struct.unpack("<4I",mb.read_bytes()[:16]))[:2]!=(0x52353050,1):
        raise ValueError("invalid physical A53 mailbox magic/version")
    if mb.read_bytes()[240:]!=bytes(16):
        raise ValueError("reserved A53 mailbox words are nonzero")
    actual=root/"final_ddr/core0_after.bin"
    if not actual.exists() or len(actual.read_bytes())!=0x80000:
        raise ValueError("missing original 512KiB physical DDR core0 dump")
    return d,actual

def provenance(root:Path):
    a=root/"p05_artifacts"
    h=(a/"p05_header.bin").read_bytes()
    payload=(a/"p05_payload.bin").read_bytes()
    w=struct.unpack("<64I",h)
    if (len(h)!=256 or w[12]!=len(payload) or
        w[12]>0xE0000 or w[22]!=zlib.crc32(payload) or
        w[23]!=zlib.crc32(h[:92]+bytes(4)+h[96:])):
        raise ValueError("P05G binary payload/header length/CRC")
    if (w[0],w[1],w[2],w[3],w[4],w[5],w[6],
        w[13],w[14],w[20]) not in (
            (0x47353050,1,256,1,1,1,1,4096,3,1),
            (0x47353050,1,256,1,1,1,1,4097,3,1),
        ):
        raise ValueError("not an exact one-core capacity test P05G")
    if (w[17],w[18])!=(32,32+w[13]*16):
        raise ValueError("capacity event/checkpoint table not tightly packed")
    row=struct.unpack_from("<8I",payload,0)
    expected_meta=0|(1<<7)|(1<<18)
    if (row[0],row[1]|(row[2]<<32),row[5],row[6],row[7])!=(
        0,expected_meta,AXON,0,0):
        raise ValueError("unexpected full-bank deployment core metadata")
    init=(a/"core0_initial.bin").read_bytes()
    if (len(init)!=0x80000 or row[3]!=struct.unpack_from("<I",init,0x1000)[0]
        or row[4]!=zlib.crc32(init)):
        raise ValueError("initial staged DDR does not match P05G core descriptor")
    for i in range(w[13]):
        if struct.unpack_from("<4I",payload,w[17]+16*i)!=(0,0,AXON,0):
            raise ValueError(f"capacity event {i} is not sole registered axon")
    return w,h,payload,init

def verify_full(root:Path)->bool:
    try:
        d,actual=physical_files(root)
        w,header,payload,init=provenance(root)
        g=json.loads((root/"p05_2g_full_gate.json").read_text())
        man=json.loads((root/"p05_artifacts/p05_manifest.json").read_text())
        spec=json.loads((root/"p05_2g_full_spec.json").read_text())
        ref=json.loads((root/"capacity_golden/manifest.json").read_text())
        if ((w[13],w[14])!=(CAPACITY,3) or g["event_count"]!=CAPACITY or
            g["status"]!="MODEL_ONLY_NOT_HARDWARE_ACCEPTED"):
            raise ValueError("full bank limit/identity differs from frozen 4096 profile")
        if (man["header_sha256"]!=g["p05_header_sha256"]!=hashlib.sha256(header).hexdigest() or
            man["payload_sha256"]!=g["p05_payload_sha256"]!=hashlib.sha256(payload).hexdigest() or
            man["input_spec_sha256"]!=g["p05_input_spec_sha256"]!=hashlib.sha256(
                (root/"p05_2g_full_spec.json").read_bytes()).hexdigest()):
            raise ValueError("P05G full deployment fingerprint changed")
        if (spec["mode"]!="diagnostic" or len(spec["events"])!=4096 or
            [x["state_class"] for x in spec["checkpoints"]]!=[
                "state0","event0","event1"]):
            raise ValueError("expected three distinct physical barrier observations")
        if (g["model"]!=ref or
            g["model_manifest_sha256"]!=digest(root/"capacity_golden/manifest.json") or
            init!=(root/"capacity_golden/core0_initial.bin").read_bytes() or
            digest(root/"capacity_golden/core0_expected.bin")!=ref["final_record_sha256"]):
            raise ValueError("model golden record/manifest provenance mismatch")
        with tempfile.TemporaryDirectory(prefix="p05_2g_independent_regen_") as td:
            independently_recomputed=full_model(Path(td)/"regenerated")
            if independently_recomputed!=ref:
                raise ValueError("independent 4096-event regenerated model disagrees")
        for i,key in enumerate(("state0_crc","event0_word0_crc","event1_word0_crc")):
            row=struct.unpack_from("<4I",payload,w[18]+16*i)
            if row!=(0,0,i+1,int(ref[key],16)):
                raise ValueError(f"model hardware checkpoint table invalid {i}")
        want={
            "magic":0x52353050,"version":1,"result":0x600D600D,
            "error":0,"steps":1,"completed_steps":1,"cores":1,"slots":1,
            "phase":18,"fault":0,"fault_phase":0,"dispatches":1,
            "packets":0,"barriers":1,"initial_ins":1,"replacement_ins":0,
            "runtime_outs":0,"final_outs":1,"evictions":0,"hits":1,
            "resident_deliveries":0,"inputs_consumed":4096,"checkpoints_passed":3,
            "hw_id":0x4C543302,"hw_caps":0x0001031F,
            "hw_dispatches":1,"hw_pages":2,"hw_last_page_bytes":106496,
            "hw_status":0,"hw_pending_bytes":0,
            "failed_step":0,"failed_core":0,"failed_class":0,
            "expected_crc":0,"observed_crc":0,
            "header_crc":w[23],"payload_crc":w[22],
            "diagnostic_mode":1,"expected_events":4096,
            "expected_checks":3,"expected_dispatches":1,"diag_flags":0,
            "last_page_error":0,
        }
        for key,value in want.items():
            if d[key]!=value:
                raise ValueError(f"physical mailbox {key} 0x{d[key]:X} expected 0x{value:X}")
        for key in ("cntfrq_hz","hw_read_bursts","hw_write_bursts"):
            if d[key]<=0:raise ValueError(f"missing live physical {key}")
        for low,high in (("pl_dispatch_lo","pl_dispatch_hi"),
                         ("pl_page_lo","pl_page_hi"),
                         ("ps_infer_lo","ps_infer_hi")):
            if d[low]|d[high]==0:
                raise ValueError(f"missing physical timing {low}")
        frozen=(root/"capacity_golden/core0_expected.bin").read_bytes()
        output=actual.read_bytes()
        if output!=frozen:
            first=next(i for i,(a,b) in enumerate(zip(output,frozen)) if a!=b)
            raise ValueError(f"full 512KiB physical DDR mismatch at 0x{first:05X}: "
                             f"actual=0x{output[first]:02X} expected=0x{frozen[first]:02X}")
        if digest(actual)!=ref["final_record_sha256"]:
            raise ValueError("physical DDR full-record SHA drift")
    except (OSError,ValueError,AssertionError,KeyError,TypeError,struct.error) as e:
        print("FAIL: P05.2g 4096 FULL physical gate: "+str(e),file=sys.stderr)
        print("P05_2G_FULL_VERIFY_EXIT=1",file=sys.stderr)
        return False
    print("PASS: P05.2g exactly 4096 genuine FPGA CURRENT-bank input events, 1 dispatch, 1 barrier, 3/3 device checkpoints")
    print("PASS: P05.2g complete 512KiB real DDR record byte-exact to independent full-bank Python oracle")
    print("P05_2G_FULL_METADATA="+json.dumps({
        "physical_ddr_sha256":digest(actual),
        "p05_header_sha256":g["p05_header_sha256"],
        "p05_payload_sha256":g["p05_payload_sha256"],
    },sort_keys=True))
    print("P05_2G_FULL_VERIFY_EXIT=0")
    return True

def verify_overflow(root:Path)->bool:
    try:
        d,actual=physical_files(root)
        w,header,payload,init=provenance(root)
        g=json.loads((root/"p05_2g_overflow_gate.json").read_text())
        if ((w[13],w[14])!=(OVER,3) or
            g["profile"]!="p05-2g-crc-valid-4097-overflow-admission-v1" or
            g["expected_result"]!="0xDEAD0002"):
            raise ValueError("invalid CRC-valid overdepth negative test configuration")
        if (g["p05_header_sha256"]!=hashlib.sha256(header).hexdigest() or
            g["p05_payload_sha256"]!=hashlib.sha256(payload).hexdigest() or
            g["initial_record_sha256"]!=hashlib.sha256(init).hexdigest()):
            raise ValueError("overflow staged identity drift")
        # Exactly one extra event; remove it and independently reconstruct
        # the original legal header/payload to detect other modifications.
        original_payload=payload[:w[17]+CAPACITY*16]+payload[w[17]+OVER*16:]
        original_h=list(w)
        original_h[13]=CAPACITY
        original_h[12]-=16
        original_h[18]-=16
        original_h[22]=zlib.crc32(original_payload)
        original_h[23]=0
        original_h[23]=zlib.crc32(struct.pack("<64I",*original_h))
        if (hashlib.sha256(original_payload).hexdigest()!=
            g["clean_full_payload_sha256"] or
            hashlib.sha256(struct.pack("<64I",*original_h)).hexdigest()!=
            g["clean_full_header_sha256"]):
            raise ValueError("overflow test changes more than the single extra event")
        # The accepted standalone runner must refuse this P05G at its
        # first descriptor check, before MMIO width probe, page load or
        # neural dispatch. An unrelated failure is NEVER a PASS.
        expected={"magic":0x52353050,"version":1,
                  "result":0xDEAD0002,"error":2}
        for key,value in expected.items():
            if d[key]!=value:
                raise ValueError(f"wrong device rejection {key} 0x{d[key]:X}, wanted 0x{value:X}")
        for key in FIELDS[4:]:
            if d[key]!=0:
                raise ValueError(f"device touched runtime state before pre-admission reject: {key}=0x{d[key]:X}")
        if actual.read_bytes()!=init:
            raise ValueError("device overflow admission unexpectedly mutated source DDR context")
    except (OSError,ValueError,AssertionError,KeyError,TypeError,struct.error) as e:
        print("FAIL: P05.2g CRC-valid 4097 device rejection: "+str(e),file=sys.stderr)
        print("P05_2G_OVERFLOW_VERIFY_EXIT=1",file=sys.stderr)
        return False
    print("PASS: P05.2g CRC-valid 4097-event descriptor rejected by real A53 before MMIO/dispatch with 0xDEAD0002")
    print("PASS: P05.2g no dispatch/page/barrier and original full 512KiB device DDR record unchanged")
    print("P05_2G_OVERFLOW_VERIFY_EXIT=0")
    return True

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("full","overflow"),required=True)
    p.add_argument("--directory",type=Path,required=True)
    a=p.parse_args()
    root=a.directory.resolve()
    return 0 if (verify_full(root) if a.mode=="full" else verify_overflow(root)) else 1

if __name__=="__main__":
    raise SystemExit(main())
