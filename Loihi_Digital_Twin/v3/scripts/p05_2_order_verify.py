#!/usr/bin/env python3
"""P05.2c order-invariant physical golden: reordered [2,0,1] service.

The live KV260 P05R is checked against the independently simulated
permuted-order LogicalChip and byte-exact whole-image DDR oracle,
AND the previous physically accepted original-order DDR SHA identities.
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


def load(name:str,path:Path):
    sp=importlib.util.spec_from_file_location(name,path)
    assert sp is not None and sp.loader is not None
    module=importlib.util.module_from_spec(sp)
    sp.loader.exec_module(module)
    return module


MODEL=load("p05_2c_order_reference",ROOT/"scripts/p05_2_order_fixture.py")
TRI=load("p05_2c_triangle_config",ROOT/"scripts/p05_1_triangle_fixture.py")
FIELDS=load("p05_2c_result_layout",ROOT/"scripts/p05_1_verify.py").FIELDS


def verify(mailbox:Path,root:Path)->bool:
    errors=[]
    try:
        rraw=mailbox.read_bytes()
        if len(rraw)!=256:raise ValueError("exact 256-byte A53 mailbox required")
        w=struct.unpack("<64I",rraw)
        d=dict(zip(FIELDS,w))
        g=json.loads((root/"p05_2_order_gate.json").read_text())
        s=json.loads((root/"p05_2_order_spec.json").read_text())
        base=json.loads((root/"triangle_spec.json").read_text())
        base_gate=json.loads((root/"triangle_gate.json").read_text())
        m=json.loads((root/"p05_artifacts/p05_manifest.json").read_text())
        original=json.loads((root/"triangle_golden/manifest.json").read_text())
        permuted=json.loads((root/"reordered_golden/manifest.json").read_text())
        hb=(root/"p05_artifacts/p05_header.bin").read_bytes()
        pb=(root/"p05_artifacts/p05_payload.bin").read_bytes()
        h=struct.unpack("<64I",hb)
        if (g["profile"]!=MODEL.PROFILE or
            g["permuted_service_order"]!=list(MODEL.ORDER) or
            g["original_order"]!=list(MODEL.BASELINE)):
            raise ValueError("unexpected source service permutation")
        if g["accepted_original_service_order_physical_sha256"]!=MODEL.ACCEPTED_RECORD_SHA:
            raise ValueError("tampered accepted original physical SHA anchors")
        if (h[0],h[1],h[2],h[3],h[4],h[5],h[6],
            h[13],h[14],h[20])!=(
            0x47353050,1,256,1,5,3,3,15,15,15):
            raise ValueError("bad permuted P05G deployment header")
        if h[12]!=len(pb) or h[12]>0xE0000:
            raise ValueError("invalid P05G payload size")
        if h[22]!=zlib.crc32(pb) or (
            h[23]!=zlib.crc32(hb[:92]+bytes(4)+hb[96:])):
            raise ValueError("bad P05G binary CRC")
        if (g["p05_header_sha256"]!=m["header_sha256"]!=
                hashlib.sha256(hb).hexdigest() or
            g["p05_payload_sha256"]!=m["payload_sha256"]!=
                hashlib.sha256(pb).hexdigest() or
            g["p05_input_spec_sha256"]!=m["input_spec_sha256"]!=
                hashlib.sha256((root/"p05_2_order_spec.json").read_bytes()).hexdigest()):
            raise ValueError("P05G actual staged SHA drift")
        if (s["mode"]!="diagnostic" or s["timesteps"]!=5 or
            s["slot_count"]!=3 or s["schema"]!="p05-regression-deployment-v1" or
            [x["id"] for x in s["cores"]]!=list(MODEL.ORDER) or
            m["logical_core_ids_in_service_order"]!=list(MODEL.ORDER)):
            raise ValueError("P05G service order/spec/manifest disagree")
        if (s["events"]!=[
                {"timestep":t,"core":core,"axon":10+core}
                for t in range(5) for core in MODEL.ORDER]):
            raise ValueError("new spec changes or omits neural event inputs")
        if {tuple(sorted(e.items())) for e in s["events"]}!={
             tuple(sorted(e.items())) for e in base["events"]}:
            raise ValueError("service permutation changed external spike multiset")
        if not (base["mode"]=="diagnostic" and
                [x["id"] for x in base["cores"]]==list(MODEL.BASELINE) and
                len(base["checkpoints"])==15 and len(s["checkpoints"])==15):
            raise ValueError("original baseline spec drift")
        if (original["expected_packet_count_total"],
            permuted["expected_packet_count_total"],
            permuted["dispatch_count"])!=(12,12,15):
            raise ValueError("independently simulated packet count mismatch")
        if (g["baseline_model_trace_sha256"]!=original["trace_fingerprint"] or
            g["permuted_model_trace_sha256"]!=permuted["trace_fingerprint"] or
            g["baseline_model_manifest_sha256"]!=hashlib.sha256(
                (root/"triangle_golden/manifest.json").read_bytes()).hexdigest() or
            g["permuted_model_manifest_sha256"]!=hashlib.sha256(
                (root/"reordered_golden/manifest.json").read_bytes()).hexdigest()):
            raise ValueError("permuted and original model identities drift")
        states=MODEL.states(root/"reordered_golden")
        baseline_states=MODEL.states(root/"triangle_golden")
        if states!=baseline_states:
            raise ValueError("independent model says service order changes neural state")
        if (h[17],h[18])!=(3*32,3*32+15*16):
            raise ValueError("bad ordered event/checkpoint offsets")
        for n,core in enumerate(MODEL.ORDER):
            row=struct.unpack_from("<8I",pb,n*32)
            alt=(root/"reordered_golden"/f"core{core}_initial.bin").read_bytes()
            orig=(root/"triangle_golden"/f"core{core}_initial.bin").read_bytes()
            staged=(root/"p05_artifacts"/f"core{core}_initial.bin").read_bytes()
            if (row[0]!=core or row[4]!=zlib.crc32(alt) or
                row[5]!=10+core or row[6:]!=(0,0) or
                len(alt)!=0x80000 or alt!=orig or staged!=alt):
                raise ValueError(f"permuted record {core} corrupted")
        for i in range(15):
            step=i//3
            core=MODEL.ORDER[i%3]
            erow=struct.unpack_from("<4I",pb,h[17]+16*i)
            crow=struct.unpack_from("<4I",pb,h[18]+16*i)
            crc=zlib.crc32(struct.pack("<Q",states[step,core]))
            if erow!=(step,core,10+core,0):
                raise ValueError(f"permuted ingress event {i} invalid")
            if crow!=(step,core,1,crc):
                raise ValueError(f"permuted state checkpoint {i} invalid")
            if s["checkpoints"][i]!={
                    "timestep":step,"core":core,
                    "state_class":"state0",
                    "expected_crc32":f"0x{crc:08X}"}:
                raise ValueError(f"source checkpoint {i} mismatch")
        for core in MODEL.BASELINE:
            expected=(root/"reordered_golden"/f"core{core}_expected.bin").read_bytes()
            normal=(root/"triangle_golden"/f"core{core}_expected.bin").read_bytes()
            sha=hashlib.sha256(expected).hexdigest()
            if (expected!=normal or
                sha!=MODEL.ACCEPTED_RECORD_SHA[str(core)] or
                g["expected_final_record_sha256"][str(core)]!=sha):
                raise ValueError(f"model golden order sensitivity core {core}")
    except (OSError,ValueError,KeyError,TypeError,struct.error) as e:
        print("FAIL: P05.2c service-order evidence admission: "+str(e),file=sys.stderr)
        return False

    expected={
        "magic":0x52353050,"version":1,"result":0x600D600D,
        "error":0,"steps":5,"completed_steps":5,
        "cores":3,"slots":3,"phase":18,"fault":0,"fault_phase":0,
        "dispatches":15,"packets":12,"barriers":5,
        "initial_ins":3,"replacement_ins":0,"runtime_outs":0,
        "final_outs":3,"evictions":0,"hits":15,
        "hw_id":0x4C543302,"hw_caps":0x1031F,
        "hw_dispatches":15,"hw_pages":6,
        "hw_last_page_bytes":106496,
        "hw_status":0,"hw_pending_bytes":0,
        "resident_deliveries":12,
        "inputs_consumed":15,"checkpoints_passed":15,
        "failed_step":0,"failed_core":0,"failed_class":0,
        "expected_crc":0,"observed_crc":0,
        "header_crc":h[23],"payload_crc":h[22],
        "diagnostic_mode":1,"expected_events":15,
        "expected_checks":15,"expected_dispatches":15,
        "diag_flags":0,"last_page_error":0,
    }
    for name,val in expected.items():
        if d[name]!=val:
            errors.append(f"{name} actual=0x{d[name]:X} expected=0x{val:X}")
    if w[60:]!=(0,0,0,0):
        errors.append("reserved P05R words not zero")
    for name in ("cntfrq_hz","hw_read_bursts","hw_write_bursts"):
        if not d[name]:errors.append(f"{name} must be positive")
    for low,high in (("pl_dispatch_lo","pl_dispatch_hi"),
                     ("pl_page_lo","pl_page_hi"),
                     ("ps_infer_lo","ps_infer_hi")):
        if (d[low]|d[high])==0:
            errors.append(f"{low} must be positive")
    ddr=None
    ddr_error=None
    try:
        reordered_oracle=TRI.oracle_module()
        reordered_oracle.SERVICE_ORDER=MODEL.ORDER
        ddr=reordered_oracle.verify(root/"reordered_golden",root/"final_ddr")
        normal_oracle=TRI.oracle_module()
        normal_oracle.verify(root/"triangle_golden",root/"final_ddr")
        for core in MODEL.BASELINE:
            physical_sha=ddr["records"][str(core)]["sha256"]
            if physical_sha!=MODEL.ACCEPTED_RECORD_SHA[str(core)]:
                errors.append(f"core {core} differs from previously accepted original-order KV260 SHA256")
    except (OSError,ValueError,AssertionError) as e:
        ddr_error=str(e)
    if errors or ddr_error:
        for error in errors:
            print("FAIL: P05.2c service-order mailbox/data "+error,file=sys.stderr)
        print("P05_2_ORDER_FINAL_DDR="+(
            "FAIL "+ddr_error if ddr_error else "PASS (mailbox still failed)"
        ),file=sys.stderr)
        return False
    print(
        "PASS: P05.2c permuted service-order physical golden "
        "order=2,0,1 timesteps=5 dispatches=15 packets=12 "
        "resident_deliveries=12 barriers=5 events=15 checkpoints=15"
    )
    print(
        "PASS: P05.2c three full 512KiB DDR records byte-exact to "
        "BOTH independently reordered and baseline Python models "
        "and previously accepted original-order KV260 physical SHA256s"
    )
    print("P05_2_ORDER_METADATA="+json.dumps({
        "service_order":list(MODEL.ORDER),
        "reference_trace_sha256":permuted["trace_fingerprint"],
        "header_crc32":f"0x{h[23]:08X}",
        "payload_crc32":f"0x{h[22]:08X}",
        "record_sha256":{str(core):ddr["records"][str(core)]["sha256"]
                         for core in MODEL.BASELINE},
    },sort_keys=True))
    return True


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mailbox",type=Path,required=True)
    ap.add_argument("--directory",type=Path,required=True)
    args=ap.parse_args()
    return 0 if verify(args.mailbox,args.directory) else 1


if __name__=="__main__":
    raise SystemExit(main())
