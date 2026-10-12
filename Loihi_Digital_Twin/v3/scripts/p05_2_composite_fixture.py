#!/usr/bin/env python3
"""P05.2e five-over-three composite golden: fanout + mixed arithmetic +
reordered logical execution + dirty eviction and mixed routing residency.

Reference neural state/complete DDR from a fresh independent LogicalChip.
Independently replay *actual accepted P03 scheduler victim policy* over
model-emitted packet words to predict page operations and direct-vs-DDR
delivery counts. The model and victim predictor are intentionally separate
and do not consult a physical mailbox when deriving expected values.

This is NOT 4096-event-capacity saturation/backpressure coverage.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import sys
import zlib

ROOT=Path(__file__).resolve().parents[1]
TRI=ROOT/"scripts/p05_1_triangle_fixture.py"
BUILDER=ROOT/"scripts/p05_deployment.py"
PROFILE="p05-2e-five-over-three-reordered-fanout-paging-v1"
CORES=(0,1,2,3,4)
ORDER=(4,1,3,0,2)
TIMESTEPS=8
SLOTS=3
THRESHOLDS=(4,5,6,7,8)
WEIGHT=3


def load(name:str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def model():
    tri=load("p05_2e_reusable_config",TRI)
    oracle=tri.oracle_module()
    oracle.LOGICAL_CORES=CORES
    oracle.SERVICE_ORDER=ORDER
    oracle.RESIDENT_SLOTS=SLOTS
    oracle.TIMESTEPS=TIMESTEPS

    def config(cid:int):
        next_ids=((cid+1)%len(CORES),(cid+2)%len(CORES))
        return oracle.LogicalCoreConfig(
            core_id=cid,
            compartments=(oracle.CompartmentConfig(
                current_decay=4096,voltage_decay=0,
                threshold=THRESHOLDS[cid],
            ),),
            input_axons=(oracle.InputAxonBinding(10+cid,0),),
            synapse_templates=(oracle.SynapseTemplate(
                0,(oracle.SynapseEntry(0,WEIGHT),)
            ),),
            output_routes=(oracle.OutputRouteEntry(
                0,tuple(oracle.OutputRoute(dest,10+dest) for dest in next_ids)
            ),),
            arithmetic=oracle.P03_REQUIRED_ARITHMETIC,
        )
    oracle._ring_core=config
    return oracle


def vectors(directory:Path,block:str)->dict[tuple[int,int],int|tuple[int,...]]:
    """Read existing P02 Tcl *expected* per-dispatch values, not host guesses."""
    rows={}
    start=f"array set {block} {{"
    reading=False
    for raw in (directory/"p02_4b_vectors.tcl").read_text().splitlines():
        s=raw.strip()
        if s==start:
            reading=True;continue
        if reading and s=="}":break
        if not reading:continue
        m=re.fullmatch(r"(\d+),(\d+)\s+(.+)",s)
        if m is None:raise ValueError(f"invalid oracle Tcl row: {s}")
        t,c=int(m.group(1)),int(m.group(2))
        tag=(t,c)
        if tag in rows:raise ValueError("duplicate oracle vector tag")
        value=m.group(3).strip()
        if block=="P02B_EXPECT_PACKETS":
            if not value.startswith("{") or not value.endswith("}"):
                raise ValueError("invalid packed oracle packets")
            raw_words=value[1:-1].strip()
            rows[tag]=tuple(int(item,0) for item in raw_words.split()) if raw_words else ()
        else:
            rows[tag]=int(value,0)
    expected={(t,c) for t in range(TIMESTEPS) for c in CORES}
    if set(rows)!=expected:
        raise ValueError(f"missing {block} oracle vectors")
    return rows


def scheduler_prediction(packets:dict)->dict:
    """Exact single-engine P03 C deterministic round-robin victim replay.

    Resident counts are observed at packet emission/drain, BEFORE
    later cores page/evict. Conservative dirty marking: every dispatched
    core dirty, and every committed packet dirties all then-resident slots.
    """
    resident=[*ORDER[:SLOTS]]
    dirty=[False]*SLOTS
    victim=0
    counts=dict(
        initial_ins=SLOTS,replacement_ins=0,runtime_outs=0,
        evictions=0,hits=0,resident_deliveries=0,
        nonresident_deliveries=0,emitted_packets=0,
        max_packets_from_dispatch=0,
    )
    by_step=[]
    for timestep in range(TIMESTEPS):
        local={"step":timestep,"direct":0,"nonresident":0,
               "packets":0,"page_ins":0,"page_outs":0}
        for core in ORDER:
            if core in resident:
                slot=resident.index(core)
                counts["hits"]+=1
            else:
                slot=victim
                victim=(victim+1)%SLOTS
                if dirty[slot]:
                    counts["runtime_outs"]+=1
                    local["page_outs"]+=1
                if resident[slot] is not None:
                    counts["evictions"]+=1
                counts["replacement_ins"]+=1
                local["page_ins"]+=1
                resident[slot]=core
                dirty[slot]=False
            dirty[slot]=True
            packet_words=packets[timestep,core]
            if len(packet_words)>2:
                raise ValueError("source exceeded two fanout routes")
            counts["max_packets_from_dispatch"]=max(
                counts["max_packets_from_dispatch"],len(packet_words)
            )
            for word in packet_words:
                target=word & 0x7F
                if target not in CORES or target==core:
                    raise ValueError(f"model illegal fanout packet {word:X}")
                if target in resident:
                    counts["resident_deliveries"]+=1
                    local["direct"]+=1
                else:
                    counts["nonresident_deliveries"]+=1
                    local["nonresident"]+=1
                # Physical P03 marks all resident slots as dirty after
                # committed nonzero packet burst.
                counts["emitted_packets"]+=1
                local["packets"]+=1
            if packet_words:
                for slot_idx in range(SLOTS):
                    dirty[slot_idx]=True
        by_step.append(local)
    counts["final_outs"]=sum(dirty)
    counts["page_commands"]=(counts["initial_ins"]+
        counts["replacement_ins"]+counts["runtime_outs"]+counts["final_outs"])
    counts["final_resident"]=resident
    counts["per_step"]=by_step
    return counts


def make(out:Path)->dict:
    if out.exists():raise ValueError(f"refusing to overwrite composite: {out}")
    out.mkdir(parents=True)
    oracle=model()
    golden=out/"composite_golden"
    sim=oracle.generate(golden)
    if (sim["logical_core_ids"],sim["dispatch_count"],sim["timesteps"],
        sim["service_order"],sim["resident_context_count"])!=(
        list(CORES),len(CORES)*TIMESTEPS,TIMESTEPS,list(ORDER),SLOTS):
        raise ValueError("independent composite neural run has wrong shape")
    expected_states=vectors(golden,"P02B_EXPECT_STATE")
    expected_events=vectors(golden,"P02B_EXPECT_EVENT_COUNT")
    expected_packets=vectors(golden,"P02B_EXPECT_PACKETS")
    counts=scheduler_prediction(expected_packets)
    if sim["expected_packet_count_total"]!=counts["emitted_packets"]:
        raise ValueError("independent model and deterministic physical packet ledger disagree")
    if not (counts["replacement_ins"]>=20 and
            counts["runtime_outs"]>=20 and counts["evictions"]>=20 and
            counts["resident_deliveries"]>0 and
            counts["nonresident_deliveries"]>0 and
            counts["max_packets_from_dispatch"]==2 and
            counts["final_outs"]==SLOTS):
        raise ValueError("composite fails to exercise full paging+mixed-routing stress")
    max_input=max(expected_events.values())
    if max_input<3:
        raise ValueError("composite never aggregates two routed with external input")
    if len({expected_states[t,c] for t in range(2) for c in CORES})<2:
        raise ValueError("composite has no early arithmetic state diversity")
    backing=oracle.export_paged_hardware_image(
        oracle.make_workload(),resident_context_count=SLOTS
    ).backing_by_logical_core
    core_rows=[]
    for core in ORDER:
        img=backing[core].image
        if img.route_count!=2 or img.compartment_count!=1:
            raise ValueError(f"core {core} not physically two-route 1-neuron")
        meta=core | (img.compartment_count<<7) | (
            img.synapse_count<<18) | (img.route_count<<34)
        core_rows.append({
            "id":core,"metadata":f"0x{meta:016X}",
            "input_axon":10+core,
            "record":str((golden/f"core{core}_initial.bin").resolve()),
        })
    spec={
        "schema":"p05-regression-deployment-v1",
        "mode":"diagnostic",
        "timesteps":TIMESTEPS,"slot_count":SLOTS,
        "cores":core_rows,
        "events":[
            {"timestep":t,"core":core,"axon":10+core}
            for t in range(TIMESTEPS) for core in ORDER
        ],
        "checkpoints":[
            {"timestep":t,"core":core,"state_class":"state0",
             "expected_crc32":f"0x{zlib.crc32(struct.pack('<Q',expected_states[t,core])):08X}"}
            for t in range(TIMESTEPS) for core in ORDER
        ],
    }
    source=out/"p05_2_composite_spec.json"
    source.write_text(json.dumps(spec,indent=2,sort_keys=True)+"\n")
    builder=load("p05_2e_p05g_builder",BUILDER)
    artifacts=out/"p05_artifacts"
    manifest=builder.build(source,artifacts)
    if (manifest["dispatches"],manifest["events"],manifest["checkpoints"],
        manifest["logical_core_ids_in_service_order"])!=(
        40,40,40,list(ORDER)):
        raise ValueError("P05G composite descriptor shape drift")
    for core in CORES:
        if (artifacts/f"core{core}_initial.bin").read_bytes()!=(
            golden/f"core{core}_initial.bin").read_bytes():
            raise ValueError(f"composite core{core} initial image drift")
    if len(sim["expected_final_record_sha256"])!=len(CORES):
        raise ValueError("not all golden DDR images generated")
    gate={
        "profile":PROFILE,
        "status":"MODEL_ONLY_NOT_PHYSICAL_ACCEPTANCE",
        "logical_cores":list(CORES),"slots":SLOTS,
        "service_order":list(ORDER),
        "timesteps":TIMESTEPS,"expected_dispatches":40,
        "expected_external_events":40,"expected_checkpoints":40,
        "expected_barriers":TIMESTEPS,
        "two_outgoing_destinations_per_core":{
            str(c):[(c+1)%5,(c+2)%5] for c in CORES},
        "threshold_by_core":{str(c):THRESHOLDS[c] for c in CORES},
        "synaptic_weight":WEIGHT,
        "arithmetic_note":"Varied normal-range thresholds only; NOT signed/saturation edge-case coverage.",
        "max_current_events_per_core":max_input,
        "scheduler_model":counts,
        "trace_reference_sha256":sim["trace_fingerprint"],
        "oracle_manifest_sha256":hashlib.sha256(
            (golden/"manifest.json").read_bytes()).hexdigest(),
        "oracle_final_record_sha256":sim["expected_final_record_sha256"],
        "p05_header_sha256":manifest["header_sha256"],
        "p05_payload_sha256":manifest["payload_sha256"],
        "p05_input_spec_sha256":manifest["input_spec_sha256"],
        "coverage_limits":"No event-depth=4096 saturation, hardware backpressure timing or signed fixed-point overflow.",
    }
    (out/"p05_2_composite_gate.json").write_text(
        json.dumps(gate,indent=2,sort_keys=True)+"\n"
    )
    (out/"p05_mailbox_zero.bin").write_bytes(bytes(256))
    return gate


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",required=True,type=Path)
    args=p.parse_args()
    try:
        info=make(args.output_dir.resolve())
    except (OSError,ValueError,KeyError,AssertionError,TypeError) as e:
        p.exit(2,"FAIL: P05.2e composite oracle: "+str(e)+"\n")
    counts=info["scheduler_model"]
    print("PASS: P05.2e 5-over-3 composite model and scheduler oracle "+
          json.dumps({k:counts[k] for k in (
            "emitted_packets","resident_deliveries",
            "nonresident_deliveries","replacement_ins",
            "runtime_outs","evictions","hits","page_commands"
          )},sort_keys=True))


if __name__=="__main__":
    main()
