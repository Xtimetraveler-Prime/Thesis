#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mnist_app.comparison import compare_float_checkpoint_to_golden


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare float SNN and quantized NeuromorphicCore inference on the "
            "same MNIST test samples"
        )
    )
    parser.add_argument("checkpoint")
    parser.add_argument("deployment")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--output")
    args = parser.parse_args()

    result = compare_float_checkpoint_to_golden(
        args.checkpoint,
        args.deployment,
        limit=args.limit,
        batch_size=args.batch_size,
    )
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(text, end="")
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"comparison: {path}")


if __name__ == "__main__":
    main()
