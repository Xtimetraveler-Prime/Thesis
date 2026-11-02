#!/usr/bin/env python3
"""P08-B4.2 full1024 ORIGINAL B2.4 A53 independent admission/physical runner.

DEFAULT: PC-only read-only preflight; 63 pending numerical shard
references or unverified full1024 ELF => NO-GO. Destructive execute
requires the complete original full1024 signed scalar oracle, original
user-built Vitis full1024 ELF+map, separate recorded approvals, same
session physical PS-width/A53 halt/PL programming, SIX original DDR
readbacks, and strict 1024 terminal + neural/timing capture.
No explicit energy, speedup or A/B latency result is accepted here.
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
import p08_b3_pilot16_physical_run as prior
import p08_b3_pilot16_stage_host as source
import p08_b2_3_elf_admission as elfcheck
import p08_b4_1_merge_scalar_1024 as full_ref
import p08_b4_2_verify_full1024 as numerical

V3=Path(__file__).resolve().parents[1]
ELF_SHA="0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1"
MAP_SHA="f7ce75a736b6b093066b8df09a8b02aaa41b490fd48c36c23151b4ac22125efc"
ORIGINAL_FULL1024_ORACLE_SHA="7e564d188651aeabdc284328ea65705bcb0b5571468b9f70d5dcacaa3f5493b8"
LAUNCH_TCL="vivado/p08_b4_2_full1024_run_and_capture.tcl"
STAGE_TCL=prior.STAGE_TCL
STAGE_TOKEN=prior.STAGE_TOKEN
RUN_TOKEN="P08_B4_FULL1024_AFTER_SIX_SIGNED_PHYSICAL_READBACK_RISK_APPROVED"
APPROVALS=(
    "dedicated_jtag_owner",
    "discard_linux_and_halt_all_a53_approved",
    "unproven_boot_ddr_dma_exclusivity_risk_accepted",
    "six_original_ddr_transfers_overwrite_approved",
    "original_p03_pl_programming_approved",
    "low_ddr_full1024_elf_overwrite_approved",
    "mailbox_and_full1024_journals_overwrite_approved",
    "reboot_and_recovery_approved",
)
class FullPhysicalNoGo(ValueError):pass

def require(ok:bool,msg:str)->None:
    if not ok:raise FullPhysicalNoGo("NO-GO: "+msg)

def sha(path:Path)->str:
    require(path.is_file() and not path.is_symlink(),
            "missing/symlink signed input "+str(path))
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1048576),b""):
            h.update(block)
    return h.hexdigest()

def admission(args:argparse.Namespace)->dict:
    # Reuse the ORIGINAL signed source plan and first16 oracle as read-only
    # provenance gate; never modify the accepted 16-image physical evidence.
    prior.original_inputs(args.stage,args.first16)
    b3_pin="b21e388ab2c3896e76373aaf1663b3b3b1a6d6e1e3c192684f7da02d40b0ed11"
    require(sha(args.b3_report)==b3_pin,
            "previous original 16-image independently accepted physical evidence drift")
    b3=json.loads(args.b3_report.read_text())
    require(b3.get("schema")==
            "p08-b3-original-b24-first16-independent-physical-jtag-oracle-verification-v1"
            and b3.get("same_session_original_6_DDR_physical_readbacks_byte_exact") is True
            and b3.get("all_16_original_neural_classifier_and_10_output_spike_vectors_equal_scalar") is True
            and b3.get("all_16_full_26tick_1010_neuron_FNV_fingerprint_equal_scalar") is True
            and b3.get("all_16_A53_full_service_timers_structurally_valid") is True
            and b3.get("original_OFFICIAL_MNIST_TEST")=="SEALED_NOT_ACCESSED",
            "accepted independent original B3 physical numerical/clock evidence invalid")
    require(args.shards.is_absolute() and args.shards.is_dir(),
            "all 64 original B4.1 scalar shard files required")
    require(args.oracle.is_absolute() and
            args.oracle.is_file() and not args.oracle.is_symlink(),
            "new independently generated original full1024 oracle missing")
    require(sha(args.oracle)==ORIGINAL_FULL1024_ORACLE_SHA,
            "operator independently completed all 1024 original scalar oracle SHA changed")
    with TemporaryDirectory(prefix="p08_b4_2_oracle_recheck_") as tmp:
        validated=full_ref.merge(
            args.shards,args.ingress,args.first16,
            Path(tmp)/"original1024.json")
    require(json.loads(args.oracle.read_text())==validated,
            "full1024 oracle differs from regenerated all64 original scalar shards")
    require(args.elf.is_absolute() and args.elf.name=="p08_b4_original_full1024.elf"
            and args.linker_map.is_absolute() and
            args.linker_map.name=="p08_b4_original_full1024.map",
            "separate full1024 Vitis candidate ELF/map staging names required")
    require(sha(args.elf)==ELF_SHA and sha(args.linker_map)==MAP_SHA,
            "original independently admitted 1024 Vitis ELF/map SHA changed")
    with TemporaryDirectory(prefix="p08_b4_2_elf_recheck_") as tmp:
        elfcheck.audit(
            args.elf,args.linker_map,
            args.reports/"p03_2_ps_mmio.xsa",
            args.reset_pins/"p08_b2_2_original_context_sha256.h",
            Path(tmp)/"elf_loads.json")
    # Exact A53 identity + 1024 terminal marker (not a 16-image pilot)
    raw=args.elf.read_bytes()
    require(elfcheck.IDENTITY in raw and
            b"P08_B2_3_IMAGE_ONLY_1024_TERMINAL_DONE=1" in raw and
            b"P08_B3_ORIGINAL_27CORE_FIRST16_PILOT_A53_V1" not in raw,
            "original B2.3 1024-ELF model execution identity wrong")
    metrics=(args.reports/"p03_2_post_route_metrics.txt").read_text().splitlines()
    require(all(x in metrics for x in b4i.REQUIRED_METRICS),
            "accepted original P03 FPD128 routed metadata changed")
    accepted={}
    for filename,pin in b4i.EXPECTED_SHA.items():
        require(sha(args.reports/filename)==pin,
                "original accepted P03 XSA/bitstream/LTX SHA drift: "+filename)
        accepted[filename]=pin
    return {
        "schema":"p08-b4-2-original-b24-full1024-read-only-admission-v1",
        "original_B3_signed_first16_scalar_sha256":prior.gate.ORACLE_SHA,
        "genuine_B3_physically_accepted_pilot16_report_sha256":b3_pin,
        "original_full1024_scalar_oracle_sha256":ORIGINAL_FULL1024_ORACLE_SHA,
        "original_full1024_scalar_shard_count":64,
        "exact_full1024_original_B23_A53_ELF_SHA256":ELF_SHA,
        "exact_full1024_original_B23_A53_linker_map_SHA256":MAP_SHA,
        "accepted_P03_shell":accepted,
        "original_27core_P02_sha256":source.EXPECTED_SHA[source.FILES[0][0]],
        "original_1024_pixel_sha256":source.EXPECTED_SHA[source.FILES[4][0]],
        "physical_DDR_owner_exclusivity_proven":False,
        "operator_destructive_JTAG_authorized_by_preflight":False,
        "full1024_KV260_actual_physical_run":False,
        "benchmark_TrackB_latency_accepted":False,
        "original_OFFICIAL_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }

def marker(path:Path,s:str)->None:
    require(path.read_text().splitlines().count(s)==1,
            "authentic physical tool transcript missing unique "+s)

def execute(args:argparse.Namespace,approved:dict)->None:
    for name in APPROVALS:
        require(getattr(args,name)=="YES",
                "independent explicit --"+name.replace("_","-")+" YES required")
    require(args.evidence is not None and args.evidence.is_absolute() and
            not args.evidence.exists() and not args.evidence.is_symlink() and
            not args.evidence.resolve().is_relative_to(b4i.ROOT.resolve())
            and args.evidence.parent.is_dir(),
            "NEW external physical evidence directory required")
    require(all(shutil.which(t) for t in ("xsdb","vivado")),
            "genuine XSDB/Vivado tools absent from operator machine")
    root=args.evidence
    root.mkdir(mode=0o700)
    (root/"preflight.json").write_text(json.dumps(
        {**approved,"operator_destructive_JTAG_authorized_by_preflight":False,
         "eight_distinct_operator_execute_approvals":True,
         "physical_JTAG_session_started":False},
        indent=2,sort_keys=True)+"\n")
    cap=root/"full1024_capture"
    cap.mkdir()
    reads=root/"source_physical_readback"
    reads.mkdir()
    try:
        (root/"stage.txt").write_text(
            "P08_B4_2_FULL1024_DESTRUCTIVE_JTAG_ATTEMPT_STARTED_REBOOT_REQUIRED\n")
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
        src=[args.stage/name for name,_,_ in source.FILES]
        b4i.log_call([
            "xsdb",STAGE_TCL,STAGE_TOKEN,*map(str,src),str(reads),
            "tcp:127.0.0.1:3121",
        ],root/"six_original_ddr_physical_stage.log")
        marker(root/"six_original_ddr_physical_stage.log",
               "P08_B3_PILOT_SIX_PHYSICAL_DDR_TRANSFERS_BYTE_EXACT_PASS=1")
        signed=prior.readback_original(args.stage,reads)
        (root/"same_session_six_source_receipt.json").write_text(json.dumps(
            {"original_six_physical_source_sha256":signed,
             "exact_full1024_original_ELF_sha256":ELF_SHA,
             "original_full1024_scalar_sha256":approved[
                 "original_full1024_scalar_oracle_sha256"],
             "same_session_JTAG_physical_DDR_readbacks":True,
             "full1024_A53_ELF_downloaded_at_receipt_time":False,
             "operator_reboot_required":True,
             "original_OFFICIAL_MNIST_TEST":"SEALED_NOT_ACCESSED"},
            indent=2,sort_keys=True)+"\n")
        (root/"stage.txt").write_text(
            "P08_B4_2_FULL1024_SIX_ORIGINAL_PHYSICAL_DDR_READBACKS_PASS_REBOOT_REQUIRED\n")
        zero256=root/"zero256.bin"
        zero262144=root/"zero262144.bin"
        zero256.write_bytes(bytes(256))
        zero262144.write_bytes(bytes(1024*256))
        b4i.log_call([
            "xsdb",LAUNCH_TCL,RUN_TOKEN,str(args.elf),
            str(zero256),str(zero262144),
            str(cap),"tcp:127.0.0.1:3121",
        ],root/"full1024_a53_physical_run.log")
        for s in (
            "P08_B4_FULL1024_EXACT_OPERATOR_SHA_PINNED_ELF_DOWNLOADED=1",
            "P08_B4_FULL1024_REAL_1024_JOURNAL_AND_TIMING_SIDECARS_PHYSICAL_CAPTURED=1",
            "P08_B4_FULL1024_EXACT_1024_FRAME_HARDWARE_TERMINAL_OBSERVED=1",
        ):
            marker(root/"full1024_a53_physical_run.log",s)
        untrusted=numerical.verify(
            args.oracle,args.first16,cap/"journal1024_physical.bin",
            cap/"timing1024_physical.bin",cap/"mailbox_terminal_physical.bin",
            root/"full1024_untrusted_scalar_and_timing_precheck.json")
        require(untrusted["count"]==1024,
                "full1024 original scalar numerical precheck incomplete")
        (root/"stage.txt").write_text(
            "P08_B4_2_1024_REAL_A53_TERMINAL_AND_NUMERICAL_PRECHECK_PASS_INDEPENDENT_JTAG_VERIFICATION_PENDING_REBOOT_REQUIRED\n")
        print("P08_B4_2_FULL1024_REAL_HARDWARE_NUMERICAL_PRECHECK_PASS=1")
        print("P08_B4_2_INDEPENDENT_PHYSICAL_PROVENANCE_VERIFICATION_PENDING=1")
    finally:
        print("P08_B4_2_AFTER_ANY_DESTRUCTIVE_JTAG_ATTEMPT_REBOOT_REQUIRED=1",flush=True)
        print("REBOOT KV260 before Linux or any new hardware experiment.",flush=True)

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=("preflight","execute"),default="preflight")
    for name in ("stage","shards","ingress","oracle","first16",
                 "b3_report","elf","linker_map","reset_pins","reports"):
        p.add_argument("--"+name.replace("_","-"),required=True,type=Path)
    p.add_argument("--evidence",type=Path)
    for a in APPROVALS:
        p.add_argument("--"+a.replace("_","-"),choices=("YES","NO"),default="NO")
    args=p.parse_args()
    try:
        approved=admission(args)
        print("P08_B4_2_ORIGINAL_ALL1024_SCALAR_AND_GENUINE_ELF_OFFLINE_PREFLIGHT_PASS=1")
        print("P08_B4_2_GENUINE_ORIGINAL_FULL1024_ELF_SHA="+ELF_SHA)
        print("P08_B4_2_GENUINE_ORIGINAL_FULL1024_MAP_SHA="+MAP_SHA)
        print("P08_B4_2_DDR_BOOT_FW_DMA_OWNER_EXCLUSIVITY_PROVEN=0")
        if args.mode=="preflight":
            print("P08_B4_2_READONLY_BOARD_VISITED=0")
            print("P08_B4_2_PHYSICAL_EXECUTE_NOT_AUTHORIZED_BY_PREFLIGHT=1")
            return 0
        execute(args,approved)
        return 0
    except (FullPhysicalNoGo,prior.PilotPhysicalNoGo,
            full_ref.MergeNoGo,numerical.FullRecordNoGo,elfcheck.ElfNoGo,
            ValueError,TypeError,KeyError,OSError,RuntimeError,
            subprocess.TimeoutExpired) as e:
        print("P08_B4_2_PHYSICAL_NO_GO="+str(e),file=sys.stderr,flush=True)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
