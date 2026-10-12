#!/usr/bin/env python3
"""P05.2c permutation of A53 service order with independent P02 oracle.

Same already physically accepted 3-core threshold-4 triangle. New service
order (2,0,1) replaces (0,1,2). 3/3 cores remain resident, isolating
service-order correctness from page replacement.

Golden for reordered execution is recomputed with a SEPARATELY LOADED
Python LogicalChip oracle, not copied from baseline; exact independent
model byte-for-byte final-state invariance is proved before deployment.
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
TRI=ROOT/"scripts/p05_1_triangle_fixture.py"
BUILDER=ROOT/"scripts/p05_deployment.py"
PROFILE="p05-2-reordered-resident-triangle-v1"
ORDER=(2,0,1)
BASELINE=(0,1,2)
ACCEPTED_RECORD_SHA={
    "0":"5c4288e41e1599aea5f854a4022fb88a6b04ddc003b01238e16f5a7c59665381",
    "1":"2767f8cbca59d8e9bb85d0f37d055a7b4a7c4e94676d56bbd3efeff4f4f6c0f2",
    "2":"d6c8982882023c8b0065ca856a3caf35a1b6fa54196a6fb546b774deca32c82f",
}


def load(name: str,path: Path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def states(directory:Path)->dict[tuple[int,int],int]:
    rows={}
    reading=False
    for raw in (directory/"p02_4b_vectors.tcl").read_text().splitlines():
        row=raw.strip()
        if row=="array set P02B_EXPECT_STATE {":
            reading=True
            continue
        if reading and row=="}":
            break
        if reading:
            tag,value=row.split()
            t,core=map(int,tag.split(","))
            key=t,core
            if key in rows:raise ValueError("duplicate neural state vector")
            rows[key]=int(value,0)
    if set(rows)!={(t,c) for t in range(5) for c in BASELINE}:
        raise ValueError("incomplete reordered neural reference vectors")
    return rows


def make(directory:Path)->dict:
    if directory.exists():
        raise ValueError(f"refusing to overwrite evidence: {directory}")
    tri=load("p05_2c_tri_config",TRI)
    tri.make(directory)
    base_gate=json.loads((directory/"triangle_gate.json").read_text())
    base_model=json.loads((directory/"triangle_golden/manifest.json").read_text())
    original_spec=json.loads((directory/"triangle_spec.json").read_text())
    if (base_gate["expected_packets"],base_gate["expected_resident_deliveries"],
        base_gate["timesteps"])!=(12,12,5):
        raise ValueError("accepted baseline triangle drift")
    oracle=tri.oracle_module()
    oracle.SERVICE_ORDER=ORDER
    reordered_dir=directory/"reordered_golden"
    reordered_model=oracle.generate(reordered_dir)
    if (reordered_model["logical_core_ids"],reordered_model["dispatch_count"],
        reordered_model["expected_packet_count_total"])!=([0,1,2],15,12):
        raise ValueError("reordered model did not preserve packet count")
    base_dir=directory/"triangle_golden"
    base_states=states(base_dir)
    alt_states=states(reordered_dir)
    for key in base_states:
        if base_states[key]!=alt_states[key]:
            raise ValueError(f"neural model service-order state dependence {key}")
    for core in BASELINE:
        for suffix in ("initial","expected"):
            old=(base_dir/f"core{core}_{suffix}.bin").read_bytes()
            new=(reordered_dir/f"core{core}_{suffix}.bin").read_bytes()
            if old!=new:
                raise ValueError(
                    f"model order invariance failed core {core} {suffix}"
                )
        if hashlib.sha256((reordered_dir/f"core{core}_expected.bin").read_bytes()).hexdigest()!=ACCEPTED_RECORD_SHA[str(core)]:
            raise ValueError(f"model differs from real diagnostic physical SHA core {core}")
    if original_spec["mode"]!="diagnostic" or len(original_spec["checkpoints"])!=15:
        raise ValueError("baseline diagnostic descriptor drift")
    by_core={x["id"]:x for x in original_spec["cores"]}
    reordered={
        **original_spec,
        "cores":[
            {**by_core[core],"record":str(
                (reordered_dir/f"core{core}_initial.bin").resolve())}
            for core in ORDER
        ],
        "events":[
            {"timestep":t,"core":core,"axon":10+core}
            for t in range(5) for core in ORDER
        ],
        "checkpoints":[
            {
                "timestep":t,"core":core,"state_class":"state0",
                "expected_crc32":
                    f"0x{zlib.crc32(struct.pack('<Q',alt_states[t,core])):08X}"
            }
            for t in range(5) for core in ORDER
        ],
    }
    spec_path=directory/"p05_2_order_spec.json"
    spec_path.write_text(json.dumps(reordered,indent=2,sort_keys=True)+"\n")
    builder=load("p05_2c_deployment_builder",BUILDER)
    manifest=builder.build(spec_path,directory/"p05_artifacts")
    payload=(directory/"p05_artifacts/p05_payload.bin").read_bytes()
    header=struct.unpack("<64I",(
        directory/"p05_artifacts/p05_header.bin").read_bytes())
    if (header[3],header[4],header[5],header[6],
        header[13],header[14],header[20])!=(1,5,3,3,15,15,15):
        raise ValueError("reordered P05G descriptor count drift")
    if manifest["logical_core_ids_in_service_order"]!=list(ORDER):
        raise ValueError("P05G service order not the selected permutation")
    if tuple(struct.unpack_from("<I",payload,c*32)[0]
             for c in range(3))!=ORDER:
        raise ValueError("P05G core rows not permuted")
    for idx in range(15):
        step=idx//3
        core=ORDER[idx%3]
        if struct.unpack_from("<4I",payload,header[17]+16*idx)!=(
            step,core,10+core,0):
            raise ValueError(f"bad sorted event row {idx}")
        if struct.unpack_from("<4I",payload,header[18]+16*idx)!=(
            step,core,1,zlib.crc32(struct.pack("<Q",alt_states[step,core]))):
            raise ValueError(f"bad sorted checkpoint row {idx}")
    ledger={
        "profile":PROFILE,
        "status":"MODEL_ONLY_NOT_PHYSICAL_ACCEPTANCE",
        "original_order":list(BASELINE),
        "permuted_service_order":list(ORDER),
        "logical_core_ids":list(BASELINE),
        "resident_slots":3,
        "timesteps":5,
        "expected_dispatches":15,
        "expected_packets":12,
        "expected_resident_deliveries":12,
        "expected_events":15,
        "expected_checkpoints":15,
        "expected_barriers":5,
        "expected_initial_page_ins":3,
        "expected_replacement_page_ins":0,
        "expected_runtime_page_outs":0,
        "expected_final_page_outs":3,
        "expected_hw_page_commands":6,
        "baseline_model_trace_sha256":base_model["trace_fingerprint"],
        "permuted_model_trace_sha256":reordered_model["trace_fingerprint"],
        "baseline_model_manifest_sha256":hashlib.sha256(
            (base_dir/"manifest.json").read_bytes()).hexdigest(),
        "permuted_model_manifest_sha256":hashlib.sha256(
            (reordered_dir/"manifest.json").read_bytes()).hexdigest(),
        "initial_record_sha256":manifest["record_sha256"],
        "expected_final_record_sha256":
            reordered_model["expected_final_record_sha256"],
        "accepted_original_service_order_physical_sha256":ACCEPTED_RECORD_SHA,
        "p05_header_sha256":manifest["header_sha256"],
        "p05_payload_sha256":manifest["payload_sha256"],
        "p05_input_spec_sha256":manifest["input_spec_sha256"],
        "acceptance":"All 15 physical model-derived checkpoints + 12 packet deliveries + 3 full DDR records exact to both independently regenerated permuted model and previously accepted physical diagnostic SHA",
    }
    (directory/"p05_2_order_gate.json").write_text(
        json.dumps(ledger,indent=2,sort_keys=True)+"\n")
    (directory/"p05_mailbox_zero.bin").write_bytes(bytes(256))
    return ledger


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    try:
        gate=make(args.output_dir.resolve())
    except (OSError,ValueError,AssertionError,KeyError,TypeError) as e:
        parser.exit(2,"FAIL: P05.2 reorder fixture: "+str(e)+"\n")
    print("PASS: P05.2 reordered service-order model and P05G contract "+
          json.dumps({k:gate[k] for k in (
              "permuted_service_order","expected_dispatches",
              "expected_packets","expected_resident_deliveries",
              "expected_checkpoints")},sort_keys=True))


if __name__=="__main__":
    main()
