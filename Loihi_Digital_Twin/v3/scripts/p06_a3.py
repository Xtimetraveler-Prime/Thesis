#!/usr/bin/env python3
"""P06-A3 command-line gate: canonical train-only download, preflight, training.

Invoke from v3 directory with PYTHONPATH="$PWD/src" python scripts/p06_a3.py.
Four explicit modes; none ever accesses official t10k IDX files.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from loihi_twin_v2.p06_a3_data import download_training_archives, load_train_validation
from loihi_twin_v2.p06_a3_pilot import run_pilot_cli
from loihi_twin_v2.p06_a3_training import (
    TrainSettings, MIN_VALIDATION_ACCURACY, evaluate, fit_canonical_mnist,
    initialize_model, load_candidate, train_epoch,
)


def _synthetic_smoke() -> None:
    """No dataset/download/checkpoint; just test optimizer and integer model."""
    import torch
    from torch.utils.data import DataLoader, TensorDataset

    config = TrainSettings(seed=20261013, batch_size=4, epochs=1)
    model = initialize_model(config)
    pixels = torch.zeros((12, 784), dtype=torch.uint8)
    labels = torch.tensor([j % 3 for j in range(12)], dtype=torch.int64)
    for j in range(12):
        pixels[j, (j % 3) * 50 : (j % 3) * 50 + 50] = 255
    loader = DataLoader(TensorDataset(pixels, labels), batch_size=4, shuffle=False)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    before = model(pixels)
    metrics = train_epoch(model, loader, optimizer)
    after = model(pixels)
    val = evaluate(model, loader)
    assert before.shape == after.shape == (12, 10)
    assert bool(torch.equal(after, after.round()))
    assert metrics["count"] == val["count"] == 12
    assert 0 <= val["accuracy"] <= 1
    print("P06_A3_SYNTHETIC_SMOKE_PASS=1")
    print("P06_A3_SYNTHETIC_METRICS=" + json.dumps(
        {"train": metrics, "validation": val}, sort_keys=True
    ))
    print("P06_A3_BENCHMARK_FREEZE=NO_MNIST_TRAINING_NO_OFFICIAL_TEST_NO_FPGA")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    modes = p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--download-train-only", action="store_true")
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--pilot", action="store_true")
    modes.add_argument("--synthetic-smoke", action="store_true")
    modes.add_argument("--train", action="store_true")
    modes.add_argument("--validate-candidate", action="store_true")
    p.add_argument("--data-dir", type=Path, default=Path("data/mnist_raw"))
    p.add_argument("--manifest-file", type=Path, help="Where to write preflight JSON")
    p.add_argument("--output-dir", type=Path, help="NEW training trial directory, or existing candidate for validation")
    p.add_argument("--seed", type=int, default=20261013)
    p.add_argument("--epochs", type=int, default=8)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--learning-rate", type=float, default=0.05)
    p.add_argument("--surrogate-width", type=float, default=16.0)
    args = p.parse_args()

    if args.download_train_only:
        files = download_training_archives(args.data_dir)
        for path in files:
            print(f"A3 TRAIN-only downloaded/verified: {path}")
        print("P06_A3_OFFICIAL_TEST_STATUS=SEALED")
        return
    if args.synthetic_smoke:
        _synthetic_smoke()
        return
    if args.validate_candidate:
        if args.output_dir is None:
            p.error("--validate-candidate requires --output-dir")
        model, manifest = load_candidate(args.output_dir)
        assert model.to_integer_network()
        print("P06_A3_CANDIDATE_INTEGRITY_PASS=1")
        print("P06_A3_VALIDATION_GO=" + str(manifest["candidate_go"]))
        return

    # Both preflight and real training enforce canonical 60,000 TRAIN records.
    split = load_train_validation(args.data_dir)
    if args.pilot:
        run_pilot_cli(split)
        return
    if args.preflight:
        if args.manifest_file is not None:
            args.manifest_file.parent.mkdir(parents=True, exist_ok=True)
            if args.manifest_file.exists():
                raise FileExistsError("preflight output exists: do not silently overwrite")
            args.manifest_file.write_text(split.manifest_json(), encoding="utf-8")
        print("P06_A3_DATA_PREFLIGHT_PASS=1")
        print("P06_A3_SPLIT=" + json.dumps({
            "total": split.count, "train": len(split.train_indices),
            "validation": len(split.validation_indices),
            "split_seed": split.manifest["split_seed"],
            "train_indices_sha256": split.manifest["train_indices_le32_sha256"],
            "validation_indices_sha256": split.manifest["validation_indices_le32_sha256"],
            "archives": split.manifest["archives"],
            "official_test": "SEALED",
        }, sort_keys=True))
        return

    if args.train:
        if args.output_dir is None:
            p.error("--train requires a fresh --output-dir (cannot overwrite existing trial)")
        if args.output_dir.exists():
            raise FileExistsError("training trial directory already exists: refuse before any costly training")
        config = TrainSettings(
            seed=args.seed, epochs=args.epochs, batch_size=args.batch_size,
            learning_rate=args.learning_rate, surrogate_width=args.surrogate_width,
        )
        result = fit_canonical_mnist(split, args.output_dir, config)
        print("P06_A3_TRAINED_CANDIDATE_SAVED=1")
        print("P06_A3_VALIDATION_BEST=" + json.dumps(result["best_validation"], sort_keys=True))
        print("P06_A3_VALIDATION_GO=" + str(result["candidate_go"]))
        print("P06_A3_VALIDATION_FLOOR_PREDECLARED=" + str(MIN_VALIDATION_ACCURACY))
        print("P06_A3_OFFICIAL_TEST_STATUS=SEALED")
        return
    raise AssertionError("unrecognized A3 mode")


if __name__ == "__main__":
    main()
