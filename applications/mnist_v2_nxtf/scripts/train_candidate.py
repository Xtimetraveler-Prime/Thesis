#!/usr/bin/env python3
"""Train and freeze the validation-selected P08 ANN candidate."""

from __future__ import annotations

import argparse
from pathlib import Path

from mnist_v2_nxtf.training import train_ann


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=20)
    args = parser.parse_args()
    result = train_ann(args.output, max_epochs=args.epochs)
    print(
        "P08 ANN training PASS: "
        f"best_epoch={result['best_epoch']} "
        f"validation_accuracy={result['best_validation_accuracy']:.6f} "
        f"parameters={result['parameter_count']} "
        "official_test_images_evaluated=0"
    )
    print(f"P08 training artifacts: {args.output}")


if __name__ == "__main__":
    main()
