#!/usr/bin/env python3
"""Independent PC-ONLY verifier for a genuine B5.3 original 27core RAW trace.

Never invokes XSDB or trusts a standalone user-supplied raw binary as board
proof. Requires same-session original signed 27 DDR readbacks, 16K bindings,
80K/896K routes, original TRAIN ingress, new B5 ELF/map launch contract,
genuine XSDB log markers, 256B B5 terminal mailbox and exact 840320B
PSU physical readback. Scalar is independently regenerated from original
immutable B2.4. No official MNIST TEST. Does not prove DDR ownership.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import p07_b4m_verify_full_receipt as full
import p07_b4m_physical_staging as staging
import p07_b4m_v3_train0_scalar_vs_physical as base
import p07_b5_raw_trace_reference as oracle
import p07_b5_scaled_validation as old_b5
import p07_b5_raw_trace_offline_admission as gate
import p07_b4l_physical_model_deploy as physical_model
import p07_b4l_b3_physical_epoch as binds
import p07_b4m_frozen_inputs as trained

ROOT=Path(__file__).resolve().parents[1]
RAW_NAME="b5_raw_physical_trace_840320.bin"
MAILBOX_NAME="b5_raw_physical_mailbox_256.bin"
LOG_NAME="b5_raw_a53_run.log"
CONTRACT_NAME="b5_raw_launch_contract.json"
STAGE_SUCCESS="P07_B5_RAW_COMPLETE_PHYSICAL_TRACE_STORED_REBOOT_REQUIRED"
B5_MAGIC=0x42355331
TRACE_MAGIC=0x42354331
TRACE_SHA_ORIGINAL_0="7fd6d5cbfa44cc1f69745b492c7b60649a49ec5b69c42821ba6619e503554f7d"
MARKERS=(
    "P07_B5_RAW_NEW_256B_MAILBOX_ZERO_PHYSICAL_READBACK_PASS=1",
    "P07_B5_RAW_NEW_A53_ELF_DOWNLOADED=1",
    "P07_B5_RAW_NEW_256B_PHYSICAL_MAILBOX_CAPTURED=1",
    "P07_B5_RAW_NEW_A53_TERMINAL_DONE_PHYSICALLY_OBSERVED=1",
    "P07_B5_RAW_NEW_COMPLETE_CAPTURE_RECEIPT_PHYSICAL_PASS=1",
    "P07_B5_RAW_840320_BYTE_PSU_PHYSICAL_TRACE_READBACK_CAPTURED=1",
    "P07_B5_RAW_PHYSICAL_MAILBOX_AND_TRACE_READY_FOR_INDEPENDENT_VERIFY=1",
)
class RawPhysicalNoGo(ValueError):
    pass

def ensure(ok:bool,msg:str)->None:
    if not ok: raise RawPhysicalNoGo("NO-GO: "+msg)

def file_bytes(path:Path,exact:int|None=None)->bytes:
    ensure(path.is_file() and not path.is_symlink(),
           "missing genuine regular evidence file: "+str(path))
    if exact is not None:
        ensure(path.stat().st_size==exact,"wrong evidence byte count: "+str(path))
    return path.read_bytes()

def digest(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()

def verify_b5_mailbox(raw:bytes,expected_class:int|None=None)->dict:
    ensure(len(raw)==256,"exact 256B physical B5 mailbox required")
    words=struct.unpack("<64I",raw)
    ensure((words[0],words[1],words[2],words[63])==
           (B5_MAGIC,1,full.PASS,full.DONE),
           "B5 diagnostic identity/schema/PASS/DONE rejected")
    ensure((words[47],words[48],words[49],words[50],
            words[51],words[52],words[53],words[54],
            words[55],words[56])==
           (TRACE_MAGIC,0,0,0,26260,210080,0x42000000,0x420CD280,0,1),
           "new B5 capture address/geometry/finished/zero-fault not proven")
    ensure(all(words[i]==0 for i in range(57,63)),
           "B5 failure-only MMIO snapshot is nonzero on PASS")
    # Independent original readout/paging validator checks EVERY original
    # B4m field. We normalize only explicitly authenticated B5 extensions
    # to the equivalent original shared accounting ABI, not the source
    # physical record. The returned evidence is labeled B5 throughout.
    shared=list(words)
    shared[0]=full.MAGIC
    shared[47:63]=[0]*16
    structural=full.verify(struct.pack("<64I",*shared),expected_class)
    structural["schema"]="p07-b5-original-raw-a53-26tick-physical-mailbox-v1"
    structural["raw_mailbox_sha256"]=digest(raw)
    structural["B5_capture_finished"]=True
    structural["B5_capture_neurons"]=26260
    structural["B5_trace_words"]=210080
    structural["B5_trace_base"]="0x42000000"
    structural["B5_trace_end_exclusive"]="0x420CD280"
    return structural

def verify_original_stage(evidence:Path,ordinal:int,staged:Path,
                          routes:Path,index:dict,frame_name:str)->dict:
    r=old_b5.read_json(evidence/"independent_staging_receipt.json")
    for k,v in {
        "original_27core_contexts_sha256":physical_model.ACCEPTED_BUNDLE_SHA,
        "original_descriptor_16k_sha256":binds.ACCEPTED_DESCRIPTOR_SHA,
        "validation_ordinal":ordinal,
        "real_elf_downloaded":False,
        "first_barrier_acknowledged":False,
        "inference_executed":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "reboot_required":True,
    }.items():
        ensure(r.get(k)==v,"same-session physical signed source receipt: "+k)
    readback=physical_model.verify_physical_readback(
        staged,evidence/"physical_readback",index)
    ensure(readback["physical_readback_sha256"]==
           physical_model.ACCEPTED_BUNDLE_SHA,
           "original 27 core DDR physical byte readbacks disagree")
    ensure(digest(file_bytes(evidence/"binding_readback_16k.bin",16384))==
           binds.ACCEPTED_DESCRIPTOR_SHA,
           "original signed 16K descriptor physical readback mismatch")
    expected={
        "output_routes_80k_physical.bin":routes/trained.OUT_FILENAME,
        "input_routes_896k_physical.bin":routes/trained.IN_FILENAME,
        "original_TRAIN_ingress_physical.bin":routes/frame_name,
    }
    got=r.get("original_B2_4_routes_and_train_physical_sha256")
    ensure(isinstance(got,dict) and set(got)==set(expected),
           "original same-session three route/ingress physical receipts absent")
    for name,source in expected.items():
        original=file_bytes(source)
        observed=file_bytes(evidence/"b4m_physical_route_readback"/name,len(original))
        ensure(observed==original and got[name].get("sha256")==digest(original)
               and got[name].get("byte_exact_vs_signed_host_input") is True,
               "original route/TRAIN physical bytes mismatch: "+name)
    return r

def verify_session(*,evidence:Path,ordinal:int,
                   frozen:Path,staged:Path,routes:Path,
                   build:Path,reports:Path,offline_report:Path)->dict:
    ensure(ordinal in (0,1,2),"only original TRAIN validation ordinals")
    ensure(evidence.is_absolute() and evidence.is_dir() and
           not evidence.is_symlink() and
           not evidence.resolve().is_relative_to(ROOT),
           "real external physical evidence folder required")
    ensure(file_bytes(evidence/"stage.txt").decode().strip()==STAGE_SUCCESS,
           "incomplete or unsuccessful same-session B5 physical run")
    admissible=gate.admit(frozen=frozen,routes=routes,
                          build=build,reports=reports)
    ensure(old_b5.read_json(offline_report)==admissible,
           "genuine built new B5 ELF+map offline report source mismatch")
    ensure(admissible["new_genuine_b5_ELF"]["new_elf_sha256"]==
           "0e018a9cabf45b7e65a366b9e21df0cc90cb5b072053cac8c19d2f601be1d2cf",
           "not original accepted separately built B5 ELF")
    ensure(admissible["new_genuine_b5_linker_map_sha256"]==
           "1e6cf5d0a9744378fb0aebe2e6271da661b8739a2fb930e983342477fd0e78c8",
           "not original accepted B5 linker map")
    source_original=old_b5.load_original(frozen,staged,routes)
    network,compiled,index,rows=source_original
    reference=old_b5.make_reference(ordinal,network,compiled,rows,routes)
    contract=old_b5.read_json(evidence/CONTRACT_NAME)
    for key,value in {
        "schema":"p07-b5-new-raw-physical-launch-contract-v1",
        "new_firmware_identity":gate.IDENTITY.decode(),
        "new_elf_sha256":admissible["new_genuine_b5_ELF"]["new_elf_sha256"],
        "new_linker_map_sha256":admissible["new_genuine_b5_linker_map_sha256"],
        "original_TRAIN_validation_ordinal":ordinal,
        "original_TRAIN_frame_sha256":reference["frame_sha256"],
        "raw_capture_bytes":oracle.TRACE_BYTES,
        "raw_capture_base":"0x42000000",
        "mailbox_address":"0x43FF0100",
        "operator_explicit_new_sidecar_and_low_DDR_risk_acceptance":True,
        "actual_DDR_physical_ownership_independently_proven":False,
        "original_model_changed":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "reboot_required":True,
    }.items():
        ensure(contract.get(key)==value,"B5 physical launch contract: "+key)
    stage=verify_original_stage(evidence,ordinal,staged,routes,index,
                                reference["frame_filename"])
    log=file_bytes(evidence/LOG_NAME).decode("utf-8",errors="replace")
    for marker in MARKERS:
        ensure(marker in log,"real XSDB physical marker absent: "+marker)
    ensure("P07_B5_RAW_PHYSICAL_ATTEMPT_FAILED_REBOOT_REQUIRED=1" not in log,
           "XSDB physical experiment failed, not accepted")
    mailbox=file_bytes(evidence/MAILBOX_NAME,256)
    receipt=verify_b5_mailbox(mailbox,reference["metrics"]["trained_readout_prediction"])
    observed=file_bytes(evidence/RAW_NAME,oracle.TRACE_BYTES)
    expected,coords=oracle.expected_raw_trace(
        # regenerate from exact frozen 26tick reference (not user-provided raw)
        _scalar_for_original(frozen,routes,ordinal,network),
        compiled.compiled)
    ensure(len(expected)==oracle.TRACE_BYTES and len(coords)==26260,
           "independent full 26tick original neuron oracle incomplete")
    first=oracle.first_mismatch(expected,observed,coords)
    checks=base.compare(receipt,reference["metrics"],
                        reference["trace_fingerprint_FNV64"])
    # The full 64-bit raw physical FNV must independently reproduce the
    # same per-tick/full fingerprint, in addition to bytewise equality.
    combined=base.FNV_SEED
    ticks=[]
    for tick in range(26):
        chunk=observed[tick*32320:(tick+1)*32320]
        h=base.fnv_bytes(base.FNV_SEED,chunk)
        ticks.append(f"0x{h:016X}")
        combined=base.fnv_bytes(combined,h.to_bytes(8,"little"))
    ensure(ticks==reference["per_tick_trace_fingerprint_FNV64"] and
           f"0x{combined:016X}"==receipt["all_26_tick_trace_hash"],
           "raw physical trace and B5 hardware original FNV receipt mismatch")
    ensure(first is None,"first raw byte discrepancy: "+json.dumps(first))
    ensure(all(checks.values()),"B5 actual physical counters differ from independent scalar")
    return {
        "schema":"p07-b5-original-raw-physical-by-neuron-authenticated-scalar-gate-v1",
        "physical_original_TRAIN_ordinal":ordinal,
        "train_index":reference["canonical_train_index"],
        "physical_evidence_dir":str(evidence.resolve()),
        "original_TRAIN_frame_sha256":reference["frame_sha256"],
        "new_B5_ELF_sha256":admissible["new_genuine_b5_ELF"]["new_elf_sha256"],
        "new_B5_map_sha256":admissible["new_genuine_b5_linker_map_sha256"],
        "physical_B5_mailbox_sha256":digest(mailbox),
        "physical_raw_trace_sha256":digest(observed),
        "independent_original_raw_trace_sha256":digest(expected),
        "actual_physical_trace_size":len(observed),
        "physical_raw_FNV64":f"0x{combined:016X}",
        "physical_per_tick_FNV64":ticks,
        "independent_scalar_checks":checks,
        "physical_B5_mailbox":receipt,
        "raw_neuron_original_26x1010_bytes_exactly_equal":True,
        "same_session_original_27core_and_route_stage_verified":True,
        "original_signed_model_modified":False,
        "original_V3_ELF_modified":False,
        "original_official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "board_contact_this_verifier":False,
        "user_power_cycle_independently_attested":False,
        "physical_DDR_ownership_independently_proven":False,
        "P07_B5_final_acceptance":False,
    }

def _scalar_for_original(frozen:Path,routes:Path,ordinal:int,network):
    if str(ROOT/"src") not in sys.path:
        sys.path.insert(0,str(ROOT/"src"))
    from loihi_twin_v2.p06_b14_monolithic import (
        pixel_schedule_independent,simulate_monolithic)
    frame=file_bytes(routes/f"p07_b4m_original_TRAIN_validation_{ordinal}_ingress.bin")
    return simulate_monolithic(network,
        {"pixels":pixel_schedule_independent(bytes(frame[-784:]))},
        readout_population="readout")

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ordinal",type=int,choices=(0,1,2),required=True)
    for name in ("evidence","frozen-dir","staged-dir","routes-dir",
                 "build-dir","reports","offline-report","out"):
        p.add_argument("--"+name,type=Path,required=True)
    args=p.parse_args()
    try:
        old_b5.require_external_report(args.out)
        result=verify_session(
            evidence=args.evidence,ordinal=args.ordinal,
            frozen=args.frozen_dir,staged=args.staged_dir,
            routes=args.routes_dir,build=args.build_dir,
            reports=args.reports,offline_report=args.offline_report)
        old_b5.write_report(args.out,result)
        print("P07_B5_GENUINE_PHYSICAL_RAW_NEURON_TRACE_BYTEWISE_SCALAR_PASS=1")
        print("P07_B5_RAW_READBACK_SHA256="+result["physical_raw_trace_sha256"])
        print("P07_B5_TEST_SEALED=1")
        print("P07_B5_PHYSICAL_BOARD_CONTACT_THIS_VERIFIER=0")
        print("P07_B5_FINAL_MILESTONE_ACCEPTED=0")
        print("P07_B5_RAW_GENUINE_AUDIT_REPORT="+str(args.out))
        return 0
    except (ValueError,TypeError,OSError,KeyError,struct.error) as error:
        print("P07_B5_GENUINE_RAW_NEURON_VERIFY_NO_GO="+str(error),
              file=sys.stderr,flush=True)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
