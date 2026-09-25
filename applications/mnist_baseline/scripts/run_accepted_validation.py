#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mnist_app.accepted_validation import run_accepted_software_validation


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Export both accepted MNIST checkpoints, run matched float/golden "
            "evaluation, and preserve artifact hashes"
        )
    )
    parser.add_argument(
        "--training-dir",
        default="applications/mnist_baseline/build/accepted-training",
    )
    parser.add_argument(
        "--deployment-root",
        default="applications/mnist_baseline/build/accepted-deployment",
    )
    parser.add_argument(
        "--output",
        default="applications/mnist_baseline/build/accepted-validation",
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()

    manifest = run_accepted_software_validation(
        args.training_dir,
        args.deployment_root,
        args.output,
        limit=args.limit,
        batch_size=args.batch_size,
    )
    payload = json.loads(Path(manifest).read_text(encoding="utf-8"))
    print(f"validation manifest: {manifest}")
    for profile, record in payload["profiles"].items():
        summary = record["summary"]
        print(
            f"{profile}: float={summary['float_accuracy']:.4f} "
            f"golden={summary['golden_accuracy']:.4f} "
            f"delta={summary['golden_minus_float_accuracy']:+.4f} "
            f"agreement={summary['prediction_agreement']:.4f} "
            f"synapses={summary['deployment_stored_synapses']}"
        )


if __name__ == "__main__":
    main()
