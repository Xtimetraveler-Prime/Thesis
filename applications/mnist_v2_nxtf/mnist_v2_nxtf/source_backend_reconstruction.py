"""P08.3.5b source-recovered NxTF/SNN-Toolbox conversion semantics.

This module reconstructs the public Intel Loihi backend normalization path before
another converted-SNN accuracy measurement is allowed.  It intentionally does
not consume the official MNIST test split.

Recovered public backend behavior used here:

* frame input is injected as an 8-bit bias current into an input spiking layer;
* parameter normalization uses the full parameter distribution by default;
* layer thresholds are calibrated from the 99.999th percentile of nonzero dV/dt;
* the calibrated dV/dt is multiplied by the configured desired threshold/input
  ratio before conversion to a threshold mantissa/exponent pair;
* each layer has its own parameter scale and threshold;
* the previous layer slope rescales the next layer bias before quantization; and
* a softmax output layer is quantized but skips ordinary spiking-threshold
  normalization in the historical backend.

The public backend relies on NxSDK/NxTF for the final hardware representation.
The code below therefore reproduces the exposed integer-normalization algorithm
and uses the accepted FPGA-v2 hard-reset primitive only for an activity preflight.
It does not claim bit-level equivalence to proprietary Loihi microcode.
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

from .accepted_ann import (
    ACCEPTED_ANN_CHECKPOINT_SHA256,
    ACCEPTED_ANN_WEIGHTS_FINGERPRINT,
    validate_accepted_checkpoint,
)
from .policy import CONVERSION_POLICY, OFFICIAL_TEST_POLICY
from .training import prepare_full_training_arrays

SOURCE_BACKEND_SCHEMA = "p08-nxtf-source-backend-reconstruction-v1"
SOURCE_BACKEND_MANIFEST = "source_backend_manifest.json"
SOURCE_BACKEND_PARAMETERS = "source_backend_parameters.npz"
ACTIVITY_DIAGNOSTIC_EXAMPLES = 100
SOURCE_PARAM_PERCENTILE = 100.0
SOURCE_ACTIVATION_PERCENTILE = 99.999
SOURCE_WEIGHT_MAX = 2**8 - 1
SOURCE_BIAS_MAX = 2**12 - 1
SOURCE_WEIGHT_MIN = -(2**8)
SOURCE_BIAS_MIN = -(2**12)
SOURCE_THRESHOLD_MANT_MAX = 2**8
SOURCE_THRESHOLD_EXP_MAX = 7
SOURCE_INPUT_SCALE = 255


@dataclass(frozen=True, slots=True)
class LayerNormalization:
    name: str
    parameter_scale: float
    previous_slope: float
    slope: float | None
    threshold_mantissa: int | None
    threshold_exponent: int | None
    threshold: int | None
    dvdt_percentile: float | None
    float_weight_min: float
    float_weight_max: float
    scaled_bias_min: float
    scaled_bias_max: float
    integer_weight_min: int
    integer_weight_max: int
    integer_bias_min: int
    integer_bias_max: int
    weight_clipped: int
    bias_clipped: int
    softmax_readout: bool


def _json_fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def source_to_mantexp(value: float, mantissa_max: int, exponent_max: int) -> tuple[int, int]:
    """Public NxTF backend ``to_mantexp`` rule."""

    if value < 0 or not np.isfinite(value):
        raise ValueError("threshold candidate must be finite and nonnegative")
    if mantissa_max <= 0 or exponent_max < 0:
        raise ValueError("invalid mantissa/exponent bounds")
    ratio = max(abs(float(value)) / float(mantissa_max), 1.0)
    exponent = int(np.ceil(np.log2(ratio)))
    if exponent > exponent_max:
        raise OverflowError("threshold exponent exceeds recovered NxTF bound")
    mantissa = int(np.rint(float(value) / float(2**exponent)))
    if abs(mantissa) > mantissa_max:
        raise OverflowError("threshold mantissa exceeds recovered NxTF bound")
    return mantissa, exponent


def source_parameter_scale(weights: np.ndarray, biases: np.ndarray) -> float:
    """Recovered NxTF backend parameter-scale calculation at percentile 100."""

    w = np.asarray(weights, dtype=np.float64)
    b = np.asarray(biases, dtype=np.float64)
    weight_norm = float(np.percentile(np.abs(w).ravel(), SOURCE_PARAM_PERCENTILE))
    if not np.isfinite(weight_norm) or weight_norm <= 0.0:
        raise ValueError("layer weight norm must be positive and finite")
    scale_ratio = float(
        np.percentile(np.abs(b) / weight_norm, SOURCE_PARAM_PERCENTILE)
    ) if b.size else 0.0
    if scale_ratio > 0.0:
        return float(min(SOURCE_WEIGHT_MAX, SOURCE_BIAS_MAX / scale_ratio) / weight_norm)
    return float(SOURCE_WEIGHT_MAX / weight_norm)


def source_to_int(value: np.ndarray, scale: float, num_bits: int) -> tuple[np.ndarray, int]:
    """Recovered NxTF backend integer conversion plus an explicit clip count."""

    raw = np.rint(np.asarray(value, dtype=np.float64) * float(scale)).astype(np.int64)
    low = -(2**num_bits)
    high = 2**num_bits - 1
    clipped = int(np.count_nonzero((raw < low) | (raw > high)))
    return np.clip(raw, low, high).astype(np.int32), clipped


def _activation_threshold(dvdt: np.ndarray) -> tuple[float, int, int, int]:
    values = np.asarray(dvdt, dtype=np.float64)
    nonzero = values[np.nonzero(values)]
    percentile = (
        float(np.percentile(nonzero, SOURCE_ACTIVATION_PERCENTILE))
        if nonzero.size
        else 1.0
    )
    target = percentile * float(CONVERSION_POLICY.desired_threshold_to_input_ratio)
    mantissa, exponent = source_to_mantexp(
        target, SOURCE_THRESHOLD_MANT_MAX, SOURCE_THRESHOLD_EXP_MAX
    )
    threshold = int(mantissa * (2**exponent))
    if threshold <= 0:
        raise ValueError("calibrated threshold must be positive")
    return percentile, mantissa, exponent, threshold


def _conv_relu_batches(
    inputs: np.ndarray,
    kernel: np.ndarray,
    bias: np.ndarray,
    stride: int,
    *,
    batch_size: int = 256,
) -> np.ndarray:
    try:
        import tensorflow as tf
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("TensorFlow is required for P08.3.5b normalization") from exc

    k = tf.constant(np.asarray(kernel, dtype=np.float32))
    b = tf.constant(np.asarray(bias, dtype=np.float32))
    outputs: list[np.ndarray] = []
    for start in range(0, len(inputs), batch_size):
        x = tf.constant(inputs[start : start + batch_size], dtype=tf.float32)
        y = tf.nn.conv2d(x, k, strides=[1, stride, stride, 1], padding="VALID")
        y = tf.nn.bias_add(y, b)
        y = tf.nn.relu(y)
        outputs.append(np.asarray(y.numpy(), dtype=np.float32))
    return np.concatenate(outputs, axis=0)


def reconstruct_source_backend(
    checkpoint_path: str | Path,
    training_manifest_path: str | Path,
    output_dir: str | Path,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Reconstruct public NxTF normalization without observing SNN accuracy."""

    if CONVERSION_POLICY.desired_threshold_to_input_ratio != 8:
        raise AssertionError("P08 hard-reset DThIR must remain 8")
    if not CONVERSION_POLICY.threshold_normalization:
        raise AssertionError("P08 source recovery requires threshold normalization enabled")

    model, _ = validate_accepted_checkpoint(checkpoint_path, training_manifest_path)
    arrays = prepare_full_training_arrays()
    calibration = np.asarray(arrays.x_train[::10], dtype=np.float32)
    if calibration.shape != (5500, 28, 28, 1):
        raise AssertionError(f"unexpected calibration shape {calibration.shape}")

    # Public NxTF backend normalizes the supplied normalization corpus once more
    # and maps frame values into an unsigned 8-bit input bias domain.
    global_max = float(np.max(calibration))
    if global_max <= 0.0:
        raise ValueError("calibration corpus has no positive input")
    x = calibration / global_max
    input_dvdt = x.astype(np.float64) * SOURCE_INPUT_SCALE
    input_percentile, input_mantissa, input_exponent, input_threshold = _activation_threshold(
        input_dvdt
    )
    input_slope = float(SOURCE_INPUT_SCALE / input_threshold)
    spikerates = np.minimum(input_dvdt / input_threshold, 1.0).astype(np.float32)

    parameter_arrays: dict[str, np.ndarray] = {
        "input_threshold": np.asarray([input_threshold], dtype=np.int32),
    }
    layer_reports: list[LayerNormalization] = []
    prev_slope = input_slope
    strides = (2, 1, 2, 1)

    for index in range(1, 5):
        layer = model.get_layer(f"conv{index}")
        weights, biases = layer.get_weights()
        weights = np.asarray(weights, dtype=np.float64)
        biases = np.asarray(biases, dtype=np.float64) * prev_slope
        param_scale = source_parameter_scale(weights, biases)
        q_weights, weight_clipped = source_to_int(weights, param_scale, 8)
        q_biases, bias_clipped = source_to_int(biases, param_scale, 12)
        if weight_clipped or bias_clipped:
            raise OverflowError(
                f"source normalization unexpectedly clipped conv{index}: "
                f"weights={weight_clipped} biases={bias_clipped}"
            )
        parameter_arrays[f"conv{index}_kernel_integer"] = q_weights.astype(np.int16)
        parameter_arrays[f"conv{index}_bias_integer"] = q_biases.astype(np.int16)

        is_softmax = index == 4
        if is_softmax:
            layer_reports.append(
                LayerNormalization(
                    name=f"conv{index}",
                    parameter_scale=param_scale,
                    previous_slope=prev_slope,
                    slope=None,
                    threshold_mantissa=None,
                    threshold_exponent=None,
                    threshold=None,
                    dvdt_percentile=None,
                    float_weight_min=float(np.min(weights)),
                    float_weight_max=float(np.max(weights)),
                    scaled_bias_min=float(np.min(biases)),
                    scaled_bias_max=float(np.max(biases)),
                    integer_weight_min=int(np.min(q_weights)),
                    integer_weight_max=int(np.max(q_weights)),
                    integer_bias_min=int(np.min(q_biases)),
                    integer_bias_max=int(np.max(q_biases)),
                    weight_clipped=weight_clipped,
                    bias_clipped=bias_clipped,
                    softmax_readout=True,
                )
            )
            break

        dvdt = _conv_relu_batches(spikerates, q_weights, q_biases, strides[index - 1])
        percentile, mantissa, exponent, threshold = _activation_threshold(dvdt)
        slope = float(param_scale * prev_slope / threshold)
        spikerates = np.minimum(dvdt / threshold, 1.0).astype(np.float32)
        parameter_arrays[f"conv{index}_threshold"] = np.asarray([threshold], dtype=np.int32)
        layer_reports.append(
            LayerNormalization(
                name=f"conv{index}",
                parameter_scale=param_scale,
                previous_slope=prev_slope,
                slope=slope,
                threshold_mantissa=mantissa,
                threshold_exponent=exponent,
                threshold=threshold,
                dvdt_percentile=percentile,
                float_weight_min=float(np.min(weights)),
                float_weight_max=float(np.max(weights)),
                scaled_bias_min=float(np.min(biases)),
                scaled_bias_max=float(np.max(biases)),
                integer_weight_min=int(np.min(q_weights)),
                integer_weight_max=int(np.max(q_weights)),
                integer_bias_min=int(np.min(q_biases)),
                integer_bias_max=int(np.max(q_biases)),
                weight_clipped=weight_clipped,
                bias_clipped=bias_clipped,
                softmax_readout=False,
            )
        )
        prev_slope = slope

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    parameter_path = output / SOURCE_BACKEND_PARAMETERS
    np.savez_compressed(parameter_path, **parameter_arrays)

    manifest: dict[str, Any] = {
        "schema": SOURCE_BACKEND_SCHEMA,
        "status": "P08_3_5B_SOURCE_RECOVERY_PREFLIGHT_CANDIDATE",
        "official_test_policy": OFFICIAL_TEST_POLICY,
        "official_test_used": False,
        "test_examples_observed": 0,
        "accepted_ann_checkpoint_sha256": ACCEPTED_ANN_CHECKPOINT_SHA256,
        "accepted_ann_weights_fingerprint": ACCEPTED_ANN_WEIGHTS_FINGERPRINT,
        "calibration_examples": 5500,
        "calibration_source": "frozen_55k_training_remainder_every_10th",
        "param_percentile": SOURCE_PARAM_PERCENTILE,
        "activation_percentile": SOURCE_ACTIVATION_PERCENTILE,
        "desired_threshold_to_input_ratio": CONVERSION_POLICY.desired_threshold_to_input_ratio,
        "input_mode": "NxTF_BIAS_FRAME_RECONSTRUCTION",
        "input_scale": SOURCE_INPUT_SCALE,
        "input_threshold": input_threshold,
        "input_threshold_mantissa": input_mantissa,
        "input_threshold_exponent": input_exponent,
        "input_dvdt_percentile": input_percentile,
        "input_slope": input_slope,
        "hidden_thresholds_are_per_layer": True,
        "softmax_output_uses_ordinary_spike_threshold": False,
        "normalization_origin": "RECOVERED_PUBLIC_INTEL_NXTF_BACKEND",
        "fpga_execution_adaptation": "hard_reset_project_profile",
        "layers": [asdict(report) for report in layer_reports],
    }
    manifest["manifest_fingerprint"] = _json_fingerprint(manifest)
    (output / SOURCE_BACKEND_MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return parameter_arrays, manifest


def _build_activity_simulator(parameters: dict[str, np.ndarray], timesteps: int):
    try:
        import tensorflow as tf
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("TensorFlow is required for P08.3.5b activity preflight") from exc

    input_threshold = int(parameters["input_threshold"][0])
    hidden_thresholds = [
        int(parameters[f"conv{i}_threshold"][0]) for i in range(1, 4)
    ]
    weights = [
        tf.constant(parameters[f"conv{i}_kernel_integer"].astype(np.float32))
        for i in range(1, 5)
    ]
    biases = [
        tf.constant(parameters[f"conv{i}_bias_integer"].astype(np.int32))
        for i in range(1, 5)
    ]

    @tf.function(
        input_signature=[tf.TensorSpec(shape=[None, 28, 28, 1], dtype=tf.int32)],
        reduce_retracing=True,
    )
    def simulate(pixel_bias):
        batch = tf.shape(pixel_bias)[0]
        vin = tf.zeros_like(pixel_bias, dtype=tf.int32)
        v1 = tf.zeros([batch, 12, 12, 14], dtype=tf.int32)
        v2 = tf.zeros([batch, 10, 10, 20], dtype=tf.int32)
        v3 = tf.zeros([batch, 4, 4, 12], dtype=tf.int32)
        v4 = tf.zeros([batch, 1, 1, 10], dtype=tf.int32)
        p0 = tf.zeros_like(pixel_bias, dtype=tf.bool)
        p1 = tf.zeros_like(v1, dtype=tf.bool)
        p2 = tf.zeros_like(v2, dtype=tf.bool)
        p3 = tf.zeros_like(v3, dtype=tf.bool)
        totals = tf.zeros([4], dtype=tf.int64)
        active0 = tf.zeros([batch], dtype=tf.bool)
        active1 = tf.zeros([batch], dtype=tf.bool)
        active2 = tf.zeros([batch], dtype=tf.bool)
        active3 = tf.zeros([batch], dtype=tf.bool)
        first_ticks = tf.fill([4], tf.constant(-1, dtype=tf.int32))
        max_candidates = tf.fill([4], tf.constant(-(2**31), dtype=tf.int32))

        for tick in tf.range(timesteps):
            cin = vin + pixel_bias
            sin = cin > input_threshold
            vin = tf.where(sin, tf.zeros_like(cin), cin)

            syn1 = tf.cast(tf.nn.conv2d(tf.cast(p0, tf.float32), weights[0], [1, 2, 2, 1], "VALID"), tf.int32)
            syn2 = tf.cast(tf.nn.conv2d(tf.cast(p1, tf.float32), weights[1], [1, 1, 1, 1], "VALID"), tf.int32)
            syn3 = tf.cast(tf.nn.conv2d(tf.cast(p2, tf.float32), weights[2], [1, 2, 2, 1], "VALID"), tf.int32)
            syn4 = tf.cast(tf.nn.conv2d(tf.cast(p3, tf.float32), weights[3], [1, 1, 1, 1], "VALID"), tf.int32)

            c1 = v1 + syn1 + biases[0]
            c2 = v2 + syn2 + biases[1]
            c3 = v3 + syn3 + biases[2]
            s1 = c1 > hidden_thresholds[0]
            s2 = c2 > hidden_thresholds[1]
            s3 = c3 > hidden_thresholds[2]
            v1 = tf.where(s1, tf.zeros_like(c1), c1)
            v2 = tf.where(s2, tf.zeros_like(c2), c2)
            v3 = tf.where(s3, tf.zeros_like(c3), c3)

            # Recovered NxTF softmax path does not use the normal spiking
            # threshold. Accumulate its affine membrane evidence instead.
            c4 = v4 + syn4 + biases[3]
            v4 = c4

            tick_counts = tf.stack([
                tf.reduce_sum(tf.cast(sin, tf.int64)),
                tf.reduce_sum(tf.cast(s1, tf.int64)),
                tf.reduce_sum(tf.cast(s2, tf.int64)),
                tf.reduce_sum(tf.cast(s3, tf.int64)),
            ])
            totals += tick_counts
            first_ticks = tf.where(
                tf.logical_and(first_ticks < 0, tick_counts > 0),
                tf.fill([4], tf.cast(tick, tf.int32)),
                first_ticks,
            )
            max_candidates = tf.maximum(
                max_candidates,
                tf.stack([
                    tf.reduce_max(cin),
                    tf.reduce_max(c1),
                    tf.reduce_max(c2),
                    tf.reduce_max(c3),
                ]),
            )
            active0 = tf.logical_or(active0, tf.reduce_any(sin, axis=[1, 2, 3]))
            active1 = tf.logical_or(active1, tf.reduce_any(s1, axis=[1, 2, 3]))
            active2 = tf.logical_or(active2, tf.reduce_any(s2, axis=[1, 2, 3]))
            active3 = tf.logical_or(active3, tf.reduce_any(s3, axis=[1, 2, 3]))
            p0, p1, p2, p3 = sin, s1, s2, s3

        active = tf.stack([
            tf.reduce_sum(tf.cast(active0, tf.int32)),
            tf.reduce_sum(tf.cast(active1, tf.int32)),
            tf.reduce_sum(tf.cast(active2, tf.int32)),
            tf.reduce_sum(tf.cast(active3, tf.int32)),
        ])
        evidence = tf.reshape(v4, [batch, 10])
        return totals, active, first_ticks, max_candidates, evidence

    return simulate


def run_source_semantics_preflight(
    checkpoint_path: str | Path,
    training_manifest_path: str | Path,
    output_dir: str | Path,
    *,
    examples: int = ACTIVITY_DIAGNOSTIC_EXAMPLES,
) -> dict[str, Any]:
    if examples <= 0 or examples > 5000:
        raise ValueError("diagnostic examples must be in 1..5000")
    parameters, manifest = reconstruct_source_backend(
        checkpoint_path, training_manifest_path, output_dir
    )
    arrays = prepare_full_training_arrays()
    images = np.asarray(arrays.x_validation[:examples], dtype=np.float32)
    scale_max = float(np.max(images))
    if scale_max <= 0:
        raise ValueError("diagnostic images contain no positive pixels")
    pixel_bias = (images / scale_max * SOURCE_INPUT_SCALE).astype(np.int32)
    simulator = _build_activity_simulator(parameters, CONVERSION_POLICY.primary_timesteps)
    totals_t, active_t, first_ticks_t, max_candidates_t, evidence_t = simulator(pixel_bias)
    totals = np.asarray(totals_t.numpy(), dtype=np.int64)
    active = np.asarray(active_t.numpy(), dtype=np.int64)
    first_ticks = np.asarray(first_ticks_t.numpy(), dtype=np.int64)
    max_candidates = np.asarray(max_candidates_t.numpy(), dtype=np.int64)
    evidence = np.asarray(evidence_t.numpy(), dtype=np.int64)

    if np.any(totals <= 0):
        dead = ("input", "conv1", "conv2", "conv3")[int(np.flatnonzero(totals <= 0)[0])]
    else:
        dead = None

    evidence_nonzero_examples = int(np.count_nonzero(np.any(evidence != 0, axis=1)))
    evidence_distinct_examples = int(
        np.count_nonzero(np.max(evidence, axis=1) != np.min(evidence, axis=1))
    )
    activity = {
        "examples": examples,
        "timesteps": CONVERSION_POLICY.primary_timesteps,
        "input_spikes": int(totals[0]),
        "conv1_spikes": int(totals[1]),
        "conv2_spikes": int(totals[2]),
        "conv3_spikes": int(totals[3]),
        "input_active_examples": int(active[0]),
        "conv1_active_examples": int(active[1]),
        "conv2_active_examples": int(active[2]),
        "conv3_active_examples": int(active[3]),
        "first_spike_ticks": [int(x) for x in first_ticks],
        "max_candidate_values": [int(x) for x in max_candidates],
        "first_dead_stage": dead,
        "softmax_evidence_nonzero_examples": evidence_nonzero_examples,
        "softmax_evidence_distinct_examples": evidence_distinct_examples,
        "softmax_evidence_min": int(np.min(evidence)),
        "softmax_evidence_max": int(np.max(evidence)),
        "classification_accuracy_evaluated": False,
    }
    manifest["activity_preflight"] = activity
    manifest["official_test_used"] = False
    manifest["test_examples_observed"] = 0
    manifest["manifest_fingerprint"] = _json_fingerprint(
        {k: v for k, v in manifest.items() if k != "manifest_fingerprint"}
    )
    output = Path(output_dir)
    (output / SOURCE_BACKEND_MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run P08.3.5b source-recovered NxTF semantics preflight"
    )
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--training-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--examples", type=int, default=ACTIVITY_DIAGNOSTIC_EXAMPLES)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    manifest = run_source_semantics_preflight(
        args.checkpoint,
        args.training_manifest,
        args.output_dir,
        examples=args.examples,
    )
    activity = manifest["activity_preflight"]
    print(
        "PASS: P08.3.5b source normalization "
        f"calibration={manifest['calibration_examples']} "
        f"activation_percentile={manifest['activation_percentile']} "
        f"dthir={manifest['desired_threshold_to_input_ratio']} "
        f"input_threshold={manifest['input_threshold']}"
    )
    for layer in manifest["layers"]:
        print(
            "PASS: P08.3.5b layer normalization "
            f"layer={layer['name']} scale={layer['parameter_scale']:.6g} "
            f"threshold={layer['threshold']} slope={layer['slope']} "
            f"W=[{layer['integer_weight_min']},{layer['integer_weight_max']}] "
            f"B=[{layer['integer_bias_min']},{layer['integer_bias_max']}] "
            f"softmax={str(layer['softmax_readout']).lower()} clipping=0"
        )
    print(
        "PASS: P08.3.5b hidden activity "
        f"input={activity['input_spikes']} conv1={activity['conv1_spikes']} "
        f"conv2={activity['conv2_spikes']} conv3={activity['conv3_spikes']} "
        f"first_dead_stage={activity['first_dead_stage']}"
    )
    print(
        "PASS: P08.3.5b softmax evidence "
        f"nonzero_examples={activity['softmax_evidence_nonzero_examples']} "
        f"distinct_examples={activity['softmax_evidence_distinct_examples']} "
        f"range=[{activity['softmax_evidence_min']},{activity['softmax_evidence_max']}]"
    )
    print(
        "PASS: P08.3.5b test lock official_test_used=false test_examples_observed=0 "
        "classification_accuracy_evaluated=false"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
