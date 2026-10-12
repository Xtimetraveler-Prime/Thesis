#!/usr/bin/env python3
"""P05.2d physical dual-route fanout; independent full-record model golden.

Two packets per firing dispatch and two routed NEXT events per
destination are required. Counters/checkpoints/final authoritative
DDR records must all agree with a separately generated LogicalChip.
A successful synthetic host mailbox is NOT a physical result.
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
if SRC in sys.path:sys.path.remove(SRC)
sys.path.insert(0,SRC)


def load(name:str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODEL=load("p05_fanout_model",ROOT/"scripts/p05_2_fanout_fixture.py")
FIELDS=load("p05_fanout_mailbox",ROOT/"scripts/p05_1_verify.py").FIELDS


def verify(mailbox:Path,folder:Path)->bool:
    try:
        blob=mailbox.read_bytes()
        if len(blob)!=256:
            raise ValueError("P05R must be exactly 256 bytes")
        result=struct.unpack("<64I",blob)
        r=dict(zip(FIELDS,result))
        gate=json.loads((folder/"p05_2_fanout_gate.json").read_text())
        spec=json.loads((folder/"p05_2_fanout_spec.json").read_text())
        manifest=json.loads((folder/"p05_artifacts/p05_manifest.json").read_text())
        model=json.loads((folder/"fanout_golden/manifest.json").read_text())
        head=(folder/"p05_artifacts/p05_header.bin").read_bytes()
        payload=(folder/"p05_artifacts/p05_payload.bin").read_bytes()
        h=struct.unpack("<64I",head)
        if gate["profile"]!=MODEL.PROFILE:
            raise ValueError("wrong fanout model identity")
        if gate["topology"]!={"0":[1,2],"1":[0,2],"2":[0,1]}:
            raise ValueError("fanout connectivity drift")
        if (gate["expected_packets"],gate["expected_direct_resident_deliveries"],
            gate["expected_max_packets_from_one_dispatch"],
            gate["expected_max_current_input_events_per_core"])!=(24,24,2,3):
            raise ValueError("fanout coverage targets changed")
        if gate["arithmetic"]!={"threshold":4,"synaptic_weight":3,
                                "current_decay":4096,"voltage_decay":0}:
            raise ValueError("fanout neural arithmetic parameters drift")
        if (h[0],h[1],h[2],h[3],h[4],h[5],h[6],
            h[13],h[14],h[20])!=(
            0x47353050,1,256,1,5,3,3,15,15,15):
            raise ValueError("fanout deployment shape drift")
        if len(payload)!=h[12] or not 0<len(payload)<=0xE0000:
            raise ValueError("invalid fanout payload length")
        if h[22]!=zlib.crc32(payload) or (
            h[23]!=zlib.crc32(head[:92]+bytes(4)+head[96:])):
            raise ValueError("fanout binary CRC mismatch")
        if (manifest["header_sha256"]!=gate["p05_header_sha256"]!=
                hashlib.sha256(head).hexdigest() or
            manifest["payload_sha256"]!=gate["p05_payload_sha256"]!=
                hashlib.sha256(payload).hexdigest() or
            manifest["input_spec_sha256"]!=gate["p05_input_spec_sha256"]!=
                hashlib.sha256((folder/"p05_2_fanout_spec.json").read_bytes()).hexdigest()):
            raise ValueError("fanout SHA identity drift")
        if (model["logical_core_ids"],model["timesteps"],
            model["dispatch_count"],model["expected_packet_count_total"])!=(
            [0,1,2],5,15,24):
            raise ValueError("fanout model cannot support selected target")
        if (gate["oracle_trace_sha256"]!=model["trace_fingerprint"] or
            gate["oracle_manifest_sha256"]!=hashlib.sha256(
                (folder/"fanout_golden/manifest.json").read_bytes()).hexdigest()):
            raise ValueError("independent fanout oracle trace drift")
        if (spec["mode"],spec["timesteps"],spec["slot_count"])!=(
            "diagnostic",5,3):
            raise ValueError("invalid fanout descriptor mode or dimensions")
        if [entry["id"] for entry in spec["cores"]]!=[0,1,2]:
            raise ValueError("fanout core service order drift")
        if (manifest["logical_core_ids_in_service_order"]!=[0,1,2] or
            manifest["events"]!=15 or manifest["checkpoints"]!=15 or
            manifest["dispatches"]!=15):
            raise ValueError("fanout binary manifest count/order drift")
        if (h[17],h[18])!=(3*32,3*32+15*16):
            raise ValueError("fanout P05G table offsets incorrect")
        ref=MODEL.states(folder/"fanout_golden")
        neural=MODEL.model()
        image=neural.export_paged_hardware_image(
            neural.make_workload(),resident_context_count=3)
        for core in (0,1,2):
            original=(folder/"fanout_golden"/f"core{core}_initial.bin").read_bytes()
            staged=(folder/"p05_artifacts"/f"core{core}_initial.bin").read_bytes()
            data=image.backing_by_logical_core[core].image
            row=struct.unpack_from("<8I",payload,core*32)
            meta=(core | (data.compartment_count<<7) |
                  (data.synapse_count<<18) | (data.route_count<<34))
            if (len(original)!=0x80000 or staged!=original or
                data.route_count!=2 or row[0]!=core or
                (row[1]|(row[2]<<32))!=meta or
                row[4]!=zlib.crc32(original) or row[5]!=10+core or
                row[6:]!=(0,0)):
                raise ValueError(f"fanout core{core} metadata/route input mismatch")
        for i in range(15):
            step=i//3;core=i%3
            event=struct.unpack_from("<4I",payload,h[17]+16*i)
            cp=struct.unpack_from("<4I",payload,h[18]+16*i)
            crc=zlib.crc32(struct.pack("<Q",ref[step,core]))
            if event!=(step,core,10+core,0):
                raise ValueError(f"fanout event {i} != independent stimulus")
            if cp!=(step,core,1,crc):
                raise ValueError(f"fanout checkpoint {i} != independent neuron state")
            if spec["events"][i]!={"timestep":step,"core":core,"axon":10+core}:
                raise ValueError(f"fanout spec stimulus row {i} wrong")
    except (OSError,ValueError,AssertionError,KeyError,TypeError,struct.error) as e:
        print("FAIL: P05.2d fanout evidence admission: "+str(e),file=sys.stderr)
        return False

    wants={
        "magic":0x52353050,"version":1,"result":0x600D600D,
        "error":0,"steps":5,"completed_steps":5,
        "cores":3,"slots":3,"phase":18,"fault":0,"fault_phase":0,
        "dispatches":15,"packets":24,"barriers":5,
        "initial_ins":3,"replacement_ins":0,"runtime_outs":0,
        "final_outs":3,"evictions":0,"hits":15,
        "hw_id":0x4C543302,"hw_caps":0x0001031F,
        "hw_dispatches":15,"hw_pages":6,
        "hw_last_page_bytes":106496,
        "hw_status":0,"hw_pending_bytes":0,
        "resident_deliveries":24,"inputs_consumed":15,
        "checkpoints_passed":15,"failed_step":0,"failed_core":0,
        "failed_class":0,"expected_crc":0,"observed_crc":0,
        "header_crc":h[23],"payload_crc":h[22],
        "diagnostic_mode":1,"expected_events":15,
        "expected_checks":15,"expected_dispatches":15,
        "diag_flags":0,"last_page_error":0,
    }
    errors=[]
    for k,v in wants.items():
        if r[k]!=v:
            errors.append(f"{k} got=0x{r[k]:X}, expected=0x{v:X}")
    if result[60:]!=(0,0,0,0):
        errors.append("reserved P05R mailbox words nonzero")
    for key in ("cntfrq_hz","hw_read_bursts","hw_write_bursts"):
        if r[key]==0:errors.append(key+" unexpectedly zero")
    for lo,hi in (("pl_dispatch_lo","pl_dispatch_hi"),
                  ("pl_page_lo","pl_page_hi"),
                  ("ps_infer_lo","ps_infer_hi")):
        if not(r[lo]|r[hi]):errors.append(lo+" / "+hi+" unexpectedly zero")
    ddr=None
    ddr_error=None
    try:
        ddr=MODEL.model().verify(folder/"fanout_golden",folder/"final_ddr")
        for core in (0,1,2):
            actual=ddr["records"][str(core)]["sha256"]
            pinned=gate["expected_final_record_sha256"][str(core)]
            if actual!=pinned:
                errors.append(f"fanout final core{core} SHA drift {actual} vs {pinned}")
    except (OSError,AssertionError,ValueError) as e:
        ddr_error=str(e)
    if errors or ddr_error:
        for e in errors:print("FAIL: P05.2d fanout mailbox/data "+e,file=sys.stderr)
        print("P05_2_FANOUT_FINAL_DDR="+(
            "FAIL "+ddr_error if ddr_error else "PASS (other error still FAIL)"
        ),file=sys.stderr)
        if r["result"]!=0x600D600D:
            print("P05_2_FANOUT_FIRST_DIAGNOSTIC="+json.dumps({
                key:r[key] for key in (
                    "error","fault","fault_phase","dispatches",
                    "packets","resident_deliveries","barriers",
                    "failed_step","failed_core","failed_class",
                    "expected_crc","observed_crc"
                )
            },sort_keys=True),file=sys.stderr)
        return False
    print(
        "PASS: P05.2d physical two-route fanout model "
        "timesteps=5 dispatches=15 packets=24 "
        "resident_deliveries=24 barriers=5 events=15 checkpoints=15"
    )
    print(
        "PASS: P05.2d three complete 512KiB final DDR records byte-exact "
        "to independent fanout LogicalChip model (2 routes/source; "
        "two NEXT deliveries/destination on firing timesteps)"
    )
    print("P05_2_FANOUT_METADATA="+json.dumps({
        "reference_trace_sha256":model["trace_fingerprint"],
        "header_crc32":f"0x{h[23]:08X}",
        "payload_crc32":f"0x{h[22]:08X}",
        "record_sha256":{str(core):ddr["records"][str(core)]["sha256"]
                         for core in (0,1,2)},
    },sort_keys=True))
    return True


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mailbox",required=True,type=Path)
    p.add_argument("--directory",required=True,type=Path)
    a=p.parse_args()
    return 0 if verify(a.mailbox,a.directory) else 1


if __name__=="__main__":
    raise SystemExit(main())
