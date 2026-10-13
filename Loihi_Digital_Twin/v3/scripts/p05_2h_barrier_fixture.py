#!/usr/bin/env python3
"""P05.2h high-traffic alternating bank/barrier + mixed-residency paging oracle.

Full independent LogicalChip golden remains unchanged. A separate physical
packet RAM oracle accounts ONLY for registered HLS output-route order.
At EVERY stable barrier, read back both event-bank word0s for ALL cores,
plus neural state0 and each newly emitted output packet0.
No device output participates in expected data generation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib

from p05_2_composite_fixture import load

ROOT=Path(__file__).resolve().parents[1]
ORACLE_PATH=ROOT/"scripts/p05_1_triangle_fixture.py"
COMPOSITE=ROOT/"scripts/p05_2_composite_fixture.py"
BUILDER=ROOT/"scripts/p05_deployment.py"
PROFILE="p05-2h-dual-bank-checkpoints-16-barriers-mixed-routing-v1"
CORES=(0,1,2,3,4)
ORDER=(4,1,3,0,2)
STEPS=16
SLOTS=3
THRESHOLDS=(2,3,4,5,6)
WEIGHT=5
MAX_OUT=2
BANK_FIRST_WORD=4
RECORD_BYTES=0x80000
BANK_OFF=(0x54000,0x58000)
PACKET_OFF=0x64000

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source():
    tri=load("p05_2h_ring_adapter",ORACLE_PATH)
    oracle=tri.oracle_module()
    oracle.LOGICAL_CORES=CORES
    oracle.SERVICE_ORDER=ORDER
    oracle.RESIDENT_SLOTS=SLOTS
    oracle.TIMESTEPS=STEPS
    def configure(cid:int):
        destinations=((cid+1)%5,(cid+2)%5)
        return oracle.LogicalCoreConfig(
            core_id=cid,
            compartments=(oracle.CompartmentConfig(
                current_decay=4096,voltage_decay=0,threshold=THRESHOLDS[cid],
            ),),
            input_axons=(oracle.InputAxonBinding(10+cid,0),),
            synapse_templates=(oracle.SynapseTemplate(0,(oracle.SynapseEntry(0,WEIGHT),)),),
            output_routes=(oracle.OutputRouteEntry(
                0,tuple(oracle.OutputRoute(dest,10+dest) for dest in destinations),
            ),),
            arithmetic=oracle.P03_REQUIRED_ARITHMETIC,
        )
    oracle._ring_core=configure
    return oracle

def vectors(directory:Path, block:str):
    reader=load("p05_2h_vector_reader",COMPOSITE)
    reader.TIMESTEPS=STEPS
    reader.CORES=CORES
    return reader.vectors(directory,block)

def replay(packets:dict)->dict:
    scheduler=load("p05_2h_scheduler_replay",COMPOSITE)
    scheduler.CORES=CORES
    scheduler.ORDER=ORDER
    scheduler.TIMESTEPS=STEPS
    scheduler.SLOTS=SLOTS
    return scheduler.scheduler_prediction(packets)

def physical_golden(golden:Path, out:Path, words:dict)->dict:
    """Only final packet RAM bank may change relative to normalized oracle."""
    if out.exists():raise ValueError("refuse to overwrite P05.2h physical oracle")
    out.mkdir()
    images=source().export_paged_hardware_image(
        source().make_workload(),resident_context_count=SLOTS
    ).backing_by_logical_core
    records={}
    converted={}
    for cid in CORES:
        img=images[cid].image
        order=tuple(int(w&0x7f) for w in img.route_words)
        if order!=((cid+1)%5,(cid+2)%5):
            raise ValueError(f"unexpected physical route ROM destination order core {cid}")
        last_logical=()
        last_physical=()
        for t in range(STEPS):
            normalized=words[t,cid]
            if normalized:
                if tuple(sorted(w&0x7f for w in normalized))!=tuple(sorted(order)):
                    raise ValueError("normalized packet vectors inconsistent with source route ROM")
                table={word&0x7f:word for word in normalized}
                last_logical=normalized
                last_physical=tuple(table[d] for d in order)
                if sorted(last_physical)!=sorted(last_logical):
                    raise ValueError("physical packet order changed payload")
        initial=(golden/f"core{cid}_initial.bin").read_bytes()
        data=bytearray((golden/f"core{cid}_expected.bin").read_bytes())
        if len(data)!=RECORD_BYTES or len(initial)!=RECORD_BYTES:
            raise ValueError("expected exactly 512KiB oracle DDR")
        for index in range(MAX_OUT):
            normalized=last_logical[index] if index<len(last_logical) else 0
            actual=struct.unpack_from("<Q",data,PACKET_OFF+index*8)[0]
            if actual!=normalized:
                raise ValueError(f"original model packet RAM drift core={cid} offset={index}")
            physical=last_physical[index] if index<len(last_physical) else 0
            struct.pack_into("<Q",data,PACKET_OFF+index*8,physical)
        (out/f"core{cid}_expected.bin").write_bytes(data)
        converted[str(cid)]={
            "route_order":list(order),
            "logical_packet0":f"0x{(last_logical[0] if last_logical else 0):016X}",
            "physical_packet0":f"0x{(last_physical[0] if last_physical else 0):016X}",
            "logical_record_sha256":sha(golden/f"core{cid}_expected.bin"),
            "physical_record_sha256":sha(out/f"core{cid}_expected.bin"),
        }
        if bytes(data[:PACKET_OFF])!=(
            golden/f"core{cid}_expected.bin").read_bytes()[:PACKET_OFF]:
            raise ValueError("physical golden changed non-packet DDR regions")
        if bytes(data[PACKET_OFF+MAX_OUT*8:])!=(
            golden/f"core{cid}_expected.bin").read_bytes()[PACKET_OFF+MAX_OUT*8:]:
            raise ValueError("physical golden changed non-packet tail")
        records[str(cid)]=sha(out/f"core{cid}_expected.bin")
    return {"physical_final_record_sha256":records,"packet_route_order":converted}

def barrier_observations(states:dict,packets:dict,events:dict):
    """Separate chronological NEXT routing + CURRENT stimulus bank-word replay.

    The neural Oracle emits sorted destination packet vectors. Each source has
    at most one route to each destination; sorting packets per source has no
    impact on per-destination arrival order. This replay never imports device
    or physical verifier output.
    """
    counts={c:[0,0] for c in CORES}
    bank={c:[[0]*32,[0]*32] for c in CORES}
    packet0={c:0 for c in CORES}
    rows=[]
    timeline=[]
    for t in range(STEPS):
        current=t&1
        nxt=1-current
        # The actual P05 A53 injects immediately before each dispatch;
        # these event0/1 snapshots are computed at barrier AFTER all routes.
        for cid in ORDER:
            index=counts[cid][current]
            if index>=4096:raise ValueError("unexpected P05.2h incoming event overflow")
            if index>=32:raise ValueError("P05.2h >32/event derived scratch unexpected")
            bank[cid][current][index]=10+cid
            counts[cid][current]+=1
            if counts[cid][current]!=events[t,cid]:
                raise ValueError(f"model event count drift at t{t},core{cid}")
            counts[cid][current]=0
        routed_per_target={c:0 for c in CORES}
        for cid in ORDER:
            words=packets[t,cid]
            if len(words) not in (0,MAX_OUT):
                raise ValueError(f"invalid 0/2 fanout from logical core{cid} t{t}")
            if words:
                source_order=((cid+1)%5,(cid+2)%5)
                by_target={w&0x7f:w for w in words}
                if len(by_target)!=MAX_OUT or set(by_target)!=set(source_order):
                    raise ValueError(f"source{cid} expected distinct pair to next logical cores")
                packet0[cid]=by_target[source_order[0]]
            for word in words:
                dest=word&0x7f
                axon=(word>>7)&0xfff
                timestep=(word>>29)&0xffffffff
                if dest not in CORES or axon!=10+dest or timestep!=t+1:
                    raise ValueError("NEXT packet target timestamp/axon mismatch")
                index=counts[dest][nxt]
                if index>=32:raise ValueError("expected-event replay scratch bank full")
                bank[dest][nxt][index]=axon
                counts[dest][nxt]+=1
                routed_per_target[dest]+=1
        for cid in ORDER:
            # Check neural after dispatch, both raw event-bank first words
            # and newly emitted physically ordered output packet0.
            raw={
                1:struct.pack("<Q",states[t,cid]),
                2:struct.pack("<I",bank[cid][0][0]),
                3:struct.pack("<I",bank[cid][1][0]),
            }
            if packets[t,cid]:raw[4]=struct.pack("<Q",packet0[cid])
            for cls,raw_bytes in sorted(raw.items()):
                rows.append({
                    "timestep":t,"core":cid,"state_class":{
                        1:"state0",2:"event0",3:"event1",4:"packet0",
                    }[cls],
                    "expected_crc32":f"0x{zlib.crc32(raw_bytes):08X}",
                })
        timeline.append({
            "step":t,"current_bank":current,"next_bank":nxt,
            "route_packets":sum(routed_per_target.values()),
            "routed_next_counts":{str(cid):routed_per_target[cid] for cid in CORES},
            "current_count_after_barrier":{str(cid):counts[cid][current] for cid in CORES},
            "next_count_after_barrier":{str(cid):counts[cid][nxt] for cid in CORES},
            "next_first_word_after_barrier":{str(cid):bank[cid][nxt][0] for cid in CORES},
        })
        if any(counts[c][current]!=0 for c in CORES):
            raise ValueError("incomplete CURRENT input at barrier")
    return rows,timeline

def make(out:Path):
    if out.exists():raise ValueError("refuse overwrite existing P05.2h evidence")
    out.mkdir(parents=True)
    golden=out/"barrier_logical_golden"
    model=source()
    sim=model.generate(golden)
    if (sim["logical_core_ids"],sim["service_order"],sim["timesteps"],
        sim["resident_context_count"],sim["dispatch_count"])!=(
        list(CORES),list(ORDER),STEPS,SLOTS,STEPS*len(CORES)):
        raise ValueError("independent long-run Loihi model wrong size")
    states=vectors(golden,"P02B_EXPECT_STATE")
    packets=vectors(golden,"P02B_EXPECT_PACKETS")
    events=vectors(golden,"P02B_EXPECT_EVENT_COUNT")
    pager=replay(packets)
    if (pager["emitted_packets"]!=sim["expected_packet_count_total"] or
        pager["replacement_ins"]<40 or pager["runtime_outs"]<40 or
        pager["resident_deliveries"]<10 or pager["nonresident_deliveries"]<10 or
        pager["max_packets_from_dispatch"]!=MAX_OUT or
        pager["final_outs"]!=SLOTS):
        raise ValueError("high-traffic barrier/paging coverage not reached")
    checks,timeline=barrier_observations(states,packets,events)
    if not all(t["current_count_after_barrier"]=={
            str(c):0 for c in CORES} for t in timeline):
        raise ValueError("barrier gate cannot prove empty consumed CURRENT")
    if not all(t["next_bank"]==1-t["current_bank"] for t in timeline):
        raise ValueError("barrier gate lacks strict alternating NEXT/CURRENT")
    if len(checks)<3*STEPS*len(CORES):
        raise ValueError("multi-bank barrier checkpoints incomplete")
    physical=out/"barrier_physical_golden"
    layout=physical_golden(golden,physical,packets)
    config=model.export_paged_hardware_image(
        model.make_workload(),resident_context_count=SLOTS
    ).backing_by_logical_core
    spec={
        "schema":"p05-regression-deployment-v1",
        "mode":"diagnostic","timesteps":STEPS,"slot_count":SLOTS,
        "cores":[{
            "id":c,
            "metadata":f"0x{(c|(1<<7)|(1<<18)|(2<<34)):016X}",
            "input_axon":10+c,
            "record":str((golden/f"core{c}_initial.bin").resolve()),
        } for c in ORDER],
        "events":[{"timestep":t,"core":c,"axon":10+c}
                  for t in range(STEPS) for c in ORDER],
        "checkpoints":checks,
    }
    for c in CORES:
        img=config[c].image
        if (img.compartment_count,img.synapse_count,img.route_count)!=(1,1,2):
            raise ValueError("unexpected HLS-neural encoding")
    spec_path=out/"p05_2h_barrier_spec.json"
    spec_path.write_text(json.dumps(spec,indent=2,sort_keys=True)+"\n")
    deployment=load("p05_2h_p05g_builder",BUILDER).build(
        spec_path,out/"p05_artifacts"
    )
    if (deployment["dispatches"],deployment["events"],deployment["checkpoints"])!=(
        STEPS*5,STEPS*5,len(checks)):
        raise ValueError("P05G high-traffic barrier dimensions drift")
    for cid in CORES:
        if (out/"p05_artifacts"/f"core{cid}_initial.bin").read_bytes()!=(
            golden/f"core{cid}_initial.bin").read_bytes():
            raise ValueError("initial P05G DDR record not identical to Loihi oracle")
    (out/"p05_mailbox_zero.bin").write_bytes(bytes(256))
    gate={
        "profile":PROFILE,"status":"MODEL_ONLY_NOT_HARDWARE_ACCEPTED",
        "steps":STEPS,"cores":list(CORES),"order":list(ORDER),"slots":SLOTS,
        "thresholds":list(THRESHOLDS),"weight":WEIGHT,
        "expected_dispatches":STEPS*5,"expected_events":STEPS*5,
        "expected_checkpoints":len(checks),
        "checkpoint_classes":["state0","event0","event1","packet0-if-emitted"],
        "expected_packets":pager["emitted_packets"],"scheduler_model":pager,
        "barrier_timeline":timeline,
        "model_trace_sha256":sim["trace_fingerprint"],
        "logical_manifest_sha256":sha(golden/"manifest.json"),
        "physical_final_record_sha256":layout["physical_final_record_sha256"],
        "packet_layout":layout["packet_route_order"],
        "p05_header_sha256":deployment["header_sha256"],
        "p05_payload_sha256":deployment["payload_sha256"],
        "p05_input_spec_sha256":deployment["input_spec_sha256"],
        "coverage_boundary":"adversarial routed traffic/bank swaps/paging, not overflow recovery or calibrated AXI traffic",
    }
    (out/"p05_2h_barrier_gate.json").write_text(
        json.dumps(gate,indent=2,sort_keys=True)+"\n")
    return gate

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",required=True,type=Path)
    args=parser.parse_args()
    try:
        gate=make(args.output_dir.resolve())
    except (OSError,ValueError,AssertionError,TypeError,KeyError,IndexError) as e:
        parser.exit(2,"FAIL: P05.2h model-derived barrier fixture: "+str(e)+"\n")
    sched=gate["scheduler_model"]
    print("PASS: P05.2h independent 16-step 5-over-3 multi-bank barrier oracle prepared "+
          json.dumps({
              "dispatches":gate["expected_dispatches"],
              "checkpoints":gate["expected_checkpoints"],
              "packets":gate["expected_packets"],
              "resident_deliveries":sched["resident_deliveries"],
              "nonresident_deliveries":sched["nonresident_deliveries"],
              "evictions":sched["evictions"],
          },sort_keys=True))
    print("P05_2H_PREPARE_MODEL_ONLY=1")

if __name__=="__main__":
    main()
