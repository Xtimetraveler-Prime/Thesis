#!/usr/bin/env python3
from __future__ import annotations

import argparse

import numpy as np

from mnist_app.config import DEFAULT_PROFILE, get_profile
from mnist_app.export import write_deployment


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a trained MNIST SNN to project-native integer storage"
    )
    parser.add_argument("checkpoint")
    parser.add_argument("--output")
    args = parser.parse_args()

    checkpoint = np.load(args.checkpoint)
    profile = get_profile(
        str(np.asarray(checkpoint["profile"]).item())
        if "profile" in checkpoint
        else DEFAULT_PROFILE
    )
    output = args.output or f"applications/mnist_baseline/build/deployment/{profile.name}"
    manifest = write_deployment(args.checkpoint, output)
    print(f"profile:    {profile.name}")
    print(f"deployment: {manifest}")


if __name__ == "__main__":
    main()
