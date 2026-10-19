"""P08-A5 deterministic CPU-vs-physical LATENCY closeout report construction.

Produces a DRAFT human-readable technical artifact, not an approved FPGA
speedup claim. Checks all available report contracts and same TRAIN stage hash.
No physical hardware, live clock calibration or standalone CPU TEST data.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from .p08_a3_2_analysis import distribution,FRAME_COUNT,TRACE_FRAME
from .p08_a3_2_repeats import AGG_SCHEMA
from .p08_a5_cpu_benchmark import SCHEMA as CPU_SCHEMA

CPU_NAMES=("preloaded_core_endpoint","full_raw_image_to_class_endpoint")
STAGE_PAIRS=(
    ("stage_descriptor","original_train_stage_descriptor"),
    ("stage_pixels","original_train_stage_pixels"),
    ("stage_manifest","original_train_stage_manifest"),
)


def read_json(path: Path) -> dict:
    obj=json.loads(path.read_text(encoding="utf8"))
    if not isinstance(obj,dict):
        raise ValueError("A5 closeout expects an object-shaped JSON report")
    return obj


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _valid_series(series: object) -> list[float]:
    if (not isinstance(series,list) or len(series)!=FRAME_COUNT or
            any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in series)):
        raise ValueError("A5 CPU report must contain 1024 positive finite millisecond measurements per run")
    return [float(v) for v in series]


def validate_cpu_report(cpu: dict) -> None:
    if (cpu.get("schema")!=CPU_SCHEMA or cpu.get("unique_images")!=FRAME_COUNT or
            cpu.get("ordinary_images")!=TRACE_FRAME or
            cpu.get("selected_full_trace_image")!=TRACE_FRAME or
            cpu.get("logical_timesteps")!=26 or cpu.get("benchmark_repeats")!=3 or
            cpu.get("all_1024_original_physical_journal_outputs_exact")!="PASS" or
            cpu.get("all_1024_original_26tick_spike_traces_exact")!="PASS" or
            cpu.get("fpga_service_scope_matched_exactly") is not False or
            cpu.get("power_energy")!="DEFERRED" or
            cpu.get("official_mnist_test")!="NOT_RERUN"):
        raise ValueError("A5 CPU report is not a validated 1024-image 3-repeat original-spike-parity report")
    if not isinstance(cpu.get("host_cpu_environment"),dict):
        raise ValueError("A5 missing host CPU provenance")
    provenance=cpu.get("provenance")
    if not isinstance(provenance,dict) or provenance.get(
            "original_p07_packed_independent_physical_oracle")!="PASS_ALL_1024":
        raise ValueError("A5 source physical P07 packed oracle not independently verified")
    for name in CPU_NAMES:
        endpoint=cpu.get(name)
        if not isinstance(endpoint,dict):
            raise ValueError("A5 missing CPU endpoint")
        samples=endpoint.get("three_sequential_runs_ms")
        if not isinstance(samples,list) or len(samples)!=3:
            raise ValueError("A5 CPU endpoint needs three distinct per-frame run arrays")
        runs=[_valid_series(row) for row in samples]
        summaries=endpoint.get("ordinary_1023_distributions_ms")
        if not isinstance(summaries,list) or len(summaries)!=3:
            raise ValueError("A5 CPU run distribution missing")
        for run,summary in zip(runs,summaries):
            want=distribution(run[:TRACE_FRAME])
            if (not isinstance(summary,dict) or any(k not in summary or not math.isclose(
                    summary[k],v,rel_tol=1e-10,abs_tol=1e-8)
                    for k,v in want.items())):
                raise ValueError("A5 original CPU timing summary tampered or inconsistent")


def validate_cross_provenance(cpu: dict,physical: dict) -> None:
    if (physical.get("schema")!=AGG_SCHEMA or
            physical.get("independent_firmware_sessions_per_variant")!=3 or
            physical.get("independent_physical_pairs")!=3 or
            physical.get("unique_train_validation_images")!=FRAME_COUNT or
            physical.get("ordinary_images_per_pair")!=TRACE_FRAME or
            physical.get("selected_full_trace_frame")!=TRACE_FRAME or
            physical.get("frame_repeats_are_new_independent_images") is not False or
            physical.get("original_p07_neural_oracle")!="passed for each source pair before aggregation" or
            physical.get("power_energy")!="DEFERRED" or
            physical.get("official_mnist_test")!="NOT_RERUN"):
        raise ValueError("A5 repeated physical 3-pair source is not accepted")
    hashes=physical.get("immutable_stage_sha256")
    cpu_hashes=cpu["provenance"].get("source_sha256")
    if not isinstance(hashes,dict) or not isinstance(cpu_hashes,dict):
        raise ValueError("A5 cannot compare without original staged-data hashes")
    for cpu_key,physical_key in STAGE_PAIRS:
        if cpu_hashes.get(cpu_key)!=hashes.get(physical_key):
            raise ValueError(f"A5 CPU and physical paired study have different TRAIN stage {cpu_key}")
    # Physical CPU reference must be the actual original A2.1 physical session
    # included among the previously repeated three paired benchmark runs.
    session=cpu["provenance"].get("physical_capture_run_directory")
    original=physical.get("source_evidence")
    if (not isinstance(session,str) or not isinstance(original,list) or
            len(original)!=3 or not any(
                isinstance(item,dict) and item.get("a21_run_dir")==session
                for item in original)):
        raise ValueError("A5 CPU numerical proof is not tied to one accepted physical A2.1 run")
    for item in original:
        for field in ("a21_service_ordinary_ms","a22_service_ordinary_ms"):
            summary=item.get(field) if isinstance(item,dict) else None
            if not isinstance(summary,dict) or any(
                key not in summary or type(summary[key]) not in (int,float) or
                not math.isfinite(summary[key])
                for key in ("median","p95_nearest_rank","sample_stdev")
            ) or summary.get("n")!=TRACE_FRAME:
                raise ValueError("A5 A53 physical ordinary-frame source distributions missing")
    for field in ("a21_ordinary_median_service_ms_by_run",
                  "a22_ordinary_median_service_ms_by_run",
                  "paired_ordinary_median_delta_ms_by_pair"):
        values=physical.get(field)
        if (not isinstance(values,list) or len(values)!=3 or
                any(type(x) not in (int,float) or not math.isfinite(x) for x in values)):
            raise ValueError("A5 missing physical pair-level raw median values")
    for key in ("a21_ordinary_per_image_ms_by_run",
                "a22_ordinary_per_image_ms_by_run",
                "paired_ordinary_delta_ms_by_run"):
        runs=physical.get(key)
        if not isinstance(runs,list) or len(runs)!=3:
            raise ValueError("A5 physical 3-run ordinary per-image vectors missing")
        if any(not isinstance(row,list) or len(row)!=TRACE_FRAME for row in runs):
            raise ValueError("A5 physical distinct frame count mismatch")
    if physical.get("measurement_scope")!="instrumented A53 complete frame service, NOT pure FPGA neural compute":
        raise ValueError("A5 physical metric scope changed unexpectedly")


def _fmt(values: list[float],factor:float=1) -> str:
    return ", ".join(f"{value*factor:.4f}" for value in values)


def make_draft(cpu: dict,physical: dict,
               *,cpu_sha: str,physical_sha: str) -> str:
    validate_cpu_report(cpu)
    validate_cross_provenance(cpu,physical)
    host=cpu["host_cpu_environment"]
    cpu_core=cpu["preloaded_core_endpoint"]
    cpu_full=cpu["full_raw_image_to_class_endpoint"]
    a=physical["a21_ordinary_median_service_ms_by_run"]
    b=physical["a22_ordinary_median_service_ms_by_run"]
    deltas=physical["paired_ordinary_median_delta_ms_by_pair"]
    core=[r["median"] for r in cpu_core["ordinary_1023_distributions_ms"]]
    full=[r["median"] for r in cpu_full["ordinary_1023_distributions_ms"]]
    pairdist=physical["between_pair_median_delta_ms"]
    paragraph=[
        "# P08-A5 — CPU reference and KV260 latency closeout CANDIDATE",
        "",
        "**STATUS: GENERATED OFFLINE; NOT YET ACCEPTED BY USER; DO NOT MERGE P08-A.**",
        "The comparison uses the same original 1024 distinct TRAIN-derived held-out",
        "validation frames, with 1023 ordinary frames and selected full physical",
        "26×42 trace frame 1023 reported separately. No MNIST official TEST rerun.",
        "Power and energy characterization remain deferred.",
        "",
        "## Frozen source / physical evidence binding",
        "",
        f"- CPU report SHA256: `{cpu_sha}`.",
        f"- Repeated physical paired source SHA256: `{physical_sha}`.",
        "- Original data descriptor, raw pixels and manifest SHA256 match exactly",
        "  across the CPU and six real physical study sessions.",
        "- CPU prepared reference was differential-checked against the P06 packed",
        "  replay and independently checked per frame and tick against a P07 journal.",
        "- Original accepted P07 physical full 26×42 selected trace was independently",
        "  verified by the source P07 oracle gate.",
        "",
        "## Benchmarked endpoints — DO NOT LABEL THIS TABLE 'FPGA SPEEDUP'",
        "",
        "| Endpoint | Three per-run ordinary 1023-image medians (ms) | Boundary |",
        "|---|---|---|",
        f"| Host CPU preloaded scalar integer core | {_fmt(core)} | Packed 26 ticks and routes; event schedules ready |",
        f"| Host CPU full 784-byte raw image to class | {_fmt(full)} | Original encoder + packed 26 ticks + spike readout; model decoded once |",
        f"| KV260 A53 with A2.1 | {_fmt(a)} | Instrumented complete physical A53 image service, MMIO, PS+PL and result commit |",
        f"| KV260 A53 with A2.2 | {_fmt(b)} | Same plus seven-timestamp per-tick instrumentation |",
        "",
        "### Same-frame-population p95 and sample standard deviation (ms)",
        "",
        "| Paired trial | Host CPU preloaded p95 / SD | Host CPU image-to-class p95 / SD | KV260 A2.1 p95 / SD | KV260 A2.2 p95 / SD |",
        "|---:|---:|---:|---:|---:|",
        *[
            "| "+str(i+1)+" | "+
            f"{cpu_core['ordinary_1023_distributions_ms'][i]['p95_nearest_rank']:.4f} / {cpu_core['ordinary_1023_distributions_ms'][i]['sample_stdev']:.4f} | "+
            f"{cpu_full['ordinary_1023_distributions_ms'][i]['p95_nearest_rank']:.4f} / {cpu_full['ordinary_1023_distributions_ms'][i]['sample_stdev']:.4f} | "+
            f"{physical['source_evidence'][i]['a21_service_ordinary_ms']['p95_nearest_rank']:.4f} / {physical['source_evidence'][i]['a21_service_ordinary_ms']['sample_stdev']:.4f} | "+
            f"{physical['source_evidence'][i]['a22_service_ordinary_ms']['p95_nearest_rank']:.4f} / {physical['source_evidence'][i]['a22_service_ordinary_ms']['sample_stdev']:.4f} |"
            for i in range(3)
        ],
        "",
        "These 1023-image p95/SD values describe within-session heterogeneity.",
        "Host CPU repeats are sequential in one process; 3 FPGA pairs were",
        "separately booted. They do NOT share a common physical clock, OS or",
        "exactly corresponding service endpoints.",
        "",
        "### Within-three-physical-pair profiler perturbation (not calibrated timer cost)",
        "",
        f"- Median-of-matched-image pair differences in µs: **{_fmt(deltas,1000)}**.",
        f"- Mean of paired medians: **{pairdist['mean']*1000:.3f} µs**,",
        f"  sample standard deviation **{pairdist['sample_stdev']*1000:.3f} µs**.",
        "- Original CPU replay does not include Cortex-A53 scheduling, FPGA MMIO",
        "  polling, physical event-bank writes, DDR paging or physical journal",
        "  commit. The *full CPU* endpoint still does not equal the FPGA's full",
        "  service boundary. Therefore raw latency ratios are **not scope-matched",
        "  PL acceleration factors**, and there is **no supported pure FPGA",
        "  speedup claim** from this table.",
        "- The preloaded CPU endpoint can only be compared to a similarly scoped",
        "  PL-only engine interval once the achieved PL cycle-clock frequency and",
        "  exact event-processing counter boundaries are physically qualified.",
        "",
        "## CPU runtime configuration (self-reported)",
        "",
        f"- CPU model: {host.get('processor_from_proc_cpuinfo') or host.get('processor_reported_by_platform') or 'NOT_REPORTED'}.",
        f"- CPU ISA/machine: {host.get('machine')}; logical CPUs: {host.get('logical_cpu_count')}.",
        f"- Affinity: {host.get('process_cpu_affinity')}.",
        f"- cpu0 scaling governor: {host.get('current_cpu_governor_cpu0') or 'NOT_REPORTED'}.",
        f"- Reported cpu0 scaling frequency kHz (instantaneous): {host.get('current_cpu_scaling_freq_cpu0_khz') or 'NOT_REPORTED'}.",
        f"- Python implementation/version: {host.get('implementation')}, {str(host.get('python_version','')).splitlines()[0]}.",
        f"- Execution: {host.get('benchmark_language')}; {host.get('threading')}.",
        f"- Timer: {host.get('timer')}; counter is *not* A53 CNTVCT or PL cycles.",
        "",
        "## Acceptance and limitations",
        "",
        "1. A3 repeated KV260 physical inference and numerical/sidecar verification",
        "   user-attested complete. Exactly three physical paired sessions and",
        "   1024 distinct validation IDs, not 3072 statistically independent inputs.",
        "2. CPU reference has two separate measured endpoints, original 26 ticks,",
        "   fixed checkpoint and all-1024 physical output parity. CPU host native",
        "   timing is *pure Python scalar*; it should not be marketed as best CPU",
        "   native optimized C/AVX performance or hardware-only acceleration.",
        "3. FPGA achieved PL clock/time not independently calibrated here; raw",
        "   PL dispatch counters cannot be turned into seconds using A53 CNTFRQ.",
        "4. Arm CNTFRQ is firmware-reported, not an external stopwatch calibration;",
        "   CPU frequency and thermal state were observed where available but",
        "   not held constant by code; CPU and FPGA timings are separate devices.",
        "5. Physical power/energy deferred, no Loihi/FPGA energy comparisons.",
        "6. THIS IS A REVIEW CANDIDATE, not user acceptance. Confirm local raw",
        "   SHA256, host timing stability and explicit final scope before closeout.",
        "",
        "**NEXT GATE: user evaluates benchmark native tests, host CPU measurements",
        "and report; user explicitly approves latency-only P08-A closeout.**",
        "",
    ]
    return "\n".join(paragraph)
