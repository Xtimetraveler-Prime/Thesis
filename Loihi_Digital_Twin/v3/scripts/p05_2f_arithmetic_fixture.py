#!/usr/bin/env python3
"""P05.2f signed/24-bit limit, decay and refractory *combined* physical oracle.

One autonomous 5-logical-over-3-slot run probes distinct neuron classes,
packet routing, repeated DDR victim paging and 30 barrier state checkpoints.
This is NOT a capacity-4096/backpressure or measured-bus-traffic test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib

from p05_2_composite_fixture import load, vectors, scheduler_prediction

ROOT=Path(__file__).resolve().parents[1]
TRI=ROOT/"scripts/p05_1_triangle_fixture.py"
BUILDER=ROOT/"scripts/p05_deployment.py"
PROFILE="p05-2f-signed-decay-saturation-five-over-three-v1"
CORES=(0,1,2,3,4)
ORDER=(4,1,3,0,2)
STEPS=6
SLOTS=3
MAX24=(1<<23)-1
MIN24=-(1<<23)

# Fixed, independently encoded parameters, not fitted to device output.
PARAMETERS={
    0:dict(weight=127,current_decay=4096,voltage_decay=4096,
           threshold=MAX24,bias=MAX24,refractory_ticks=0),
    1:dict(weight=-127,current_decay=4096,voltage_decay=4096,
           threshold=4,bias=MIN24,refractory_ticks=0),
    2:dict(weight=-5,current_decay=2048,voltage_decay=1024,
           threshold=1024,bias=0,refractory_ticks=0),
    3:dict(weight=3,current_decay=2048,voltage_decay=1024,
           threshold=4,bias=0,refractory_ticks=2),
    4:dict(weight=7,current_decay=0,voltage_decay=0,
           threshold=15,bias=-2,refractory_ticks=0),
}

def model():
    triangle=load("p05_2f_triangle_base",TRI)
    oracle=triangle.oracle_module()
    oracle.LOGICAL_CORES=CORES
    oracle.SERVICE_ORDER=ORDER
    oracle.RESIDENT_SLOTS=SLOTS
    oracle.TIMESTEPS=STEPS
    def per_core(cid:int):
        p=PARAMETERS[cid]
        nxt=(cid+1)%5
        return oracle.LogicalCoreConfig(
            core_id=cid,
            compartments=(oracle.CompartmentConfig(
                current_decay=p["current_decay"],
                voltage_decay=p["voltage_decay"],
                threshold=p["threshold"],bias=p["bias"],
                refractory_ticks=p["refractory_ticks"],
            ),),
            input_axons=(oracle.InputAxonBinding(10+cid,0),),
            synapse_templates=(oracle.SynapseTemplate(
                0,(oracle.SynapseEntry(0,p["weight"]),)
            ),),
            output_routes=(oracle.OutputRouteEntry(
                0,(oracle.OutputRoute(nxt,10+nxt),)
            ),),
            arithmetic=oracle.P03_REQUIRED_ARITHMETIC,
        )
    oracle._ring_core=per_core
    return oracle

def read_vectors(directory:Path,block:str):
    # Reuse the independently frozen P02 Tcl vector parser without altering
    # the original model. Its globals only govern expected key-set size.
    parser=load("p05_2f_vector_reader",ROOT/"scripts/p05_2_composite_fixture.py")
    parser.CORES=CORES
    parser.TIMESTEPS=STEPS
    return parser.vectors(directory,block)

def make(out:Path):
    if out.exists():
        raise ValueError("refuse to overwrite original or prepared P05.2f evidence")
    out.mkdir(parents=True)
    oracle=model()
    golden=out/"arithmetic_golden"
    sim=oracle.generate(golden)
    if (sim["logical_core_ids"],sim["timesteps"],sim["dispatch_count"],
        sim["service_order"],sim["resident_context_count"])!=(
        list(CORES),STEPS,STEPS*len(CORES),list(ORDER),SLOTS):
        raise ValueError("five-over-three independent neural model drift")
    states=read_vectors(golden,"P02B_EXPECT_STATE")
    packets=read_vectors(golden,"P02B_EXPECT_PACKETS")
    event_counts=read_vectors(golden,"P02B_EXPECT_EVENT_COUNT")
    replay=scheduler_prediction(packets)
    if replay["emitted_packets"]!=sim["expected_packet_count_total"]:
        raise ValueError("PS victim replay disagrees with Loihi model packets")
    if not (replay["replacement_ins"]>=15 and replay["runtime_outs"]>=15
            and replay["final_outs"]==3 and replay["emitted_packets"]>0):
        raise ValueError("combined arithmetic gate does not stress paging and routing")
    from loihi_twin_v2.hardware_p03 import unpack_compartment_state
    if not all(unpack_compartment_state(states[t,0]).voltage==MAX24
               for t in range(STEPS)):
        raise ValueError("positive 24-bit saturation vector not exercised")
    if not all(unpack_compartment_state(states[t,1]).voltage==MIN24
               for t in range(STEPS)):
        raise ValueError("negative 24-bit saturation vector not exercised")
    if not all(unpack_compartment_state(states[t,2]).current<0
               for t in range(STEPS)):
        raise ValueError("negative signed-current/rounding vector not exercised")
    if not any(unpack_compartment_state(states[t,3]).refractory_remaining>0
               for t in range(STEPS)):
        raise ValueError("refractory timing vector not exercised")
    if max(event_counts.values())<2:
        raise ValueError("no routed+external event aggregation occurred")
    net=oracle.export_paged_hardware_image(
        oracle.make_workload(),resident_context_count=SLOTS
    ).backing_by_logical_core
    rows=[]
    for cid in ORDER:
        img=net[cid].image
        if (img.compartment_count,img.synapse_count,img.route_count)!=(1,1,1):
            raise ValueError(f"unexpected core {cid} hardware encoding")
        meta=cid|(1<<7)|(1<<18)|(1<<34)
        rows.append({
            "id":cid,"metadata":f"0x{meta:016X}",
            "input_axon":10+cid,
            "record":str((golden/f"core{cid}_initial.bin").resolve()),
        })
    spec={
        "schema":"p05-regression-deployment-v1",
        "timesteps":STEPS,"slot_count":SLOTS,"mode":"diagnostic",
        "cores":rows,
        "events":[{"timestep":t,"core":cid,"axon":10+cid}
                  for t in range(STEPS) for cid in ORDER],
        "checkpoints":[
            {"timestep":t,"core":cid,"state_class":"state0",
             "expected_crc32":f"0x{zlib.crc32(struct.pack('<Q',states[t,cid])):08X}"}
            for t in range(STEPS) for cid in ORDER
        ],
    }
    spec_path=out/"p05_2f_arithmetic_spec.json"
    spec_path.write_text(json.dumps(spec,indent=2,sort_keys=True)+"\n")
    builder=load("p05_2f_p05g_builder",BUILDER)
    manifest=builder.build(spec_path,out/"p05_artifacts")
    if (manifest["events"],manifest["checkpoints"],manifest["dispatches"],
        manifest["logical_core_ids_in_service_order"])!=(30,30,30,list(ORDER)):
        raise ValueError("P05G 30 dispatch/checkpoint shape drift")
    for cid in CORES:
        if (out/"p05_artifacts"/f"core{cid}_initial.bin").read_bytes()!=(
            golden/f"core{cid}_initial.bin").read_bytes():
            raise ValueError("staged and independent DDR initial record mismatch")
    gate={
        "profile":PROFILE,"status":"MODEL_ONLY_NOT_HARDWARE_ACCEPTED",
        "cores":list(CORES),"order":list(ORDER),"slots":SLOTS,"steps":STEPS,
        "parameters":{str(k):v for k,v in PARAMETERS.items()},
        "expected_dispatches":30,"expected_events":30,"expected_checks":30,
        "expected_packets":replay["emitted_packets"],
        "scheduler_model":replay,
        "max_current_events_per_core":max(event_counts.values()),
        "oracle_trace_sha256":sim["trace_fingerprint"],
        "oracle_manifest_sha256":hashlib.sha256(
            (golden/"manifest.json").read_bytes()).hexdigest(),
        "oracle_final_record_sha256":sim["expected_final_record_sha256"],
        "p05_header_sha256":manifest["header_sha256"],
        "p05_payload_sha256":manifest["payload_sha256"],
        "p05_input_spec_sha256":manifest["input_spec_sha256"],
        "not_tested":"4096-event capacity or overflow/backpressure, calibrated AXI bytes",
    }
    (out/"p05_2f_gate.json").write_text(json.dumps(gate,indent=2,sort_keys=True)+"\n")
    (out/"p05_mailbox_zero.bin").write_bytes(bytes(256))
    return gate

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--output-dir",type=Path,required=True)
    args=a.parse_args()
    try:
        g=make(args.output_dir.resolve())
    except (OSError,ValueError,AssertionError,KeyError,TypeError) as e:
        a.exit(2,"FAIL: P05.2f combined arithmetic golden: "+str(e)+"\n")
    print("PASS: P05.2f independent signed/decay/saturation/refractory five-over-three golden "+json.dumps({
        "dispatches":g["expected_dispatches"],
        "packets":g["expected_packets"],
        "pages":g["scheduler_model"]["page_commands"],
        "checkpoints":g["expected_checks"]},sort_keys=True))

if __name__=="__main__":
    main()
