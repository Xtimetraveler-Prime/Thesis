#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from mnist_app.frozen_validation import validate_frozen_deployment


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a frozen MNIST deployment package and all hashes"
    )
    parser.add_argument(
        "root",
        nargs="?",
        default="applications/mnist_baseline/frozen/mnist-v1",
    )
    args = parser.parse_args()
    result = validate_frozen_deployment(args.root)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
