"""P08.3.5c source-recovered conversion artifact and P06 deployment freeze.

This module supersedes the earlier blanket-scale P08.3.4 conversion for forward
P08 execution. It reuses the source-recovered NxTF/SNN-Toolbox normalization
from P08.3.5b, maps those integer parameters into the accepted project graph,
and compiles the exact graph through P06 without evaluating classification
accuracy or loading the official MNIST test split.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from loihi_twin_v2 import (
    CompartmentConfig,
    InputPopulationSpec,
    InputProjectionSpec,
    MappingOptions,
    NetworkSpec,
    PopulationSpec,
    ProjectionConnection,
    ProjectionSpec,
    compile_network,
)

from .accepted_ann import (
    ACCEPTED_ANN_CHECKPOINT_SHA256,
    ACCEPTED_ANN_WEIGHTS_FINGERPRINT,
)
from .conversion import (
    _array_identity,
    _channel_population,
    _spatial_index,
    conv_geometries,
)
from .policy import CONVERSION_POLICY, OFFICIAL_TEST_POLICY
from .reconstruction import PROPOSED_METRICS
from .source_backend_reconstruction import (
    SOURCE_ACTIVATION_PERCENTILE,
    SOURCE_BACKEND_MANIFEST,
    SOURCE_BACKEND_PARAMETERS,
    SOURCE_INPUT_SCALE,
    SOURCE_PARAM_PERCENTILE,
    reconstruct_source_backend,
)
from .structural import P06_STRUCTURAL_COMPARTMENTS_PER_CORE

SOURCE_RECOVERED_SCHEMA = "p08-source-recovered-conversion-v1"
SOURCE_RECOVERED_MANIFEST = "source_recovered_conversion_manifest.json"
SOURCE_RECOVERED_PARAMETERS = "source_recovered_parameters.npz"
SOURCE_RECOVERED_NETWORK = "source_recovered_network.json"
SOURCE_RECOVERED_COMPILED = "source_recovered_compiled_deployment.json"

# Intel's public backend defines V_THR_MAX = 2**17 - 1 and states that softmax
# output takes the voltage trace while the threshold is set to maximum.
SOFTMAX_READOUT_THRESHOLD = 2**17 - 1
SOFTMAX_READOUT_MODE = "final_membrane_voltage_argmax"
INPUT_INGRESS_MODE = "host_bias_encoder_to_external_pixel_spikes"


def _arrays_fingerprint(arrays: dict[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    for name in sorted(arrays):
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(_array_identity(arrays[name]))
    return digest.hexdigest()


def _json_fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_source_recovered_network(parameters: dict[str, np.ndarray]) -> NetworkSpec:
    """Build the accepted 4-convolution graph using recovered source semantics.

    The 784-pixel BIAS input layer is represented by the ingress encoder rather
    than by an additional P06 population. This preserves the accepted 4,218
    computational-neuron comparison graph. Hidden layers use their recovered
    calibrated thresholds. Conv4 uses the recovered softmax maximum-threshold
    voltage-readout behavior.
    """

    hidden_thresholds = {
        f"conv{i}": int(np.asarray(parameters[f"conv{i}_threshold"]).reshape(-1)[0])
        for i in range(1, 4)
    }
    if any(value <= 0 for value in hidden_thresholds.values()):
        raise ValueError(f"invalid recovered thresholds: {hidden_thresholds}")

    populations: list[PopulationSpec] = []
    projections: list[ProjectionSpec] = []
    input_projections: list[InputProjectionSpec] = []

    for stage_index, geometry in enumerate(conv_geometries(), start=1):
        q_kernel = np.asarray(parameters[f"{geometry.name}_kernel_integer"], dtype=np.int64)
        q_bias = np.asarray(parameters[f"{geometry.name}_bias_integer"], dtype=np.int64)
        spatial_size = geometry.output_height * geometry.output_width
        threshold = (
            hidden_thresholds[geometry.name]
            if stage_index <= 3
            else SOFTMAX_READOUT_THRESHOLD
        )

        for output_channel in range(geometry.output_channels):
            populations.append(
                PopulationSpec(
                    name=_channel_population(geometry.name, output_channel),
                    size=spatial_size,
                    compartment=CompartmentConfig(
                        current_decay=CONVERSION_POLICY.current_decay,
                        voltage_decay=CONVERSION_POLICY.voltage_decay,
                        threshold=threshold,
                        bias=int(q_bias[output_channel]),
                        reset_voltage=CONVERSION_POLICY.reset_voltage,
                        refractory_ticks=CONVERSION_POLICY.refractory_ticks,
                    ),
                )
            )

        for output_channel in range(geometry.output_channels):
            destination_population = _channel_population(geometry.name, output_channel)
            for input_channel in range(geometry.input_channels):
                source_name = (
                    "pixels"
                    if stage_index == 1
                    else _channel_population(f"conv{stage_index - 1}", input_channel)
                )
                connections: list[ProjectionConnection] = []
                for output_y in range(geometry.output_height):
                    for output_x in range(geometry.output_width):
                        destination_index = _spatial_index(output_y, output_x, geometry.output_width)
                        for kernel_y in range(geometry.kernel):
                            input_y = output_y * geometry.stride + kernel_y
                            for kernel_x in range(geometry.kernel):
                                input_x = output_x * geometry.stride + kernel_x
                                source_index = _spatial_index(input_y, input_x, geometry.input_width)
                                weight = int(q_kernel[kernel_y, kernel_x, input_channel, output_channel])
                                connections.append(
                                    ProjectionConnection(
                                        source_index=source_index,
                                        destination_index=destination_index,
                                        weight=weight,
                                    )
                                )

                projection_name = f"{source_name}_to_{destination_population}"
                if stage_index == 1:
                    input_projections.append(
                        InputProjectionSpec(
                            name=projection_name,
                            source_input="pixels",
                            destination_population=destination_population,
                            connections=tuple(connections),
                        )
                    )
                else:
                    projections.append(
                        ProjectionSpec(
                            name=projection_name,
                            source_population=source_name,
                            destination_population=destination_population,
                            connections=tuple(connections),
                        )
                    )

    network = NetworkSpec(
        populations=tuple(populations),
        projections=tuple(projections),
        input_populations=(InputPopulationSpec(name="pixels", size=28 * 28),),
        input_projections=tuple(input_projections),
    )
    neurons = sum(population.size for population in network.populations)
    expanded = sum(
        len(projection.connections)
        for projection in (*network.projections, *network.input_projections)
    )
    if neurons != PROPOSED_METRICS.neuron_count:
        raise AssertionError(f"source-recovered neuron count drifted: {neurons}")
    if expanded != PROPOSED_METRICS.expanded_connections:
        raise AssertionError(f"source-recovered connection count drifted: {expanded}")
    return network


def run_source_recovered_conversion(
    checkpoint_path: str | Path,
    training_manifest_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    parameters, source_manifest = reconstruct_source_backend(
        checkpoint_path, training_manifest_path, output
    )
    parameter_fingerprint = _arrays_fingerprint(parameters)
    network = build_source_recovered_network(parameters)
    compiled = compile_network(
        network,
        MappingOptions(compartments_per_core=P06_STRUCTURAL_COMPARTMENTS_PER_CORE),
    )
    logical_core_count = len(compiled.logical_deployment.core_configs)
    if logical_core_count != 5:
        raise AssertionError(
            f"source-recovered graph expected five P06 logical cores; got {logical_core_count}"
        )

    parameters_path = output / SOURCE_RECOVERED_PARAMETERS
    network_path = output / SOURCE_RECOVERED_NETWORK
    compiled_path = output / SOURCE_RECOVERED_COMPILED
    np.savez_compressed(parameters_path, **parameters)
    network.write_json(network_path)
    compiled.write_json(compiled_path)

    hidden_thresholds = [
        int(np.asarray(parameters[f"conv{i}_threshold"]).reshape(-1)[0])
        for i in range(1, 4)
    ]
    layer_ranges = []
    for index in range(1, 5):
        w = np.asarray(parameters[f"conv{index}_kernel_integer"], dtype=np.int64)
        b = np.asarray(parameters[f"conv{index}_bias_integer"], dtype=np.int64)
        layer_ranges.append(
            {
                "name": f"conv{index}",
                "weight_min": int(w.min()),
                "weight_max": int(w.max()),
                "bias_min": int(b.min()),
                "bias_max": int(b.max()),
            }
        )

    manifest: dict[str, Any] = {
        "schema": SOURCE_RECOVERED_SCHEMA,
        "status": "P08_3_5C_SOURCE_RECOVERED_COMPILE_REVIEW_PENDING",
        "supersedes_forward_execution_artifact": "P08_3_4_DTHIR_BLANKET_SCALE",
        "preserve_superseded_artifact_for_audit": True,
        "accepted_ann_checkpoint_sha256": ACCEPTED_ANN_CHECKPOINT_SHA256,
        "accepted_ann_weights_fingerprint": ACCEPTED_ANN_WEIGHTS_FINGERPRINT,
        "official_test_policy": OFFICIAL_TEST_POLICY,
        "official_test_used": False,
        "test_examples_observed": 0,
        "classification_accuracy_evaluated": False,
        "calibration_examples": int(source_manifest["calibration_examples"]),
        "normalization_origin": source_manifest["normalization_origin"],
        "param_percentile": SOURCE_PARAM_PERCENTILE,
        "activation_percentile": SOURCE_ACTIVATION_PERCENTILE,
        "desired_threshold_to_input_ratio": CONVERSION_POLICY.desired_threshold_to_input_ratio,
        "input_ingress_mode": INPUT_INGRESS_MODE,
        "input_scale": SOURCE_INPUT_SCALE,
        "input_threshold": int(source_manifest["input_threshold"]),
        "input_population_counted_in_benchmark_neurons": False,
        "hidden_thresholds": hidden_thresholds,
        "softmax_readout_mode": SOFTMAX_READOUT_MODE,
        "softmax_readout_threshold": SOFTMAX_READOUT_THRESHOLD,
        "softmax_output_spike_count_decoder": False,
        "parameter_fingerprint": parameter_fingerprint,
        "network_fingerprint": network.fingerprint,
        "compiled_fingerprint": compiled.fingerprint,
        "logical_core_count": logical_core_count,
        "resident_context_count": 3,
        "physical_engine_count": 1,
        "neuron_count": PROPOSED_METRICS.neuron_count,
        "expanded_connections": PROPOSED_METRICS.expanded_connections,
        "layer_ranges": layer_ranges,
        "source_backend_manifest_fingerprint": source_manifest["manifest_fingerprint"],
        "project_arithmetic_note": (
            "NxTF integer parameter values are executed in project integer units; "
            "native Loihi exponent micro-encoding is not claimed bit-for-bit."
        ),
    }
    manifest["manifest_fingerprint"] = _json_fingerprint(manifest)
    (output / SOURCE_RECOVERED_MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze and P06-compile the P08.3.5 source-recovered conversion"
    )
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--training-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    manifest = run_source_recovered_conversion(
        args.checkpoint, args.training_manifest, args.output_dir
    )
    print(
        "PASS: P08.3.5c source-recovered conversion "
        f"calibration={manifest['calibration_examples']} "
        f"input_threshold={manifest['input_threshold']} "
        f"hidden_thresholds={manifest['hidden_thresholds']}"
    )
    print(
        "PASS: P08.3.5c softmax readout "
        f"mode={manifest['softmax_readout_mode']} "
        f"threshold={manifest['softmax_readout_threshold']} spike_decoder=false"
    )
    print(
        "PASS: P08.3.5c P06 compile "
        f"logical_cores={manifest['logical_core_count']} "
        f"resident_contexts={manifest['resident_context_count']} "
        f"physical_engines={manifest['physical_engine_count']} "
        f"neurons={manifest['neuron_count']} expanded={manifest['expanded_connections']}"
    )
    print(
        "PASS: P08.3.5c artifact identities "
        f"parameters={manifest['parameter_fingerprint']} "
        f"network={manifest['network_fingerprint']} "
        f"compiled={manifest['compiled_fingerprint']}"
    )
    print(
        "PASS: P08.3.5c test lock official_test_used=false "
        "test_examples_observed=0 classification_accuracy_evaluated=false"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
