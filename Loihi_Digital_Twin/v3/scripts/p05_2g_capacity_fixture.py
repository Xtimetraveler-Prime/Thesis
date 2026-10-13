#!/usr/bin/env python3
"""P05.2g capacity test: exact 4096 legal current-bank events and 4097 CRC-valid invalid descriptor.

Two distinct profiles. The 4097 case is a deployment-admission fault,
NOT proof of physical route backpressure. Never modify accepted P05 C/PL.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import zlib

ROOT=Path(__file__).resolve().parents[1]
SRC=str(ROOT/"src")
if SRC in sys.path:sys.path.remove(SRC)
sys.path.insert(0,SRC)
from loihi_twin_v2 import (
    LogicalCoreConfig,CompartmentConfig,InputAxonBinding,
    SynapseTemplate,SynapseEntry,LogicalChip,SpikePacket,
    P03_REQUIRED_ARITHMETIC,export_paged_hardware_image,
)
from loihi_twin_v2.hardware_p03 import pack_compartment_state
from loihi_twin_v2.ddr_abi import build_initial_ddr_context_record
from p02_4b_ring_fixture import _write_word,_trace_word
from p05_2_composite_fixture import load

PROFILE="p05-2g-one-core-4096-current-bank-v1"
CAPACITY=4096
OVER=4097
AXON=10
CORE=0
RECORD_BYTES=0x80000

def digest(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def full_model(golden:Path):
    golden.mkdir(parents=True)
    config=LogicalCoreConfig(
        core_id=CORE,
        compartments=(CompartmentConfig(
            current_decay=0,voltage_decay=0,threshold=7000
        ),),
        input_axons=(InputAxonBinding(AXON,0),),
        synapse_templates=(SynapseTemplate(
            0,(SynapseEntry(0,1),)
        ),),
        output_routes=(),
        arithmetic=P03_REQUIRED_ARITHMETIC,
    )
    backing=export_paged_hardware_image((config,),resident_context_count=1)
    img=backing.backing_by_logical_core[CORE].image
    if (img.compartment_count,img.synapse_count,img.route_count)!=(1,1,0):
        raise ValueError("unexpected exact-capacity HLS image")
    initial=build_initial_ddr_context_record(backing.backing_by_logical_core[CORE])
    if len(initial)!=RECORD_BYTES:raise ValueError("initial DDR record not 512KiB")
    external=tuple(
        SpikePacket(target_timestep=0,destination_core=CORE,destination_axon=AXON)
        for _ in range(CAPACITY)
    )
    chip=LogicalChip((config,))
    traces=chip.evaluate(external_packets=external,service_order=(CORE,))
    if len(traces)!=1:raise ValueError("not one logical core")
    trace=traces[0]
    if (len(trace.packet_in),len(trace.synaptic_contributions),
        len(trace.packets_out),len(trace.spikes_out))!=(CAPACITY,CAPACITY,0,0):
        raise ValueError("no real 4096-event integration stress")
    state=pack_compartment_state(trace.compartment_state_after[0].state)
    if (trace.compartment_state_after[0].state.current,
        trace.compartment_state_after[0].state.voltage)!=(4096,4096):
        raise ValueError("independent 4096-event arithmetic oracle unexpected")
    after=bytearray(initial)
    _write_word(after,"state",0,state)
    for idx in range(CAPACITY):
        _write_word(after,"event0",idx,AXON)
    synaptic=sum(x.weight for x in trace.synaptic_contributions)
    before=pack_compartment_state(trace.compartment_state_before[0].state)
    rawtrace=_trace_word(before,synaptic,state,False)
    _write_word(after,"trace",0,rawtrace)
    chip.drain_packets()
    chip.advance()
    first=(golden/"core0_initial.bin")
    final=(golden/"core0_expected.bin")
    first.write_bytes(initial);final.write_bytes(bytes(after))
    return {
        "state0":f"0x{state:016X}",
        "state0_crc":f"0x{zlib.crc32(struct.pack('<Q',state)):08X}",
        "event0_word0_crc":f"0x{zlib.crc32(struct.pack('<I',AXON)):08X}",
        "event1_word0_crc":f"0x{zlib.crc32(struct.pack('<I',0)):08X}",
        "trace0_crc":f"0x{zlib.crc32(rawtrace.to_bytes(32,'little')):08X}",
        "event0_bank_sha256":hashlib.sha256(after[0x54000:0x58000]).hexdigest(),
        "initial_record_sha256":digest(first),
        "final_record_sha256":digest(final),
        "trace_word":f"0x{rawtrace:064X}",
        "hardware_meta":f"0x{(CORE|(1<<7)|(1<<18)):016X}",
    }

def make(root:Path):
    if root.exists():raise ValueError("refuse to overwrite P05.2g evidence")
    full=root/"full"
    over=root/"overflow"
    full.mkdir(parents=True)
    over.mkdir()
    gold=full/"capacity_golden"
    oracle=full_model(gold)
    (gold/"manifest.json").write_text(json.dumps(oracle,indent=2,sort_keys=True)+"\n")
    spec={
        "schema":"p05-regression-deployment-v1",
        "timesteps":1,"slot_count":1,"mode":"diagnostic",
        "cores":[{
            "id":0,"metadata":oracle["hardware_meta"],
            "input_axon":AXON,"record":str((gold/"core0_initial.bin").resolve()),
        }],
        "events":[{"timestep":0,"core":CORE,"axon":AXON} for _ in range(CAPACITY)],
        "checkpoints":[
            {"timestep":0,"core":0,"state_class":"state0",
             "expected_crc32":oracle["state0_crc"]},
            {"timestep":0,"core":0,"state_class":"event0",
             "expected_crc32":oracle["event0_word0_crc"]},
            {"timestep":0,"core":0,"state_class":"event1",
             "expected_crc32":oracle["event1_word0_crc"]},
        ],
    }
    sp=full/"p05_2g_full_spec.json"
    sp.write_text(json.dumps(spec,indent=2,sort_keys=True)+"\n")
    b=load("p05_2g_deployment_builder",ROOT/"scripts/p05_deployment.py")
    built=b.build(sp,full/"p05_artifacts")
    if (built["events"],built["checkpoints"],built["dispatches"])!=(4096,3,1):
        raise ValueError("4096 legal P05G builder fixture shape changed")
    if (full/"p05_artifacts/core0_initial.bin").read_bytes()!=(
        gold/"core0_initial.bin").read_bytes():
        raise ValueError("full deployment core image differs from golden")
    (full/"p05_mailbox_zero.bin").write_bytes(bytes(256))
    full_gate={
        "profile":PROFILE,"status":"MODEL_ONLY_NOT_HARDWARE_ACCEPTED",
        "max_event_bank_depth":CAPACITY,"event_count":CAPACITY,
        "timesteps":1,"cores":1,"slots":1,"dispatches":1,
        "barriers":1,"packets":0,"checkpoints":3,
        "initial_page_ins":1,"replacement_page_ins":0,
        "dirty_runtime_outs":0,"final_page_outs":1,"hw_page_commands":2,
        "model":oracle,
        "p05_header_sha256":built["header_sha256"],
        "p05_payload_sha256":built["payload_sha256"],
        "p05_input_spec_sha256":built["input_spec_sha256"],
        "model_manifest_sha256":digest(gold/"manifest.json"),
    }
    (full/"p05_2g_full_gate.json").write_text(
        json.dumps(full_gate,indent=2,sort_keys=True)+"\n")
    # The legal builder MUST reject 4097 events. We then construct a
    # deliberately CRC-VALID descriptor solely to test the device-side
    # P05 admission guard, with one and ONLY one extra event.
    invalid=dict(spec)
    invalid["events"]=[*spec["events"],{"timestep":0,"core":CORE,"axon":AXON}]
    bad_spec=over/"p05_2g_overflow_spec.json"
    bad_spec.write_text(json.dumps(invalid,indent=2,sort_keys=True)+"\n")
    try:
        b.build(bad_spec,over/"must_not_exist")
    except ValueError as err:
        if "event overflow" not in str(err):raise
    else:
        raise ValueError("host builder incorrectly accepted 4097 events")
    src=full/"p05_artifacts"
    dst=over/"p05_artifacts"
    dst.mkdir()
    shutil.copy2(src/"core0_initial.bin",dst/"core0_initial.bin")
    shutil.copy2(full/"p05_mailbox_zero.bin",over/"p05_mailbox_zero.bin")
    old_head=bytearray((src/"p05_header.bin").read_bytes())
    old_payload=(src/"p05_payload.bin").read_bytes()
    h=list(struct.unpack("<64I",old_head))
    row=struct.pack("<4I",0,CORE,AXON,0)
    before=old_payload[:h[18]]
    after=old_payload[h[18]:]
    invalid_payload=before+row+after
    h[13]=OVER
    h[12]=len(invalid_payload)
    h[18]+=16
    h[22]=zlib.crc32(invalid_payload)
    h[23]=0
    invalid_head=struct.pack("<64I",*h)
    h[23]=zlib.crc32(invalid_head)
    invalid_head=struct.pack("<64I",*h)
    if h[12]>0xE0000 or len(invalid_head)!=256 or h[23]!=zlib.crc32(
        invalid_head[:92]+bytes(4)+invalid_head[96:]):
        raise ValueError("malformed negative descriptor binary")
    (dst/"p05_header.bin").write_bytes(invalid_head)
    (dst/"p05_payload.bin").write_bytes(invalid_payload)
    (over/"capacity_golden").mkdir()
    shutil.copy2(gold/"core0_initial.bin",over/"capacity_golden/core0_initial.bin")
    over_gate={
        "profile":"p05-2g-crc-valid-4097-overflow-admission-v1",
        "status":"EXPECTED_DEVICE_REJECTION_NOT_HARDWARE_ACCEPTED",
        "event_count":OVER,"last_event_index":CAPACITY,
        "expected_result":"0xDEAD0002","expected_error":2,
        "expected_dispatches":0,"expected_pl_page_commands":0,
        "no_algorithmic_timestep":"P05C rejects in load_descriptor before MMIO",
        "initial_record_sha256":oracle["initial_record_sha256"],
        "p05_header_sha256":digest(dst/"p05_header.bin"),
        "p05_payload_sha256":digest(dst/"p05_payload.bin"),
        "clean_full_header_sha256":digest(src/"p05_header.bin"),
        "clean_full_payload_sha256":digest(src/"p05_payload.bin"),
    }
    (over/"p05_2g_overflow_gate.json").write_text(
        json.dumps(over_gate,indent=2,sort_keys=True)+"\n")
    return full_gate,over_gate

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",required=True,type=Path)
    args=p.parse_args()
    try:
        full,over=make(args.output_dir.resolve())
    except (OSError,ValueError,AssertionError,KeyError,TypeError) as e:
        p.exit(2,"FAIL: P05.2g 4096/4097 boundary fixture: "+str(e)+"\n")
    print("PASS: P05.2g full 4096-event + CRC-valid 4097-event admission-reject profiles staged OFFLINE")
    print("P05_2G_PROFILE_COUNTS="+json.dumps({
        "full":full["event_count"],"invalid":over["event_count"]},sort_keys=True))

if __name__=="__main__":
    main()
