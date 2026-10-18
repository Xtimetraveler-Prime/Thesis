#!/usr/bin/env python3
"""P08-A3.2.1 fail-closed OFFLINE comparison of two real 1024-image runs.

No hardware access, no official TEST and no writes except new report. Requires
accepted byte-complete physical evidence from the future A3.2.2 JTAG runner.
Both runs must independently PASS frozen P07 integer/P03 packed oracle before
ANY numeric latency can be accepted. Exact original A2.1/A2.2 ELF pinned.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from loihi_twin_v2.p06_input_contract import image_event_schedule
from loihi_twin_v2.p07_a4_stream import parse_journal
from loihi_twin_v2.p08_a2_timing import parse_timing
from loihi_twin_v2.p08_a2_2_ticks import parse_ticks
from loihi_twin_v2.p08_a3_2_analysis import (
    FRAME_COUNT, TRACE_FRAME, ELF_A21_SHA256, ELF_A22_SHA256,
    analyze_verified_pair,
)
from p07_a4_2_verify import validate_staging


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified_source(run: Path, mode: str, expected_elf: str) -> tuple[Path,Path,Path]:
    """Require logs/provenance written by upcoming separate A3.2.2 runner."""
    if not run.is_dir():
        raise ValueError("A3.2: raw readback evidence directory missing")
    manifest=(run/"physical_identity.txt").read_text()
    if (f"firmware_variant={mode}" not in manifest.splitlines() or
            f"candidate_elf_sha256={expected_elf}" not in manifest.splitlines() or
            "scope=TRAIN_DERIVED_VALIDATION_FIRST_1024" not in manifest.splitlines()):
        raise ValueError(f"A3.2: {mode} provenance/ELF identity missing or wrong")
    log=(run/"a53_run.log").read_text()
    expected_marker={
        "A2_1":"P08_A2_1_KV260_STATUS=TERMINAL_BOTH_SUCCESS_UNVERIFIED_NUMERICS",
        "A2_2":"P08_A2_2_KV260_STATUS=TERMINAL_ALL_THREE_SUCCESS_UNVERIFIED_NUMERICS",
    }[mode]
    if expected_marker not in log.splitlines():
        raise ValueError(f"A3.2: {mode} expected physical terminal not present")
    journal=run/"p07_a4_journal_1m.bin"
    trace=run/"p07_a4_trace_64k.bin"
    images=run/"p08_a2_1_images_1m.bin"
    for f in (journal,trace,images):
        if not f.is_file():
            raise ValueError("A3.2: physically read back required file missing")
    if mode=="A2_2" and not (run/"p08_a2_2_ticks_3m.bin").is_file():
        raise ValueError("A3.2: detailed FPGA per-tick sidecar missing")
    return journal,trace,images


def require_original_p07_oracle(stage: Path, journal: Path, trace: Path) -> None:
    command=[sys.executable,str(Path(__file__).with_name("p07_a4_2_verify.py")),
             "--stage-dir",str(stage),"--journal",str(journal),
             "--trace",str(trace)]
    run=subprocess.run(command,capture_output=True,text=True,check=False)
    if (run.returncode != 0 or
            "P07_A4_2C_PHYSICAL_SEALED_VALIDATION_GATE_PASS=1" not in run.stdout.splitlines() or
            "P07_A4_2C_PHYSICAL_ALL_OUTPUTS_EXACT=1" not in run.stdout.splitlines() or
            "P07_A4_2C_PHYSICAL_SELECTED_TRACE_26X42_EXACT=1" not in run.stdout.splitlines()):
        raise ValueError("A3.2: frozen independent P07 packed-oracle verification FAILED; "+
                         run.stderr[-1400:])
    print("P08_A3_2_INDEPENDENT_ORACLE_PASS_FOR="+journal.as_posix())


def validate_detailed_telemetry(stream, journal_rows, ticks) -> None:
    for i,out in enumerate(journal_rows):
        part=ticks.ticks[i*26:(i+1)*26]
        schedule=image_event_schedule(stream.image(i))
        if (any(t.external_events!=len(schedule[index]) for index,t in enumerate(part)) or
            any(t.emitted_packets!=t.acknowledged_packets for t in part) or
            sum(t.acknowledged_packets for t in part[:25])!=out.routes or
            part[-1].emitted_packets!=out.discarded or
            sum(t.external_events for t in part)!=out.external_events):
            raise ValueError(f"A3.2: frame {i} physical encoder/route/drain mismatch")


def pair_report(
    stage:Path, baseline_dir:Path, detailed_dir:Path,
    baseline_elf:Path, detailed_elf:Path,
) -> dict:
    if baseline_dir.resolve()==detailed_dir.resolve():
        raise ValueError("A3.2: physical evidence directories must be distinct")
    if sha256(baseline_elf)!=ELF_A21_SHA256 or sha256(detailed_elf)!=ELF_A22_SHA256:
        raise ValueError("A3.2: physical ELF hashes differ from user-attested binaries")
    meta,stream=validate_staging(stage)
    if (meta["scope"]!="TRAIN_DERIVED_VALIDATION_FIRST_1024" or
            stream.image_count!=FRAME_COUNT or stream.trace_index!=TRACE_FRAME):
        raise ValueError("A3.2: only first1024 TRAIN validation + trace frame1023")
    bj,bt,bi=verified_source(baseline_dir,"A2_1",ELF_A21_SHA256)
    dj,dt,di=verified_source(detailed_dir,"A2_2",ELF_A22_SHA256)
    # Crucial: independent original P07 replay for *both* physical captures,
    # not an optimistic comparison of the two firmware journals to each other.
    require_original_p07_oracle(stage,bj,bt)
    require_original_p07_oracle(stage,dj,dt)

    neural_a=parse_journal(bj.read_bytes(),stream)
    neural_b=parse_journal(dj.read_bytes(),stream)
    image_a=parse_timing(bi.read_bytes(),expected_count=FRAME_COUNT)
    image_b=parse_timing(di.read_bytes(),expected_count=FRAME_COUNT)
    tick= parse_ticks((detailed_dir/"p08_a2_2_ticks_3m.bin").read_bytes(),image_b,
                      expected_descriptor_crc32=int.from_bytes(stream.header[252:256],"little"))
    validate_detailed_telemetry(stream,neural_b,tick)
    report=analyze_verified_pair(image_a,image_b,tick,neural_a,neural_b)
    inputs={
        "A2_1_neural_journal":bj, "A2_1_selected_full_trace":bt,
        "A2_1_image_timing":bi,
        "A2_2_neural_journal":dj, "A2_2_selected_full_trace":dt,
        "A2_2_image_timing":di,
        "A2_2_per_tick_timing":detailed_dir/"p08_a2_2_ticks_3m.bin",
        "original_train_stage_descriptor":stage/"p07_a4_descriptor_256.bin",
        "original_train_stage_pixels":stage/"p07_a4_pixels_raw.bin",
        "original_train_stage_manifest":stage/"p07_a4_2a_stage_manifest.json",
    }
    report["input_evidence_sha256"]={k:sha256(v) for k,v in inputs.items()}
    report["a21_physical_run_directory"]=str(baseline_dir.resolve())
    report["a22_physical_run_directory"]=str(detailed_dir.resolve())
    report["both_independent_original_p07_oracles"]="PASS"
    report["detailed_tick_encoder_and_route_crosschecks"]="PASS"
    report["physical_pair_numerics_and_timing_integrity"]="PASS_SINGLE_PAIR"
    report["full_replicated_latency_baseline"]="NOT_YET_ACCEPTED"
    return report


def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage-dir",type=Path,required=True)
    ap.add_argument("--a21-run-dir",type=Path,required=True)
    ap.add_argument("--a22-run-dir",type=Path,required=True)
    ap.add_argument("--a21-elf",type=Path,required=True)
    ap.add_argument("--a22-elf",type=Path,required=True)
    ap.add_argument("--report",type=Path,required=True)
    args=ap.parse_args()
    if args.report.exists():
        ap.error("A3.2 never overwrites existing evidence")
    report=pair_report(args.stage_dir,args.a21_run_dir,args.a22_run_dir,
                       args.a21_elf,args.a22_elf)
    with args.report.open("x",encoding="utf-8") as out:
        json.dump(report,out,indent=2,sort_keys=True)
        out.write("\n")
    print("P08_A3_2_1024_BOTH_ORACLES_EXACT=1")
    print("P08_A3_2_1024_PAIRED_LATENCY_SINGLE_PAIR_PASS=1")
    print("P08_A3_2_REPEATED_BASELINE_ACCEPTED=0")
    print("P08_A3_2_POWER=DEFERRED")


if __name__=="__main__":
    main()
