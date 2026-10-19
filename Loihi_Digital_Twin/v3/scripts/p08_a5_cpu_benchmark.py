#!/usr/bin/env python3
"""P08-A5: original-frozen P03 CPU reference benchmark vs real P07 journal.

OFFLINE ONLY; original canonical first1024 TRAIN-derived validation population.
No JTAG/Vivado/physical DDR, no MNIST TEST, no retraining or P03/P07 edits.
Not a PL-only vs CPU speedup comparison: endpoint scope remains different.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from loihi_twin_v2.p06_a3_data import load_train_validation
from loihi_twin_v2.p06_a3_training import load_candidate,integer_weights_sha256
from loihi_twin_v2.p06_a4_snapshot import (
    compile_and_check_traces,require_pinned_training_candidate,
    PINNED_INTEGER_WEIGHTS_SHA256,PINNED_CHECKPOINT_SHA256,
)
from loihi_twin_v2.p06_input_contract import image_event_schedule
from loihi_twin_v2.p06_packed_replay import replay_p03_image
from loihi_twin_v2.p07_a1_ingress import mapping_from_compiled
from loihi_twin_v2.p07_a4_stream import parse_journal
from loihi_twin_v2.p07_a4_validation import (
    select_validation_prefix,validate_ledger,
)
from loihi_twin_v2.p08_a3_2_analysis import FRAME_COUNT,TRACE_FRAME,ELF_A21_SHA256
from loihi_twin_v2.p08_a5_cpu_reference import (
    prepare_cpu,preloaded_compute,assert_matches_original_packed,
)
from loihi_twin_v2.p08_a5_cpu_benchmark import (
    benchmark_cpu_two_endpoints,sha256,
)
from p07_a4_2_verify import validate_staging
from p08_a3_2_pair_check import verified_source,require_original_p07_oracle

DEFAULT_CANDIDATE=Path("artifacts/p06_a3_candidate_seed20261013")
DEFAULT_TRAIN=Path("data/mnist_raw")
ORIGINAL_PROBE_INDICES=(0,1,15,127,255,511,1023)


def ensure_cpu_inputs(
    stage_dir: Path, physical_run_dir: Path, train_dir:Path,
    candidate_dir:Path, elf_path:Path,
):
    """Run original independent FULL P07 KV260 packed replay gate first."""
    meta,stream=validate_staging(stage_dir)
    if (meta["scope"]!="TRAIN_DERIVED_VALIDATION_FIRST_1024" or
        stream.image_count!=FRAME_COUNT or stream.trace_index!=TRACE_FRAME):
        raise ValueError("A5 only exact canonical TRAIN validation1024 / trace1023")
    if sha256(elf_path)!=ELF_A21_SHA256:
        raise ValueError("A5 CPU benchmark physical source must be original pinned A2.1 ELF")
    journal,trace,_timing=verified_source(physical_run_dir,"A2_1",ELF_A21_SHA256)
    # A full 1024-frame physical P07 packed-integer reference check, including
    # all 26x10 physical spikes and the selected 26x42 full neural state trace.
    require_original_p07_oracle(stage_dir,journal,trace)
    physical_rows=parse_journal(journal.read_bytes(),stream)

    split=load_train_validation(train_dir)  # ONLY MNIST TRAIN gzip IDX archives
    model,candidate=load_candidate(candidate_dir)
    require_pinned_training_candidate(candidate,integer_weights_sha256(model))
    if split.manifest!=candidate["source_dataset"]:
        raise ValueError("A5 TRAIN source split differs from accepted checkpoint")
    selected=select_validation_prefix(split,FRAME_COUNT)
    ledger=json.loads((stage_dir/"p07_a4_2a_validation_labels_HOST_ONLY.json").read_text())
    validate_ledger(ledger,selected,stream.images)
    image,compiled,checked=compile_and_check_traces(model,())
    if checked or compiled.fingerprint!=meta["compiled_fingerprint"]:
        raise ValueError("A5 compiled packed image fingerprint differs from physical stage")
    mapping=mapping_from_compiled(compiled)
    if mapping!=stream.mapping:
        raise ValueError("A5 input axon map differs from frozen real P07 physical input")
    prepared=prepare_cpu(image,mapping)
    # Independent oracle differential probes including selected trace frame.
    # Physical independent oracle has already checked EVERY image and tick.
    for i in ORIGINAL_PROBE_INDICES:
        oracle=replay_p03_image(image,mapping,stream.image(i))
        schedule=image_event_schedule(stream.image(i))
        result=preloaded_compute(prepared,schedule)
        assert_matches_original_packed(result,oracle,schedule,i)

    provenance={
        "physical_A2_1_firmware_elf_sha256":ELF_A21_SHA256,
        "trained_weights_effective_integer_sha256":PINNED_INTEGER_WEIGHTS_SHA256,
        "trained_checkpoint_sha256":PINNED_CHECKPOINT_SHA256,
        "stage_scope":meta["scope"],
        "stage_trace_index":stream.trace_index,
        "compiled_fingerprint":compiled.fingerprint,
        "original_p07_packed_independent_physical_oracle":"PASS_ALL_1024",
        "prepared_cpu_vs_original_independent_packed_probe_indices":list(ORIGINAL_PROBE_INDICES),
        "canonical_train_archive_manifest":split.manifest,
        "physical_capture_original_variant":"A2_1",
        "physical_capture_run_directory":str(physical_run_dir.resolve()),
        "source_sha256":{
            "stage_descriptor":sha256(stage_dir/"p07_a4_descriptor_256.bin"),
            "stage_mapping":sha256(stage_dir/"p07_a4_mapping_1568.bin"),
            "stage_pixels":sha256(stage_dir/"p07_a4_pixels_raw.bin"),
            "stage_manifest":sha256(stage_dir/"p07_a4_2a_stage_manifest.json"),
            "physical_original_neural_journal":sha256(journal),
            "physical_selected_26x42_trace":sha256(trace),
            "candidate_weights_state_dict":sha256(candidate_dir/"weights_state_dict.pt"),
        },
        "official_mnist_test":"SEALED_AND_NOT_RERUN",
    }
    return prepared,tuple(stream.image(i) for i in range(FRAME_COUNT)),physical_rows,provenance


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-dir",type=Path,required=True)
    parser.add_argument("--physical-a21-run-dir",type=Path,required=True)
    parser.add_argument("--physical-a21-elf",type=Path,required=True)
    parser.add_argument("--candidate-dir",type=Path,default=DEFAULT_CANDIDATE)
    parser.add_argument("--train-data-dir",type=Path,default=DEFAULT_TRAIN)
    parser.add_argument("--report",type=Path,required=True)
    parser.add_argument("--warmup",type=int,default=2)
    args=parser.parse_args()
    if args.report.exists() or args.report.is_symlink():
        parser.error("A5 refuses to overwrite original evidence or existing CPU report")
    if not args.report.is_absolute():
        parser.error("A5 benchmark evidence report must be absolute")
    if not args.report.parent.is_dir():
        parser.error("A5 output parent directory missing")
    repo=Path(__file__).resolve().parents[3].resolve()
    target=args.report.resolve()
    if target==repo or repo in target.parents:
        parser.error("A5 CPU report must be outside tracked repository")
    prepared,pixels,physical,provenance=ensure_cpu_inputs(
        args.stage_dir,args.physical_a21_run_dir,args.train_data_dir,
        args.candidate_dir,args.physical_a21_elf,
    )
    result=benchmark_cpu_two_endpoints(
        prepared,pixels,physical,warmup=args.warmup,
    )
    result["provenance"]=provenance
    with args.report.open("x",encoding="utf8") as output:
        json.dump(result,output,indent=2,sort_keys=True)
        output.write("\n")
    core=result["preloaded_core_endpoint"]["ordinary_1023_aggregate_of_per_image_medians_ms"]
    full=result["full_raw_image_to_class_endpoint"]["ordinary_1023_aggregate_of_per_image_medians_ms"]
    print("P08_A5_CPU_SOURCE_PHYSICAL_P07_1024_PACKED_ORACLE_PASS=1")
    print("P08_A5_CPU_PRELOADED_1024_PHYSICAL_SPIKES_EXACT=1")
    print("P08_A5_CPU_FULL_1024_PHYSICAL_SPIKES_EXACT=1")
    print(f"P08_A5_CPU_PRELOADED_MEDIAN_MS={core['median']:.6f}")
    print(f"P08_A5_CPU_FULL_MEDIAN_MS={full['median']:.6f}")
    print("P08_A5_CPU_TWO_ENDPOINT_THREE_REPEAT_BENCHMARK_PASS=1")
    print("P08_A5_CPU_VS_FPGA_CLAIM=SCOPES_NOT_IDENTICAL")
    print("P08_A5_FPGA_PL_ONLY_SECONDS=NOT_MEASURED")
    print("P08_A5_POWER=DEFERRED")
    print("P08_A5_OFFICIAL_TEST=SEALED")


if __name__=="__main__":
    main()
