#!/usr/bin/env python3
"""PC-only admission of an operator-built B4m DIAGNOSTIC_V2 ELF.

Checks the entire staged C/header source against committed V2 and unchanged
V1 transport, the original accepted frozen B2.4 trained model/route identity,
accepted routed P03 XSA, and the real GNU-linked A53 ELF+map/LOAD/sections.
NEVER contacts FPGA and NEVER authorizes V2 JTAG launch, low DDR, or parity.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

import p07_b4m_offline_admission as admission
import p07_b4l1_stage_frozen_27core as frozen27
import p07_b4m_frozen_inputs as original

V3=Path(__file__).resolve().parents[1]
IDENTITY=b"P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V2"
ELF_NAME="p07_b4m_diag_v2_26tick.elf"
STAGE_MOD=V3/"software/p07/build_p07_b4m_diag.py"
XSA_SHA="52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f"

class DiagnosticAdmissionError(ValueError):
    pass

def sha(path:Path)->str:
    if path.is_symlink() or not path.is_file():
        raise DiagnosticAdmissionError("NO-GO: non-regular source/build artifact: "+str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()

def import_build_contract():
    spec=importlib.util.spec_from_file_location("b4m_diag_v2_vitis",STAGE_MOD)
    if spec is None or spec.loader is None:
        raise DiagnosticAdmissionError("NO-GO: V2 Vitis source contract missing")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if (module.IDENTITY.encode()!=IDENTITY or
        module.APP!="p07_b4m_diag_v2_26tick" or
        module.SOURCES[0]!="p07_b4m_full_board_diag.c"):
        raise DiagnosticAdmissionError("NO-GO: diagnostic V2 build identity drift")
    return module

def verify_staged_source(stage:Path)->dict:
    if not stage.is_absolute() or stage.is_symlink() or not stage.is_dir():
        raise DiagnosticAdmissionError("NO-GO: actual absolute V2 build source directory required")
    contract=import_build_contract()
    contract.check_stage(stage)
    result={}
    names=(*contract.SOURCES,*contract.HEADERS)
    for name in names:
        if name=="p07_b4m_full_board_diag.c":
            reference=V3/"software/p07"/name
        elif name.endswith(".c"):
            prefix="software/p03" if name.startswith("p03_hw_") else "software/p07"
            reference=V3/prefix/name
        elif name.startswith("p03_"):
            reference=V3/"software/p03/include"/name
        elif name=="p05_deployment.h":
            reference=V3/"software/p05/include"/name
        else:
            reference=V3/"software/p07/include"/name
        expected=reference.read_bytes()
        if name=="p07_a2_sha256.c":
            before=b'#include "include/p07_a2_sha256.h"'
            if expected.count(before)!=1:
                raise DiagnosticAdmissionError("NO-GO: accepted SHA source include unexpected")
            expected=expected.replace(before,b'#include "p07_a2_sha256.h"')
        if name=="p07_b2_packet.h":
            before=b"#define P07_B2_MAX_ROUTE_BINDINGS 8192u"
            if expected.count(before)!=1:
                raise DiagnosticAdmissionError("NO-GO: original packet route cap drift")
            expected=expected.replace(before,b"#define P07_B2_MAX_ROUTE_BINDINGS 10000u")
        actual=(stage/name).read_bytes()
        if actual!=expected:
            raise DiagnosticAdmissionError("NO-GO: actual staged V2 compiler source differs from current signed repository: "+name)
        result[name]=hashlib.sha256(actual).hexdigest()
    if len(result)!=len(names):
        raise DiagnosticAdmissionError("NO-GO: incomplete unique imported V2 sources")
    return result

def admit(*,frozen:Path,routes:Path,build:Path,reports:Path)->dict:
    if not build.is_absolute() or build.is_symlink() or not build.is_dir():
        raise DiagnosticAdmissionError("NO-GO: exact operator-local absolute V2 build required")
    frozen27.admit_freeze(frozen)
    source=verify_staged_source(build/"source")
    routes_record=admission.require_routes(routes,frozen)
    if routes_record["input_routes"]!=20384 or routes_record["output_routes"]!=1000:
        raise DiagnosticAdmissionError("NO-GO: original B2.4 topology altered")
    xsa=reports/"p03_2_ps_mmio.xsa"
    if sha(xsa)!=XSA_SHA:
        raise DiagnosticAdmissionError("NO-GO: accepted original P03 routed XSA changed")
    metrics=reports/"p03_2_post_route_metrics.txt"
    metrics_data=metrics.read_text()
    if not all(x in metrics_data.splitlines() for x in (
        "p03_hpm0_data_width_bits=128",
        "p03_hpm0_transport=smartconnect_width_protocol",
        "p03_mmio_slave_data_width_bits=32",
        "p03_ps_mmio_master=FPD",
        "p03_mmio_base=0xA4000000",
    )):
        raise DiagnosticAdmissionError("NO-GO: routed PS128 and P03 original MMIO shell acceptance drift")
    workspace=build/"vitis_workspace"
    elf=workspace/ELF_NAME
    elf_data=admission.require_elf(elf,expected_name=ELF_NAME,expected_id=IDENTITY)
    original_v1=b"P07_B4M_A53_TRAIN_26_TICK_CANDIDATE_V1"
    if original_v1 in elf.read_bytes():
        raise DiagnosticAdmissionError("NO-GO: V2 artifact polluted with V1 firmware identity")
    if not (0<int(elf_data["pt_load_memsz"])<=0x01000000):
        raise DiagnosticAdmissionError("NO-GO: genuine diag V2 ELF outside admitted low DDR envelope")
    # Do not accept external hashes as a substitute for real file checks.
    record={
        "schema":"p07-b4m-diag-v2-genuine-elf-sources-offline-preflight-v1",
        "diagnostic_firmware_identity":IDENTITY.decode(),
        "source_sha256":source,
        "original_frozen_B24_compiled_fingerprint":original.PINNED_SHA,
        "original_route_source":routes_record,
        "accepted_P03_XSA_sha256":XSA_SHA,
        "genuine_diagnostic_v2_elf":elf_data,
        "prior_real_first_dispatch_protocol_error":-5,
        "prior_physical_dispatch_counter":1,
        "prior_failure_mailbox_sha256":"4ff427fca04f75b89712c7ea81d7065710ce46de586f6eb07ec8bd1ea1105baf",
        "original_frozen_model_edited":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "expanded_low_DDR_boot_firmware_exclusivity_independently_proven":False,
        "diagnostic_v2_physical_launch_authorized":False,
        "original_26tick_hardware_inference_accepted":False,
        "numerical_parity_verified":False,
    }
    return record

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--frozen-dir",type=Path,required=True)
    p.add_argument("--routes-dir",type=Path,required=True)
    p.add_argument("--build-dir",type=Path,required=True)
    p.add_argument("--reports",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    try:
        if (not args.out.is_absolute() or args.out.exists() or
            args.out.is_symlink() or
            args.out.resolve().is_relative_to(frozen27.REPO.resolve())):
            raise DiagnosticAdmissionError("NO-GO: new absolute external V2 offline report path required")
        record=admit(frozen=args.frozen_dir,routes=args.routes_dir,
                     build=args.build_dir,reports=args.reports)
        args.out.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
        print("P07_B4M_DIAG_V2_GENUINE_A53_ELF_AND_ORIGINAL_MODEL_OFFLINE_PREFLIGHT_PASS=1")
        print("P07_B4M_DIAG_V2_PHYSICAL_LAUNCH_AUTHORIZED=0")
        print("P07_B4M_DIAG_V2_EXPANDED_LOW_DDR_FIRMWARE_OWNERSHIP_PROVEN=0")
        print("P07_B4M_DIAG_V2_OFFLINE_REPORT="+str(args.out))
        return 0
    except (OSError,ValueError,TypeError,KeyError) as e:
        print("P07_B4M_DIAG_V2_OFFLINE_NO_GO="+str(e),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
