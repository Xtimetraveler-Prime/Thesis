#!/usr/bin/env python3
"""P07-B.5: independent TRAIN-derived V3 validation and physical evidence.

Modes:
  preview       Independently regenerate 26-tick reference for ordinals 0,1,2.
  verify        Verify ONE original physical V3 run against the independent
                scalar 26-tick per-compartment FNV, packets, input and readout.
  consolidate   Reverify ALL evidence afresh; require 0/1/2 plus independent
                0 repeat. Does NOT prove cold reboot or bytewise trace.

This program does not run XSDB/Vivado/Vitis, touch the board, open official
MNIST TEST, modify the frozen graph, or alter the accepted V3 ELF.
All results require ORIGINAL signed 27x512K core readback, bindings, route
tables, each exact registered TRAIN frame and an authentic accepted physical
mailbox for the proper ordinal. Never trust synthetic fixtures as board proof.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import p07_b4l1_stage_frozen_27core as b4l1
import p07_b4l_physical_model_deploy as physical_model
import p07_b4l_b3_physical_epoch as bindings
import p07_b4m_frozen_inputs as train
import p07_b4m_offline_admission as original_routes
import p07_b4m_verify_full_receipt as verifier
import p07_b4m_diag_v3_physical_run as v3
import p07_b4m_v3_train0_scalar_vs_physical as base

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="p07-b5-original-scaled-train-multiframe-independent-physical-validation-v1"
EXPECTED_SCHEMA="p07-b5-original-scaled-train-validation-reference-v1"
GATE_SCHEMA="p07-b5-original-scaled-train-multirun-physical-gate-v1"
STAGE_OK="P07_B4M_DIAG_V3_STRUCTURAL_RECEIPT_ACCEPTED_REBOOT_REQUIRED"

class ValidationNoGo(ValueError):
    pass

def ensure(condition:bool,message:str)->None:
    if not condition:
        raise ValidationNoGo("NO-GO: "+message)

def read_json(path:Path)->dict:
    obj=json.loads(base.read(path).decode("utf-8"))
    ensure(isinstance(obj,dict),"expected JSON object: "+str(path))
    return obj

def require_external_report(path:Path)->None:
    ensure(path.is_absolute() and not path.is_symlink() and
           not path.exists() and path.parent.is_dir() and
           not path.resolve().is_relative_to(b4l1.REPO.resolve()),
           "output report must be NEW, absolute and outside repository")

def write_report(path:Path,record:dict)->None:
    require_external_report(path)
    with path.open("x",encoding="utf-8") as f:
        json.dump(record,f,indent=2,sort_keys=True)
        f.write("\n")

def load_original(frozen:Path,staged:Path,routes:Path):
    if str(ROOT/"src") not in sys.path:
        sys.path.insert(0,str(ROOT/"src"))
    from loihi_twin_v2.compiler import NetworkSpec
    from loihi_twin_v2.p06_b12_partition import B12Result
    from loihi_twin_v2.p06_b24_freeze import (
        PINNED_B23_SOURCE_SHA256,PINNED_B23_DEPLOYMENT_SHA256,
        PINNED_B23_FRAMES,
    )
    b4l1.admit_freeze(frozen)
    index=physical_model.prepare_verified_contexts(frozen,staged)
    stage=original_routes.require_routes(routes,frozen)
    ensure(stage["input_routes"]==20384 and stage["output_routes"]==1000,
           "original source routing sizes differ")
    network=NetworkSpec.from_json(base.read(frozen/"network_source.json").decode("utf-8"))
    packed=B12Result.from_json(base.read(frozen/"packed_deployment.json").decode("utf-8"))
    ensure(network.fingerprint==PINNED_B23_SOURCE_SHA256 and
           packed.compiled.source_fingerprint==network.fingerprint and
           packed.compiled.fingerprint==PINNED_B23_DEPLOYMENT_SHA256,
           "original frozen integer model, source, or compiled SHA drift")
    b23=read_json(frozen/"b23_validation_parity.json")
    rows=b23.get("validation_frames")
    ensure(isinstance(rows,list) and len(rows)==3 and
           [r["validation_ordinal"] for r in rows]==[0,1,2],
           "expected original exact three B2.3 TRAIN validation references")
    for i,row in enumerate(rows):
        witness=PINNED_B23_FRAMES[i]
        ensure((row["validation_ordinal"],row["canonical_train_idx"],
                row["image_sha256"],row["monolithic_trace_sha256"],
                row["partitioned_trace_sha256"])==witness and
                row["all_26_ticks_full_neuron_parity"] is True,
               f"original frozen B2.3 parity reference {i} drift")
    return network,packed,index,rows

def make_reference(ordinal:int,network,packed,rows:list[dict],routes:Path)->dict:
    if str(ROOT/"src") not in sys.path:
        sys.path.insert(0,str(ROOT/"src"))
    from loihi_twin_v2.p06_b14_monolithic import (
        pixel_schedule_independent,simulate_monolithic,
    )
    ensure(type(ordinal) is int and ordinal in (0,1,2),
           "only original pinned TRAIN ordinals 0,1,2 permitted")
    frame_name=f"p07_b4m_original_TRAIN_validation_{ordinal}_ingress.bin"
    frame=base.read(routes/frame_name)
    ensure(base.sha(frame)==train_frames_sha(routes,frame_name) and
           base.sha(frame[-784:])==train.FRAME_SHA[ordinal] and
           len(frame)>=784 and len(frame)<=0xE0000,
           "original selected TRAIN frame SHA, pixel identity or size changed")
    schedule=pixel_schedule_independent(bytes(frame[-784:]))
    reference=simulate_monolithic(network,{"pixels":schedule},
                                  readout_population="readout")
    row=rows[ordinal]
    ensure(row["canonical_train_idx"]==train.FRAME_IDX[ordinal] and
           reference.trace_sha256==row["monolithic_trace_sha256"] and
           reference.predicted_class==row["predicted_class"] and
           list(reference.readout_spike_counts)==row["readout_spike_counts"],
           "independent scalar reference does not recreate original frozen B2.3")
    metrics=base.expected_counters(reference,schedule,packed.compiled)
    trace_hash,per_tick=base.trace_fingerprint(reference,packed.compiled.placement)
    return {
        "ordinal":ordinal,
        "canonical_train_index":train.FRAME_IDX[ordinal],
        "original_label":row["label"],
        "frame_filename":frame_name,
        "frame_sha256":base.sha(frame),
        "image_sha256":train.FRAME_SHA[ordinal],
        "independent_scalar_monolithic_sha256":reference.trace_sha256,
        "metrics":metrics,
        "trace_fingerprint_FNV64":trace_hash,
        "per_tick_trace_fingerprint_FNV64":per_tick,
    }

def train_frames_sha(routes:Path,name:str)->str:
    # Canonical independently signed routing frame stage includes ALL 3.
    manifest=read_json(routes/"p07_b4m_frozen_inputs_manifest.json")
    v=manifest["files"].get(name)
    ensure(isinstance(v,str) and len(v)==64,
           "original TRAIN frame missing from signed manifest")
    return v

def verify_run(evidence:Path,ordinal:int,ref:dict,staged:Path,
               routes:Path,index:dict)->dict:
    ensure(evidence.is_absolute() and not evidence.is_symlink() and
           evidence.is_dir() and not evidence.resolve().is_relative_to(ROOT),
           "physical evidence must be a real, external absolute run directory")
    ensure(base.read(evidence/"stage.txt").decode().strip()==STAGE_OK,
           "no accepted original V3 structural stage")
    contract=read_json(evidence/"diag_v3_launch_contract.json")
    expected={
        "diagnostic_firmware_identity":v3.V3_ID,
        "new_elf_sha256":v3.V3_ELF_SHA,
        "new_linker_map_sha256":v3.V3_MAP_SHA,
        "original_TRAIN_validation_ordinal":ordinal,
        "original_TRAIN_frame_sha256":ref["frame_sha256"],
        "full_independent_neuron_numerical_parity_proven":False,
    }
    for k,v in expected.items():
        ensure(contract.get(k)==v,"original physical V3 launch contract mismatch: "+k)
    ensure(contract.get("expanded_low_DDR_firmware_exclusivity_independently_proven") is False,
           "boot firmware DDR exclusivity was not proven; do not fabricate proof")
    stage=read_json(evidence/"independent_staging_receipt.json")
    for k,v in {
        "original_27core_contexts_sha256":physical_model.ACCEPTED_BUNDLE_SHA,
        "original_descriptor_16k_sha256":bindings.ACCEPTED_DESCRIPTOR_SHA,
        "validation_ordinal":ordinal,
        "real_elf_downloaded":False,
        "inference_executed":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "reboot_required":True,
    }.items():
        ensure(stage.get(k)==v,"original same-session physical stage mismatch: "+k)
    actual=physical_model.verify_physical_readback(
        staged,evidence/"physical_readback",index)
    ensure(actual["physical_readback_sha256"]==physical_model.ACCEPTED_BUNDLE_SHA,
           "physical 27x512K DDR contexts do not match signed original freeze")
    ensure(base.sha(base.read(evidence/"binding_readback_16k.bin",16384))==
           bindings.ACCEPTED_DESCRIPTOR_SHA,
           "physical 16K binding descriptor byte mismatch")
    sources={
       "input_routes_896k_physical.bin":routes/train.IN_FILENAME,
       "output_routes_80k_physical.bin":routes/train.OUT_FILENAME,
       "original_TRAIN_ingress_physical.bin":routes/ref["frame_filename"],
    }
    stage_records=stage.get("original_B2_4_routes_and_train_physical_sha256")
    ensure(isinstance(stage_records,dict) and set(stage_records)==set(sources),
           "original three physical DDR route/frame readback receipts absent")
    for name,source in sources.items():
        src=base.read(source)
        on_board=base.read(evidence/"b4m_physical_route_readback"/name)
        observed=stage_records[name]
        ensure(on_board==src and observed.get("sha256")==base.sha(src) and
               observed.get("byte_exact_vs_signed_host_input") is True,
               "signed original source and physical DDR readback mismatch: "+name)
    execution_log=base.read(evidence/"diag_v3_a53_run.log").decode(errors="replace")
    for marker in v3.LAUNCH_MARKERS:
        ensure(marker in execution_log,
               "physical XSDB A53 execution log does not contain "+marker)
    raw=base.read(evidence/"diag_v3_physical_mailbox_256.bin",256)
    physical=verifier.verify(raw)
    receipt=read_json(evidence/"diag_v3_structural_receipt.json")
    for k,v in {
        "diagnostic_v3_A53_elf_sha256":v3.V3_ELF_SHA,
        "diagnostic_v3_firmware_identity":v3.V3_ID,
        "trained_original_validation_ordinal":ordinal,
        "physical_mailbox":physical,
        "full_26tick_trained_physical_execution_structurally_verified":True,
        "independent_full_neuron_numerical_parity_verified":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "reboot_required":True,
    }.items():
        ensure(receipt.get(k)==v,
               "original structural receipt mismatches raw physical mailbox: "+k)
    checks=base.compare(physical,ref["metrics"],ref["trace_fingerprint_FNV64"])
    return {
        "schema":SCHEMA,
        "original_train_validation_ordinal":ordinal,
        "original_train_index":ref["canonical_train_index"],
        "original_train_label":ref["original_label"],
        "evidence_dir":str(evidence.resolve()),
        "physical_raw_mailbox_sha256":base.sha(raw),
        "signed_original_model_bundle_sha256":physical_model.ACCEPTED_BUNDLE_SHA,
        "original_train_frame_sha256":ref["frame_sha256"],
        "physical":{k:physical[k] for k in (
            *ref["metrics"],"all_26_tick_trace_hash",
            "physical_dispatches","physical_barriers_acked","physical_page_ins",
            "physical_dirty_page_outs","physical_final_page_outs")},
        "independent_scalar":ref,
        "individual_checks":checks,
        "aggregate_and_full_26tick_FNV64_all_match":all(checks.values()),
        "strict_raw_neuron_by_neuron_trace_equality_proven":False,
        "verified_board_cold_reboot_between_runs":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "board_contact_this_audit":False,
        "original_model_or_V3_ELF_changed":False,
    }

def parse_run_spec(spec:str)->tuple[int,Path]:
    ordinal,sep,name=spec.partition(":")
    ensure(sep and ordinal in ("0","1","2") and name,
           "run must be written ORDINAL:/absolute/evidence/directory")
    path=Path(name)
    ensure(path.is_absolute(),"run evidence path must be absolute")
    return int(ordinal),path

def run(args:argparse.Namespace)->tuple[dict,int]:
    ensure(args.mode in ("preview","verify","consolidate"),
           "unknown P07-B.5 mode")
    network,packed,index,rows=load_original(
        args.frozen_dir,args.staged_dir,args.routes_dir)
    if args.mode=="preview":
        ensure(not args.run,"preview must not accept physical run evidence")
        refs=[make_reference(i,network,packed,rows,args.routes_dir)
              for i in range(3)]
        return {
            "schema":EXPECTED_SCHEMA,
            "reference":[*refs],
            "original_model_sha256":packed.compiled.fingerprint,
            "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
            "physical_run_executed":False,
            "physical_parity_proven":False,
        },0
    runs=[parse_run_spec(r) for r in args.run]
    if args.mode=="verify":
        ensure(len(runs)==1,"verify requires exactly one ORDINAL:physical_evidence run")
    else:
        ensure(len(runs)==4 and Counter(i for i,_ in runs)==Counter({0:2,1:1,2:1}),
               "consolidate requires exact 0/1/2 original TRAIN plus one 0-repeat")
    paths=[p.resolve() for _,p in runs]
    ensure(len(set(paths))==len(paths),
           "each physical run must use a DISTINCT genuine evidence directory")
    references={
        i:make_reference(i,network,packed,rows,args.routes_dir)
        for i in sorted(set(idx for idx,_ in runs))
    }
    verified=[verify_run(folder,ordinal,references[ordinal],
                         args.staged_dir,args.routes_dir,index)
              for ordinal,folder in runs]
    status=all(item["aggregate_and_full_26tick_FNV64_all_match"] for item in verified)
    if args.mode=="verify":
        return verified[0],0 if status else 4
    repeat=[record for record in verified if record["original_train_validation_ordinal"]==0]
    same=all(repeat[0]["physical"][key]==repeat[1]["physical"][key]
             for key in repeat[0]["physical"])
    status=status and same
    return {
        "schema":GATE_SCHEMA,
        "source_original_B24_sha256":packed.compiled.fingerprint,
        "genuine_independently_verified_sessions":len(verified),
        "distinct_train_validation_frames":3,
        "required_ordinal_sequence":[ordinal for ordinal,_ in runs],
        "session_reports":verified,
        "train0_repeat_physical_metrics_and_FNV64_equal":same,
        "all_three_distinct_frames_scalar_vs_physical_equal":all(
            x["aggregate_and_full_26tick_FNV64_all_match"]
            for x in verified),
        "all_independent_fingerprint_gate_conditions_pass":status,
        "full_raw_per_neuron_hardware_trace_directly_compared":False,
        "cold_reboot_between_runs_independently_proven":False,
        "ready_for_strong_trace_and_restart_acceptance":status,
        "P07_B5_final_full_parity_and_acceptance":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "board_contact_this_audit":False,
    },0 if status else 4

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",required=True,
                   choices=("preview","verify","consolidate"))
    for name in ("frozen-dir","staged-dir","routes-dir","out"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--run",action="append",default=[],
                   help="For verify/consolidate: 0:/absolute/real/run; repeated")
    args=p.parse_args()
    try:
        require_external_report(args.out)
        result,status=run(args)
        write_report(args.out,result)
        print("P07_B5_VALIDATION_REPORT="+str(args.out),flush=True)
        print("P07_B5_ORIGINAL_MODEL_TEST_SEALED=1",flush=True)
        print("P07_B5_PHYSICAL_BOARD_CONTACT=0",flush=True)
        if args.mode=="preview":
            print("P07_B5_THREE_FROZEN_TRAIN_SCALAR_REFERENCE_PASS=1",flush=True)
        else:
            print("P07_B5_INDEPENDENT_MULTI_FRAME_FP_AND_COUNTS_PASS="+
                  ("1" if status==0 else "0"),flush=True)
            print("P07_B5_FULL_RAW_NEURON_PARITY_VERIFIED=0",flush=True)
        return status
    except (OSError,ValueError,KeyError,TypeError,RuntimeError) as exc:
        print("P07_B5_VALIDATION_NO_GO="+str(exc),file=sys.stderr,flush=True)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
