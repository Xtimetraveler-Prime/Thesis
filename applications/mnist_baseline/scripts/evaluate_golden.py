#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mnist_app.dataset import load_mnist
from mnist_app.inference import evaluate_dataset, load_deployment


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate an MNIST deployment through the project NeuromorphicCore"
    )
    parser.add_argument("deployment")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output")
    args = parser.parse_args()

    dataset = load_mnist()
    images, labels = dataset.x_test, dataset.y_test
    if args.limit is not None:
        images, labels = images[: args.limit], labels[: args.limit]

    runtime = load_deployment(args.deployment)
    result = evaluate_dataset(
        runtime.core,
        images,
        labels,
        profile=runtime.profile,
        row_lengths=runtime.row_lengths,
    )

    output = args.output or (
        f"applications/mnist_baseline/build/{runtime.profile.name}_golden_evaluation.json"
    )
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
