"""P08-A5 host CPU timing methodology; no physical hardware calls.

All per-frame samples are monotonic perf_counter_ns elapsed time, in a
SINGLE host CPU process. Python pure-scalar reference NOT native C CPU
inference. CPU and A53/FPGA subsystem do not share identical service scope.
"""
from __future__ import annotations

import hashlib
import math
import os
import platform
import statistics
import sys
import time
from collections.abc import Callable,Sequence
from pathlib import Path
from typing import Any

from .p06_input_contract import image_event_schedule
from .p08_a3_2_analysis import FRAME_COUNT,TRACE_FRAME,distribution
from .p08_a5_cpu_reference import (
    PreparedCPU,CPUOutcome,preloaded_compute,image_to_class,assert_matches_physical,
)

SCHEMA="p08-a5-host-cpu-two-endpoint-1024-v1"
REPEATS=3
CORE="preloaded_packed_integer_26tick_cpu"
FULL="raw784_encoder_integer_26tick_to_class_cpu"


def _read_sys_file(name: str) -> str | None:
    try:
        value=Path(name).read_text(encoding="utf8").strip()
        return value[:300] if value else None
    except (OSError,UnicodeError):
        return None


def cpu_environment() -> dict:
    """Observed host provenance; do not invent or silently set CPU governor."""
    cpuinfo=_read_sys_file("/proc/cpuinfo") or ""
    processor_line=next((line.split(":",1)[1].strip()
                         for line in cpuinfo.splitlines()
                         if line.startswith(("model name","Hardware","Processor")) and ":" in line),
                        None)
    affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,"sched_getaffinity") else None
    return {
        "python_version":sys.version,"implementation":platform.python_implementation(),
        "benchmark_language":"pure Python scalar; NOT compiled C/NumPy/Torch inference",
        "platform":platform.platform(),"machine":platform.machine(),
        "processor_reported_by_platform":platform.processor() or None,
        "processor_from_proc_cpuinfo":processor_line,
        "logical_cpu_count":os.cpu_count(),
        "process_cpu_affinity":affinity,
        "current_cpu_governor_cpu0":
            _read_sys_file("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
        "current_cpu_scaling_freq_cpu0_khz":
            _read_sys_file("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"),
        "omp_num_threads":os.environ.get("OMP_NUM_THREADS"),
        "mkl_num_threads":os.environ.get("MKL_NUM_THREADS"),
        "python_hash_seed":os.environ.get("PYTHONHASHSEED"),
        "threading":"single Python interpreter thread for actual replay; no multithreaded engine",
        "timer":"time.perf_counter_ns(), wall-clock monotonic high-resolution host timer",
        "perf_counter_info":str(time.get_clock_info("perf_counter")),
        "environment_is_fixed_or_calibrated":False,
    }


def measured_once(fn: Callable[[],CPUOutcome], expected: Any,
                  index: int) -> int:
    """Keep physical/neural verification strictly outside timed interval."""
    start=time.perf_counter_ns()
    result=fn()
    stop=time.perf_counter_ns()
    assert_matches_physical(result,expected,index)
    elapsed=stop-start
    if elapsed<=0:
        raise ValueError("A5 non-positive host monotonic timing interval")
    return elapsed


def benchmark_cpu_two_endpoints(
    prepared: PreparedCPU, pixels: Sequence[bytes], journal_rows: Sequence[Any],
    *, repeats: int=REPEATS, warmup: int=2, timer_environment: dict | None=None,
) -> dict:
    """Benchmark EXACTLY original first1024 population, 1023 ordinary + trace.

    Precompute event schedule for CORE endpoint OUTSIDE all timings. FULL endpoint
    re-encodes original 784B pixels inside the measured function. Replay each
    frame in A2.1 journal against accepted hardware before recording latency.
    The clock is PC host perf_counter_ns, NOT A53 CNTVCT or FPGA PL cycles.
    """
    if (type(repeats) is not int or repeats!=REPEATS or
            type(warmup) is not int or not 0<=warmup<=16 or
            len(pixels)!=FRAME_COUNT or len(journal_rows)!=FRAME_COUNT):
        raise ValueError("A5 benchmark requires 1024 original frames and three repeats")
    if any(not isinstance(frame,bytes) or len(frame)!=784 for frame in pixels):
        raise ValueError("A5 only original uint8 784B images accepted")
    schedules=tuple(image_event_schedule(frame) for frame in pixels)
    # Untimed differential parity on ALL 1024 before any benchmark outcome is accepted.
    for index,frame in enumerate(pixels):
        assert_matches_physical(preloaded_compute(prepared,schedules[index]),
                                journal_rows[index],index)
        assert_matches_physical(image_to_class(prepared,frame),journal_rows[index],index)
    for x in range(warmup):
        index=x%FRAME_COUNT
        assert_matches_physical(preloaded_compute(prepared,schedules[index]),
                                journal_rows[index],index)
        assert_matches_physical(image_to_class(prepared,pixels[index]),
                                journal_rows[index],index)
    measurements={CORE:[],FULL:[]}
    # Alternating path order reduces, but does not eliminate, host drift.
    for repeat in range(repeats):
        timing={CORE:[],FULL:[]}
        order=(CORE,FULL) if repeat%2==0 else (FULL,CORE)
        for i,frame in enumerate(pixels):
            for label in order:
                if label==CORE:
                    fn=lambda j=i:preloaded_compute(prepared,schedules[j])
                else:
                    fn=lambda raw=frame:image_to_class(prepared,raw)
                timing[label].append(measured_once(fn,journal_rows[i],i))
        for label in (CORE,FULL):
            measurements[label].append(timing[label])
    # Defer all statistics and file IO until AFTER 1024*3*2 measured outputs checked.
    numeric={}
    for label in (CORE,FULL):
        runs=[[ticks/1e6 for ticks in row] for row in measurements[label]]
        numeric[label]={
            "three_sequential_runs_ns":measurements[label],
            "three_sequential_runs_ms":runs,
            "ordinary_1023_distributions_ms":[distribution(v[:TRACE_FRAME]) for v in runs],
            "ordinary_1023_per_image_median_across_three_runs_ms":[
                statistics.median(run[i] for run in runs) for i in range(TRACE_FRAME)
            ],
            "selected_trace_index1023_cpu_ms":[run[TRACE_FRAME] for run in runs],
        }
        numeric[label]["ordinary_1023_aggregate_of_per_image_medians_ms"]=distribution(
            numeric[label]["ordinary_1023_per_image_median_across_three_runs_ms"]
        )
    # Same-frame delta is provided only as host SW FULL-CORE difference, not a
    # clock-instruction overhead measurement or CPU-vs-FPGA speedup ratio.
    differences=[
        [numeric[FULL]["three_sequential_runs_ms"][j][i]-
         numeric[CORE]["three_sequential_runs_ms"][j][i]
         for i in range(FRAME_COUNT)] for j in range(repeats)
    ]
    return {
        "schema":SCHEMA,
        "population":"TRAIN_DERIVED_VALIDATION_FIRST_1024",
        "unique_images":FRAME_COUNT,
        "ordinary_images":TRACE_FRAME,
        "selected_full_trace_image":TRACE_FRAME,
        "logical_timesteps":26,
        "host_cpu_environment":timer_environment or cpu_environment(),
        "cpu_impl":"original P03 packed arrays, accepted P06 scalar integer LIF; separately implemented predecoded loop, exact original P07 full-frame journal parity",
        "benchmark_repeats":repeats,
        "warmup_frames_each_endpoint":warmup,
        "alternating_benchmark_order":"CORE,FULL; FULL,CORE; CORE,FULL per original frame",
        "unverified_external_cpu_clock_calibration":True,
        "preloaded_core_endpoint":numeric[CORE],
        "full_raw_image_to_class_endpoint":numeric[FULL],
        "full_minus_core_same_frame_ms_by_run":differences,
        "all_1024_original_physical_journal_outputs_exact":"PASS",
        "all_1024_original_26tick_spike_traces_exact":"PASS",
        "selected_trace_frame_cpu_endpoint_is_normal_10output_readout":True,
        "fpga_service_scope_matched_exactly":False,
        "board_only_pl_compute_vs_cpu_core_speedup":"NOT_SUPPORTED_NO_ACHIEVED_PL_HZ",
        "full_cpu_to_a53_fpga_speedup":"NOT_SUPPORTED_ENDPOINTS_ASYMMETRIC",
        "official_mnist_test":"NOT_RERUN",
        "power_energy":"DEFERRED",
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
