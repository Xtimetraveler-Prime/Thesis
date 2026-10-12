#!/usr/bin/env python3
"""P05.2 physical negative-checkpoint gate: FAIL expected and verified.

An A53 ERROR is a *successful negative test* only when the deterministic
first-mismatch fields, earlier completed work, and the *independent* clean
neural oracle all match the planned deliberately wrong expected CRC.
Never accept an unrelated crash/failure, and never require final golden
DDR equality after an early stop with dirty resident contexts.
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
if SRC in sys.path:
    sys.path.remove(SRC)
sys.path.insert(0,SRC)


def load(name: str,path: Path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


FIELDS=load("p05_2_mailbox_contract",ROOT/"scripts/p05_1_verify.py").FIELDS
PROFILE="p05-2-expected-crc-first-mismatch-t2-core1-v1"


def verify(mailbox:Path,root:Path)->bool:
    try:
        blob=mailbox.read_bytes()
        if len(blob)!=256:
            raise ValueError("physical P05R mailbox must be 256B")
        w=struct.unpack("<64I",blob)
        d=dict(zip(FIELDS,w))
        gate=json.loads((root/"p05_2_fault_gate.json").read_text())
        clean=json.loads((root/"triangle_gate.json").read_text())
        original_spec=json.loads((root/"triangle_spec.json").read_text())
        corrupt_spec=json.loads((root/"p05_2_fault_spec.json").read_text())
        model=json.loads((root/"triangle_golden/manifest.json").read_text())
        art=root/"p05_artifacts"
        manifest=json.loads((art/"p05_manifest.json").read_text())
        header=(art/"p05_header.bin").read_bytes()
        payload=(art/"p05_payload.bin").read_bytes()
        words=struct.unpack("<64I",header)
        if gate["profile"]!=PROFILE:
            raise ValueError("incorrect negative-test profile")
        if (clean["expected_packets"],clean["logical_cores"],
            clean["expected_checkpoints"])!=(12,[0,1,2],15):
            raise ValueError("clean triangle reference drift")
        if (model["expected_packet_count_total"],model["dispatch_count"],
            model["trace_fingerprint"])!=(12,15,clean["oracle_trace_sha256"]):
            raise ValueError("neural model not independent triangle")
        if (words[0],words[1],words[3],words[4],words[5],
            words[6],words[13],words[14],words[20])!=(
            0x47353050,1,1,5,3,3,15,15,15):
            raise ValueError("P05 diagnostic descriptor wrong shape")
        if words[12]!=len(payload) or words[17]!=3*32 or (
            words[18]!=3*32+15*16):
            raise ValueError("P05 diagnostic descriptor wrong offsets")
        if words[22]!=zlib.crc32(payload) or (
            words[23]!=zlib.crc32(header[:92]+bytes(4)+header[96:])):
            raise ValueError("fault payload/header CRC does not match bytes")
        if (manifest["header_sha256"]!=hashlib.sha256(header).hexdigest() or
            manifest["payload_sha256"]!=hashlib.sha256(payload).hexdigest() or
            manifest["input_spec_sha256"]!=hashlib.sha256(
                (root/"p05_2_fault_spec.json").read_bytes()).hexdigest()):
            raise ValueError("fault manifest SHA does not match actual input")
        if (gate["p05_header_sha256"]!=manifest["header_sha256"] or
            gate["p05_payload_sha256"]!=manifest["payload_sha256"] or
            gate["p05_input_spec_sha256"]!=manifest["input_spec_sha256"]):
            raise ValueError("fault gate stage identity drift")
        if not (original_spec["schema"]=="p05-regression-deployment-v1" and
                original_spec["timesteps"]==5 and
                original_spec["slot_count"]==3 and
                original_spec["mode"]=="diagnostic" and
                len(original_spec["events"])==15 and
                len(original_spec["checkpoints"])==15):
            raise ValueError("clean reference deployment invalid")
        # Exactly one expected-checkpoint value is changed. ALL neural
        # events and core descriptors must remain byte-for-byte identical.
        baseline=dict(original_spec)
        mutation=dict(corrupt_spec)
        old=baseline.pop("checkpoints")
        new=mutation.pop("checkpoints")
        if mutation!=baseline or len(old)!=15 or len(new)!=15:
            raise ValueError("unexpected neural workload/stimulus mutation")
        altered=[]
        for i,(o,n) in enumerate(zip(old,new)):
            if o!=n:
                altered.append(i)
                if (set(o)!=set(n) or
                    (o["timestep"],o["core"],o["state_class"])!=(
                     n["timestep"],n["core"],n["state_class"])):
                    raise ValueError("invalid checkpoint selector change")
        if altered!=[7]:
            raise ValueError("must mutate ONLY checkpoint t=2/core=1")
        if (old[7]["timestep"],old[7]["core"],old[7]["state_class"])!=(
            2,1,"state0"):
            raise ValueError("unexpected diagnostic target")
        expected_model=int(old[7]["expected_crc32"],0)
        injected=expected_model^1
        if int(new[7]["expected_crc32"],0)!=injected:
            raise ValueError("negative CRC must flip exactly bit 0")
        for core in range(3):
            ref=(root/"triangle_golden"/f"core{core}_initial.bin").read_bytes()
            rec=(art/f"core{core}_initial.bin").read_bytes()
            if len(ref)!=0x80000 or rec!=ref:
                raise ValueError(f"neural backing record {core} was mutated")
            row=struct.unpack_from("<8I",payload,core*32)
            if row[0]!=core or row[4]!=zlib.crc32(ref) or row[5]!=10+core:
                raise ValueError(f"fault descriptor core {core} drift")
        for i in range(15):
            ev=struct.unpack_from("<4I",payload,words[17]+16*i)
            if ev!=(i//3,i%3,10+i%3,0):
                raise ValueError(f"external input row {i} changed")
            cp=struct.unpack_from("<4I",payload,words[18]+16*i)
            base_cp=old[i]
            base_crc=int(base_cp["expected_crc32"],0)
            if cp!=(i//3,i%3,1,base_crc^(1 if i==7 else 0)):
                raise ValueError(f"checkpoint {i} unexpected CRC")
        # Independently rederive the expected real state from the
        # reference per-dispatch mathematical model's Tcl vectors.
        states={}
        reading=False
        for s in (root/"triangle_golden/p02_4b_vectors.tcl").read_text().splitlines():
            s=s.strip()
            if s=="array set P02B_EXPECT_STATE {":
                reading=True;continue
            if reading and s=="}":break
            if reading:
                key,value=s.split()
                timestep,core=map(int,key.split(","))
                states[timestep,core]=int(value,0)
        if len(states)!=15:
            raise ValueError("oracle state checkpoint vector incomplete")
        measured_ideal=zlib.crc32(struct.pack("<Q",states[2,1]))
        if measured_ideal!=expected_model:
            raise ValueError("clean checkpoint CRC disagrees with model")
        if (gate["target_step"],gate["target_core"],
            gate["target_class"],gate["target_checkpoint_index"])!=(
            2,1,1,7):
            raise ValueError("negative gate target changed")
        if (gate["expected_bad_crc32"]!=f"0x{injected:08X}" or
            gate["expected_observed_crc32"]!=f"0x{expected_model:08X}"):
            raise ValueError("negative gate CRC identity changed")
    except (OSError,ValueError,KeyError,TypeError,struct.error) as e:
        print("FAIL: P05.2 negative evidence admission: "+str(e),file=sys.stderr)
        return False

    wants={
        "magic":0x52353050,"version":1,
        "result":0xDEAD000A,"error":10,
        "steps":5,"completed_steps":2,"cores":3,"slots":3,
        "phase":19,"fault":11,"fault_phase":13,
        "dispatches":9,"packets":6,"barriers":2,
        "initial_ins":3,"replacement_ins":0,"runtime_outs":0,
        "final_outs":0,"evictions":0,"hits":9,
        "resident_deliveries":6,"inputs_consumed":9,
        "checkpoints_passed":7,
        "failed_step":2,"failed_core":1,"failed_class":1,
        "expected_crc":injected,"observed_crc":expected_model,
        "header_crc":words[23],"payload_crc":words[22],
        "diagnostic_mode":1,"expected_events":15,
        "expected_checks":15,"expected_dispatches":15,
        "diag_flags":1,"last_page_error":0,
        "hw_id":0,"hw_caps":0,"hw_pages":0,"hw_dispatches":0,
    }
    issues=[]
    for name,want in wants.items():
        if d[name]!=want:
            issues.append(f"{name}: got 0x{d[name]:08X} expected 0x{want:08X}")
    if w[60:]!=(0,0,0,0):
        issues.append("reserved mailbox words not zero")
    for lo,hi in (("pl_dispatch_lo","pl_dispatch_hi"),
                  ("pl_page_lo","pl_page_hi")):
        if d[lo] | d[hi] == 0:
            issues.append(lo+" unexpectedly zero")
    if issues:
        for e in issues:
            print("FAIL: P05.2 first-mismatch mailbox "+e,file=sys.stderr)
        print("P05_2_NEGATIVE_DIAGNOSTIC="+json.dumps({
            k:d[k] for k in (
                "result","error","fault","fault_phase","phase",
                "completed_steps","dispatches","packets","barriers",
                "resident_deliveries","inputs_consumed",
                "checkpoints_passed","failed_step","failed_core",
                "failed_class","expected_crc","observed_crc","diag_flags",
            )
        },sort_keys=True),file=sys.stderr)
        return False
    print(
        "PASS: P05.2 deliberate bad checkpoint REJECTED by real A53 "
        "terminal=0xDEAD000A fault=11 fault_phase=13 "
        "first_mismatch_timestep=2 core=1 class=state0 "
        f"expected_bad_crc=0x{injected:08X} "
        f"observed_model_crc=0x{expected_model:08X} "
        "dispatches_before_stop=9 packets=6 resident_deliveries=6 "
        "completed_barriers=2 checkpoints_passed=7"
    )
    print("PASS: P05.2 prior real neural records/events unchanged; rejected only deliberately incorrect model expectation")
    print("P05_2_NEGATIVE_VERIFY_EXIT=0")
    print("IMPORTANT: NO final-DDR equality is claimed for early halted dirty resident slots.")
    return True


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mailbox",required=True,type=Path)
    ap.add_argument("--directory",required=True,type=Path)
    a=ap.parse_args()
    return 0 if verify(a.mailbox,a.directory) else 1


if __name__=="__main__":
    raise SystemExit(main())
