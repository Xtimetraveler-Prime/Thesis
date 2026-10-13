#!/usr/bin/env python3
"""P05.2 directed *diagnostic expectation* fault, not neural corruption.

Builds the independent accepted 3-core triangle model and deliberately flips
one bit of the EXPECTED state0 CRC at barrier t=2, core=1. The A53 should
execute real inference correctly but reject the supplied checkpoint and
publish a first-mismatch P05R mailbox before barrier 2 completes.

Does NOT change FPGA image, neural stimuli, routes or model golden.
The ordinary triangle reference still expects all 12 packets to the end;
the diagnostic STOP happens early and final authoritative DDR is NOT
expected to equal final golden until dirty contexts are flushed.
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
TRI_PATH=ROOT/"scripts/p05_1_triangle_fixture.py"
P05_PATH=ROOT/"scripts/p05_deployment.py"
STEP=2
CORE=1
CLASS=1
INDEX=STEP*3+CORE
PROFILE="p05-2-expected-crc-first-mismatch-t2-core1-v1"


def _load(name:str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make(out:Path)->dict:
    if out.exists():
        raise ValueError(f"evidence path already exists: {out}")
    triangle=_load("p05_2_triangle_reference",TRI_PATH)
    triangle.make(out)
    spec_path=out/"triangle_spec.json"
    spec=json.loads(spec_path.read_text())
    row=spec["checkpoints"][INDEX]
    assert (row["timestep"],row["core"],row["state_class"])==(
        STEP,CORE,"state0"
    )
    original=int(row["expected_crc32"],0)
    tampered=original^1
    assert tampered!=original
    # New spec and deployment describe an intentionally *bad expected*
    # value; the honest/reference triangle_spec.json is preserved.
    spec["checkpoints"][INDEX]["expected_crc32"]=f"0x{tampered:08X}"
    new_spec=out/"p05_2_fault_spec.json"
    new_spec.write_text(json.dumps(spec,indent=2,sort_keys=True)+"\n")
    builder=_load("p05_2_deployment_builder",P05_PATH)
    # Rebuild only the new descriptor/header; all per-core 512KiB
    # neural records remain byte-identical to model-generated initial.
    artifact_dir=out/"p05_artifacts"
    manifest=builder.build(new_spec,artifact_dir)
    if (manifest["timesteps"],manifest["events"],manifest["checkpoints"],
        manifest["dispatches"])!=(5,15,15,15):
        raise ValueError("P05.2 negative diagnostic descriptor drift")

    vectors=(out/"triangle_golden/p02_4b_vectors.tcl").read_text()
    lookup={}
    inside=False
    for line in vectors.splitlines():
        s=line.strip()
        if s=="array set P02B_EXPECT_STATE {":
            inside=True;continue
        if inside and s=="}":break
        if inside:
            key,value=s.split()
            t,k=map(int,key.split(","))
            lookup[t,k]=int(value,0)
    actual_crc=zlib.crc32(struct.pack("<Q",lookup[STEP,CORE]))
    if actual_crc!=original:
        raise ValueError("negative injection does not match independent model")

    # Hardware should finish all three dispatches at t=2, read cp0,
    # then fail at cp1 BEFORE completing barrier t=2 or dirty flush.
    gate={
        "profile":PROFILE,
        "status":"NEGATIVE_TEST_MODEL_ONLY_NOT_PHYSICAL_PASS",
        "target_step":STEP,
        "target_core":CORE,
        "target_class":CLASS,
        "target_checkpoint_index":INDEX,
        "expected_bad_crc32":f"0x{tampered:08X}",
        "expected_observed_crc32":f"0x{original:08X}",
        "expected_terminal":f"0x{0xDEAD000A:08X}",
        "expected_error_code":10,
        "expected_runtime_fault":11,
        "expected_fault_phase":13,
        "expected_runtime_phase":19,
        "expected_dispatches_before_stop":9,
        "expected_packets_before_stop":6,
        "expected_barriers_before_stop":2,
        "expected_completed_steps_before_stop":2,
        "expected_consumed_events_before_stop":9,
        "expected_passing_checkpoints_before_stop":INDEX,
        "expected_resident_deliveries_before_stop":6,
        "expected_initial_page_ins":3,
        "expected_final_flushes":0,
        "expected_fpga_dispatches":9,
        "expected_fpga_page_commands":3,
        "p05_header_sha256":manifest["header_sha256"],
        "p05_payload_sha256":manifest["payload_sha256"],
        "p05_input_spec_sha256":manifest["input_spec_sha256"],
        "baseline_trace_sha256":json.loads((
            out/"triangle_gate.json").read_text())["oracle_trace_sha256"],
        "note":"A PASS means expected hardware REJECTION with accurate diagnostics, not successful neural execution. Final DDR has not been flushed and must not be checked against final golden.",
    }
    (out/"p05_2_fault_gate.json").write_text(
        json.dumps(gate,indent=2,sort_keys=True)+"\n"
    )
    for cid in range(3):
        new=(artifact_dir/f"core{cid}_initial.bin").read_bytes()
        original_image=(out/"triangle_golden"/f"core{cid}_initial.bin").read_bytes()
        if new!=original_image:
            raise ValueError(f"fault injection mutated core{cid} neural image")
    return gate


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",required=True,type=Path)
    args=ap.parse_args()
    try:
        gate=make(args.output_dir.resolve())
    except (OSError,ValueError,AssertionError,KeyError) as e:
        ap.exit(2,"FAIL: P05.2 negative fixture: "+str(e)+"\n")
    print("PASS: P05.2 first-mismatch negative fixture "+json.dumps({
        k:gate[k] for k in (
            "target_step","target_core","target_checkpoint_index",
            "expected_bad_crc32","expected_observed_crc32",
            "expected_terminal","expected_dispatches_before_stop",
        )
    },sort_keys=True))


if __name__=="__main__":
    main()
