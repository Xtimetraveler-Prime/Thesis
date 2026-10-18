#!/usr/bin/env python3
"""Prepare immutable 128-image validation-only / 10-launch A53 protocol."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from loihi_twin_v2.ddr_abi import parse_ddr_context_header
from loihi_twin_v2.p06_a3_data import load_train_validation
from loihi_twin_v2.p06_a3_training import load_candidate, integer_weights_sha256
from loihi_twin_v2.p06_a4_snapshot import (
    compile_and_check_traces, require_pinned_training_candidate,
)
from loihi_twin_v2.p07_a1_ingress import mapping_from_compiled
from loihi_twin_v2.p07_a2_batch import COMPILED_FINGERPRINT, DDR_SHA256
from loihi_twin_v2.p07_a3_3_protocol import (
    prepare_protocol, select_frames, write_protocol,
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir", type=Path, default=Path("data/mnist_raw"))
    p.add_argument("--candidate-dir", type=Path,
                   default=Path("artifacts/p06_a3_candidate_seed20261013"))
    p.add_argument("--ddr-file", type=Path, default=Path(
        "artifacts/p06_a4_static_ddr_seed20261013/core0_initial_p02_ddr_512k.bin"))
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        p.error("immutable P07-A3.3 protocol output exists; choose a new path")
    split = load_train_validation(args.data_dir)
    frames = select_frames(split)
    model, manifest = load_candidate(args.candidate_dir)
    require_pinned_training_candidate(manifest, integer_weights_sha256(model))
    if manifest.get("source_dataset") != split.manifest:
        raise ValueError("P07-A3.3 canonical training/validation source differs from frozen model")
    image, compiled, traces = compile_and_check_traces(model, ())
    if traces or image.core_id != 0 or compiled.fingerprint != COMPILED_FINGERPRINT:
        raise ValueError("P07-A3.3 frozen trained compiler mismatch")
    ddr = args.ddr_file.read_bytes()
    if hashlib.sha256(ddr).hexdigest() != DDR_SHA256:
        raise ValueError("P07-A3.3 immutable full DDR digest mismatch")
    header = parse_ddr_context_header(ddr, verify_payload=True)
    if (header.logical_core_id, header.compartment_count,
            header.synapse_count, header.route_count) != (0, 42, 25408, 32):
        raise ValueError("P07-A3.3 wrong physical DDR neural dimensions")
    plan, batches = prepare_protocol(frames, mapping_from_compiled(compiled), split.manifest)
    write_protocol(args.out, plan, batches)
    print("P07_A3_3_VALIDATION_SELECTION=FROZEN_FIRST_128")
    print("P07_A3_3_UNIQUE_FRAMES=128")
    print("P07_A3_3_PRIMARY_BATCHES=8")
    print("P07_A3_3_REPEAT_BATCHES=2")
    print("P07_A3_3_REQUIRED_A53_LAUNCHES=10")
    print("P07_A3_3_DIAGNOSTIC_DENOMINATOR=128")
    print("P07_A3_3_CORPUS_NATIVE_PASS=1")
    print("P07_A3_3_PHYSICAL_STATUS=NOT_RUN")
    print("P07_A3_3_OFFICIAL_TEST=SEALED")
    print("P07_A3_3_CORPUS_DIR="+str(args.out.resolve()))


if __name__ == "__main__":
    main()
