"""P08.3.4 source-bounded ANN-to-SNN conversion for the accepted checkpoint.

This module intentionally separates three stages:

1. Rueckauer-style data normalization of floating ANN parameters.
2. Project integer quantization into the accepted FPGA-v2 threshold/weight/bias
   arithmetic domain.
3. Construction and P06 compilation of the exact converted integer graph.

The official MNIST test split is not part of this module. Calibration uses only
the frozen 55k training remainder.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
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
    validate_accepted_checkpoint,
)
from .data import prepare_full_training_arrays if False else None
from .policy import ANN_POLICY, CONVERSION_POLICY, OFFICIAL_TEST_POLICY, validate_frozen_policy
from .reconstruction import OUTPUT_CLASSES, PROPOSED_FILTERS, PROPOSED_METRICS
from .structural import P06_STRUCTURAL_COMPARTMENTS_PER_CORE
from .training import prepare_full_training_arrays


CONVERSION_SCHEMA = "p08-ann-to-snn-conversion-v1"
CONVERSION_ARTIFACT_FILENAME = "converted_parameters.npz"
CONVERSION_MANIFEST_FILENAME = "conversion_manifest.json"
CONVERTED_NETWORK_FILENAME = "converted_network.json"
COMPILED_DEPLOYMENT_FILENAME = "compiled_deployment.json"
NORMALIZATION_PERCENTILE = 100.0
INTEGER_THRESHOLD_SCALE = CONVERSION_POLICY.threshold_mantissa


@dataclass(frozen=True, slots=True)
class ConvGeometry:
    name: str
    input_height: int
    input_width: int
    input_channels: int
    output_height: int
    output_width: int
    output_channels: int
    kernel: int
    stride: int


@dataclass(frozen=True, slots=True)
class LayerConversion:
    name: str
    lambda_previous: float
    lambda_current: float
    float_weight_min: float
    float_weight_max: float
    normalized_weight_min: float
    normalized_weight_max: float
    normalized_bias_min: float
    normalized_bias_max: float
    integer_weight_min: int
    integer_weight_max: int
    integer_bias_min: int
    integer_bias_max: int
    zero_integer_weights: int
    total_weights: int


@dataclass(frozen=True, slots=True)
class ConversionResult:
    output_dir: Path
    manifest_path: Path
    parameters_path: Path
    network_path: Path
    compiled_path: Path
    conversion_fingerprint: str
    network_fingerprint: str
    compiled_fingerprint: str
    logical_core_count: int


def conv_geometries() -> tuple[ConvGeometry, ...]:
    f1, f2, f3 = PROPOSED_FILTERS
    return (
        ConvGeometry("conv1", 28, 28, 1, 12, 12, f1, 5, 2),
        ConvGeometry("conv2", 12, 12, f1, 10, 10, f2, 3, 1),
        ConvGeometry("conv3", 10, 10, f2, 4, 4, f3, 3, 2),
        ConvGeometry("conv4", 4, 4, f3, 1, 1, OUTPUT_CLASSES, 4, 1),
    )


def _channel_population(layer: str, channel: int) -> str:
    return f"{layer}_c{channel:02d}"


def _spatial_index(y: int, x: int, width: int) -> int:
    return y * width + x


def _array_identity(array: np.ndarray) -> bytes:
    value = np.ascontiguousarray(array)
    header = json.dumps(
        {"shape": value.shape, "dtype": str(value.dtype)},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return header + b"\0" + value.tobytes(order="C")


def _arrays_fingerprint(arrays: dict[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    for name in sorted(arrays):
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(_array_identity(arrays[name]))
    return digest.hexdigest()


def _manifest_fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _extract_ann_parameters(model) -> tuple[tuple[np.ndarray, np.ndarray], ...]:
    result: list[tuple[np.ndarray, np.ndarray]] = []
    for geometry in conv_geometries():
        layer = model.get_layer(geometry.name)
        params = layer.get_weights()
        if len(params) != 2:
            raise ValueError(f"{geometry.name} must contain kernel and bias")
        kernel = np.asarray(params[0], dtype=np.float32)
        bias = np.asarray(params[1], dtype=np.float32)
        expected_kernel = (
            geometry.kernel,
            geometry.kernel,
            geometry.input_channels,
            geometry.output_channels,
        )
        if kernel.shape != expected_kernel:
            raise ValueError(
                f"{geometry.name} kernel shape {kernel.shape} != {expected_kernel}"
            )
        if bias.shape != (geometry.output_channels,):
            raise ValueError(f"{geometry.name} bias shape drifted: {bias.shape}")
        result.append((kernel, bias))
    return tuple(result)


def calibrate_activation_maxima(model, calibration_images: np.ndarray, *, batch_size: int = 128) -> tuple[float, ...]:
    """Return lambda_0..lambda_4 using max activation normalization.

    Hidden lambdas are measured from the ReLU outputs of conv1..conv3. The ANN's
    final softmax is not a spiking operation; for conversion, conv4 is evaluated
    as its affine transform followed by ReLU, matching SNN-Toolbox's standard
    softmax-to-rate/readout treatment.
    """

    try:
        import tensorflow as tf
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("TensorFlow is required for P08.3 conversion") from exc

    images = np.asarray(calibration_images, dtype=np.float32)
    if images.ndim != 4 or images.shape[1:] != (28, 28, 1):
        raise ValueError(f"calibration images must have shape (N,28,28,1); got {images.shape}")
    if not len(images):
        raise ValueError("calibration images cannot be empty")

    hidden_model = tf.keras.Model(
        model.inputs,
        [model.get_layer("conv1").output, model.get_layer("conv2").output, model.get_layer("conv3").output],
    )
    kernel4, bias4 = model.get_layer("conv4").get_weights()
    maxima = [float(np.max(images))]
    hidden_max = [0.0, 0.0, 0.0]
    output_max = 0.0

    for start in range(0, len(images), batch_size):
        batch = images[start : start + batch_size]
        hidden = hidden_model(batch, training=False)
        for index, activation in enumerate(hidden):
            hidden_max[index] = max(hidden_max[index], float(tf.reduce_max(activation).numpy()))
        conv3 = hidden[-1]
        logits = tf.nn.conv2d(conv3, kernel4, strides=[1, 1, 1, 1], padding="VALID")
        logits = tf.nn.bias_add(logits, bias4)
        relu_logits = tf.nn.relu(logits)
        output_max = max(output_max, float(tf.reduce_max(relu_logits).numpy()))

    maxima.extend(hidden_max)
    maxima.append(output_max)
    if len(maxima) != 5 or any((not np.isfinite(value) or value <= 0.0) for value in maxima):
        raise ValueError(f"invalid calibration activation maxima: {maxima}")
    return tuple(maxima)


def normalize_layer_parameters(
    kernel: np.ndarray,
    bias: np.ndarray,
    lambda_previous: float,
    lambda_current: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply Rueckauer data normalization W*lprev/lcur and b/lcur."""

    if lambda_previous <= 0.0 or lambda_current <= 0.0:
        raise ValueError("normalization lambdas must be positive")
    normalized_kernel = np.asarray(kernel, dtype=np.float64) * (
        float(lambda_previous) / float(lambda_current)
    )
    normalized_bias = np.asarray(bias, dtype=np.float64) / float(lambda_current)
    return normalized_kernel, normalized_bias


