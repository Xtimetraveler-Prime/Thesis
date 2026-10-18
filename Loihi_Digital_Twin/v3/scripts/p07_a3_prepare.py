#!/usr/bin/env python3
"""Prepare first 16 fixed TRAIN-derived validation images for P07-A3.

No t10k MNIST test archives are opened. The selected image IDs are the
first 16 entries of the user-accepted, seeded 10k validation partition.
"""
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
from loihi_twin_v2.p07_a3_validation import (
    extract_validation_frames, make_validation_bundle,
    write_validation_bundle,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/mnist_raw"))
    parser.add_argument("--candidate-dir", type=Path,
                        default=Path("artifacts/p06_a3_candidate_seed20261013"))
    parser.add_argument("--ddr-file", type=Path, default=Path(
        "artifacts/p06_a4_static_ddr_seed20261013/core0_initial_p02_ddr_512k.bin"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("P07-A3 output directory exists; refusing overwrite")
    split = load_train_validation(args.data_dir)
    frames = extract_validation_frames(split)
    model, candidate = load_candidate(args.candidate_dir)
    require_pinned_training_candidate(candidate, integer_weights_sha256(model))
    if candidate.get("source_dataset") != split.manifest:
        raise ValueError("P07-A3 dataset provenance differs from frozen checkpoint")
    image, compiled, traces = compile_and_check_traces(model, ())
    if traces or compiled.fingerprint != COMPILED_FINGERPRINT:
        raise ValueError("P07-A3 compiler fingerprint mismatch")
    ddr = args.ddr_file.read_bytes()
    if hashlib.sha256(ddr).hexdigest() != DDR_SHA256:
        raise ValueError("P07-A3 immutable physical DDR identity differs")
    header = parse_ddr_context_header(ddr, verify_payload=True)
    if (header.logical_core_id, header.compartment_count,
        header.synapse_count, header.route_count) != (0, 42, 25408, 32):
        raise ValueError("P07-A3 static DDR header is not frozen Track A")
    batch, payload, manifest, ledger = make_validation_bundle(
        frames, mapping_from_compiled(compiled), split_manifest=split.manifest)
    write_validation_bundle(args.out, batch, payload, manifest, ledger)
    print("P07_A3_FIXED_VALIDATION_SELECTION=FIRST_16")
    print("P07_A3_FRAME_COUNT=16")
    print("P07_A3_BATCH_HOST_PASS=1")
    print("P07_A3_OFFICIAL_TEST=SEALED")
    print("P07_A3_BOARD_STATUS=NOT_RUN")
    print("P07_A3_BATCH_DIR="+str(args.out.resolve()))


if __name__ == "__main__":
    main()
