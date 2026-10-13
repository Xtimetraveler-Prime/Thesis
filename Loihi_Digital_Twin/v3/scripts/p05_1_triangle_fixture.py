#!/usr/bin/env python3
"""P05.1 distinct THREE-core, THREE-resident, five-timestep spike triangle.

New *neural topology and parameters* derived from the accepted Python
LogicalChip and P02 DDR image/oracle functions. Frozen P02/P03 source and
goldens are NEVER modified. Intended second independent KV260 profile
using the SAME P05 A53 ELF and accepted FPD128 PL shell.

Threshold=4, weight=3, one external axon/core/step: the state integrates\non t=0, then recurrent spikes emerge on all subsequent timesteps.
Routes 0->1,1->2,2->0. All three destinations remain resident (no
paging replacements), so this specifically exercises direct-resident
packet routing, absent from P03/first P05 physical workloads.
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

ROOT = Path(__file__).resolve().parents[1]
SRC = str(ROOT / "src")
if SRC in sys.path:
    sys.path.remove(SRC)
sys.path.insert(0, SRC)
FROZEN = ROOT / "scripts/p02_4b_ring_fixture.py"
PRODUCER = ROOT / "scripts/p05_deployment.py"
STEPS = 5
CORES = (0, 1, 2)
SLOTS = 3
PROFILE = "p05-1-three-core-resident-triangle-threshold4-v1"


def oracle_module():
    """Load a separate instance; monkeypatch only *this instance's globals*.

    The accepted original module and its module-global golden parameters
    remain untouched on disk. Reuse the exact same LogicalChip, FPGA
    image encoder, and DDR expected-memory emission functions.
    """
    spec = importlib.util.spec_from_file_location("p05_triangle_oracle", FROZEN)
    assert spec is not None and spec.loader is not None
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    oracle.LOGICAL_CORES = CORES
    oracle.SERVICE_ORDER = CORES
    oracle.RESIDENT_SLOTS = SLOTS
    oracle.TIMESTEPS = STEPS

    def different_core(core_id: int):
        successor = (core_id + 1) % len(CORES)
        return oracle.LogicalCoreConfig(
            core_id=core_id,
            compartments=(oracle.CompartmentConfig(
                current_decay=4096, voltage_decay=0, threshold=4,
            ),),
            input_axons=(oracle.InputAxonBinding(10 + core_id, 0),),
            synapse_templates=(oracle.SynapseTemplate(
                0, (oracle.SynapseEntry(0, 3),)
            ),),
            output_routes=(oracle.OutputRouteEntry(
                0, (oracle.OutputRoute(successor, 10 + successor),)
            ),),
            arithmetic=oracle.P03_REQUIRED_ARITHMETIC,
        )
    oracle._ring_core = different_core
    return oracle


def make(root: Path) -> dict:
    if root.exists():
        raise ValueError(f"refusing to overwrite existing triangle directory: {root}")
    root.mkdir(parents=True)
    golden_dir = root / "triangle_golden"
    a = oracle_module()
    model = a.generate(golden_dir)
    if (model["timesteps"],model["logical_core_ids"],model["dispatch_count"]) != (
        STEPS,list(CORES),STEPS * len(CORES)
    ):
        raise ValueError("independent triangle model did not select 3 x 5")
    if model["expected_packet_count_total"] != (STEPS-1) * len(CORES):
        raise ValueError("triangle must emit three packets each timestep after the first")
    cfg = a.make_workload()
    image = a.export_paged_hardware_image(
        cfg,resident_context_count=SLOTS
    )
    backing = image.backing_by_logical_core
    events = [
        {"timestep": t, "core": c, "axon": 10+c}
        for t in range(STEPS) for c in CORES
    ]
    cores = []
    for c in CORES:
        img = backing[c].image
        meta = (c | (img.compartment_count << 7) |
                (img.synapse_count << 18) | (img.route_count << 34))
        cores.append({
            "id": c, "metadata": f"0x{meta:016X}",
            "input_axon": 10+c,
            "record": str((golden_dir/f"core{c}_initial.bin").resolve()),
        })
    # The original oracle generator emits per-dispatch expected state
    # values into the Tcl vectors. Use those independently computed
    # states to construct diagnostics, never a hand-coded checksum.
    expected = {}
    reading = False
    for raw in (golden_dir/"p02_4b_vectors.tcl").read_text().splitlines():
        line=raw.strip()
        if line=="array set P02B_EXPECT_STATE {":
            reading=True
            continue
        if reading and line=="}":
            break
        if reading:
            key,value=line.split()
            step,cid=map(int,key.split(","))
            expected[step,cid]=int(value,0)
    if len(expected)!=len(CORES)*STEPS:
        raise ValueError("triangle model missing per-core state vectors")
    checkpoints = [
        {
            "timestep": t,
            "core": c,
            "state_class": "state0",
            "expected_crc32": f"0x{zlib.crc32(struct.pack('<Q',expected[t,c])):08X}",
        } for t in range(STEPS) for c in CORES
    ]
    spec_path=root/"triangle_spec.json"
    spec = {
        "schema":"p05-regression-deployment-v1",
        "timesteps":STEPS,"slot_count":SLOTS,"mode":"diagnostic",
        "cores":cores,"events":events,"checkpoints":checkpoints,
    }
    spec_path.write_text(json.dumps(spec,indent=2,sort_keys=True)+"\n")
    from importlib import util
    producer_spec=util.spec_from_file_location("p05_triangle_builder",PRODUCER)
    assert producer_spec and producer_spec.loader
    builder=util.module_from_spec(producer_spec)
    producer_spec.loader.exec_module(builder)
    manifest=builder.build(spec_path,root/"p05_artifacts")
    if (manifest["dispatches"],manifest["events"],manifest["checkpoints"])!=(
        15,15,15
    ):
        raise ValueError("triangle binary deployment count mismatch")
    if manifest["logical_core_ids_in_service_order"]!=list(CORES):
        raise ValueError("triangle unexpected service order")
    (root/"p05_mailbox_zero.bin").write_bytes(bytes(256))
    ledger = {
        "profile":PROFILE,
        "neural_parameters":{"threshold":4,"synaptic_weight":3,
                             "current_decay":4096,"voltage_decay":0},
        "topology":{"0":1,"1":2,"2":0},
        "logical_cores":list(CORES),
        "slots":SLOTS,"timesteps":STEPS,
        "expected_dispatches":15,
        "expected_packets":model["expected_packet_count_total"],
        "expected_barriers":STEPS,
        "expected_events":len(events),
        "expected_checkpoints":len(checkpoints),
        "expected_resident_deliveries":12,
        "expected_initial_page_ins":3,
        "expected_replacement_page_ins":0,
        "expected_runtime_page_outs":0,
        "expected_final_page_outs":3,
        "expected_page_operations":6,
        "oracle_trace_sha256":model["trace_fingerprint"],
        "oracle_manifest_sha256":hashlib.sha256(
            (golden_dir/"manifest.json").read_bytes()
        ).hexdigest(),
        "p05_header_sha256":manifest["header_sha256"],
        "p05_payload_sha256":manifest["payload_sha256"],
        "p05_input_spec_sha256":manifest["input_spec_sha256"],
        "expected_final_record_sha256":model["expected_final_record_sha256"],
        "status":"MODEL_ONLY_NOT_PHYSICAL_ACCEPTANCE",
    }
    (root/"triangle_gate.json").write_text(
        json.dumps(ledger,indent=2,sort_keys=True)+"\n"
    )
    return ledger


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",required=True,type=Path)
    args=ap.parse_args()
    try:
        result=make(args.output_dir.resolve())
    except (ValueError,OSError,AssertionError,KeyError) as e:
        ap.exit(2,f"FAIL: P05.1 triangle fixture: {e}\n")
    print("PASS: P05.1 independent 3-core triangle model/deployment fixture "+
          json.dumps({k:result[k] for k in (
              "expected_dispatches","expected_packets",
              "expected_resident_deliveries","expected_checkpoints",
              "oracle_trace_sha256")},sort_keys=True))


if __name__=="__main__":
    main()
