#!/usr/bin/env python3
"""P08-A3.2.2 OFFLINE single-run original-oracle + timing proof.

Consumes ONLY the user-performed XSDB physical readbacks, not a mock.
Never operates KV260, never runs t10k, writes one new report only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from loihi_twin_v2.p07_a4_stream import parse_journal
from loihi_twin_v2.p08_a2_timing import parse_timing
from loihi_twin_v2.p08_a2_2_ticks import parse_ticks
from loihi_twin_v2.p08_a3_2_analysis import (
    FRAME_COUNT, TRACE_FRAME, ELF_A21_SHA256, ELF_A22_SHA256,
)
from p07_a4_2_verify import validate_staging
from p08_a3_2_pair_check import (
    verified_source, require_original_p07_oracle, validate_detailed_telemetry,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_single(stage: Path, run: Path, variant: str, elf: Path) -> dict:
    if variant not in ("A2_1", "A2_2"):
        raise ValueError("A3.2.2 requires variant A2_1 or A2_2")
    expected = ELF_A21_SHA256 if variant=="A2_1" else ELF_A22_SHA256
    if sha(elf)!=expected:
        raise ValueError("A3.2.2 firmware ELF SHA256 mismatch")
    meta, stream = validate_staging(stage)
    if (meta["scope"]!="TRAIN_DERIVED_VALIDATION_FIRST_1024" or
        stream.image_count!=FRAME_COUNT or stream.trace_index!=TRACE_FRAME):
        raise ValueError("A3.2.2 only frozen original TRAIN first1024 / trace1023")
    journal, trace, timing=verified_source(run, variant, expected)

    # CRITICAL: original P07 independent packed replay must succeed BEFORE
    # accepting even one A53 latency reading.
    require_original_p07_oracle(stage, journal, trace)
    neural=parse_journal(journal.read_bytes(),stream)
    images=parse_timing(timing.read_bytes(),expected_count=FRAME_COUNT)
    if images.trace_index!=TRACE_FRAME:
        raise ValueError("A3.2.2 timing trace index not 1023")
    tick_file=run/"p08_a2_2_ticks_3m.bin"
    if variant=="A2_2":
        ticks=parse_ticks(tick_file.read_bytes(),images,
             expected_descriptor_crc32=int.from_bytes(stream.header[252:256],"little"))
        validate_detailed_telemetry(stream, neural, ticks)
    else:
        if tick_file.exists():
            raise ValueError("A3.2.2 A2.1 run must not claim an A2.2 tick sidecar")
    evidence={"physical_journal":journal,"selected_trace":trace,"image_timing":timing,
              "stage_descriptor":stage/"p07_a4_descriptor_256.bin",
              "stage_mapping":stage/"p07_a4_mapping_1568.bin",
              "stage_pixels":stage/"p07_a4_pixels_raw.bin",
              "stage_host_labels":stage/"p07_a4_2a_validation_labels_HOST_ONLY.json",
              "stage_manifest":stage/"p07_a4_2a_stage_manifest.json",
              "run_identity":run/"physical_identity.txt",
              "xsdb_terminal_log":run/"a53_run.log"}
    if variant=="A2_2":
        evidence["tick_timing"]=tick_file
    durations=[r.service_ticks * 1000/images.cntfrq_hz for r in images.records]
    return {
       "schema":"p08-a3-2-single-1024-physical-capture-v1",
       "variant":variant,"elf_sha256":expected,
       "population":"TRAIN_DERIVED_VALIDATION_FIRST_1024",
       "frame_count":FRAME_COUNT,"trace_frame":TRACE_FRAME,
       "per_image_a53_service_ms":durations,
       "cntfrq_el0_hz_reported":images.cntfrq_hz,
       "pl_dispatch_cycles_26tick_sum":[r.pl_dispatch_cycles for r in images.records],
       "pl_cycle_clock":"separate PL domain; Hz not verified",
       "a53_service_scope":"instrumented, including scheduler and A53/PL calls",
       "original_independent_p07_oracle":"PASS_ALL_1024",
       "selected_26x42_neural_trace":"EXACT",
       "a2_2_tick_encoder_route_and_cycle_correlations":
            "PASS" if variant=="A2_2" else "NOT_APPLICABLE",
       "source_sha256":{key:sha(file) for key,file in evidence.items()},
       "physical_capture_single_run":"PASS",
       "paired_overhead":"NOT_YET_MEASURED",
       "repeated_baseline":"NOT_ACCEPTED",
       "official_mnist_TEST":"NOT_RERUN",
       "power_energy":"DEFERRED",
    }


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage-dir",type=Path,required=True)
    p.add_argument("--run-dir",type=Path,required=True)
    p.add_argument("--variant",required=True,choices=("A2_1","A2_2"))
    p.add_argument("--elf",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    args=p.parse_args()
    if args.report.exists():
        p.error("A3.2.2 refuses to overwrite an earlier physical result")
    outcome=check_single(args.stage_dir,args.run_dir,args.variant,args.elf)
    with args.report.open("x",encoding="utf-8") as f:
        json.dump(outcome,f,sort_keys=True,indent=2)
        f.write("\n")
    print("P08_A3_2_2_ORIGINAL_P07_1024_PACKED_ORACLE_PASS=1")
    print("P08_A3_2_2_SINGLE_RUN_TIMING_CRC_PASS=1")
    print("P08_A3_2_2_SINGLE_1024_PHYSICAL_CAPTURE_PASS=1")
    print("P08_A3_2_2_PAIRED_1024_BASELINE=NOT_RUN")
    print("P08_A3_2_2_POWER=DEFERRED")


if __name__=="__main__":
    main()
