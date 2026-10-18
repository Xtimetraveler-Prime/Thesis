#!/usr/bin/env python3
"""A3.1: independent physical 16-frame TRAIN-validation + latency proof.

Board-only outputs MUST be produced by the guarded physical runner, not by
this script. Verify unchanged P07 packed oracle FIRST, then join P08-A2.1
and P08-A2.2 timing artifacts to the original stage and neural results.
No official TEST replay, power measurement or inferred PL clock.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path
import subprocess
import sys

from loihi_twin_v2.p06_input_contract import image_event_schedule
from loihi_twin_v2.p07_a4_stream import parse_journal
from loihi_twin_v2.p08_a2_timing import parse_timing
from loihi_twin_v2.p08_a2_2_ticks import parse_ticks

# P07 verifier's validation-stage routine is accepted and does not touch
# the board. Full P07 numerical/oracle comparison is invoked as a subprocess.
try:
    from scripts.p07_a4_2_verify import validate_staging
except ModuleNotFoundError as exc:
    if exc.name != "scripts":
        raise
    # Running directly as "python scripts/p08_a3_1_verify.py"
    from p07_a4_2_verify import validate_staging


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_evidence(
    stage: Path, journal: Path, trace: Path, images: Path, ticks: Path,
    *, oracle_proof: bool = True,
) -> dict:
    metadata, stream = validate_staging(stage)
    if (metadata["scope"] != "TRAIN_DERIVED_VALIDATION_FIRST_16" or
            stream.image_count != 16):
        raise ValueError("A3.1 requires the exact first-16 TRAIN-derived validation prefix")
    if oracle_proof:
        command = [
            sys.executable, str(Path(__file__).with_name("p07_a4_2_verify.py")),
            "--stage-dir", str(stage), "--journal", str(journal),
            "--trace", str(trace),
        ]
        result = subprocess.run(command, capture_output=True, text=True,
                                check=False)
        print(result.stdout, end="")
        if (result.returncode != 0 or
            "P07_A4_2C_PHYSICAL_SEALED_VALIDATION_GATE_PASS=1" not in
                result.stdout.splitlines() or
            "P07_A4_2C_PHYSICAL_SELECTED_TRACE_26X42_EXACT=1" not in
                result.stdout.splitlines()):
            raise ValueError(
                "P07 independent packed replay did NOT pass; no physical latency "
                f"claim allowed; exit={result.returncode}: " + result.stderr[-1200:]
            )
    original = parse_journal(journal.read_bytes(), stream)
    image_times = parse_timing(images.read_bytes(), expected_count=16)
    expected_descriptor = int.from_bytes(stream.header[252:256], "little")
    tick_times = parse_ticks(ticks.read_bytes(), image_times,
                             expected_descriptor_crc32=expected_descriptor)
    if tick_times.count != stream.image_count:
        raise ValueError("tick capture image count disagrees with original input")
    for frame, out in enumerate(original):
        rows = tick_times.ticks[frame * 26:(frame+1)*26]
        expected_schedule = image_event_schedule(stream.image(frame))
        if any(row.external_events != len(expected_schedule[t]) for t,row in enumerate(rows)):
            raise ValueError(f"frame={frame}: per-tick event count differs from frozen encoder")
        if any(row.emitted_packets != row.acknowledged_packets for row in rows):
            raise ValueError(f"frame={frame}: PL packet acknowledgement mismatch")
        if sum(row.acknowledged_packets for row in rows[:-1]) != out.routes:
            raise ValueError(f"frame={frame}: aggregate real NEXT routing mismatch")
        if rows[-1].emitted_packets != out.discarded:
            raise ValueError(f"frame={frame}: final drain drop differs from journal")
        if sum(row.external_events for row in rows) != out.external_events:
            raise ValueError(f"frame={frame}: sum of physical event-source counts invalid")
    hz=image_times.cntfrq_hz
    service_seconds=[rec.service_ticks/hz for rec in image_times.records]
    tick_stages={
        "event_encode":lambda t:t.source_ticks,
        "event_bank_append":lambda t:t.bank_ticks,
        "dispatch_MMIO_and_poll":lambda t:t.dispatch_wrapper_ticks,
        "output_trace_readback":lambda t:t.trace_ticks,
        "route":lambda t:t.route_ticks,
        "barrier":lambda t:t.barrier_ticks,
    }
    stage_medians={
        name:statistics.median(fn(row)/hz for row in tick_times.ticks)
        for name,fn in tick_stages.items()
    }
    ordinary=[
        rec.service_ticks/hz for rec in image_times.records
        if rec.index!=stream.trace_index
    ]
    paths={"journal":journal, "selected_trace":trace,
           "a2_1_image_timing":images,"a2_2_tick_timing":ticks,
           "descriptor":stage/"p07_a4_descriptor_256.bin",
           "mapping":stage/"p07_a4_mapping_1568.bin",
           "pixels":stage/"p07_a4_pixels_raw.bin",
           "stage_manifest":stage/"p07_a4_2a_stage_manifest.json"}
    return {
        "schema":"p08-a3-1-latency-pilot-v1",
        "scope": metadata["scope"],
        "completed_frames":16,
        "distinct_train_derived_validation_frames":16,
        "timesteps_per_frame":26,
        "trace_frame":stream.trace_index,
        "cntfrq_el0_hz_reported":image_times.cntfrq_hz,
        "a53_timestamp_domain":"CNTVCT_EL0 with ISB; conversion uses CNTFRQ_EL0",
        "pl_dispatch_cycles_domain":"separate FPGA counter; Hz not yet independently confirmed",
        "raw_a53_image_service_ticks":[r.service_ticks for r in image_times.records],
        "a53_image_service_seconds":service_seconds,
        "median_16image_service_seconds_instrumented":
            statistics.median(service_seconds),
        "min_16image_service_seconds_instrumented":min(service_seconds),
        "max_16image_service_seconds_instrumented":max(service_seconds),
        "selected_trace_frame_service_seconds":
            service_seconds[stream.trace_index],
        "ordinary_15frame_service_seconds_median":
            statistics.median(ordinary),
        "per_tick_stage_seconds_median_instrumented":stage_medians,
        "raw_a53_26tick_dispatch_cycles":[r.pl_dispatch_cycles for r in image_times.records],
        "full_dataset_a53_ticks":image_times.dataset_stop - image_times.dataset_start,
        "bytes_sha256":{name:sha256(path) for name,path in paths.items()},
        "p07_independent_oracle_parity":"PASS" if oracle_proof else "NOT_RUN_UNIT_TEST_ONLY",
        "both_timing_sidecar_parsers":"PASS",
        "tick_input_route_drain_crosschecks":"PASS",
        "pl_counter_vs_26tick_sum":"PASS",
        "physical_power_energy":"DEFERRED",
        "physical_latency_accepted":bool(oracle_proof),
        "measurement_scope":"INSTRUMENTED A53 service; NOT core-only FPGA computation",
        "warning":"A3.1 is a 16-image timing pilot, not a repeated statistical baseline",
    }


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage-dir",type=Path,required=True)
    p.add_argument("--journal",type=Path,required=True)
    p.add_argument("--trace",type=Path,required=True)
    p.add_argument("--image-timing",type=Path,required=True)
    p.add_argument("--tick-timing",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True,help="NEW filename, never overwrite")
    args=p.parse_args()
    if args.report.exists():
        p.error("A3.1 refuses overwrite of an existing result")
    result=validate_evidence(args.stage_dir,args.journal,args.trace,
                             args.image_timing,args.tick_timing)
    with args.report.open("x",encoding="utf-8") as f:
        json.dump(result,f,sort_keys=True,indent=2)
        f.write("\n")
    print("P08_A3_1_P07_INDEPENDENT_PACKED_ORACLE_PASS=1")
    print("P08_A3_1_PER_TICK_LATENCY_CROSSCHECK_PASS=1")
    print("P08_A3_1_16FRAME_PHYSICAL_PILOT_PASS=1")
    print("P08_A3_1_1024FRAME_BASELINE=NOT_RUN")
    print("P08_A3_1_POWER=DEFERRED")


if __name__=="__main__":
    main()
