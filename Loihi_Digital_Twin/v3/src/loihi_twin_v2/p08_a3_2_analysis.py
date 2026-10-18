"""P08-A3.2.1: deterministic paired latency statistics for verified A2.1/A2.2.

No physical board access. These functions MUST receive records authenticated by
both original P07 independent hardware oracles and strict timing-sidecar parsers.
An instrumented firmware delta is NOT equal to exact timer-instruction overhead.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import statistics

from .p08_a2_timing import TimingRun
from .p08_a2_2_ticks import TickRun

FRAME_COUNT = 1024
TRACE_FRAME = 1023
ELF_A21_SHA256 = "fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0"
ELF_A22_SHA256 = "87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361"


def percentile_nearest_rank(values: list[float], percent: int) -> float:
    """Nearest-rank method, index ceil(p*N/100)-1; N must be nonzero."""
    if not values or not 0 <= percent <= 100:
        raise ValueError("A3.2 percentiles need nonempty samples and p in [0,100]")
    ordered = sorted(values)
    index = max(0, math.ceil(percent * len(ordered) / 100) - 1)
    return ordered[index]


def distribution(values: list[float]) -> dict[str, float | int]:
    if not values or any(not math.isfinite(x) for x in values):
        raise ValueError("A3.2 distribution requires finite observed values")
    return {
        "n":len(values),
        "min":min(values),
        "median":statistics.median(values),
        "p95_nearest_rank":percentile_nearest_rank(values,95),
        "max":max(values),
        "mean":statistics.mean(values),
        "sample_stdev":statistics.stdev(values) if len(values)>1 else 0.0,
    }


def neural_signature(row: object) -> tuple:
    """Only neural semantic fields; original P07 elapsed timer value excluded."""
    return tuple(getattr(row, name) for name in (
        "image_index", "predicted", "counts", "all_silent", "routes",
        "discarded", "external_events", "output_spikes"
    ))


def analyze_verified_pair(
    baseline: TimingRun, detailed: TimingRun, ticks: TickRun,
    baseline_neural: tuple, detailed_neural: tuple,
) -> dict:
    """Pure analysis after BOTH immutable original packed-oracle PASSes.

    A3.2.1 unit tests may construct synthetic dataclasses. Calling this pure
    function never attests physical evidence. Only guarded CLI can do that.
    """
    if (baseline.count != FRAME_COUNT or detailed.count != FRAME_COUNT or
            len(baseline.records) != FRAME_COUNT or
            len(detailed.records) != FRAME_COUNT or
            len(baseline_neural) != FRAME_COUNT or
            len(detailed_neural) != FRAME_COUNT or
            baseline.trace_index != TRACE_FRAME or
            detailed.trace_index != TRACE_FRAME or
            ticks.count != FRAME_COUNT or ticks.trace_index != TRACE_FRAME or
            len(ticks.ticks) != FRAME_COUNT*26):
        raise ValueError("A3.2 requires same original 1024 validation positions and last trace")
    if (baseline.cntfrq_hz<=0 or detailed.cntfrq_hz<=0 or
            ticks.hz!=detailed.cntfrq_hz):
        raise ValueError("A3.2 timer frequencies invalid; A2.2 tick clock must match image")
    for i,(left,right) in enumerate(zip(baseline_neural,detailed_neural)):
        if neural_signature(left)!=neural_signature(right):
            raise ValueError(f"A3.2 neural mismatch across firmware at frame {i}")
        if baseline.records[i].index!=i or detailed.records[i].index!=i:
            raise ValueError(f"A3.2 timing misindexed frame {i}")

    # CNTFRQ is recorded per physical RUN, never shared between firmware
    # versions. Their start timestamps are unrelated across reboots.
    left_ms=[r.service_ticks * 1e3 / baseline.cntfrq_hz
             for r in baseline.records]
    right_ms=[r.service_ticks * 1e3 / detailed.cntfrq_hz
              for r in detailed.records]
    delta_ms=[new-old for old,new in zip(left_ms,right_ms)]
    # Only 1023 normal trace-path images for apples-to-apples comparisons.
    normal=range(TRACE_FRAME)
    stage={
        "event_encode":lambda t:t.source_ticks,
        "event_bank_append":lambda t:t.bank_ticks,
        "dispatch_mmio_and_poll":lambda t:t.dispatch_wrapper_ticks,
        "trace_readback":lambda t:t.trace_ticks,
        "route":lambda t:t.route_ticks,
        "barrier":lambda t:t.barrier_ticks,
    }
    tick_rows=[t for t in ticks.ticks if t.frame!=TRACE_FRAME]
    if len(tick_rows)!=(FRAME_COUNT-1)*26 or any(
            t.frame>=TRACE_FRAME or t.tick!=index%26
            for index,t in enumerate(tick_rows)):
        raise ValueError("A3.2 selected-trace tick boundary unexpectedly changed")
    timing_stages={
        k:distribution([fn(t)*1e6 / detailed.cntfrq_hz for t in tick_rows])
        for k,fn in stage.items()
    }
    return {
        "schema":"p08-a3-2-paired-1024-latency-v1",
        "sample_population":"TRAIN_DERIVED_VALIDATION_FIRST_1024",
        "distinct_images":FRAME_COUNT,
        "trace_frame":TRACE_FRAME,
        "ordinary_images":FRAME_COUNT-1,
        "logical_timesteps_per_image":26,
        "a21_elf_sha256":ELF_A21_SHA256,
        "a22_elf_sha256":ELF_A22_SHA256,
        "a21_a53_cntfrq_el0_hz":baseline.cntfrq_hz,
        "a22_a53_cntfrq_el0_hz":detailed.cntfrq_hz,
        "normal_1023_a21_service_ms":distribution([left_ms[i] for i in normal]),
        "normal_1023_a22_service_ms":distribution([right_ms[i] for i in normal]),
        "paired_ordinary_1023_a22_minus_a21_service_ms":
            distribution([delta_ms[i] for i in normal]),
        "full_trace_frame_a21_ms":left_ms[TRACE_FRAME],
        "full_trace_frame_a22_ms":right_ms[TRACE_FRAME],
        "full_trace_frame_a22_minus_a21_ms":delta_ms[TRACE_FRAME],
        "per_tick_ordinary_1023_a22_stage_microseconds":timing_stages,
        "all_1024_a21_service_ms_raw":left_ms,
        "all_1024_a22_service_ms_raw":right_ms,
        "all_1024_paired_difference_ms_raw":delta_ms,
        "pl_dispatch_26tick_cycles_a21":
            [r.pl_dispatch_cycles for r in baseline.records],
        "pl_dispatch_26tick_cycles_a22":
            [r.pl_dispatch_cycles for r in detailed.records],
        "pl_cycles_equal_between_runs_per_image":all(
            a.pl_dispatch_cycles==b.pl_dispatch_cycles
            for a,b in zip(baseline.records,detailed.records)),
        "a21_dataset_throughput_fps_includes_sidecar_writes":
            baseline.throughput_frames_per_second,
        "a22_dataset_throughput_fps_includes_sidecar_writes":
            detailed.throughput_frames_per_second,
        "measurement_scope":
            "A53 instrumented full frame service, NOT bare PL neural inference",
        "interpretation":
            "Paired service delta mixes A53 timer/callback overhead, "
            "scheduler and memory effects and separate physical-run variability",
        "power_energy":"DEFERRED",
        "official_mnist_test":"NOT_RERUN",
        "single_pair_is_statistical_repetition":False,
    }