def quantize_normalized_parameters(
    normalized_kernel: np.ndarray,
    normalized_bias: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Map normalized threshold=1 parameters into FPGA-v2 threshold=512 units.

    No clipping is permitted. Overflow is an explicit conversion failure so the
    integer representation cannot silently change the accepted mathematical
    conversion.
    """

    scale = float(INTEGER_THRESHOLD_SCALE)
    q_kernel_64 = np.rint(np.asarray(normalized_kernel, dtype=np.float64) * scale).astype(np.int64)
    q_bias_64 = np.rint(np.asarray(normalized_bias, dtype=np.float64) * scale).astype(np.int64)

    if q_kernel_64.size and (
        int(q_kernel_64.min()) < CONVERSION_POLICY.signed_weight_min
        or int(q_kernel_64.max()) > CONVERSION_POLICY.signed_weight_max
    ):
        raise OverflowError(
            "P08.3 normalized weight does not fit the frozen signed 8-bit project range: "
            f"observed=[{int(q_kernel_64.min())},{int(q_kernel_64.max())}] "
            f"allowed=[{CONVERSION_POLICY.signed_weight_min},{CONVERSION_POLICY.signed_weight_max}]"
        )
    if q_bias_64.size and (
        int(q_bias_64.min()) < CONVERSION_POLICY.signed_bias_min
        or int(q_bias_64.max()) > CONVERSION_POLICY.signed_bias_max
    ):
        raise OverflowError(
            "P08.3 normalized bias does not fit the frozen signed 12-bit project range: "
            f"observed=[{int(q_bias_64.min())},{int(q_bias_64.max())}] "
            f"allowed=[{CONVERSION_POLICY.signed_bias_min},{CONVERSION_POLICY.signed_bias_max}]"
        )
    return q_kernel_64.astype(np.int16), q_bias_64.astype(np.int16)


def convert_parameter_arrays(
    ann_parameters: tuple[tuple[np.ndarray, np.ndarray], ...],
    lambdas: tuple[float, ...],
) -> tuple[dict[str, np.ndarray], tuple[LayerConversion, ...]]:
    if len(ann_parameters) != 4 or len(lambdas) != 5:
        raise ValueError("P08 conversion expects four convolution layers and lambda_0..lambda_4")

    arrays: dict[str, np.ndarray] = {}
    reports: list[LayerConversion] = []
    for index, ((kernel, bias), geometry) in enumerate(
        zip(ann_parameters, conv_geometries(), strict=True), start=1
    ):
        norm_kernel, norm_bias = normalize_layer_parameters(
            kernel,
            bias,
            lambdas[index - 1],
            lambdas[index],
        )
        q_kernel, q_bias = quantize_normalized_parameters(norm_kernel, norm_bias)
        arrays[f"{geometry.name}_kernel_normalized"] = norm_kernel.astype(np.float32)
        arrays[f"{geometry.name}_bias_normalized"] = norm_bias.astype(np.float32)
        arrays[f"{geometry.name}_kernel_integer"] = q_kernel
        arrays[f"{geometry.name}_bias_integer"] = q_bias
        reports.append(
            LayerConversion(
                name=geometry.name,
                lambda_previous=float(lambdas[index - 1]),
                lambda_current=float(lambdas[index]),
                float_weight_min=float(np.min(kernel)),
                float_weight_max=float(np.max(kernel)),
                normalized_weight_min=float(np.min(norm_kernel)),
                normalized_weight_max=float(np.max(norm_kernel)),
                normalized_bias_min=float(np.min(norm_bias)),
                normalized_bias_max=float(np.max(norm_bias)),
                integer_weight_min=int(np.min(q_kernel)),
                integer_weight_max=int(np.max(q_kernel)),
                integer_bias_min=int(np.min(q_bias)),
                integer_bias_max=int(np.max(q_bias)),
                zero_integer_weights=int(np.count_nonzero(q_kernel == 0)),
                total_weights=int(q_kernel.size),
            )
        )
    return arrays, tuple(reports)


def build_converted_network(arrays: dict[str, np.ndarray]) -> NetworkSpec:
    populations: list[PopulationSpec] = []
    projections: list[ProjectionSpec] = []
    input_projections: list[InputProjectionSpec] = []

    for stage_index, geometry in enumerate(conv_geometries(), start=1):
        q_kernel = np.asarray(arrays[f"{geometry.name}_kernel_integer"], dtype=np.int64)
        q_bias = np.asarray(arrays[f"{geometry.name}_bias_integer"], dtype=np.int64)
        spatial_size = geometry.output_height * geometry.output_width

        for output_channel in range(geometry.output_channels):
            populations.append(
                PopulationSpec(
                    name=_channel_population(geometry.name, output_channel),
                    size=spatial_size,
                    compartment=CompartmentConfig(
                        current_decay=CONVERSION_POLICY.current_decay,
                        voltage_decay=CONVERSION_POLICY.voltage_decay,
                        threshold=CONVERSION_POLICY.threshold_mantissa,
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
                        destination_index = _spatial_index(
                            output_y, output_x, geometry.output_width
                        )
                        for kernel_y in range(geometry.kernel):
                            input_y = output_y * geometry.stride + kernel_y
                            for kernel_x in range(geometry.kernel):
                                input_x = output_x * geometry.stride + kernel_x
                                source_index = _spatial_index(
                                    input_y, input_x, geometry.input_width
                                )
                                weight = int(
                                    q_kernel[
                                        kernel_y,
                                        kernel_x,
                                        input_channel,
                                        output_channel,
                                    ]
                                )
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
    expanded = sum(
        len(projection.connections)
        for projection in (*network.projections, *network.input_projections)
    )
    neurons = sum(population.size for population in network.populations)
    if expanded != PROPOSED_METRICS.expanded_connections:
        raise AssertionError(f"converted expanded connections drifted: {expanded}")
    if neurons != PROPOSED_METRICS.neuron_count:
        raise AssertionError(f"converted neuron count drifted: {neurons}")
    return network


def run_conversion(
    checkpoint_path: str | Path,
    training_manifest_path: str | Path,
    output_dir: str | Path,
) -> ConversionResult:
    validate_frozen_policy()
    model, training_manifest = validate_accepted_checkpoint(
        checkpoint_path,
        training_manifest_path,
    )

    training = prepare_full_training_arrays()
    calibration_images = training.x_train[:: CONVERSION_POLICY.calibration_stride]
    if len(calibration_images) != 5_500:
        raise AssertionError(f"calibration set size drifted: {len(calibration_images)}")

    lambdas = calibrate_activation_maxima(model, calibration_images)
    ann_parameters = _extract_ann_parameters(model)
    arrays, layer_reports = convert_parameter_arrays(ann_parameters, lambdas)
    conversion_fingerprint = _arrays_fingerprint(arrays)

    network = build_converted_network(arrays)
    compiled = compile_network(
        network,
        MappingOptions(compartments_per_core=P06_STRUCTURAL_COMPARTMENTS_PER_CORE),
    )
    logical_core_count = len(compiled.logical_deployment.core_configs)
    if logical_core_count < 5:
        raise AssertionError("converted graph cannot map below its five-core compartment lower bound")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    parameters_path = output / CONVERSION_ARTIFACT_FILENAME
    manifest_path = output / CONVERSION_MANIFEST_FILENAME
    network_path = output / CONVERTED_NETWORK_FILENAME
    compiled_path = output / COMPILED_DEPLOYMENT_FILENAME

    np.savez_compressed(parameters_path, **arrays)
    network.write_json(network_path)
    compiled.write_json(compiled_path)

    manifest: dict[str, Any] = {
        "schema": CONVERSION_SCHEMA,
        "status": "P08_3_4_CONVERTED_VALIDATION_PENDING",
        "accepted_ann_checkpoint_sha256": ACCEPTED_ANN_CHECKPOINT_SHA256,
        "accepted_ann_weights_fingerprint": ACCEPTED_ANN_WEIGHTS_FINGERPRINT,
        "accepted_ann_best_epoch": int(training_manifest["best_epoch"]),
        "accepted_ann_best_val_accuracy": float(training_manifest["best_val_accuracy"]),
        "official_test_policy": OFFICIAL_TEST_POLICY,
        "official_test_used": False,
        "test_examples_observed": 0,
        "calibration_source": CONVERSION_POLICY.calibration_source,
        "calibration_stride": CONVERSION_POLICY.calibration_stride,
        "calibration_examples": int(len(calibration_images)),
        "calibration_split_fingerprint": training.split_fingerprint,
        "calibration_dataset_fingerprint": training.dataset_fingerprint,
        "normalization_method": "Rueckauer-2017-data-normalization",
        "normalization_percentile": NORMALIZATION_PERCENTILE,
        "normalization_formula_weights": "W_l * lambda_(l-1) / lambda_l",
        "normalization_formula_bias": "b_l / lambda_l",
        "activation_lambdas": [float(value) for value in lambdas],
        "final_softmax_conversion": "conv4 affine output calibrated through ReLU; spike-count readout replaces softmax",
        "integer_quantization": "round(normalized_parameter * threshold_mantissa); reject overflow; no clipping",
        "integer_threshold_scale": INTEGER_THRESHOLD_SCALE,
        "weight_range": [
            CONVERSION_POLICY.signed_weight_min,
            CONVERSION_POLICY.signed_weight_max,
        ],
        "bias_range": [
            CONVERSION_POLICY.signed_bias_min,
            CONVERSION_POLICY.signed_bias_max,
        ],
        "reset_mode": CONVERSION_POLICY.reset_mode,
        "primary_timesteps": CONVERSION_POLICY.primary_timesteps,
        "decoder": CONVERSION_POLICY.decoder,
        "layers": [asdict(report) for report in layer_reports],
        "conversion_fingerprint": conversion_fingerprint,
        "converted_network_fingerprint": network.fingerprint,
        "compiled_deployment_fingerprint": compiled.fingerprint,
        "logical_core_count": logical_core_count,
        "resident_context_count": 3,
        "physical_engine_count": 1,
        "expanded_connections": PROPOSED_METRICS.expanded_connections,
        "neuron_count": PROPOSED_METRICS.neuron_count,
        "trainable_ann_parameters": PROPOSED_METRICS.trainable_parameters,
    }
    manifest_fingerprint = _manifest_fingerprint(manifest)
    manifest["manifest_fingerprint"] = manifest_fingerprint
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return ConversionResult(
        output_dir=output,
        manifest_path=manifest_path,
        parameters_path=parameters_path,
        network_path=network_path,
        compiled_path=compiled_path,
        conversion_fingerprint=conversion_fingerprint,
        network_fingerprint=network.fingerprint,
        compiled_fingerprint=compiled.fingerprint,
        logical_core_count=logical_core_count,
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert the accepted P08.3.3 ANN to a P08 SNN artifact")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--training-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_conversion(args.checkpoint, args.training_manifest, args.output_dir)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    layer_ranges = ",".join(
        f"{item['name']}:[{item['integer_weight_min']},{item['integer_weight_max']}]"
        for item in manifest["layers"]
    )
    print(
        "PASS: P08.3.4 converted accepted ANN "
        f"calibration_examples={manifest['calibration_examples']} "
        f"lambdas={manifest['activation_lambdas']}"
    )
    print(
        "PASS: P08.3.4 integer conversion "
        f"threshold={INTEGER_THRESHOLD_SCALE} weight_ranges={layer_ranges} "
        "overflow=0 clipping=0"
    )
    print(
        "PASS: P08.3.4 P06 compile "
        f"logical_cores={result.logical_core_count} "
        f"network={result.network_fingerprint} compiled={result.compiled_fingerprint}"
    )
    print(
        "PASS: P08.3.4 test lock official_test_used=false test_examples_observed=0 "
        f"conversion_fingerprint={result.conversion_fingerprint}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
