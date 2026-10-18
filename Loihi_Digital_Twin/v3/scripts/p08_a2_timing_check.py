#!/usr/bin/env python3
"""Validate P08-A2.1 timing sidecar and report clearly scoped raw intervals.

NOT a substitute for scripts/p07_a4_2_verify.py numerical/oracle evidence.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import statistics

from loihi_twin_v2.p08_a2_timing import parse_timing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timing", type=Path, required=True)
    parser.add_argument("--count", type=int, required=True,
                        help="Predeclared validation count (e.g. 16 or 1024)")
    parser.add_argument("--report", type=Path,
                        help="NEW output filename; refuse overwrite")
    args = parser.parse_args()
    if args.report and args.report.exists():
        parser.error("refusing to overwrite existing timing report")
    timing = parse_timing(args.timing.read_bytes(), expected_count=args.count)
    def seconds(ticks: int) -> float:
        return ticks / timing.cntfrq_hz
    services = [seconds(row.service_ticks) for row in timing.records]
    neural = [seconds(row.after_neural-row.after_ingress)
              for row in timing.records]
    selected = timing.records[timing.trace_index]
    result = {
        "status": "SIDE_CAR_SCHEMA_PASS_ONLY_NUMERICAL_VERIFICATION_REQUIRED",
        "clock": "A53 CNTVCT_EL0 / CNTFRQ_EL0",
        "cntfrq_hz": timing.cntfrq_hz,
        "count": timing.count,
        "distinct_population": "MUST_BE_ATTESTED_FROM_STAGING_MANIFEST",
        "trace_frame": timing.trace_index,
        "total_a53_dataset_window_ticks":
            timing.dataset_stop - timing.dataset_start,
        "a53_dataset_window_seconds":
            seconds(timing.dataset_stop - timing.dataset_start),
        "throughput_frame_per_s_including_profiler_overhead":
            timing.throughput_frames_per_second,
        "image_service_seconds_median": statistics.median(services),
        "image_service_seconds_min": min(services),
        "image_service_seconds_max": max(services),
        "prepare_plus_26tick_call_seconds_median": statistics.median(neural),
        "selected_trace_image_service_seconds": seconds(selected.service_ticks),
        "pl_dispatch_cycles_domain": "FPGA_COUNTER_FREQUENCY_NOT_YET_CONFIRMED",
        "pl_dispatch_cycles_total":
            sum(row.pl_dispatch_cycles for row in timing.records),
        "pl_page_cycles_total":
            sum(row.pl_page_cycles for row in timing.records),
        "hardware_physical_latencies_accepted": False,
        "independent_p07_packed_oracle_required": True,
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.report:
        with args.report.open("x") as f:
            f.write(rendered)
    print(rendered, end="")
    print("P08_A2_1_TIMING_SIDECAR_SCHEMA_PASS=1")
    print("P08_A2_1_PHYSICAL_NUMERICAL_GATE=NOT_RUN_BY_THIS_TOOL")
    print("P08_A2_1_PHYSICAL_LATENCY_ACCEPTED=0")


if __name__ == "__main__":
    main()
