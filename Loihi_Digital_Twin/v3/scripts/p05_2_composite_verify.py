#!/usr/bin/env python3
"""P05.2e strict FIVE-over-THREE composite KV260 physical evidence verifier.

Every expected actual-device P05R field (including 5-over-3 dirty
paging/eviction and resident/nonresident packet counts) is independently
reconstructed from the immutable deployment, separate LogicalChip
neural golden/packet vectors, and separately implemented accepted
round-robin scheduler. Finally compare FIVE complete physical 512KiB
DDR images, not only state words or a claimed mailbox PASS.
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
    assert spec is not None and spec.loader is not None
    instance=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(instance)
    return instance


MODEL=load("p05_2e_composite_neural",ROOT/"scripts/p05_2_composite_fixture.py")
PHYSICAL_PACKET_LAYOUT=load(
    "p05_2e_route_packet_order",
    ROOT/"scripts/p05_2_packet_layout.py"
)
FIELDS=load("p05_2e_p05r",ROOT/"scripts/p05_1_verify.py").FIELDS


def verify(mailbox:Path,folder:Path)->bool:
    try:
        blob=mailbox.read_bytes()
        if len(blob)!=256:
            raise ValueError("P05R physical mailbox must be exactly 256 bytes")
        words=struct.unpack("<64I",blob)
        d=dict(zip(FIELDS,words))
        gate=json.loads((folder/"p05_2_composite_gate.json").read_text())
        spec=json.loads((folder/"p05_2_composite_spec.json").read_text())
        man=json.loads((folder/"p05_artifacts/p05_manifest.json").read_text())
        model_man=json.loads((folder/"composite_golden/manifest.json").read_text())
        head=(folder/"p05_artifacts/p05_header.bin").read_bytes()
        payload=(folder/"p05_artifacts/p05_payload.bin").read_bytes()
        h=struct.unpack("<64I",head)
        if (gate["profile"]!=MODEL.PROFILE or
            gate["logical_cores"]!=list(MODEL.CORES) or
            gate["service_order"]!=list(MODEL.ORDER) or
            gate["slots"]!=MODEL.SLOTS or gate["timesteps"]!=MODEL.TIMESTEPS):
            raise ValueError("unexpected five-over-three composite profile")
        if (gate["threshold_by_core"]!={str(c):MODEL.THRESHOLDS[c]
               for c in MODEL.CORES} or
            gate["two_outgoing_destinations_per_core"]!={str(c):
                [(c+1)%5,(c+2)%5] for c in MODEL.CORES}):
            raise ValueError("neural threshold / fanout source profile drift")
        if (h[0],h[1],h[2],h[3],h[4],h[5],h[6],
            h[13],h[14],h[20])!=(
            0x47353050,1,256,1,8,5,3,40,40,40):
            raise ValueError("composite P05G binary dimensions invalid")
        if len(payload)!=h[12] or not 0<h[12]<=0xE0000 or (
            h[17],h[18])!=(5*32,5*32+40*16):
            raise ValueError("composite P05G byte offsets invalid")
        if h[22]!=zlib.crc32(payload) or (
            h[23]!=zlib.crc32(head[:92]+bytes(4)+head[96:])):
            raise ValueError("composite P05G binary CRC mismatch")
        if (gate["p05_header_sha256"]!=man["header_sha256"]!=
            hashlib.sha256(head).hexdigest() or
            gate["p05_payload_sha256"]!=man["payload_sha256"]!=
            hashlib.sha256(payload).hexdigest() or
            gate["p05_input_spec_sha256"]!=man["input_spec_sha256"]!=
            hashlib.sha256((folder/"p05_2_composite_spec.json").read_bytes()).hexdigest()):
            raise ValueError("composite P05G manifest/SHA mismatch")
        if (spec["schema"]!="p05-regression-deployment-v1" or
            spec["mode"]!="diagnostic" or spec["timesteps"]!=8 or
            spec["slot_count"]!=3 or
            [r["id"] for r in spec["cores"]]!=list(MODEL.ORDER) or
            man["logical_core_ids_in_service_order"]!=list(MODEL.ORDER) or
            (man["dispatches"],man["events"],man["checkpoints"])!=(40,40,40)):
            raise ValueError("composite core service order / event-count drift")
        if (model_man["logical_core_ids"]!=list(MODEL.CORES) or
            model_man["service_order"]!=list(MODEL.ORDER) or
            model_man["timesteps"]!=MODEL.TIMESTEPS or
            model_man["dispatch_count"]!=40 or
            model_man["resident_context_count"]!=3):
            raise ValueError("independent composite LogicalChip shape changed")
        if (gate["trace_reference_sha256"]!=model_man["trace_fingerprint"] or
            gate["oracle_manifest_sha256"]!=hashlib.sha256(
                (folder/"composite_golden/manifest.json").read_bytes()).hexdigest()):
            raise ValueError("composite model golden fingerprint changed")
        # TWO separate oracles: logical spike model preserves normalized
        # destination-sorted traces; the physical packet bank follows
        # the registered output-route descriptor order. The latter is
        # derived solely from original model vectors/configuration, not
        # physical output, and leaves all original records untouched.
        packet_layout=PHYSICAL_PACKET_LAYOUT.derive(folder)
        if packet_layout["original_logical_manifest_sha256"]!=(
            gate["oracle_manifest_sha256"]
        ):
            raise ValueError("packet layout derivation is not based on frozen model")
        if "physical_route_order_final_record_sha256" in gate and (
            gate["physical_route_order_final_record_sha256"]!=
            packet_layout["physical_full_record_sha256"]
        ):
            raise ValueError("physical packet golden SHA mismatch")
        if "physical_packet_layout_proof_sha256" in gate and (
            gate["physical_packet_layout_proof_sha256"]!=hashlib.sha256(
                (folder/PHYSICAL_PACKET_LAYOUT.LEDGER).read_bytes()
            ).hexdigest()
        ):
            raise ValueError("physical packet-model derivation ledger SHA changed")
        state=MODEL.vectors(folder/"composite_golden","P02B_EXPECT_STATE")
        ingress=MODEL.vectors(folder/"composite_golden","P02B_EXPECT_EVENT_COUNT")
        packet=MODEL.vectors(folder/"composite_golden","P02B_EXPECT_PACKETS")
        sim=MODEL.scheduler_prediction(packet)
        if sim!=gate["scheduler_model"]:
            raise ValueError("composite independent scheduling predictions disagree with gate")
        if (sim["emitted_packets"]!=model_man["expected_packet_count_total"] or
            sim["resident_deliveries"]<=0 or sim["nonresident_deliveries"]<=0 or
            sim["replacement_ins"]<20 or sim["runtime_outs"]<20 or
            sim["evictions"]<20 or sim["max_packets_from_dispatch"]!=2 or
            max(ingress.values())<3):
            raise ValueError("composite no longer covers dirty paging and mixed destinations")
        if gate["max_current_events_per_core"]!=max(ingress.values()):
            raise ValueError("model ingress multiplicity drift")
        config=MODEL.model()
        hw_image=config.export_paged_hardware_image(
            config.make_workload(),resident_context_count=MODEL.SLOTS
        ).backing_by_logical_core
        for rank,cid in enumerate(MODEL.ORDER):
            image=hw_image[cid].image
            staged=(folder/"p05_artifacts"/f"core{cid}_initial.bin").read_bytes()
            golden=(folder/"composite_golden"/f"core{cid}_initial.bin").read_bytes()
            row=struct.unpack_from("<8I",payload,rank*32)
            meta=(cid | image.compartment_count<<7 |
                  image.synapse_count<<18 | image.route_count<<34)
            if (row[0]!=cid or (row[1]|row[2]<<32)!=meta or
                row[3]!=struct.unpack_from("<I",golden,0x1000)[0] or
                row[4]!=zlib.crc32(golden) or row[5]!=10+cid or
                row[6:]!=(0,0) or len(staged)!=0x80000 or
                staged!=golden or image.route_count!=2):
                raise ValueError(f"composite core {cid} real context descriptor differs")
            # Confirm model-generated packed compartment threshold.
            packed=int.from_bytes(golden[0x1000:0x1010],"little")
            if (packed>>26)&0xFFFFFF!=MODEL.THRESHOLDS[cid]:
                raise ValueError(f"composite packed threshold differs core {cid}")
        for index in range(40):
            t=index//5
            cid=MODEL.ORDER[index%5]
            erow=struct.unpack_from("<4I",payload,h[17]+16*index)
            crow=struct.unpack_from("<4I",payload,h[18]+16*index)
            crc=zlib.crc32(struct.pack("<Q",state[t,cid]))
            if erow!=(t,cid,10+cid,0):
                raise ValueError(f"composite event {index} no longer original model input")
            if crow!=(t,cid,1,crc):
                raise ValueError(f"composite checkpoint {index} CRC deviates from model")
            if spec["events"][index]!={"timestep":t,"core":cid,"axon":10+cid}:
                raise ValueError(f"composite input specification row {index} changed")
        for cid in MODEL.CORES:
            expected=(folder/"composite_golden"/f"core{cid}_expected.bin").read_bytes()
            sha=hashlib.sha256(expected).hexdigest()
            if (len(expected)!=0x80000 or
                sha!=model_man["expected_final_record_sha256"][str(cid)] or
                sha!=gate["oracle_final_record_sha256"][str(cid)]):
                raise ValueError(f"composite independently modeled full DDR SHA drift for {cid}")
    except (OSError,ValueError,AssertionError,KeyError,TypeError,struct.error) as e:
        print("FAIL: P05.2e composite evidence admission: "+str(e),file=sys.stderr)
        return False

    wants={
        "magic":0x52353050,"version":1,"result":0x600D600D,
        "error":0,"steps":8,"completed_steps":8,"cores":5,"slots":3,
        "phase":18,"fault":0,"fault_phase":0,
        "dispatches":40,"packets":sim["emitted_packets"],
        "barriers":8,"initial_ins":3,
        "replacement_ins":sim["replacement_ins"],
        "runtime_outs":sim["runtime_outs"],
        "final_outs":sim["final_outs"],
        "evictions":sim["evictions"],"hits":sim["hits"],
        "resident_deliveries":sim["resident_deliveries"],
        "inputs_consumed":40,"checkpoints_passed":40,
        "hw_id":0x4C543302,"hw_caps":0x0001031F,
        "hw_dispatches":40,"hw_pages":sim["page_commands"],
        "hw_last_page_bytes":106496,
        "hw_status":0,"hw_pending_bytes":0,
        "failed_step":0,"failed_core":0,"failed_class":0,
        "expected_crc":0,"observed_crc":0,
        "header_crc":h[23],"payload_crc":h[22],
        "diagnostic_mode":1,"expected_events":40,
        "expected_checks":40,"expected_dispatches":40,
        "diag_flags":0,"last_page_error":0,
    }
    errors=[]
    for key,want in wants.items():
        if d[key]!=want:
            errors.append(f"{key}: 0x{d[key]:08X} != 0x{want:08X}")
    if words[60:]!=(0,0,0,0):
        errors.append("result mailbox reserved words nonzero")
    for key in ("cntfrq_hz","hw_read_bursts","hw_write_bursts"):
        if d[key]<=0:errors.append(key+" not positive")
    for low,high in (
        ("pl_dispatch_lo","pl_dispatch_hi"),
        ("pl_page_lo","pl_page_hi"),
        ("ps_infer_lo","ps_infer_hi"),
    ):
        if d[low]|d[high]==0:
            errors.append(low+" unexpectedly zero")
    ddr=None
    ddr_error=None
    try:
        # Do NOT compare physical HLS packet bank word indices against
        # the Loihi logical model's sorted packet trace. Core3 physical
        # route order [4,0] is distinct from normalized [0,4].
        # ALL other record banks remain byte-exact to that original
        # independent model; this is not a masked/bank-skipped check.
        ddr=MODEL.model().verify(
            folder/PHYSICAL_PACKET_LAYOUT.OUTPUT_DIR,
            folder/"final_ddr"
        )
        for core in MODEL.CORES:
            sha=ddr["records"][str(core)]["sha256"]
            if sha!=packet_layout["physical_full_record_sha256"][str(core)]:
                errors.append(f"core{core} physical-route-order complete DDR SHA drift {sha}")
    except (OSError,AssertionError,ValueError) as e:
        ddr_error=str(e)
    if errors or ddr_error:
        for e in errors:
            print("FAIL: P05.2e composite mailbox or golden "+e,file=sys.stderr)
        print("P05_2E_COMPOSITE_FINAL_DDR="+(
            "FAIL "+ddr_error if ddr_error else "PASS (mailbox still rejected)"
        ),file=sys.stderr)
        if d["result"]!=0x600D600D:
            print("P05_2E_COMPOSITE_FIRST_DIAGNOSTIC="+json.dumps({
                k:d[k] for k in (
                    "result","error","fault","fault_phase",
                    "dispatches","packets","barriers","resident_deliveries",
                    "checkpoints_passed","failed_step","failed_core",
                    "failed_class","expected_crc","observed_crc"
                )},sort_keys=True),file=sys.stderr)
        return False
    print(
        "PASS: P05.2e physical FIVE-over-THREE composite "
        f"order={','.join(map(str,MODEL.ORDER))} "
        f"steps=8 dispatches=40 packets={sim['emitted_packets']} "
        f"resident_deliveries={sim['resident_deliveries']} "
        f"nonresident_deliveries={sim['nonresident_deliveries']} "
        "barriers=8 events=40 checkpoints=40 "
        f"replacement_ins={sim['replacement_ins']} "
        f"runtime_outs={sim['runtime_outs']} evictions={sim['evictions']}"
    )
    print(
        "PASS: P05.2e five complete 512KiB physical DDR records byte-exact "
        "to independent mixed-threshold LogicalChip neural model with "
        "separately derived physical output-route packet RAM ordering"
    )
    print("P05_2E_COMPOSITE_METADATA="+json.dumps({
        "model_trace_sha256":model_man["trace_fingerprint"],
        "header_crc32":f"0x{h[23]:08X}",
        "payload_crc32":f"0x{h[22]:08X}",
        "runtime_page_operations":sim["page_commands"],
        "direct_resident_packet_deliveries":sim["resident_deliveries"],
        "ddr_nonresident_packet_deliveries":sim["nonresident_deliveries"],
        "model_max_events_per_core":gate["max_current_events_per_core"],
        "raw_neural_reference_trace_sha256":model_man["trace_fingerprint"],
        "route_order_packet_ram_core3":packet_layout["per_core"]["3"]["physical_route_destinations"],
        "physical_packet_layout_source":"original independent model's packets and registered output-route order",
        "record_sha256":{str(core):ddr["records"][str(core)]["sha256"]
                         for core in MODEL.CORES},
    },sort_keys=True))
    return True


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mailbox",type=Path,required=True)
    parser.add_argument("--directory",type=Path,required=True)
    args=parser.parse_args()
    return 0 if verify(args.mailbox,args.directory) else 1


if __name__=="__main__":
    raise SystemExit(main())
