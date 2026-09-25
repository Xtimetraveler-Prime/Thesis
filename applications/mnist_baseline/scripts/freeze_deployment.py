#!/usr/bin/env python3
from __future__ import annotations

import argparse

from mnist_app.deployment_freeze import freeze_accepted_deployments


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Freeze accepted MNIST deployments and FPGA validation corpus"
    )
    parser.add_argument(
        "--accepted-validation",
        default=(
            "applications/mnist_baseline/build/accepted-validation/"
            "accepted_software_validation.json"
        ),
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
        default="applications/mnist_baseline/frozen/mnist-v1",
    )
    args = parser.parse_args()

    manifest = freeze_accepted_deployments(
        args.accepted_validation,
        args.training_dir,
        args.deployment_root,
        args.output,
    )
    print(f"freeze manifest: {manifest}")
    print(f"frozen directory: {manifest.parent}")


if __name__ == "__main__":
    main()
