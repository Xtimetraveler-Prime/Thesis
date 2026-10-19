#!/usr/bin/env python3
"""P06-B2.2 deterministic canonical TRAIN-only SNN experiment.

DEFAULT: shape-only preflight; NEVER starts fitting, reads TRAIN archives,
opens official t10k MNIST TEST files, or touches the FPGA.

Explicit real fit:
  PYTHONPATH="$PWD/src" python scripts/p06_b22_train.py --train \
      --data-dir PATH_TO_CANONICAL_TRAIN_ARCHIVES \
      --output-dir PATH_TO_NEW_CANDIDATE_DIR

Test integrity after full training:
  PYTHONPATH="$PWD/src" python scripts/p06_b22_train.py --verify-candidate \
      --candidate-dir PATH_TO_NEW_CANDIDATE_DIR
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from loihi_twin_v2.p06_a3_data import load_train_validation
from loihi_twin_v2.p06_b21_training_foundation import B21Settings
from loihi_twin_v2.p06_b22_training import (
    B22_TEST_STATUS, fit_canonical_mnist, load_candidate,
    require_pinned_train_validation, resource_preflight,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--train", action="store_true",
                      help="explicitly fit complete 50k TRAIN/10k validation from TRAIN-only IDX")
    mode.add_argument("--verify-candidate", action="store_true",
                      help="SHA-verify an existing B2.2 candidate; never run training")
    mode.add_argument("--verify-training-data", action="store_true",
                      help="strict checksum/split verification without training")
    parser.add_argument("--data-dir", type=Path,
                        help="directory holding ONLY original canonical MNIST TRAIN gzip IDX files")
    parser.add_argument("--output-dir", type=Path,
                        help="NEW, not-yet-existing candidate output dir; no overwrite")
    parser.add_argument("--candidate-dir", type=Path,
                        help="existing B2.2 checkpoint folder for --verify-candidate")
    parser.add_argument("--hidden", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20261019)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--surrogate-width", type=float, default=16.0)
    parser.add_argument("--validation-go-floor", type=float, default=0.60)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args()

    settings = B21Settings(
        hidden_neurons=args.hidden, seed=args.seed, epochs=args.epochs,
        batch_size=args.batch_size, learning_rate=args.learning_rate,
        surrogate_width=args.surrogate_width,
        validation_go_floor=args.validation_go_floor)
    if args.verify_candidate:
        if args.candidate_dir is None:
            parser.error("--verify-candidate requires --candidate-dir")
        _model, manifest = load_candidate(args.candidate_dir)
        # Report only verified result, not a B2.4 frozen acceptance.
        result = {
            "schema": manifest["schema"], "mode": "VERIFY_EXISTING_TRAINED_CANDIDATE",
            "best_epoch": manifest["best_epoch"],
            "validation": manifest["best_validation"],
            "candidate_go": manifest["candidate_go"],
            "weight_file_sha256": manifest["weights_file_sha256"],
            "effective_integer_weights_sha256": manifest["effective_integer_weights_sha256"],
            "checkpoint_frozen": False,
            "official_mnist_test_status": B22_TEST_STATUS,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        print("P06_B22_CANDIDATE_INTEGRITY_PASS=1")
        return

    if args.verify_training_data:
        if args.data_dir is None:
            parser.error("--verify-training-data requires --data-dir")
        source = load_train_validation(args.data_dir, strict=True)
        manifest = require_pinned_train_validation(source)
        print(json.dumps({
            "mode": "CANONICAL_TRAIN_ONLY_PROVENANCE_CHECK_NO_TRAINING",
            "train_count": len(source.train_indices),
            "validation_count": len(source.validation_indices),
            "train_indices_sha256": manifest["train_indices_le32_sha256"],
            "validation_indices_sha256": manifest["validation_indices_le32_sha256"],
            "official_mnist_test_status": B22_TEST_STATUS,
        }, indent=2, sort_keys=True))
        print("P06_B22_TRAIN_DATA_SEAL_PASS=1")
        return

    preflight = resource_preflight(settings, args.device)
    print(json.dumps(preflight, indent=2, sort_keys=True), flush=True)
    if not args.train:
        print("P06_B22_PREFLIGHT_PASS=1")
        print("P06_B22_TRAINING_STATUS=NOT_STARTED")
        return

    if args.data_dir is None or args.output_dir is None:
        parser.error("--train requires BOTH --data-dir and --output-dir")
    if args.output_dir.exists():
        parser.error("candidate output directory already exists: refuses overwrite")
    print("P06_B22_EXPLICIT_CANONICAL_TRAINING_SELECTED=1", flush=True)
    split = load_train_validation(args.data_dir, strict=True)
    manifest = fit_canonical_mnist(split, args.output_dir, settings, device=args.device)
    # Re-open saved bytes: user should have identical weight/integer hash.
    _model, checked = load_candidate(args.output_dir)
    assert checked["weights_file_sha256"] == manifest["weights_file_sha256"]
    print(json.dumps({
        "schema": manifest["schema"], "mode": "TRAINED_CANDIDATE_NOT_FROZEN",
        "output_dir": str(args.output_dir),
        "architecture": manifest["architecture"],
        "best_epoch": manifest["best_epoch"],
        "best_validation": manifest["best_validation"],
        "candidate_go": manifest["candidate_go"],
        "weight_file_sha256": manifest["weights_file_sha256"],
        "effective_integer_weights_sha256": manifest["effective_integer_weights_sha256"],
        "official_mnist_test_status": B22_TEST_STATUS,
        "B2_3_quantized_parity_accepted": False,
        "physical_kv260_execution": "NOT_TESTED",
    }, indent=2, sort_keys=True))
    print("P06_B22_TRAIN_ONLY_CANDIDATE_PASS=1")


if __name__ == "__main__":
    main()
