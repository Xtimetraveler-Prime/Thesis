#!/usr/bin/env python3
from __future__ import annotations

import argparse

from mnist_app.export import write_deployment


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a trained MNIST SNN to project-native integer storage"
    )
    parser.add_argument("checkpoint")
    parser.add_argument("--output", default="applications/mnist/build/deployment")
    args = parser.parse_args()
    manifest = write_deployment(args.checkpoint, args.output)
    print(f"deployment: {manifest}")


if __name__ == "__main__":
    main()
