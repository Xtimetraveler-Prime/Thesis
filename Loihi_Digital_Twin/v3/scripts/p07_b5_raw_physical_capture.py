#!/usr/bin/env python3
"""New P07-B.5.3 original 27-core physical RAW sidecar experiment.

DEFAULT PRELIGHT IS PC-ONLY. New B5 CPU/DDR/mailbox and 840320B capture
are destructive, require ALL original P07-B4 staging approvals PLUS NEW
risk approvals, a fresh board POWER CYCLE, dedicated JTAG and NEW evidence
directory. Executable uses the exact independently admitted real
Vitis B5 ELF and original accepted P03 FPGA shell. NEVER reuse original
V3 physical launcher or accepted V3 mailbox. Low DDR and new trace sidecar
boot/firmware ownership were NOT proven by the offline report.
Even a completed physical attempt requires KV260 cold reboot; NEVER resume
halted Linux. No official MNIST TEST. This is not P07-B.5 final acceptance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

import p07_b4m_diag_v3_physical_run as v3
import p07_b4m_physical_staging as physical
import p07_b5_raw_trace_offline_admission as gate
import p07_b5_raw_physical_verify as audit
import p07_b5_scaled_validation as b5
import p07_b4l_physical_model_deploy as model

ROOT=Path(__file__).resolve().parents[1]
ELF_SHA="0e018a9cabf45b7e65a366b9e21df0cc90cb5b072053cac8c19d2f601be1d2cf"
MAP_SHA="1e6cf5d0a9744378fb0aebe2e6271da661b8739a2fb930e983342477fd0e78c8"
PT_END="0x00107BC0"
PT_BYTES=1080256
PT_FILE_BYTES=110676
LAUNCH_TCL="vivado/p07_b5_raw_trace_xsdb_run.tcl"
LAUNCH_TOKEN="B5_RAW_A53_NEW_DDR_TRACE_AND_MAILBOX_EXPLICITLY_APPROVED"
EXTRA_APPROVALS=(
    "b5_new_a53_26tick_capture_approved",
    "new_low_ddr_1080256_footprint_approved",
    "unproven_low_ddr_boot_firmware_exclusivity_risk_accepted",
    "new_840320b_trace_ddr_overwrite_risk_accepted",
    "new_b5_mailbox_256b_overwrite_approved",
)
class RawLaunchNoGo(ValueError):
    pass

def require_pc_original_and_new_b5(args:argparse.Namespace)->tuple[dict,dict,dict,dict]:
    """All work before physical contact. Source AND actual ELF/map revalidated."""
    ensure= b5.ensure
    ensure(args.build_dir.is_absolute() and args.build_dir.is_dir() and
           not args.build_dir.is_symlink() and
           args.elf==args.build_dir/"vitis_workspace"/(gate.APP+".elf"),
           "operator-new exact B5 Vitis build and expected ELF required")
    ensure(args.offline_report.is_absolute() and
           args.offline_report.is_file() and
           not args.offline_report.is_symlink(),
           "original exact new B5 offline report must be regular real file")
    current=gate.admit(frozen=args.frozen_dir,
                       routes=args.routes_dir,build=args.build_dir,
                       reports=args.reports)
    ensure(b5.read_json(args.offline_report)==current,
           "exact independently verified real Vitis B5 offline report changed")
    elf=current["new_genuine_b5_ELF"]
    ensure((elf["new_elf_sha256"],elf["new_linker_map_sha256"],
            elf["pt_load_end_exclusive"],elf["pt_load_filesz"],
            elf["pt_load_memsz"])==
           (ELF_SHA,MAP_SHA,PT_END,PT_FILE_BYTES,PT_BYTES),
           "must pin exact user-admitted new B5 ELF/map and low DDR footprint")
    ensure(args.validation_ordinal in (0,1,2),
           "only original frozen signed TRAIN validation frame")
    for name,sha in physical.EXPECTED_STAGE_SHA.items():
        ensure(current["original_immutable_routes"]["staged_files_sha256"].get(name)==sha,
               "signed original frozen route/TRAIN file changed: "+name)
    index=model.prepare_verified_contexts(args.frozen_dir,args.staged_dir)
    desc=physical.old.require_real_bindings(args.frozen_dir,
                                           args.staged_dir,args.bindings_dir)
    v3.preflight_original_p02_metadata(args)
    readelf,nm=physical.resolve_elf_inspection_tools()
    physical.old.b4i.preflight(args.b4i_build,args.reports,
                              readelf=readelf,nm=nm)
    ensure(current["capture_geometry"]["raw_trace_exact_bytes"]==840320,
           "raw trace geometry drift")
    return index,desc,current["original_immutable_routes"],elf

def require_new_risk_approval(args:argparse.Namespace)->None:
    physical.stage_requirements(args)  # original signed-model eight permissions
    for field in EXTRA_APPROVALS:
        if getattr(args,field)!="YES":
            raise RawLaunchNoGo("NO-GO: --"+field.replace("_","-")+
                                " YES required for NEW B5 DDR/firmware risk")
    if args.elf.name!="p07_b5_raw_trace_v1.elf":
        raise RawLaunchNoGo("NO-GO: distinct accepted new B5 A53 ELF required")
    if not (shutil.which("xsdb") and shutil.which("vivado")):
        raise RawLaunchNoGo("NO-GO: actual physical XSDB/Vivado binaries absent")

def after_same_session_stage(args:argparse.Namespace,out:Path,verified:dict)->None:
    """Only called AFTER original 27core & descriptors/routes/TRAIN readbacks."""
    stage=b5.read_json(out/"independent_staging_receipt.json")
    frame=f"p07_b4m_original_TRAIN_validation_{args.validation_ordinal}_ingress.bin"
    valid={
        "original_27core_contexts_sha256":model.ACCEPTED_BUNDLE_SHA,
        "original_descriptor_16k_sha256":physical.old.ACCEPTED_DESCRIPTOR_SHA,
        "validation_ordinal":args.validation_ordinal,
        "real_elf_downloaded":False,
        "inference_executed":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "reboot_required":True,
    }
    for name,value in valid.items():
        if stage.get(name)!=value:
            raise RawLaunchNoGo("NO-GO: incomplete signed original physical staging: "+name)
    required={
        "output_routes_80k_physical.bin":physical.frozen.OUT_FILENAME,
        "input_routes_896k_physical.bin":physical.frozen.IN_FILENAME,
        "original_TRAIN_ingress_physical.bin":frame,
    }
    if set(verified)!=set(required):
        raise RawLaunchNoGo("NO-GO: same-session original physical input source list changed")
    for name,source in required.items():
        expected=physical.EXPECTED_STAGE_SHA[source]
        if (verified[name].get("sha256")!=expected or
            verified[name].get("byte_exact_vs_signed_host_input") is not True or
            physical.old.file_sha(out/"b4m_physical_route_readback"/name)!=expected):
            raise RawLaunchNoGo("NO-GO: source not physically read back: "+name)
    if (physical.old.file_sha(args.elf)!=ELF_SHA or
        physical.old.file_sha(args.elf.with_suffix(".map"))!=MAP_SHA):
        raise RawLaunchNoGo("NO-GO: new B5 signed A53 ELF/map changed during staging")
    contract={
        "schema":"p07-b5-new-raw-physical-launch-contract-v1",
        "new_firmware_identity":gate.IDENTITY.decode(),
        "new_elf_sha256":ELF_SHA,
        "new_linker_map_sha256":MAP_SHA,
        "new_ELF_load_end":PT_END,
        "new_ELF_load_bytes":PT_BYTES,
        "original_TRAIN_validation_ordinal":args.validation_ordinal,
        "original_TRAIN_frame_sha256":physical.EXPECTED_STAGE_SHA[frame],
        "original_27core_SHA256":model.ACCEPTED_BUNDLE_SHA,
        "original_16k_binding_SHA256":physical.old.ACCEPTED_DESCRIPTOR_SHA,
        "raw_capture_bytes":840320,
        "raw_capture_base":"0x42000000",
        "raw_capture_end_exclusive":"0x420CD280",
        "mailbox_address":"0x43FF0100",
        "operator_explicit_new_sidecar_and_low_DDR_risk_acceptance":True,
        "actual_DDR_physical_ownership_independently_proven":False,
        "original_model_changed":False,
        "original_V3_A53_ELF_changed":False,
        "accepted_P03_PL_changed":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "reboot_required":True,
    }
    (out/audit.CONTRACT_NAME).write_text(json.dumps(contract,sort_keys=True,indent=2)+"\n")
    (out/"stage.txt").write_text("B5_NEW_A53_PENDING_AFTER_27CORE_SIGNED_PHYSICAL_READBACK_REBOOT_REQUIRED\n")
    zero=out/"b5_raw_mailbox_zero_256.bin"
    with zero.open("xb") as f:f.write(bytes(256))
    mailbox=out/audit.MAILBOX_NAME
    trace=out/audit.RAW_NAME
    physical.old.b4i.log_call(
        ["xsdb",LAUNCH_TCL,LAUNCH_TOKEN,str(args.elf),str(zero),
         str(mailbox),str(trace),"tcp:127.0.0.1:3121"],
        out/audit.LOG_NAME,
    )
    for marker in audit.MARKERS:
        physical.old.checked_marker(out/audit.LOG_NAME,marker)
    # Distinct genuine B5 mailbox; does NOT ever pass V3 format directly.
    receipt=audit.verify_b5_mailbox(audit.file_bytes(mailbox,256))
    observed=audit.file_bytes(trace,840320)
    (out/"b5_raw_structural_receipt.json").write_text(
        json.dumps({
            "schema":"p07-b5-raw-structural-physical-receipt-v1",
            "original_TRAIN_ordinal":args.validation_ordinal,
            "B5_mailbox":receipt,
            "physical_B5_mailbox_sha256":audit.digest(mailbox.read_bytes()),
            "physical_B5_raw_trace_sha256":audit.digest(observed),
            "physical_B5_raw_trace_bytes":840320,
            "source_original_27core_verified":True,
            "original_TEST":"SEALED_NOT_ACCESSED",
            "full_neuron_numerical_parity_independently_proven":False,
            "DDR_firmware_ownership_independently_proven":False,
            "cold_reboot_required":True
        },indent=2,sort_keys=True)+"\n"
    )
    (out/"stage.txt").write_text(audit.STAGE_SUCCESS+"\n")
    print("P07_B5_RAW_COMPLETE_840320B_PHYSICAL_CAPTURE_STRUCTURAL_PASS=1",flush=True)
    print("P07_B5_RAW_DIRECT_NEURON_NUMERICAL_PARITY_VERIFIED=0",flush=True)
    print("P07_B5_RAW_COLD_REBOOT_REQUIRED=1",flush=True)

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=("preflight","execute"),default="preflight")
    for name in ("frozen-dir","staged-dir","bindings-dir","routes-dir",
                 "offline-report","reports","b4i-build","build-dir","elf"):
        p.add_argument("--"+name,required=True,type=Path)
    p.add_argument("--validation-ordinal",type=int,choices=(0,1,2),default=0)
    p.add_argument("--evidence",type=Path)
    for name in (*physical.APPROVALS,*EXTRA_APPROVALS):
        p.add_argument("--"+name.replace("_","-"),choices=("YES","NO"),default="NO")
    args=p.parse_args()
    try:
        index,desc,routes,elf=require_pc_original_and_new_b5(args)
        print("P07_B5_NEW_RAW_GENUINE_A53_ELF_MAP_AND_ORIGINAL_TRAIN_HOST_PASS=1",flush=True)
        print("P07_B5_NEW_RAW_840320B_DDR_OWNER_INDEPENDENTLY_PROVEN=0",flush=True)
        print("P07_B5_NEW_LOW_DDR_0_TO_0x107BC0_EXCLUSIVITY_PROVEN=0",flush=True)
        if args.mode=="preflight":
            print("P07_B5_NEW_RAW_PC_ONLY_PREFLIGHT_PASS=1",flush=True)
            print("P07_B5_BOARD_CONTACT=0",flush=True)
            print("P07_B5_NEW_RAW_LAUNCH_AUTHORIZED_BY_PREFLIGHT=0",flush=True)
            return 0
        require_new_risk_approval(args)
        def continuation(out:Path,readbacks:dict)->None:
            after_same_session_stage(args,out,readbacks)
        physical.execute_staging(args,index,desc,routes,elf,
                                 on_verified=continuation)
        return 0
    except (ValueError,OSError,KeyError,TypeError,RuntimeError,
            subprocess.TimeoutExpired) as e:
        print("P07_B5_NEW_RAW_PHYSICAL_NO_GO="+str(e),file=sys.stderr,flush=True)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
