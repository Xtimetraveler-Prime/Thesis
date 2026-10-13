#!/usr/bin/env python3
"""Strict SECOND P05.1 KV260 golden: distinct 3-core resident triangle.

No host algorithmic control. Compare physical P05R counters (including
direct-resident deliveries) and three complete physical DDR images against
the independent Python LogicalChip oracle and model-derived checkpoints.
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
if str(ROOT/"src") in sys.path:
    sys.path.remove(str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"src"))


def module_at(label: str, path: Path):
    spec=importlib.util.spec_from_file_location(label,path)
    assert spec is not None and spec.loader is not None
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


P05R=module_at("p05_1_mailbox_layout",ROOT/"scripts/p05_1_verify.py")
TRI=module_at("p05_1_triangle_oracle_impl",ROOT/"scripts/p05_1_triangle_fixture.py")
FIELDS=P05R.FIELDS
MAGIC=0x52353050


def verify(mailbox: Path, directory: Path) -> bool:
    errors=[]
    try:
        result=struct.unpack("<64I",mailbox.read_bytes())
        root=directory
        artifacts=root/"p05_artifacts"
        golden=root/"triangle_golden"
        gate=json.loads((root/"triangle_gate.json").read_text())
        m=json.loads((artifacts/"p05_manifest.json").read_text())
        model=json.loads((golden/"manifest.json").read_text())
        head=(artifacts/"p05_header.bin").read_bytes()
        payload=(artifacts/"p05_payload.bin").read_bytes()
        spec=json.loads((root/"triangle_spec.json").read_text())
        words=struct.unpack("<64I",head)
        if len(result)!=64 or gate["profile"]!=TRI.PROFILE:
            raise ValueError("P05R/triangle profile admission failed")
        if (words[0],words[1],words[2],words[3],words[4],words[5],
            words[6],words[13],words[14],words[20])!=(
            0x47353050,1,256,1,5,3,3,15,15,15):
            raise ValueError("triangle binary descriptor is not 5step/3core/3slot")
        if words[12]!=len(payload) or words[12]>0xE0000:
            raise ValueError("triangle P05 payload length drift")
        if words[22]!=zlib.crc32(payload) or (
            words[23]!=zlib.crc32(head[:92]+bytes(4)+head[96:])):
            raise ValueError("triangle P05 header/payload CRC mismatch")
        if (m["header_sha256"]!=hashlib.sha256(head).hexdigest() or
            m["payload_sha256"]!=hashlib.sha256(payload).hexdigest() or
            m["input_spec_sha256"]!=hashlib.sha256(
                (root/"triangle_spec.json").read_bytes()).hexdigest()):
            raise ValueError("triangle P05 SHA drift")
        if (gate["p05_header_sha256"]!=m["header_sha256"] or
            gate["p05_payload_sha256"]!=m["payload_sha256"] or
            gate["p05_input_spec_sha256"]!=m["input_spec_sha256"]):
            raise ValueError("triangle gate binary identity drift")
        if (gate["timesteps"],gate["logical_cores"],gate["slots"],
            gate["expected_packets"],gate["expected_resident_deliveries"])!=(
            5,[0,1,2],3,12,12):
            raise ValueError("triangle reference gate expectations drift")
        if (model["logical_core_ids"],model["dispatch_count"],
            model["expected_packet_count_total"])!=([0,1,2],15,12):
            raise ValueError("triangle independent LogicalChip output drift")
        if (gate["oracle_trace_sha256"]!=model["trace_fingerprint"] or
            gate["oracle_manifest_sha256"]!=hashlib.sha256(
                (golden/"manifest.json").read_bytes()).hexdigest()):
            raise ValueError("triangle oracle trace or manifest identity mismatch")
        if (spec["schema"]!="p05-regression-deployment-v1" or
            spec["slot_count"]!=3 or spec["timesteps"]!=5 or
            [core["id"] for core in spec["cores"]]!=[0,1,2]):
            raise ValueError("triangle neural spec parameters drift")
        if (gate["neural_parameters"]!={"threshold":4,"synaptic_weight":3,
             "current_decay":4096,"voltage_decay":0} or
            gate["topology"]!={"0":1,"1":2,"2":0}):
            raise ValueError("triangle neuro-architecture schema drift")
        states={}
        reading=False
        for line in (golden/"p02_4b_vectors.tcl").read_text().splitlines():
            line=line.strip()
            if line=="array set P02B_EXPECT_STATE {":
                reading=True
                continue
            if reading and line=="}":
                break
            if reading:
                step_id,value=line.split()
                t,c=map(int,step_id.split(","))
                states[t,c]=int(value,0)
        if len(states)!=15:
            raise ValueError("triangle model checkpoint state count not 15")
        if (words[17],words[18])!=(3*32,3*32+15*16):
            raise ValueError("triangle descriptor offsets drift")
        for core in range(3):
            entry=struct.unpack_from("<8I",payload,core*32)
            fcore=(golden/f"core{core}_initial.bin").read_bytes()
            pcore=(artifacts/f"core{core}_initial.bin").read_bytes()
            img=struct.unpack_from("<8s12I",fcore,0)
            if (len(fcore)!=0x80000 or fcore!=pcore or entry[0]!=core or
                entry[3]!=struct.unpack_from("<I",fcore,0x1000)[0] or
                entry[4]!=zlib.crc32(fcore) or entry[5]!=10+core or
                entry[6:]!=(0,0) or
                ((entry[1]|(entry[2]<<32))&127)!=core or
                img[0]!=b"LTV3CTX1" or img[1]!=1 or img[4]!=core):
                raise ValueError(f"triangle core {core} initial record mismatch")
            # Explicitly confirm the *different* configured threshold
            # from each real packed DDR compartment word.
            config=int.from_bytes(fcore[0x1000:0x1010],"little")
            if ((config>>26)&0xFFFFFF)!=4:
                raise ValueError(f"triangle core {core} threshold is not 4")
            route_word=int.from_bytes(fcore[0x50000:0x50004],"little")
            target=(core+1)%3
            if (route_word & 0x7F)!=target or (
                ((route_word>>7)&0xFFF)!=10+target):
                raise ValueError(f"triangle core {core} route not {target}")
        for i in range(15):
            t,core,axon,reserved=struct.unpack_from(
                "<4I",payload,words[17]+i*16)
            if (t,core,axon,reserved)!=(i//3,i%3,10+i%3,0):
                raise ValueError(f"triangle external event {i} differs")
            cp=struct.unpack_from("<4I",payload,words[18]+i*16)
            expected=zlib.crc32(struct.pack("<Q",states[i//3,i%3]))
            if cp!=(i//3,i%3,1,expected):
                raise ValueError(f"triangle checkpoint {i} differs from model")
        if (m["events"],m["checkpoints"],m["dispatches"],
            m["logical_core_ids_in_service_order"])!=(15,15,15,[0,1,2]):
            raise ValueError("triangle generated P05 manifest mismatch")
    except (OSError,ValueError,KeyError,TypeError,struct.error) as e:
        print("FAIL: P05.1 triangle evidence admission: "+str(e),file=sys.stderr)
        return False

    d=dict(zip(FIELDS,result))
    def expected(key: str, want: int):
        if d[key]!=want:
            errors.append(f"{key}: got=0x{d[key]:X} expected=0x{want:X}")
    expected_values={
        "magic":MAGIC,"version":1,"result":0x600D600D,"error":0,
        "steps":5,"completed_steps":5,"cores":3,"slots":3,
        "phase":18,"fault":0,"fault_phase":0,
        "dispatches":15,"packets":12,"barriers":5,
        "initial_ins":3,"replacement_ins":0,"runtime_outs":0,
        "final_outs":3,"evictions":0,"hits":15,
        "hw_id":0x4C543302,"hw_caps":0x0001031F,
        "hw_dispatches":15,"hw_pages":6,
        "hw_last_page_bytes":106496,"hw_status":0,
        "hw_pending_bytes":0,"resident_deliveries":12,
        "inputs_consumed":15,"checkpoints_passed":15,
        "failed_step":0,"failed_core":0,"failed_class":0,
        "expected_crc":0,"observed_crc":0,
        "header_crc":words[23],"payload_crc":words[22],
        "diagnostic_mode":1,"expected_events":15,
        "expected_checks":15,"expected_dispatches":15,
        "diag_flags":0,"last_page_error":0,
    }
    for key,value in expected_values.items():
        expected(key,value)
    if result[60:]!=(0,0,0,0):
        errors.append("reserved mailbox result words are nonzero")
    for key in ("cntfrq_hz","hw_read_bursts","hw_write_bursts"):
        if d[key]==0:
            errors.append(key+" unexpectedly zero")
    for low,high in (("pl_dispatch_lo","pl_dispatch_hi"),
                     ("pl_page_lo","pl_page_hi"),
                     ("ps_infer_lo","ps_infer_hi")):
        if d[low] | d[high] == 0:
            errors.append(low+" / "+high+" unexpectedly zero")
    actual_ddr=None
    ddr_error=None
    try:
        oracle=TRI.oracle_module()
        actual_ddr=oracle.verify(golden,directory/"final_ddr")
    except (OSError,ValueError,AssertionError) as e:
        ddr_error=str(e)
    if errors or ddr_error:
        for e in errors:
            print("FAIL: P05.1 triangle mailbox "+e,file=sys.stderr)
        if d["result"]!=0x600D600D:
            print("P05_TRIANGLE_FIRST_DIAGNOSTIC="+json.dumps({
                k:d[k] for k in (
                    "result","error","phase","fault","fault_phase",
                    "dispatches","packets","barriers","resident_deliveries",
                    "inputs_consumed","checkpoints_passed","failed_step",
                    "failed_core","failed_class","expected_crc",
                    "observed_crc","diag_flags","last_page_error",
                )
            },sort_keys=True),file=sys.stderr)
        print("P05_TRIANGLE_FINAL_DDR_COMPARISON="+(
            "FAIL: "+ddr_error if ddr_error else
            "PASS (three exact golden records; mailbox still FAIL)"
        ),file=sys.stderr)
        return False
    print(
        "PASS: P05.1 3-core resident triangle physical golden "
        "timesteps=5 dispatches=15 packets=12 barriers=5 "
        "events=15 checkpoints=15 resident_deliveries=12 "
        "initial_ins=3 replacement_ins=0 final_outs=3"
    )
    print("PASS: P05.1 three 512KiB final DDR records byte-exact to independent 3-core Python LogicalChip oracle")
    print("P05_TRIANGLE_METADATA="+json.dumps({
        "model_trace_sha256":model["trace_fingerprint"],
        "resident_deliveries":d["resident_deliveries"],
        "header_crc32":f"0x{words[23]:08X}",
        "payload_crc32":f"0x{words[22]:08X}",
        "record_sha256":{k:v["sha256"] for k,v in actual_ddr["records"].items()},
    },sort_keys=True))
    return True


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mailbox",required=True,type=Path)
    p.add_argument("--directory",required=True,type=Path)
    a=p.parse_args()
    raise SystemExit(0 if verify(a.mailbox,a.directory) else 1)


if __name__=="__main__":
    main()
