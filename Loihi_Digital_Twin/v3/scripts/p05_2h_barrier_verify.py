#!/usr/bin/env python3
"""Strict P05.2h actual A53/FPGA checkpoint + five complete physical DDR verifier.

Re-derive every expected state/packet/event-bank first-word checkpoint from
independent original LogicalChip vectors; route-ordered packet RAM is a
separate model-derived physical layout, never fitted to KV260 output.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT=Path(__file__).resolve().parents[1]
SRC=str(ROOT/"src")
if SRC in sys.path:sys.path.remove(SRC)
sys.path.insert(0,SRC)
from p05_2h_barrier_fixture import (
    CORES,ORDER,STEPS,SLOTS,PROFILE,THRESHOLDS,WEIGHT,
    source,sha,vectors,replay,barrier_observations,
)
from p05_2_composite_fixture import load
FIELDS=load("p05_2h_result_fields",ROOT/"scripts/p05_1_verify.py").FIELDS

def verify(mailbox:Path,folder:Path)->bool:
    try:
        blob=mailbox.read_bytes()
        if len(blob)!=256:raise ValueError("original A53 P05R must be 256 bytes")
        w=struct.unpack("<64I",blob)
        d=dict(zip(FIELDS,w))
        head=(folder/"p05_artifacts/p05_header.bin").read_bytes()
        payload=(folder/"p05_artifacts/p05_payload.bin").read_bytes()
        h=struct.unpack("<64I",head)
        manifest=json.loads((folder/"p05_artifacts/p05_manifest.json").read_text())
        gate=json.loads((folder/"p05_2h_barrier_gate.json").read_text())
        spec_file=folder/"p05_2h_barrier_spec.json"
        spec=json.loads(spec_file.read_text())
        golden=folder/"barrier_logical_golden"
        oracle_manifest=json.loads((golden/"manifest.json").read_text())
        real=folder/"final_ddr"
        if (gate["profile"]!=PROFILE or
            gate["status"]!="MODEL_ONLY_NOT_HARDWARE_ACCEPTED" or
            (gate["steps"],gate["cores"],gate["order"],gate["slots"])!=(
                STEPS,list(CORES),list(ORDER),SLOTS) or
            gate["thresholds"]!=list(THRESHOLDS) or gate["weight"]!=WEIGHT):
            raise ValueError("P05.2h frozen neural/barrier profile changed")
        if (h[0],h[1],h[2],h[3],h[4],h[5],h[6],
            h[13],h[14],h[20])!=(
                0x47353050,1,256,1,STEPS,5,SLOTS,
                STEPS*5,gate["expected_checkpoints"],STEPS*5):
            raise ValueError("P05.2h actual binary deployment dimensions wrong")
        if (len(head)!=256 or len(payload)!=h[12] or h[12]>0xE0000 or
            (h[16],h[17],h[18])!=(0,5*32,5*32+STEPS*5*16) or
            h[22]!=zlib.crc32(payload) or
            h[23]!=zlib.crc32(head[:92]+bytes(4)+head[96:])):
            raise ValueError("P05.2h P05G header/payload checksum and offsets wrong")
        if (gate["p05_header_sha256"]!=manifest["header_sha256"]!=hashlib.sha256(head).hexdigest() or
            gate["p05_payload_sha256"]!=manifest["payload_sha256"]!=hashlib.sha256(payload).hexdigest() or
            gate["p05_input_spec_sha256"]!=manifest["input_spec_sha256"]!=sha(spec_file)):
            raise ValueError("P05.2h golden P05G SHA provenance mismatch")
        if (spec["schema"]!="p05-regression-deployment-v1" or
            spec["mode"]!="diagnostic" or spec["timesteps"]!=STEPS or
            spec["slot_count"]!=SLOTS or
            [entry["id"] for entry in spec["cores"]]!=list(ORDER) or
            manifest["logical_core_ids_in_service_order"]!=list(ORDER) or
            (manifest["dispatches"],manifest["events"],manifest["checkpoints"])!=(
                STEPS*5,STEPS*5,gate["expected_checkpoints"])):
            raise ValueError("P05.2h source spec cannot reproduce physical deployment")
        if (oracle_manifest["logical_core_ids"]!=list(CORES) or
            oracle_manifest["service_order"]!=list(ORDER) or
            oracle_manifest["timesteps"]!=STEPS or
            oracle_manifest["dispatch_count"]!=STEPS*5 or
            gate["model_trace_sha256"]!=oracle_manifest["trace_fingerprint"] or
            gate["logical_manifest_sha256"]!=sha(golden/"manifest.json")):
            raise ValueError("independent logical trace/model SHA differs")
        oracle=source()
        images=oracle.export_paged_hardware_image(
            oracle.make_workload(),resident_context_count=SLOTS,
        ).backing_by_logical_core
        for rank,cid in enumerate(ORDER):
            record=(golden/f"core{cid}_initial.bin").read_bytes()
            if (len(record)!=0x80000 or
                (folder/"p05_artifacts"/f"core{cid}_initial.bin").read_bytes()!=record):
                raise ValueError(f"core{cid} actual staged DDR differs from frozen neural model")
            row=struct.unpack_from("<8I",payload,rank*32)
            image=images[cid].image
            meta=cid|(image.compartment_count<<7)|(
                image.synapse_count<<18)|(image.route_count<<34)
            if (row[0],row[1]|row[2]<<32,row[3],row[4],row[5],
                row[6],row[7])!=(
                    cid,meta,struct.unpack_from("<I",record,0x1000)[0],
                    zlib.crc32(record),10+cid,0,0):
                raise ValueError(f"core{cid} P05G row or exact-model initial memory differs")
            route_order=tuple(x&0x7f for x in image.route_words)
            if route_order!=((cid+1)%5,(cid+2)%5):
                raise ValueError(f"core{cid} HLS route RAM source-order altered")
        states=vectors(golden,"P02B_EXPECT_STATE")
        packets=vectors(golden,"P02B_EXPECT_PACKETS")
        events=vectors(golden,"P02B_EXPECT_EVENT_COUNT")
        pager=replay(packets)
        checks,timeline=barrier_observations(states,packets,events)
        if (pager!=gate["scheduler_model"] or
            gate["barrier_timeline"]!=timeline or
            gate["expected_checkpoints"]!=len(checks) or
            gate["expected_dispatches"]!=STEPS*5 or
            gate["expected_events"]!=STEPS*5 or
            gate["expected_packets"]!=pager["emitted_packets"] or
            oracle_manifest["expected_packet_count_total"]!=pager["emitted_packets"]):
            raise ValueError("adversarial barrier/page/routing oracles disagree")
        if len(checks)<3*STEPS*5 or len(timeline)!=STEPS:
            raise ValueError("no bank/barrier workload stress")
        # Chronologically validate every externally injected event row.
        for i in range(STEPS*5):
            step,cindex=divmod(i,5)
            cid=ORDER[cindex]
            if struct.unpack_from("<4I",payload,h[17]+16*i)!=(
                step,cid,10+cid,0):
                raise ValueError(f"unregistered, stale, or out-of-service event row {i}")
        classnum={"state0":1,"event0":2,"event1":3,"packet0":4}
        for idx,item in enumerate(checks):
            expected=(item["timestep"],item["core"],
                      classnum[item["state_class"]],
                      int(item["expected_crc32"],16))
            actual=struct.unpack_from("<4I",payload,h[18]+16*idx)
            if expected!=actual:
                raise ValueError(f"barrier bank/state/packet CRC row {idx} does not match independent oracle")
        if [item["state_class"] for item in checks].count("event0")!=STEPS*5 or (
            [item["state_class"] for item in checks].count("event1")!=STEPS*5):
            raise ValueError("alternating event-bank coverage missing")
        for cid in CORES:
            frozen=golden/f"core{cid}_expected.bin"
            physical=folder/"barrier_physical_golden"/f"core{cid}_expected.bin"
            logical=frozen.read_bytes()
            derived=physical.read_bytes()
            actual_path=real/f"core{cid}_after.bin"
            actual=actual_path.read_bytes()
            if (len(logical)!=0x80000 or len(derived)!=0x80000 or
                len(actual)!=0x80000 or
                sha(frozen)!=oracle_manifest["expected_final_record_sha256"][str(cid)] or
                sha(physical)!=gate["physical_final_record_sha256"][str(cid)]):
                raise ValueError(f"core{cid} immutable logical/physical golden SHA drift")
            # Only packet-bank0/1 changed for registered output-route order,
            # check complete physical 512KiB data: no excluded banks.
            if (logical[:0x64000]!=derived[:0x64000] or
                logical[0x64010:]!=derived[0x64010:]):
                raise ValueError(f"core{cid} non-packet bank changed by route-layout oracle")
            if actual!=derived:
                pos=next((i for i,(a,b) in enumerate(zip(actual,derived))
                          if a!=b),None)
                raise ValueError(f"core{cid} FULL device DDR mismatch at 0x{pos:05X}, "
                                 f"got=0x{actual[pos]:02X} want=0x{derived[pos]:02X}")
    except (OSError,ValueError,KeyError,TypeError,AssertionError,IndexError,struct.error) as e:
        print("FAIL: P05.2h barrier evidence admission/full-DDR comparison: "+str(e),file=sys.stderr)
        print("P05_2H_VERIFY_EXIT=1",file=sys.stderr)
        return False
    expected={
        "magic":0x52353050,"version":1,"result":0x600D600D,"error":0,
        "steps":STEPS,"completed_steps":STEPS,"cores":5,"slots":SLOTS,
        "phase":18,"fault":0,"fault_phase":0,
        "dispatches":STEPS*5,"packets":pager["emitted_packets"],
        "barriers":STEPS,"initial_ins":SLOTS,
        "replacement_ins":pager["replacement_ins"],
        "runtime_outs":pager["runtime_outs"],
        "final_outs":pager["final_outs"],"evictions":pager["evictions"],
        "hits":pager["hits"],
        "resident_deliveries":pager["resident_deliveries"],
        "inputs_consumed":STEPS*5,"checkpoints_passed":len(checks),
        "hw_id":0x4C543302,"hw_caps":0x0001031F,
        "hw_dispatches":STEPS*5,"hw_pages":pager["page_commands"],
        "hw_last_page_bytes":106496,"hw_status":0,"hw_pending_bytes":0,
        "failed_step":0,"failed_core":0,"failed_class":0,
        "expected_crc":0,"observed_crc":0,
        "header_crc":h[23],"payload_crc":h[22],
        "diagnostic_mode":1,"expected_events":STEPS*5,
        "expected_checks":len(checks),"expected_dispatches":STEPS*5,
        "diag_flags":0,"last_page_error":0,
    }
    errs=[f"{key}=0x{d[key]:X} expected 0x{want:X}" for key,want
          in expected.items() if d[key]!=want]
    if w[60:]!=(0,0,0,0):errs.append("nonzero reserved P05R word")
    for key in ("cntfrq_hz","hw_read_bursts","hw_write_bursts"):
        if d[key]<=0:errs.append(f"physical {key} counter unexpectedly zero")
    for lo,hi in (("pl_dispatch_lo","pl_dispatch_hi"),
                  ("pl_page_lo","pl_page_hi"),
                  ("ps_infer_lo","ps_infer_hi"),
                  ("ps_route_lo","ps_route_hi"),
                  ("ps_barrier_lo","ps_barrier_hi")):
        if d[lo]|d[hi]==0:errs.append(f"missing {lo}/{hi} hardware timing")
    if errs:
        for e in errs:print("FAIL: P05.2h A53/PL runtime "+e,file=sys.stderr)
        print("P05_2H_VERIFY_EXIT=1",file=sys.stderr)
        return False
    print("PASS: P05.2h physical adversarial 5-over-3 bank/barrier order "+
          f"steps={STEPS} dispatches={STEPS*5} packets={pager['emitted_packets']} "+
          f"resident_deliveries={pager['resident_deliveries']} "+
          f"nonresident_deliveries={pager['nonresident_deliveries']} "+
          f"barriers={STEPS} checkpoints={len(checks)} "+
          f"evictions={pager['evictions']}")
    print("PASS: P05.2h both event-bank first words, state0 and emitted physical packet0 checkpointed at each barrier")
    print("PASS: P05.2h all five complete physical 512KiB DDR records byte-exact to model-derived route-ordered golden")
    print("P05_2H_METADATA="+json.dumps({
        "model_trace_sha256":gate["model_trace_sha256"],
        "physical_ddr_sha256":gate["physical_final_record_sha256"],
        "p05_header_sha256":gate["p05_header_sha256"],
        "p05_payload_sha256":gate["p05_payload_sha256"],
        "programmed_page_payload_bytes_NOT_AXIBUS":
            pager["programmed_total_page_payload_bytes"],
    },sort_keys=True))
    print("P05_2H_VERIFY_EXIT=0")
    return True

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mailbox",type=Path,required=True)
    parser.add_argument("--directory",type=Path,required=True)
    args=parser.parse_args()
    return 0 if verify(args.mailbox,args.directory) else 1

if __name__=="__main__":
    raise SystemExit(main())
