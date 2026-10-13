#!/usr/bin/env python3
"""P05.2b new FAST / no-checkpoint physical profile.

Start with the independently accepted P05.1 three-core threshold-4
triangle model, record the diagnostic deployment, then change ONLY
mode=fast and checkpoints=[]. The neural DDR records, 15 input events,
15 dispatches, five timestep barriers, and routing are unchanged.
The P05 A53 executable and accepted FPD128 bitstream are reused.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
TRI=ROOT/"scripts/p05_1_triangle_fixture.py"
BUILDER=ROOT/"scripts/p05_deployment.py"
PROFILE="p05-2-fast-no-checkpoints-triangle-v1"
ACCEPTED_RECORD_SHA={
    "0":"5c4288e41e1599aea5f854a4022fb88a6b04ddc003b01238e16f5a7c59665381",
    "1":"2767f8cbca59d8e9bb85d0f37d055a7b4a7c4e94676d56bbd3efeff4f4f6c0f2",
    "2":"d6c8982882023c8b0065ca856a3caf35a1b6fa54196a6fb546b774deca32c82f",
}


def load(name:str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    instance=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(instance)
    return instance


def make(output:Path)->dict:
    if output.exists():
        raise ValueError(f"refuse to replace existing fast-mode evidence: {output}")
    tri=load("p05_2b_triangle_model",TRI)
    tri.make(output)
    golden=json.loads((output/"triangle_gate.json").read_text())
    diag_spec_path=output/"triangle_spec.json"
    diag_spec=json.loads(diag_spec_path.read_text())
    diag_dir=output/"p05_artifacts"
    diagnostic_header=(diag_dir/"p05_header.bin").read_bytes()
    diagnostic_payload=(diag_dir/"p05_payload.bin").read_bytes()
    dwords=struct.unpack("<64I",diagnostic_header)
    if (dwords[3],dwords[4],dwords[5],dwords[6],
        dwords[13],dwords[14],dwords[20])!=(1,5,3,3,15,15,15):
        raise ValueError("accepted diagnostic triangle descriptor drift")
    (output/"p05_diag_reference_header.bin").write_bytes(diagnostic_header)
    (output/"p05_diag_reference_payload.bin").write_bytes(diagnostic_payload)
    if (golden["expected_packets"],golden["expected_resident_deliveries"],
        golden["expected_checkpoints"])!=(12,12,15):
        raise ValueError("diagnostic triangle model missing expected coverage")
    fast_spec={
        **diag_spec,
        "mode":"fast",
        "checkpoints":[],
    }
    if ({k:v for k,v in fast_spec.items() if k not in ("mode","checkpoints")}
        != {k:v for k,v in diag_spec.items() if k not in ("mode","checkpoints")}):
        raise ValueError("accidental neural profile mutation")
    fp=output/"p05_2_fast_spec.json"
    fp.write_text(json.dumps(fast_spec,indent=2,sort_keys=True)+"\n")
    builder=load("p05_2b_deployment_builder",BUILDER)
    manifest=builder.build(fp,diag_dir)
    fast_header=(diag_dir/"p05_header.bin").read_bytes()
    fast_payload=(diag_dir/"p05_payload.bin").read_bytes()
    fwords=struct.unpack("<64I",fast_header)
    if (fwords[3],fwords[4],fwords[5],fwords[6],
        fwords[13],fwords[14],fwords[20])!=(0,5,3,3,15,0,15):
        raise ValueError("fast header is not checkpoint-disabled 3-core triangle")
    # Both exact *core table* and *input-event table* must match byte-by-byte.
    if (fwords[17],fwords[18])!=(dwords[17],dwords[18]):
        raise ValueError("fast and diagnostic core/event offsets changed")
    if fast_payload!=diagnostic_payload[:dwords[18]]:
        raise ValueError("fast mode changed neural core or ingress bytes")
    for core in range(3):
        one=(diag_dir/f"core{core}_initial.bin").read_bytes()
        two=(output/"triangle_golden"/f"core{core}_initial.bin").read_bytes()
        if one!=two:
            raise ValueError(f"fast mode changed neural core {core} image")
    gate={
        "profile":PROFILE,
        "status":"FAST_MODEL_ONLY_NOT_PHYSICAL_ACCEPTANCE",
        "neural_reference_profile":golden["profile"],
        "logical_cores":[0,1,2],
        "resident_slots":3,
        "timesteps":5,
        "expected_dispatches":15,
        "expected_packets":12,
        "expected_resident_deliveries":12,
        "expected_input_events":15,
        "expected_checkpoints":0,
        "expected_barriers":5,
        "expected_initial_page_ins":3,
        "expected_replacement_page_ins":0,
        "expected_runtime_page_outs":0,
        "expected_final_page_outs":3,
        "expected_total_pl_page_commands":6,
        "reference_golden_trace_sha256":golden["oracle_trace_sha256"],
        "frozen_diagnostic_reference_header_sha256":
            hashlib.sha256(diagnostic_header).hexdigest(),
        "frozen_diagnostic_reference_payload_sha256":
            hashlib.sha256(diagnostic_payload).hexdigest(),
        "fast_header_sha256":manifest["header_sha256"],
        "fast_payload_sha256":manifest["payload_sha256"],
        "fast_spec_sha256":manifest["input_spec_sha256"],
        "accepted_prior_physical_final_ddr_sha256":ACCEPTED_RECORD_SHA,
        "acceptance":"0 checkpoints, matching counters and three full final DDR images equal to independent model and prior physical diagnostic output; no performance claim",
    }
    (output/"p05_2_fast_gate.json").write_text(
        json.dumps(gate,sort_keys=True,indent=2)+"\n"
    )
    return gate


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",required=True,type=Path)
    args=ap.parse_args()
    try:
        gate=make(args.output_dir.resolve())
    except (OSError,ValueError,AssertionError,KeyError) as e:
        ap.exit(2,f"FAIL: P05.2 fast-mode fixture: {e}\n")
    print("PASS: P05.2 fast/diagnostic deployment equivalence HOST gate "+
          json.dumps({k:gate[k] for k in (
              "expected_dispatches","expected_packets",
              "expected_input_events","expected_checkpoints",
              "expected_resident_deliveries")},sort_keys=True))


if __name__=="__main__":
    main()
