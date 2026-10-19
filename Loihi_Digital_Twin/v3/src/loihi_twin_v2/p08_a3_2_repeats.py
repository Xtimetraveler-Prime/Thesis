"""P08-A3.2.3 descriptive 3-pair aggregate of independently verified A3.2.1 reports.

Runs entirely on host. Three repetitions of the SAME 1024 image identities
are NOT 3072 independent observations. Does not invent statistical confidence,
attribute all A2.2-A2.1 difference to profiler instrumentation or read PL clocks.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import statistics

from .p08_a3_2_analysis import (
    FRAME_COUNT, TRACE_FRAME, ELF_A21_SHA256, ELF_A22_SHA256, distribution,
)

PAIR_SCHEMA="p08-a3-2-paired-1024-latency-v1"
AGG_SCHEMA="p08-a3-2-repeated-three-pair-latency-v1"
STAGE_HASH_KEYS=(
    "original_train_stage_descriptor","original_train_stage_pixels",
    "original_train_stage_manifest",
)
CAPTURE_HASH_KEYS=("A2_1_image_timing","A2_2_image_timing","A2_2_per_tick_timing")
IMAGE_KEYS=("all_1024_a21_service_ms_raw","all_1024_a22_service_ms_raw",
            "all_1024_paired_difference_ms_raw")
SUMMARY_KEYS=(
    "normal_1023_a21_service_ms","normal_1023_a22_service_ms",
    "paired_ordinary_1023_a22_minus_a21_service_ms",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _required_hash(value: object, label: str) -> str:
    if (not isinstance(value,str) or len(value)!=64 or
            any(c not in "0123456789abcdef" for c in value)):
        raise ValueError(f"P08-A3.2.3 invalid SHA256 for {label}")
    return value


def _samples(item: object, label: str) -> list[float]:
    if (not isinstance(item,list) or len(item)!=FRAME_COUNT or
            any(type(v) not in (int,float) or not math.isfinite(v) for v in item)):
        raise ValueError(f"P08-A3.2.3 {label} requires 1024 finite numeric readings")
    return [float(v) for v in item]


def _close(actual: float, wanted: float) -> bool:
    return math.isclose(actual,wanted,abs_tol=1e-8,rel_tol=1e-10)


def _validate_pair(data: dict, path: Path) -> tuple[dict,dict[str,list[float]]]:
    if (data.get("schema")!=PAIR_SCHEMA or
        data.get("sample_population")!="TRAIN_DERIVED_VALIDATION_FIRST_1024" or
        data.get("distinct_images")!=FRAME_COUNT or
        data.get("ordinary_images")!=TRACE_FRAME or
        data.get("trace_frame")!=TRACE_FRAME or
        data.get("logical_timesteps_per_image")!=26 or
        data.get("a21_elf_sha256")!=ELF_A21_SHA256 or
        data.get("a22_elf_sha256")!=ELF_A22_SHA256 or
        data.get("both_independent_original_p07_oracles")!="PASS" or
        data.get("detailed_tick_encoder_and_route_crosschecks")!="PASS" or
        data.get("physical_pair_numerics_and_timing_integrity")!="PASS_SINGLE_PAIR" or
        data.get("full_replicated_latency_baseline")!="NOT_YET_ACCEPTED" or
        data.get("power_energy")!="DEFERRED" or
        data.get("official_mnist_test")!="NOT_RERUN"):
        raise ValueError(f"P08-A3.2.3 invalid accepted single-pair contract in {path}")
    for key in ("a21_a53_cntfrq_el0_hz","a22_a53_cntfrq_el0_hz"):
        hz=data.get(key)
        if type(hz)!=int or hz<=0:
            raise ValueError(f"P08-A3.2.3 missing physical CNTFRQ in {path}")
    sha=data.get("input_evidence_sha256")
    if not isinstance(sha,dict):
        raise ValueError("P08-A3.2.3 missing original evidence SHA256 ledger")
    for key in (*STAGE_HASH_KEYS,*CAPTURE_HASH_KEYS):
        _required_hash(sha.get(key),key)
    for name in ("a21_physical_run_directory","a22_physical_run_directory"):
        if not isinstance(data.get(name),str) or not Path(data[name]).is_absolute():
            raise ValueError(f"P08-A3.2.3 missing absolute physical evidence directory: {name}")
    if (Path(data["a21_physical_run_directory"]).resolve() ==
        Path(data["a22_physical_run_directory"]).resolve()):
        raise ValueError("P08-A3.2.3 pair reuses same physical capture")
    series={name:_samples(data.get(name),name) for name in IMAGE_KEYS}
    a,b,d=[series[name] for name in IMAGE_KEYS]
    if any(v<=0 for v in a+b):
        raise ValueError("P08-A3.2.3 service durations must be positive")
    if any(not _close(d[i],b[i]-a[i]) for i in range(FRAME_COUNT)):
        raise ValueError("P08-A3.2.3 paired deltas don't equal same-frame A2.2 minus A2.1")
    for name,values in zip(SUMMARY_KEYS,(a[:TRACE_FRAME],b[:TRACE_FRAME],d[:TRACE_FRAME])):
        saved=data.get(name)
        expected=distribution(values)
        if not isinstance(saved,dict) or any(
            key not in saved or
            (saved[key]!=number if key=="n" else not _close(saved[key],number))
            for key,number in expected.items()
        ):
            raise ValueError(f"P08-A3.2.3 {name} summary differs from raw 1023 samples")
    return sha,series


def aggregate_three_pairs(paths: list[Path]) -> dict:
    """Validate three source report files and return descriptive repeat metrics.

    No hardware calls; source reports must originate from separately accepted
    complete A3.2.1 physical pairs. The aggregation itself does not re-run
    original P07 oracles. Evidence hashes and paths are bound to each report.
    """
    if len(paths)!=3 or len({str(p.resolve()) for p in paths})!=3:
        raise ValueError("P08-A3.2.3 requires exactly THREE distinct accepted pair JSON paths")
    sources=[]
    hashes=[]
    values=[]
    directories=set()
    capture_hashes={name:set() for name in CAPTURE_HASH_KEYS}
    stage_sha=None
    for index,path in enumerate(paths,1):
        if not path.is_file():
            raise ValueError(f"P08-A3.2.3 paired physical report missing: {path}")
        with path.open("r",encoding="utf-8") as f:
            obj=json.load(f)
        if not isinstance(obj,dict):
            raise ValueError("P08-A3.2.3 expected JSON object per report")
        sha,series=_validate_pair(obj,path)
        stage=tuple(sha[name] for name in STAGE_HASH_KEYS)
        if stage_sha is None:
            stage_sha=stage
        elif stage!=stage_sha:
            raise ValueError("P08-A3.2.3 original TRAIN stage differs across repeats")
        for key in CAPTURE_HASH_KEYS:
            if sha[key] in capture_hashes[key]:
                raise ValueError(f"P08-A3.2.3 duplicate {key} raw hardware timing sidecar")
            capture_hashes[key].add(sha[key])
        run_paths=(
            str(Path(obj["a21_physical_run_directory"]).resolve()),
            str(Path(obj["a22_physical_run_directory"]).resolve()),
        )
        if any(x in directories for x in run_paths):
            raise ValueError("P08-A3.2.3 reused a physical session across paired reports")
        directories.update(run_paths)
        values.append(series)
        sources.append({
            "pair_index":index,"report_file":str(path.resolve()),
            "report_sha256":_sha(path),
            "a21_run_dir":run_paths[0],"a22_run_dir":run_paths[1],
            "a21_cntfrq_el0_hz":obj["a21_a53_cntfrq_el0_hz"],
            "a22_cntfrq_el0_hz":obj["a22_a53_cntfrq_el0_hz"],
            "a21_service_ordinary_ms":obj[SUMMARY_KEYS[0]],
            "a22_service_ordinary_ms":obj[SUMMARY_KEYS[1]],
            "paired_ordinary_difference_ms":obj[SUMMARY_KEYS[2]],
            "capture_timing_sha256":{k:sha[k] for k in CAPTURE_HASH_KEYS},
        })
        hashes.append({k:sha[k] for k in STAGE_HASH_KEYS})

    # Within each image ID: three run-to-run observations, not three new IDs.
    a21=[series[IMAGE_KEYS[0]] for series in values]
    a22=[series[IMAGE_KEYS[1]] for series in values]
    deltas=[series[IMAGE_KEYS[2]] for series in values]
    fixed_means=[statistics.mean(deltas[trial][i] for trial in range(3))
                 for i in range(TRACE_FRAME)]
    within_image_ranges=[max(deltas[trial][i] for trial in range(3))-
                         min(deltas[trial][i] for trial in range(3))
                         for i in range(TRACE_FRAME)]
    per_pair_medians=[distribution(d[:TRACE_FRAME])["median"] for d in deltas]
    return {
        "schema":AGG_SCHEMA,
        "independent_firmware_sessions_per_variant":3,
        "independent_physical_pairs":3,
        "unique_train_validation_images":1024,
        "ordinary_images_per_pair":1023,
        "selected_full_trace_frame":1023,
        "frame_repeats_are_new_independent_images":False,
        "source_evidence":sources,
        "immutable_stage_sha256":dict(zip(STAGE_HASH_KEYS,stage_sha)),
        "a21_ordinary_median_service_ms_by_run":[
            distribution(a[:TRACE_FRAME])["median"] for a in a21],
        "a22_ordinary_median_service_ms_by_run":[
            distribution(b[:TRACE_FRAME])["median"] for b in a22],
        "paired_ordinary_median_delta_ms_by_pair":per_pair_medians,
        "between_pair_median_delta_ms":distribution(per_pair_medians),
        "distribution_of_fixed_frame_mean_paired_delta_ms":
            distribution(fixed_means),
        "distribution_of_fixed_frame_delta_range_across_3_runs_ms":
            distribution(within_image_ranges),
        "a21_ordinary_per_image_ms_by_run":[a[:TRACE_FRAME] for a in a21],
        "a22_ordinary_per_image_ms_by_run":[b[:TRACE_FRAME] for b in a22],
        "paired_ordinary_delta_ms_by_run":[d[:TRACE_FRAME] for d in deltas],
        "measurement_scope":"instrumented A53 complete frame service, NOT pure FPGA neural compute",
        "instrumentation_overhead_causality":"not isolated from run/order/thermal variation",
        "paired_run_order":"OPERATOR_RECORDED_OUTSIDE_TELEMETRY",
        "small_n_uncertainty":"3 independent firmware sessions per variant, descriptive only; no inferential confidence bound",
        "original_p07_neural_oracle":"passed for each source pair before aggregation",
        "official_mnist_test":"NOT_RERUN",
        "power_energy":"DEFERRED",
    }
