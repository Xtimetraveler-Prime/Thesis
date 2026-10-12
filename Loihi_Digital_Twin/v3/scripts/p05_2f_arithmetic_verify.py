#!/usr/bin/env python3
"""P05.2f strict physical five-core arithmetic / paging / routing gate."""
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
from p05_2f_arithmetic_fixture import model,read_vectors,PARAMETERS,CORES,ORDER,STEPS,SLOTS,PROFILE,load
from loihi_twin_v2.hardware_p03 import unpack_compartment_config,unpack_synapse_word

P05R=load("p05_2f_mailbox",ROOT/"scripts/p05_1_verify.py")
FIELDS=P05R.FIELDS

def verify(mailbox:Path, folder:Path)->bool:
    try:
        raw=mailbox.read_bytes()
        if len(raw)!=256:raise ValueError("missing/short 256-byte physical P05R mailbox")
        words=struct.unpack("<64I",raw)
        observed=dict(zip(FIELDS,words))
        gate=json.loads((folder/"p05_2f_gate.json").read_text())
        spec=json.loads((folder/"p05_2f_arithmetic_spec.json").read_text())
        art=folder/"p05_artifacts"
        header=(art/"p05_header.bin").read_bytes()
        payload=(art/"p05_payload.bin").read_bytes()
        hw=struct.unpack("<64I",header)
        man=json.loads((art/"p05_manifest.json").read_text())
        golden=folder/"arithmetic_golden"
        golden_man=json.loads((golden/"manifest.json").read_text())
        if gate["profile"]!=PROFILE or gate["parameters"]!={str(k):v for k,v in PARAMETERS.items()}:
            raise ValueError("neuron boundary parameters or profile changed")
        if (gate["cores"],gate["order"],gate["steps"],gate["slots"])!=(
            list(CORES),list(ORDER),STEPS,SLOTS):
            raise ValueError("core/service-order/timestep configuration drift")
        if (hw[0],hw[1],hw[2],hw[3],hw[4],hw[5],hw[6],
            hw[13],hw[14],hw[20])!=(0x47353050,1,256,1,6,5,3,30,30,30):
            raise ValueError("P05G hardware deployment dimensions changed")
        if len(payload)!=hw[12] or len(payload)>0xE0000 or (
            hw[17],hw[18])!=(5*32,5*32+30*16):
            raise ValueError("P05G payload layout/size invalid")
        if hw[22]!=zlib.crc32(payload) or hw[23]!=zlib.crc32(
            header[:92]+bytes(4)+header[96:]):
            raise ValueError("P05G CRC mismatch")
        if (gate["p05_header_sha256"]!=man["header_sha256"]!=hashlib.sha256(header).hexdigest()
            or gate["p05_payload_sha256"]!=man["payload_sha256"]!=hashlib.sha256(payload).hexdigest()
            or gate["p05_input_spec_sha256"]!=man["input_spec_sha256"]!=hashlib.sha256(
                (folder/"p05_2f_arithmetic_spec.json").read_bytes()).hexdigest()):
            raise ValueError("P05G SHA identity mismatch")
        if (spec["schema"]!="p05-regression-deployment-v1" or
            spec["mode"]!="diagnostic" or spec["timesteps"]!=6 or
            [x["id"] for x in spec["cores"]]!=list(ORDER) or
            man["logical_core_ids_in_service_order"]!=list(ORDER)):
            raise ValueError("P05G spec mode, IDs or order drift")
        if (golden_man["logical_core_ids"]!=list(CORES) or
            golden_man["service_order"]!=list(ORDER) or
            golden_man["timesteps"]!=STEPS or
            golden_man["dispatch_count"]!=30 or
            gate["oracle_trace_sha256"]!=golden_man["trace_fingerprint"] or
            gate["oracle_manifest_sha256"]!=hashlib.sha256(
                (golden/"manifest.json").read_bytes()).hexdigest()):
            raise ValueError("independent Python oracle provenance mismatch")
        oracle=model()
        images=oracle.export_paged_hardware_image(
            oracle.make_workload(),resident_context_count=SLOTS
        ).backing_by_logical_core
        for rank,cid in enumerate(ORDER):
            initial=(golden/f"core{cid}_initial.bin").read_bytes()
            staged=(art/f"core{cid}_initial.bin").read_bytes()
            meta=cid|(1<<7)|(1<<18)|(1<<34)
            fields=struct.unpack_from("<8I",payload,rank*32)
            if (len(initial)!=0x80000 or staged!=initial or
                fields[0]!=cid or fields[1]|(fields[2]<<32)!=meta or
                fields[3]!=struct.unpack_from("<I",initial,0x1000)[0] or
                fields[4]!=zlib.crc32(initial) or fields[5]!=10+cid or
                fields[6:]!=(0,0)):
                raise ValueError(f"core {cid} initial DDR/P05G descriptor mismatch")
            packed_config=int.from_bytes(initial[0x1000:0x1010],"little")
            config=unpack_compartment_config(packed_config)
            parameters=PARAMETERS[cid]
            for key in ("current_decay","voltage_decay","threshold","bias","refractory_ticks"):
                if config[key]!=parameters[key]:
                    raise ValueError(f"core {cid} packed config {key} differs from independent target")
            packed_synapse=int.from_bytes(initial[0x30000:0x30008],"little")
            if unpack_synapse_word(packed_synapse)["weight"]!=parameters["weight"]:
                raise ValueError(f"core {cid} physical packed signed weight drift")
            if images[cid].image.route_count!=1:
                raise ValueError("physical route count drift")
        states=read_vectors(golden,"P02B_EXPECT_STATE")
        packets=read_vectors(golden,"P02B_EXPECT_PACKETS")
        from p05_2_composite_fixture import scheduler_prediction
        replay=scheduler_prediction(packets)
        if (replay!=gate["scheduler_model"] or
            gate["expected_packets"]!=replay["emitted_packets"] or
            golden_man["expected_packet_count_total"]!=replay["emitted_packets"]):
            raise ValueError("model packet counts/scheduler replay drift")
        for idx in range(30):
            t,cid=divmod(idx,5)
            cid=ORDER[cid]
            erow=struct.unpack_from("<4I",payload,hw[17]+16*idx)
            crow=struct.unpack_from("<4I",payload,hw[18]+16*idx)
            want_crc=zlib.crc32(struct.pack("<Q",states[t,cid]))
            if erow!=(t,cid,10+cid,0) or crow!=(t,cid,1,want_crc):
                raise ValueError(f"event/checkpoint {idx} not independent-model-derived")
        for cid in CORES:
            gold=(golden/f"core{cid}_expected.bin").read_bytes()
            digest=hashlib.sha256(gold).hexdigest()
            if (len(gold)!=0x80000 or
                digest!=gate["oracle_final_record_sha256"][str(cid)] or
                digest!=golden_man["expected_final_record_sha256"][str(cid)]):
                raise ValueError(f"core{cid} oracle DDR digest drift")
    except (OSError,ValueError,AssertionError,KeyError,TypeError,struct.error) as e:
        print("FAIL: P05.2f independent evidence admission: "+str(e),file=sys.stderr)
        return False

    want={
        "magic":0x52353050,"version":1,"result":0x600D600D,
        "error":0,"steps":STEPS,"completed_steps":STEPS,
        "cores":5,"slots":3,"phase":18,"fault":0,"fault_phase":0,
        "dispatches":30,"packets":replay["emitted_packets"],
        "barriers":STEPS,"initial_ins":3,
        "replacement_ins":replay["replacement_ins"],
        "runtime_outs":replay["runtime_outs"],
        "final_outs":replay["final_outs"],
        "evictions":replay["evictions"],"hits":replay["hits"],
        "resident_deliveries":replay["resident_deliveries"],
        "inputs_consumed":30,"checkpoints_passed":30,
        "hw_id":0x4C543302,"hw_caps":0x0001031F,
        "hw_dispatches":30,"hw_pages":replay["page_commands"],
        "hw_last_page_bytes":106496,"hw_status":0,"hw_pending_bytes":0,
        "failed_step":0,"failed_core":0,"failed_class":0,
        "expected_crc":0,"observed_crc":0,"header_crc":hw[23],
        "payload_crc":hw[22],"diagnostic_mode":1,
        "expected_events":30,"expected_checks":30,"expected_dispatches":30,
        "diag_flags":0,"last_page_error":0,
    }
    errors=[f"{key}: 0x{observed[key]:X} != 0x{expected:X}"
            for key,expected in want.items() if observed[key]!=expected]
    if words[60:]!=(0,0,0,0):
        errors.append("reserved terminal mailbox words nonzero")
    for key in ("cntfrq_hz","hw_read_bursts","hw_write_bursts"):
        if observed[key]<=0: errors.append(key+" not positive")
    for lo,hi in (("pl_dispatch_lo","pl_dispatch_hi"),
                  ("pl_page_lo","pl_page_hi"),
                  ("ps_infer_lo","ps_infer_hi")):
        if observed[lo]|observed[hi]==0:
            errors.append(lo+" unexpectedly zero")
    try:
        # Five FULL 512KiB actual device images; no excluded packet or trace
        # bank, no comparison against anything learned from physical outputs.
        ddr=oracle.verify(golden,folder/"final_ddr")
    except (OSError,ValueError,AssertionError) as e:
        errors.append("full golden DDR: "+str(e))
        ddr=None
    if errors:
        for e in errors:print("FAIL: P05.2f "+e,file=sys.stderr)
        print("P05_2F_VERIFY_EXIT=1",file=sys.stderr)
        return False
    print("PASS: P05.2f physical five-over-three signed/decay/saturation/refractory"+
          f" steps=6 dispatches=30 packets={replay['emitted_packets']} "+
          f"resident_deliveries={replay['resident_deliveries']} "+
          f"nonresident_deliveries={replay['nonresident_deliveries']} "+
          f"barriers=6 checkpoints=30 evictions={replay['evictions']}")
    print("PASS: P05.2f five complete 512KiB physical DDR images byte-exact to independent signed 24-bit LogicalChip reference")
    print("P05_2F_METADATA="+json.dumps({
        "trace_reference_sha256":golden_man["trace_fingerprint"],
        "physical_records_sha256":{str(i):ddr["records"][str(i)]["sha256"] for i in CORES},
        "programmed_payload_bytes_NOT_AXIBUS":replay["programmed_total_page_payload_bytes"],
        "pl_dispatch_cycles_RAW":observed["pl_dispatch_lo"]|(observed["pl_dispatch_hi"]<<32),
        "pl_page_cycles_RAW":observed["pl_page_lo"]|(observed["pl_page_hi"]<<32),
        "ps_inference_ticks_RAW":observed["ps_infer_lo"]|(observed["ps_infer_hi"]<<32),
    },sort_keys=True))
    print("P05_2F_VERIFY_EXIT=0")
    return True

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mailbox",required=True,type=Path)
    p.add_argument("--directory",required=True,type=Path)
    a=p.parse_args()
    return 0 if verify(a.mailbox,a.directory) else 1

if __name__=="__main__":
    raise SystemExit(main())
