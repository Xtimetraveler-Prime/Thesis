#!/usr/bin/env python3
"""P05.2d physical directed FANOUT & same-destination event aggregation.

A NEW 3-core fully resident LogicalChip neural topology:
  each core fans out to BOTH other cores (2 routes / firing core)
  current_decay=4096, voltage_decay=0, threshold=4, weight=3
  one original external input axon/core/timestep, 5 timesteps.
Expected model: one integration-only step, 4 firing rounds
=> 3 cores * 4 steps * 2 routes = 24 packets (model independently
checks this assumption). Every core receives 2 routed packets in the
NEXT bank + one external axon on each subsequent timestep.
This is NOT buffer saturation/backpressure coverage.
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
CORES=(0,1,2)
STEPS=5
PROFILE="p05-2-three-core-two-route-fanout-v1"


def load(name: str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def model():
    triangle=load("p05_fanout_triangle_cfg",TRI)
    oracle=triangle.oracle_module()
    oracle.TIMESTEPS=STEPS

    def two_route_core(cid:int):
        others=tuple(k for k in CORES if k!=cid)
        return oracle.LogicalCoreConfig(
            core_id=cid,
            compartments=(oracle.CompartmentConfig(
                current_decay=4096,voltage_decay=0,threshold=4
            ),),
            input_axons=(oracle.InputAxonBinding(10+cid,0),),
            synapse_templates=(oracle.SynapseTemplate(
                0,(oracle.SynapseEntry(0,3),)
            ),),
            output_routes=(oracle.OutputRouteEntry(
                0,tuple(oracle.OutputRoute(dest,10+dest) for dest in others)
            ),),
            arithmetic=oracle.P03_REQUIRED_ARITHMETIC,
        )
    oracle._ring_core=two_route_core
    return oracle


def states(directory:Path)->dict[tuple[int,int],int]:
    table={}
    in_block=False
    for line in (directory/"p02_4b_vectors.tcl").read_text().splitlines():
        line=line.strip()
        if line=="array set P02B_EXPECT_STATE {":
            in_block=True;continue
        if in_block and line=="}":break
        if in_block:
            label,value=line.split()
            t,c=map(int,label.split(","))
            if (t,c) in table:
                raise ValueError("duplicate fanout state checkpoint")
            table[t,c]=int(value,0)
    if set(table)!={(t,c) for t in range(STEPS) for c in CORES}:
        raise ValueError("incomplete fanout oracle state0 vectors")
    return table


def make(out:Path)->dict:
    if out.exists():raise ValueError(f"refuse to overwrite fanout evidence: {out}")
    out.mkdir(parents=True)
    oracle=model()
    golden=out/"fanout_golden"
    oracle_result=oracle.generate(golden)
    if (oracle_result["logical_core_ids"],oracle_result["dispatch_count"],
        oracle_result["timesteps"],oracle_result["expected_packet_count_total"])!=(
        [0,1,2],15,5,24):
        raise ValueError(
            "two-route fanout model differs from expected packet/dispatch shape: "+
            json.dumps({k:oracle_result.get(k) for k in (
                "dispatch_count","expected_packet_count_total","timesteps"
            )})
        )
    network=oracle.export_paged_hardware_image(
        oracle.make_workload(),resident_context_count=3
    )
    words=states(golden)
    cores=[]
    for core in CORES:
        img=network.backing_by_logical_core[core].image
        if img.route_count!=2:
            raise ValueError(f"fanout core {core} must encode two physical routes")
        meta=core | (img.compartment_count<<7) | (
            img.synapse_count<<18) | (img.route_count<<34)
        cores.append({
            "id":core,
            "metadata":f"0x{meta:016X}",
            "input_axon":10+core,
            "record":str((golden/f"core{core}_initial.bin").resolve()),
        })
    deployment={
        "schema":"p05-regression-deployment-v1",
        "timesteps":STEPS,
        "slot_count":3,
        "mode":"diagnostic",
        "cores":cores,
        "events":[
            {"timestep":step,"core":core,"axon":10+core}
            for step in range(STEPS) for core in CORES
        ],
        "checkpoints":[
            {"timestep":step,"core":core,"state_class":"state0",
             "expected_crc32":f"0x{zlib.crc32(struct.pack('<Q',words[step,core])):08X}"}
            for step in range(STEPS) for core in CORES
        ],
    }
    spec_path=out/"p05_2_fanout_spec.json"
    spec_path.write_text(json.dumps(deployment,indent=2,sort_keys=True)+"\n")
    builder=load("p05_2d_p05g_builder",BUILDER)
    manifest=builder.build(spec_path,out/"p05_artifacts")
    if (manifest["events"],manifest["checkpoints"],
        manifest["dispatches"],manifest["logical_core_ids_in_service_order"])!=(
        15,15,15,[0,1,2]):
        raise ValueError("fanout P05G descriptor changed")
    for core in CORES:
        raw=(out/"p05_artifacts"/f"core{core}_initial.bin").read_bytes()
        if raw!=(golden/f"core{core}_initial.bin").read_bytes():
            raise ValueError(f"fanout initial DDR core {core} mismatch")
    gate={
        "profile":PROFILE,
        "status":"MODEL_ONLY_NOT_BOARD_ACCEPTANCE",
        "topology":{str(core):[k for k in CORES if k!=core] for core in CORES},
        "per_core_routes":2,
        "logical_cores":list(CORES),
        "resident_slots":3,
        "timesteps":STEPS,
        "expected_dispatches":15,
        "expected_packets":24,
        "expected_direct_resident_deliveries":24,
        "expected_events":15,
        "expected_checkpoints":15,
        "expected_barriers":5,
        "expected_initial_page_ins":3,
        "expected_replacement_ins":0,
        "expected_runtime_outs":0,
        "expected_final_outs":3,
        "expected_page_commands":6,
        "expected_max_current_input_events_per_core":3,
        "expected_max_packets_from_one_dispatch":2,
        "arithmetic":{"threshold":4,"synaptic_weight":3,
                      "current_decay":4096,"voltage_decay":0},
        "oracle_trace_sha256":oracle_result["trace_fingerprint"],
        "oracle_manifest_sha256":hashlib.sha256(
            (golden/"manifest.json").read_bytes()).hexdigest(),
        "expected_final_record_sha256":
            oracle_result["expected_final_record_sha256"],
        "p05_header_sha256":manifest["header_sha256"],
        "p05_payload_sha256":manifest["payload_sha256"],
        "p05_input_spec_sha256":manifest["input_spec_sha256"],
        "caveat":"24 packets with 2 fanout destinations is NOT 4096-deep saturation/backpressure",
    }
    (out/"p05_2_fanout_gate.json").write_text(
        json.dumps(gate,indent=2,sort_keys=True)+"\n"
    )
    (out/"p05_mailbox_zero.bin").write_bytes(bytes(256))
    return gate


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",required=True,type=Path)
    args=ap.parse_args()
    try:
        result=make(args.output_dir.resolve())
    except (ValueError,OSError,AssertionError,KeyError,TypeError) as e:
        ap.exit(2,"FAIL: P05.2d fanout fixture: "+str(e)+"\n")
    print("PASS: P05.2d independent fanout model and binary deployment "+
          json.dumps({k:result[k] for k in (
              "expected_dispatches","expected_packets",
              "expected_direct_resident_deliveries",
              "expected_max_current_input_events_per_core",
              "expected_checkpoints"
          )},sort_keys=True))


if __name__=="__main__":
    main()
