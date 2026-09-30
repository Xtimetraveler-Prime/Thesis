#!/usr/bin/env python3
"""Calibrate, quantize, map, and validation-evaluate the frozen P08 ANN."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from loihi_twin_v2 import compile_network, export_compiled_fpga_image
from mnist_v2_nxtf.config import CHARACTERIZATION_TIMESTEPS
from mnist_v2_nxtf.conversion import convert_model
from mnist_v2_nxtf.data import load_mnist
from mnist_v2_nxtf.inference import accuracy_by_horizon
from mnist_v2_nxtf.topology import build_network


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--training", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--percentile", type=float, default=99.9)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()

    training_metadata = json.loads((args.training / "p08_training.json").read_text())
    if training_metadata.get("official_test_images_evaluated") != 0:
        raise RuntimeError("training metadata indicates premature official-test evaluation")
    validation_indices = np.load(args.training / training_metadata["validation_indices"])
    dataset = load_mnist()
    calibration_images = dataset.x_train[validation_indices]
    calibration_labels = dataset.y_train[validation_indices]

    model_path = args.training / training_metadata["frozen_model"]
    integer_model, conversion_metadata = convert_model(
        model_path,
        calibration_images,
        args.output,
        percentile=args.percentile,
    )

    network = build_network(integer_model)
    compiled = compile_network(network)
    fpga = export_compiled_fpga_image(compiled)
    args.output.mkdir(parents=True, exist_ok=True)
    network.write_json(args.output / "p08_network.json")
    compiled.write_json(args.output / "p08_deployment.json")
    (args.output / "p08_mapping_report.json").write_text(
        json.dumps(compiled.report(), sort_keys=True, indent=2) + "\n"
    )
    (args.output / "p08_fpga_report.json").write_text(
        json.dumps(fpga.report(), sort_keys=True, indent=2) + "\n"
    )

    validation = accuracy_by_horizon(
        integer_model,
        calibration_images,
        calibration_labels,
        horizons=CHARACTERIZATION_TIMESTEPS,
        batch_size=args.batch_size,
    )
    result = {
        "schema": "p08-conversion-validation-v1",
        "source_network_fingerprint": network.fingerprint,
        "deployment_fingerprint": compiled.fingerprint,
        "activation_percentile": conversion_metadata["activation_percentile"],
        "validation_samples": int(len(calibration_labels)),
        "official_test_images_evaluated": 0,
        "integer_nonzero_weights": integer_model.nonzero_weights,
        "logical_core_count": compiled.report()["logical_core_count"],
        "physical_engine_count": fpga.report()["physical_engine_count"],
        "logical_capacity_changed": fpga.report()["logical_capacity_changed"],
        "connection_sharing": compiled.report()["connection_sharing"],
        "static_route_estimate": compiled.report()["static_route_estimate"],
        "validation_accuracy_by_timestep": {str(key): value for key, value in validation.items()},
    }
    (args.output / "p08_conversion_validation.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )

    print(
        "P08 conversion PASS: "
        f"deployment={compiled.fingerprint} "
        f"cores={result['logical_core_count']} "
        f"nonzero_weights={integer_model.nonzero_weights} "
        f"stored={result['connection_sharing']['stored_shared_parameters']}"
    )
    for horizon in CHARACTERIZATION_TIMESTEPS:
        metrics = validation[horizon]
        print(
            f"P08 validation t={horizon}: accuracy={metrics['accuracy']:.6f} "
            f"errors={metrics['errors']}/{metrics['samples']}"
        )
    print("P08 official test images evaluated: 0")
    print(f"P08 conversion artifacts: {args.output}")


if __name__ == "__main__":
    main()
