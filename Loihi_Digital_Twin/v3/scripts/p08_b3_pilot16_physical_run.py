#!/usr/bin/env python3
"""P08-B3 original B2.4 FIRST16 KV260 pilot runner, DEFAULT PC preflight.

Destructive --mode execute needs eight independent explicit YES approvals,
a dedicated cold-boot XSDB session, accepted FPGA bitstream, halted Linux,
six verified physical DDR transfers (including SEPARATE 27core backup),
exact SHA-pinned new pilot ELF/map, and a reboot after ANY JTAG attempt.

Neither operator risk acceptance nor PT_LOAD admission proves exclusive
boot/PS/PL DMA owners. This driver does NOT use any official MNIST TEST.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

import p07_b4i_physical_pilot as b4i
import p07_b4j_shell_program_pilot as b4j
import p08_b3_pilot16_stage_host as source
import p08_b3_pilot16_admission as gate
import p08_b2_4_verify_untrusted_first16 as scalar
import p08_b2_3_elf_admission as elf_gate

V3=Path(__file__).resolve().parents[1]
APPROVALS=(
    "dedicated_jtag_owner",
    "discard_linux_and_halt_all_a53_approved",
    "unproven_boot_ddr_dma_exclusivity_risk_accepted",
    "six_original_ddr_transfers_overwrite_approved",
    "original_p03_pl_programming_approved",
    "low_ddr_new_pilot_elf_overwrite_approved",
    "mailbox_and_two_journals_overwrite_approved",
    "reboot_and_recovery_approved",
)
ELF_SHA="29482212c80fb9137b3c185b0cbcdf2000f41417e5af8d3c46b0cd39ecb74fd3"
MAP_SHA="9d2106d82347385e936bb27176aa8f50a332beb3f13c3ca8e182890a689c674b"
STAGE_TCL="vivado/p08_b3_pilot16_six_ddr_stage.tcl"
LAUNCH_TCL="vivado/p08_b3_pilot16_run_and_capture.tcl"
STAGE_TOKEN="P08_B3_PILOT16_SIX_DDR_TRANSFERS_RISK_APPROVED"
RUN_TOKEN="P08_B3_PILOT16_AFTER_SIX_SIGNED_PHYSICAL_READBACK_RISK_APPROVED"

class PilotPhysicalNoGo(ValueError):pass

def require(ok:bool,detail:str)->None:
    if not ok: raise PilotPhysicalNoGo("NO-GO: "+detail)

def sha(path:Path)->str:
    require(path.is_file() and not path.is_symlink(),"missing or symlink file "+str(path))
    h=hashlib.sha256()
    with path.open("rb") as fd:
        for chunk in iter(lambda:fd.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def original_inputs(stage:Path,oracle:Path)->dict:
    require(stage.is_absolute() and stage.is_dir() and not stage.is_symlink(),
            "external original pilot16 immutable stage required")
    plan=stage/source.PLAN_FILE
    info=json.loads(plan.read_text())
    require(info.get("schema")==source.SCHEMA and
            info.get("first16_scalar_oracle_sha256")==gate.ORACLE_SHA and
            info.get("original_27core_P02_bytes_are_NOT_modified") is True and
            info.get("pilot_executed_frames")==0 and
            info.get("board_contact") is False and
            info.get("same_session_JTAG_readback_verified") is False and
            info.get("proposed_ddr_transfers")==source.plan_locations(),
            "original immutable PC-only transfer manifest drift")
    require(sha(oracle)==gate.ORACLE_SHA,"original scalar reference SHA drift")
    gate.source_oracle(oracle)
    expected={name for name,_,_ in source.FILES}|{source.PLAN_FILE}
    require({p.name for p in stage.iterdir()}==expected,
            "original source staging unexpected files")
    for name,lo,hi in source.FILES:
        p=stage/name
        require(p.stat().st_size==int(hi,16)-int(lo,16) and
                sha(p)==source.EXPECTED_SHA[name],
                "original frozen SHA/memory length differs: "+name)
    return info

def offline_gate(args:argparse.Namespace)->dict:
    original_inputs(args.stage,args.oracle)
    require(args.pilot_build.is_absolute() and args.pilot_build.is_dir() and
            not args.pilot_build.is_symlink(),
            "genuine new original first16 Vitis build dir required")
    elf=args.pilot_build/"vitis_workspace/p08_b3_original_pilot16.elf"
    link=args.pilot_build/"vitis_workspace/p08_b3_original_pilot16.map"
    report=args.pilot_build/"p08_b3_original_pilot16_elf_admission.json"
    xsa=args.reports/"p03_2_ps_mmio.xsa"
    hdr=args.reset_pins/"p08_b2_2_original_context_sha256.h"
    require(sha(elf)==ELF_SHA and sha(link)==MAP_SHA,
            "user-built dedicated original B2.4 PILOT16 SHA has changed")
    require(report.is_file() and not report.is_symlink(),
            "pilot16 original read-only ELF/offline report absent")
    # Regenerate real AArch64 ELF/load/oracle gate independently; never
    # trust previous JSON alone for an actual JTAG launch admission.
    with TemporaryDirectory(prefix="p08_b3_read_only_") as path:
        actual=gate.analyse(elf,link,xsa,hdr,args.oracle,
                            Path(path)/"independent.json")
    require(json.loads(report.read_text())==actual,
            "pilot16 operator genuine build preflight report has changed")
    metrics=(args.reports/"p03_2_post_route_metrics.txt").read_text().splitlines()
    require(all(m in metrics for m in b4i.REQUIRED_METRICS),
            "accepted PS FPD128 routed metrics drift")
    hashes={}
    for name,pin in b4i.EXPECTED_SHA.items():
        p=args.reports/name
        require(sha(p)==pin,"original accepted P03 XSA/bitstream/LTX changed: "+name)
        hashes[name]=pin
    return {
        "schema":"p08-b3-original-b24-first16-coldboot-physical-preflight-v1",
        "first16_scalar_sha256":gate.ORACLE_SHA,
        "original_27core_mutable_and_backup_sha256":source.EXPECTED_SHA[source.FILES[0][0]],
        "original_input_1024_pool_sha256":source.EXPECTED_SHA[source.FILES[4][0]],
        "distinct_original_pilot16_elf_sha256":ELF_SHA,
        "distinct_original_pilot16_map_sha256":MAP_SHA,
        "accepted_shell":hashes,
        "operator_hardware_approvals_received":False,
        "exclusive_boot_ddr_dma_owners_independently_proven":False,
        "JTAG_attempted":False,
        "hardware_inference_executed":False,
        "genuine_live_KV260_result_accepted":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }

def log_has_exact(path:Path,needle:str)->None:
    data=path.read_text()
    require(data.splitlines().count(needle)==1,
            "missing/duplicate physical hardware marker "+needle)

def readback_original(stage:Path,readback:Path)->dict:
    """Host byte-exact independent SHA from real mrd -bin captures."""
    proof={}
    # Keep the immutable source file's NAME (str) distinct from its full
    # filesystem PATH (Path). EXPECTED_SHA is keyed by filename strings.
    # The first real 6-transfer pilot reached this post-JTAG host check,
    # where indexing EXPECTED_SHA with a Path previously raised KeyError.
    original_name=source.FILES[0][0]
    original_path=stage/original_name
    accepted=original_path.read_bytes()
    require(len(accepted)==27*524288 and
            hashlib.sha256(accepted).hexdigest()==source.EXPECTED_SHA[original_name],
            "original 27core P02 source changed after PSU staging")
    for label in ("mutable","backup"):
        directory=readback/(label+"_original_p02_readback")
        require(directory.is_dir() and not directory.is_symlink() and
                {p.name for p in directory.iterdir()}==
                {f"core_{i:02d}_physical.bin" for i in range(27)},
                "physical 27 P02 core readback set incomplete: "+label)
        fullhash=hashlib.sha256()
        for i in range(27):
            payload=directory/f"core_{i:02d}_physical.bin"
            data=payload.read_bytes()
            require(not payload.is_symlink() and len(data)==524288 and
                    data==accepted[i*524288:(i+1)*524288],
                    f"original {label} P02 core {i} physical mrd differs from immutable")
            fullhash.update(data)
        require(fullhash.hexdigest()==source.EXPECTED_SHA[original_name],
                label+" independent original 27core aggregate SHA differs")
        proof[label+"_27core_sha256"]=fullhash.hexdigest()
    pairs=(
        (source.FILES[1][0],"binding_16k_physical.bin"),
        (source.FILES[2][0],"input_routes_896k_physical.bin"),
        (source.FILES[3][0],"output_routes_80k_physical.bin"),
        (source.FILES[4][0],"raw1024_physical.bin"),
    )
    for name,target in pairs:
        observed=readback/target
        expected=stage/name
        require(not observed.is_symlink() and observed.is_file() and
                observed.read_bytes()==expected.read_bytes() and
                sha(observed)==source.EXPECTED_SHA[name],
                "original signed stage physical readback drift: "+target)
        proof[target]=sha(observed)
    return proof

def execute(args:argparse.Namespace,preflight:dict)->None:
    for name in APPROVALS:
        require(getattr(args,name)=="YES",
                "explicit separate --"+name.replace("_","-")+" YES required")
    require(args.evidence is not None and args.evidence.is_absolute() and
            not args.evidence.exists() and not args.evidence.is_symlink() and
            not args.evidence.resolve().is_relative_to(b4i.ROOT.resolve()) and
            args.evidence.parent.is_dir(),
            "require NEW external physical evidence root directory")
    require(all(shutil.which(tool) for tool in ("xsdb","vivado")),
            "Vivado/XSDB not on operator machine")
    root=args.evidence
    root.mkdir(mode=0o700)
    (root/"stage.txt").write_text(
        "P08_B3_PILOT16_OPERATOR_APPROVAL_RECORDED_JTAG_NOT_YET_ATTEMPTED\n")
    (root/"preflight.json").write_text(json.dumps(
        {**preflight,"operator_hardware_approvals_received":True,
         "exclusive_boot_ddr_dma_owners_independently_proven":False,
         "JTAG_attempted":False},sort_keys=True,indent=2)+"\n")
    reads=root/"source_physical_readback"
    reads.mkdir()
    capture=root/"pilot16_physical_capture"
    capture.mkdir()
    original_stage=args.stage
    src=[original_stage/name for name,_,_ in source.FILES]
    elf=args.pilot_build/"vitis_workspace/p08_b3_original_pilot16.elf"
    try:
        (root/"stage.txt").write_text(
            "P08_B3_PILOT16_JTAG_ATTEMPT_STARTED_REBOOT_REQUIRED\n")
        # Original proven PS width/CPU takeover and accepted P03 VIO release.
        b4i.log_call([
            "xsdb",b4j.TAKEOVER_TCL,"DEDICATED_DISCARD_LINUX_APPROVED",
            "tcp:127.0.0.1:3121",
        ],root/"a53_takeover_and_ps128.log")
        b4i.verify_takeover_log((root/"a53_takeover_and_ps128.log").read_text())
        b4i.log_call([
            "vivado","-mode","batch","-source",b4j.PROGRAM_TCL,
            "-tclargs",str(args.reports/"p03_2_ps_mmio.bit"),
            str(args.reports/"p03_2_ps_mmio.ltx"),"localhost:3121",
        ],root/"accepted_p03_program.log")
        b4j.require_programmed_shell((root/"accepted_p03_program.log").read_text())
        (root/"stage.txt").write_text("P08_B3_ACCEPTED_P03_PL_PROGRAMMED_REBOOT_REQUIRED\n")
        b4i.log_call([
            "xsdb",STAGE_TCL,STAGE_TOKEN,*map(str,src),
            str(reads),"tcp:127.0.0.1:3121",
        ],root/"six_original_ddr_physical_stage.log")
        log_has_exact(root/"six_original_ddr_physical_stage.log",
                      "P08_B3_PILOT_SIX_PHYSICAL_DDR_TRANSFERS_BYTE_EXACT_PASS=1")
        signed=readback_original(original_stage,reads)
        (root/"same_session_six_source_receipt.json").write_text(
            json.dumps({"original_six_physical_source_sha256":signed,
                        "operator_pilot16_sha256":ELF_SHA,
                        "operator_pilot16_map_sha256":MAP_SHA,
                        "source_model_original_frozen":True,
                        "new_a53_elf_downloaded":False,
                        "same_session_jtag_source_readback":True,
                        "exclusive_boot_ddr_dma_owners_independently_proven":False,
                        "reboot_required":True,
                        "official_MNIST_TEST":"SEALED_NOT_ACCESSED"},
                       indent=2,sort_keys=True)+"\n")
        (root/"stage.txt").write_text(
            "P08_B3_PILOT_SIX_PHYSICAL_DDR_AND_IMMUTABLE_BACKUP_READBACK_PASS_REBOOT_REQUIRED\n")
        # No ELF download before ALL originals are read back and rehashed.
        (root/"zeros256.bin").write_bytes(bytes(256))
        (root/"zeros4096.bin").write_bytes(bytes(4096))
        b4i.log_call([
            "xsdb",LAUNCH_TCL,RUN_TOKEN,str(elf),
            str(root/"zeros256.bin"),str(root/"zeros4096.bin"),
            str(capture),"tcp:127.0.0.1:3121",
        ],root/"pilot16_a53_physical_run.log")
        for text in (
            "P08_B3_PILOT_EXACT_OPERATOR_SHA_PINNED_ELF_DOWNLOADED=1",
            "P08_B3_PILOT_REAL_16_JOURNAL_AND_TIMING_SIDECARS_PHYSICAL_CAPTURED=1",
            "P08_B3_PILOT_EXACT_16_FRAME_HARDWARE_TERMINAL_OBSERVED=1",
        ):
            log_has_exact(root/"pilot16_a53_physical_run.log",text)
        # This verifier is intentionally *not* a physical provenance
        # certificate; later separate independent JTAG receipt gate needed.
        preliminary=scalar.verify(
            args.oracle,capture/"journal16_physical.bin",
            capture/"timing16_physical.bin",
            capture/"mailbox_terminal_physical.bin",
            root/"pilot16_untrusted_format_scalar_precheck.json")
        require(preliminary["verified_frames"]==16,
                "pilot16 neural/timing independent scalar first-pass failed")
        (root/"stage.txt").write_text(
            "P08_B3_FIRST16_JTAG_RESULTS_MATCH_SCALAR_PRECHECK_INDEPENDENT_PHYSICAL_ATTESTATION_PENDING_REBOOT_REQUIRED\n")
        print("P08_B3_FIRST16_BOARD_RESULT_NUMERICAL_PRECHECK_PASS=1")
        print("P08_B3_PILOT16_INDEPENDENT_PHYSICAL_PROVENANCE_VERIFICATION_PENDING=1")
    finally:
        print("P08_B3_AFTER_ANY_DESTRUCTIVE_JTAG_ATTEMPT_REBOOT_REQUIRED=1",flush=True)
        print("REBOOT KV260 before Linux or any further hardware experiment.",flush=True)

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=("preflight","execute"),default="preflight")
    for name in ("stage","pilot-build","reset-pins","oracle","reports"):
        p.add_argument("--"+name.replace("_","-"),required=True,type=Path)
    p.add_argument("--evidence",type=Path)
    for name in APPROVALS:
        p.add_argument("--"+name.replace("_","-"),choices=("YES","NO"),default="NO")
    a=p.parse_args()
    try:
        report=offline_gate(a)
        print("P08_B3_PILOT16_ORIGINAL_SIGNED_SIX_SOURCE_ELF_ORACLE_PREFLIGHT_PASS=1")
        print("P08_B3_PILOT16_USER_ELF_SHA256="+ELF_SHA)
        print("P08_B3_PILOT16_USER_MAP_SHA256="+MAP_SHA)
        print("P08_B3_PILOT16_PSU_DDR_BOOT_DMA_EXCLUSIVITY_INDEPENDENTLY_PROVEN=0")
        if a.mode=="preflight":
            print("P08_B3_PILOT16_READ_ONLY_BOARD_VISITED=0")
            print("P08_B3_PILOT16_EXECUTION_NOT_AUTHORIZED_BY_PREFLIGHT=1")
            return 0
        execute(a,report)
        return 0
    except (PilotPhysicalNoGo,ValueError,KeyError,OSError,
            TypeError,RuntimeError,subprocess.TimeoutExpired) as e:
        print("P08_B3_PILOT16_PHYSICAL_NO_GO="+str(e),file=sys.stderr,flush=True)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
