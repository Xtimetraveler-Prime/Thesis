#!/usr/bin/env python3
"""P07-B.4m original signed TRAIN 26-tick FULL physical experiment.

PC preflight is the DEFAULT and never contacts FPGA. Execute is destructive
to existing Linux, the exact accepted model DDR regions, 256B mailbox, and
the A53 low DDR physical [0,0x00106B00). Explicit independent approvals
are required before ANY board step. Do NOT reuse original B4l old ELF/Tcl.

On each execute attempt, re-stage & verify the original 27x512 KiB contexts,
16KiB metadata, 80KiB and 896KiB routing, plus one original B2.3 TRAIN
frame, in the SAME JTAG-ownership session BEFORE downloading pinned new ELF.
Capture physical mailbox; independently check 702 dispatches, 26 global
barriers, real trace evidence. Structural receipt is not neural parity.
All hardware attempts require KV260 REBOOT (do NOT resume halted Linux).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import p07_b4m_physical_staging as physical
import p07_b4m_verify_full_receipt as full_verify

LAUNCH_TCL="vivado/p07_b4m_xsdb_full_26tick_run.tcl"
LAUNCH_TOKEN="B4M_FULL_26TICK_AFTER_SAME_SESSION_SIGNED_READBACK_APPROVED"
LAUNCH_MARKERS=(
    "P07_B4M_256B_MAILBOX_ZERO_PHYSICAL_READBACK_PASS=1",
    "P07_B4M_A53_26TICK_ELF_DOWNLOADED=1",
    "P07_B4M_A53_MAILBOX_CAPTURED_256_BYTES=1",
    "P07_B4M_A53_26TICK_TERMINAL_DONE_PHYSICALLY_OBSERVED=1",
    "P07_B4M_A53_FULL_26TICK_MAILBOX_CAPTURE_READY_FOR_INDEPENDENT_VERIFIER=1",
)
APPROVALS=(
    "expanded_low_ddr_1075968_footprint_approved",
    "unproven_boot_firmware_exclusivity_risk_accepted",
    "mailbox_256b_overwrite_approved",
    "a53_26tick_full_inference_approved",
)

class InferenceNoGo(ValueError):
    pass


def independent_launch_consent(args:argparse.Namespace)->None:
    # Stage-only gate is retained fully unchanged for all eight approvals.
    physical.stage_requirements(args)
    for name in APPROVALS:
        if getattr(args,name)!="YES":
            raise InferenceNoGo(
                "NO-GO: explicit --"+name.replace("_","-")+" YES required; "
                "unproven low-DDR exclusivity is NOT inferred from preflight"
            )
    # Never construe YES as proof. Require exact pinned operator ELF shape.
    if physical.EXPECTED_ELF_SHA!="ccbd8c531e5571f929e81613cfee71f54abf341c36412ebcfa7d98e2313e6b70":
        raise InferenceNoGo("NO-GO: B4m ELF identity contract drift")


def physically_execute_after_verified(args:argparse.Namespace,out:Path,
                                        readbacks:dict)->dict:
    """Invoked ONLY by verified SAME-SESSION original frozen data stager."""
    if not (out/"independent_staging_receipt.json").is_file():
        raise InferenceNoGo("NO-GO: original B2.4 physical readback receipt absent")
    staging=json.loads((out/"independent_staging_receipt.json").read_text())
    if (staging.get("original_27core_contexts_sha256")!=
            physical.model.ACCEPTED_BUNDLE_SHA or
        staging.get("original_descriptor_16k_sha256")!=
            physical.old.ACCEPTED_DESCRIPTOR_SHA or
        set(readbacks)!={
            "output_routes_80k_physical.bin",
            "input_routes_896k_physical.bin",
            "original_TRAIN_ingress_physical.bin",
        } or staging.get("real_elf_downloaded") is not False or
        staging.get("inference_executed") is not False or
        staging.get("official_MNIST_TEST")!="SEALED_NOT_ACCESSED"):
        raise InferenceNoGo("NO-GO: incomplete/mismatched same-session original physical readbacks")
    frame=f"p07_b4m_original_TRAIN_validation_{args.validation_ordinal}_ingress.bin"
    required={
        "output_routes_80k_physical.bin":physical.frozen.OUT_FILENAME,
        "input_routes_896k_physical.bin":physical.frozen.IN_FILENAME,
        "original_TRAIN_ingress_physical.bin":frame,
    }
    verified=staging.get("original_B2_4_routes_and_train_physical_sha256")
    if not isinstance(verified,dict) or set(verified)!=set(required):
        raise InferenceNoGo("NO-GO: verified staged original route/ingress list incomplete")
    for name,source in required.items():
        source_sha=physical.EXPECTED_STAGE_SHA[source]
        result=verified[name]
        if (result.get("sha256")!=source_sha or
            result.get("byte_exact_vs_signed_host_input") is not True or
            readbacks[name]["sha256"]!=source_sha or
            physical.old.file_sha(out/"b4m_physical_route_readback"/name)!=source_sha):
            raise InferenceNoGo("NO-GO: same-session original source DDR byte mismatch: "+name)
    if physical.old.file_sha(args.elf)!=physical.EXPECTED_ELF_SHA or (
        physical.old.file_sha(args.elf.with_suffix(".map"))!=physical.EXPECTED_MAP_SHA):
        raise InferenceNoGo("NO-GO: exact approved full A53 ELF/map mutated since host preflight")
    # VERY IMPORTANT: deliberately record risk as NOT proven, even with
    # separate explicit operator consent, because halted CPU / earlier
    # 0x42D40 B4l proof cannot guarantee [0,0x106B00) is firmware-exclusive.
    (out/"full_inference_launch_contract.json").write_text(json.dumps({
        "board_session":"already halted Linux, accepted P03 shell, and all ORIGINAL model/TRAIN physical readbacks",
        "new_elf_sha256":physical.EXPECTED_ELF_SHA,
        "new_linker_map_sha256":physical.EXPECTED_MAP_SHA,
        "destructive_low_DDR_span":"[0x00000000,0x00106B00)",
        "destructive_low_DDR_bytes":1075968,
        "expanded_low_DDR_firmware_exclusivity_independently_proven":False,
        "operator_explicit_risk_acceptance":True,
        "original_TRAIN_validation_ordinal":args.validation_ordinal,
        "original_TRAIN_frame_sha256":physical.EXPECTED_STAGE_SHA[frame],
        "mailbox_span":"[0x43FF0000,0x43FF0100)",
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "full_independent_neuron_numerical_parity_proven":False,
        "reboot_required":True,
    },sort_keys=True,indent=2)+"\n")
    (out/"stage.txt").write_text(
        "B4M_SIGNED_27CORE_ROUTE_TRAIN_PHYSICAL_READBACK_PASS_A53_LAUNCH_PENDING_REBOOT_REQUIRED\n"
    )
    zero=out/"full_26tick_mailbox_zero_256.bin"
    with zero.open("xb") as f:
        f.write(bytes(256))
    mailbox=out/"full_26tick_physical_mailbox_256.bin"
    physical.old.b4i.log_call([
        "xsdb",LAUNCH_TCL,LAUNCH_TOKEN,
        str(args.elf),str(zero),str(mailbox),"tcp:127.0.0.1:3121",
    ],out/"full_26tick_a53_run.log")
    for marker in LAUNCH_MARKERS:
        physical.old.checked_marker(out/"full_26tick_a53_run.log",marker)
    if (not mailbox.is_file() or mailbox.is_symlink() or
        mailbox.stat().st_size!=256):
        raise InferenceNoGo("NO-GO: A53 did not deliver exact physical 256B completion mailbox")
    receipt=full_verify.verify(mailbox.read_bytes())
    if (receipt["physical_dispatches"]!=702 or
        receipt["physical_barriers_acked"]!=26 or
        receipt["original_registered_axons"]!=21384 or
        receipt["independent_full_neuron_numerical_parity"] is not False or
        receipt["official_MNIST_TEST"]!="SEALED_NOT_ACCESSED"):
        raise InferenceNoGo("NO-GO: full inference mailbox violated original physical admission")
    complete={
        "schema":"p07-b4m-real-original-train-full-26tick-physical-execution-v1",
        "original_27core_bundle_sha256":physical.model.ACCEPTED_BUNDLE_SHA,
        "original_16k_descriptor_sha256":physical.old.ACCEPTED_DESCRIPTOR_SHA,
        "original_routing_frame_physical_readback":verified,
        "new_A53_full_26tick_elf_sha256":physical.EXPECTED_ELF_SHA,
        "trained_original_validation_ordinal":args.validation_ordinal,
        "physical_mailbox":receipt,
        "full_26tick_trained_physical_execution_structurally_verified":True,
        "independent_full_neuron_numerical_parity_verified":False,
        "expanded_low_DDR_boot_firmware_exclusivity_independently_proven":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "reboot_required":True,
    }
    (out/"independent_full_26tick_physical_receipt.json").write_text(
        json.dumps(complete,indent=2,sort_keys=True)+"\n"
    )
    (out/"stage.txt").write_text(
        "P07_B4M_GENUINE_26TICK_PHYSICAL_INFERENCE_RECEIPT_ACCEPTED_REBOOT_REQUIRED\n"
    )
    print("P07_B4M_GENUINE_26TICK_PHYSICAL_INFERENCE_RECEIPT_ACCEPTED=1",flush=True)
    print("P07_B4M_INDEPENDENT_FULL_NEURON_NUMERICAL_PARITY_VERIFIED=0",flush=True)
    return complete


def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=("preflight","execute"),default="preflight")
    for name in ("frozen-dir","staged-dir","bindings-dir","routes-dir",
                 "offline-report","reports","b4i-build","elf"):
        p.add_argument("--"+name,required=True,type=Path)
    p.add_argument("--validation-ordinal",type=int,choices=(0,1,2),default=0)
    p.add_argument("--evidence",type=Path)
    for name in (*physical.APPROVALS,*APPROVALS):
        p.add_argument("--"+name.replace("_","-"),choices=("NO","YES"),default="NO")
    args=p.parse_args()
    try:
        index,desc,staged,elf=physical.require_original(args)
        print("P07_B4M_SIGNED_MODEL_TRAIN_GENUINE_ELF_HOST_GATE_PASS=1",flush=True)
        print(f"P07_B4M_ORIGINAL_TRAIN_VALIDATION_ORDINAL={args.validation_ordinal}",flush=True)
        print("P07_B4M_LOW_DDR_0_TO_0x106B00_EXCLUSIVITY_INDEPENDENTLY_PROVEN=0",flush=True)
        if args.mode=="preflight":
            print("P07_B4M_FULL_26TICK_RUNNER_READ_ONLY_PREFLIGHT_PASS=1",flush=True)
            print("P07_B4M_KV260_ACCESSED=0",flush=True)
            print("P07_B4M_A53_FULL_INFERENCE_LAUNCH_APPROVED_BY_PREFLIGHT=0",flush=True)
            return 0
        independent_launch_consent(args)
        def continuation(out:Path,readbacks:dict)->None:
            physically_execute_after_verified(args,out,readbacks)
        # The verified stager halts Linux, programs accepted P03 PL and
        # independently SHA/byte-verifies ALL ORIGINAL DDR within this
        # single destructive board session before invoking continuation.
        physical.execute_staging(args,index,desc,staged,elf,on_verified=continuation)
        return 0
    except (InferenceNoGo,physical.StageNoGo,ValueError,OSError,TypeError,
            KeyError,RuntimeError,subprocess.TimeoutExpired) as exc:
        print("P07_B4M_FULL_26TICK_NO_GO="+str(exc),file=sys.stderr,flush=True)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
