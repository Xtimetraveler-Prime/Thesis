"""Validation-calibrated ANN-to-SNN conversion for the P08 candidate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from .config import WEIGHT_QUANT_MAX
from .data import normalize_images
from .topology import IntegerModel
from .training import require_tensorflow

LAYER_NAMES = ("stage0_conv1", "stage1_conv2", "stage2_dense8", "stage3_output10")
DEFAULT_ACTIVATION_PERCENTILE = 99.9
MAX_INTEGER_SCALE = 4096


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def activation_scales(
    model,
    calibration_images: np.ndarray,
    *,
    percentile: float = DEFAULT_ACTIVATION_PERCENTILE,
    batch_size: int = 128,
) -> tuple[float, float, float, float]:
    """Measure positive activation scales on validation-only calibration data."""

    tf = require_tensorflow()
    if not 90.0 <= float(percentile) <= 100.0:
        raise ValueError("activation percentile must be in [90, 100]")
    probe = tf.keras.Model(
        model.input,
        [model.get_layer(name).output for name in LAYER_NAMES],
    )
    images = normalize_images(calibration_images)[..., np.newaxis]
    outputs = probe.predict(images, batch_size=batch_size, verbose=0)
    scales: list[float] = []
    for name, values in zip(LAYER_NAMES, outputs):
        array = np.asarray(values, dtype=np.float32)
        positive = array[array > 0]
        if positive.size == 0:
            raise RuntimeError(f"calibration layer {name} produced no positive activations")
        scale = float(np.percentile(positive, percentile))
        if not np.isfinite(scale) or scale <= 0:
            raise RuntimeError(f"invalid calibration scale for {name}: {scale}")
        scales.append(scale)
    return tuple(scales)  # type: ignore[return-value]


def _quantize_normalized(weights: np.ndarray, normalized_gain: float) -> tuple[np.ndarray, int]:
    normalized = np.asarray(weights, dtype=np.float64) * float(normalized_gain)
    max_abs = float(np.max(np.abs(normalized)))
    if not np.isfinite(max_abs) or max_abs <= 0:
        raise RuntimeError("cannot quantize an all-zero or non-finite layer")
    scale = min(MAX_INTEGER_SCALE, int(np.floor(WEIGHT_QUANT_MAX / max_abs)))
    if scale < 1:
        raise RuntimeError(
            f"normalized layer weight {max_abs:.6g} exceeds signed integer conversion range"
        )
    quantized = np.rint(normalized * scale).astype(np.int16)
    if np.max(np.abs(quantized)) > WEIGHT_QUANT_MAX:
        raise RuntimeError("integer weight quantization exceeded the configured range")
    return quantized, int(scale)


def convert_model(
    model_path: str | Path,
    calibration_images: np.ndarray,
    output_dir: str | Path,
    *,
    percentile: float = DEFAULT_ACTIVATION_PERCENTILE,
) -> tuple[IntegerModel, dict]:
    """Convert a frozen ReLU ANN using layerwise activation normalization.

    If ``lambda_l`` is the validation activation scale of layer ``l``, each
    layer's floating weights are multiplied by ``lambda_(l-1)/lambda_l`` before
    integer quantization.  The integer quantization scale itself becomes that
    layer's spiking threshold, so firing rates approximate the normalized ANN
    activations without changing topology.
    """

    tf = require_tensorflow()
    model_file = Path(model_path)
    model = tf.keras.models.load_model(model_file)
    scales = activation_scales(model, calibration_images, percentile=percentile)

    float_weights = []
    for name in LAYER_NAMES:
        layer_weights = model.get_layer(name).get_weights()
        if len(layer_weights) != 1:
            raise RuntimeError(f"P08 layer {name} must contain weights and no bias")
        float_weights.append(np.asarray(layer_weights[0], dtype=np.float32))

    previous_activation_scale = 1.0
    integer_weights: list[np.ndarray] = []
    integer_thresholds: list[int] = []
    layer_metadata: list[dict] = []
    for name, weights, current_activation_scale in zip(LAYER_NAMES, float_weights, scales):
        gain = previous_activation_scale / current_activation_scale
        quantized, threshold = _quantize_normalized(weights, gain)
        integer_weights.append(quantized)
        integer_thresholds.append(threshold)
        layer_metadata.append(
            {
                "name": name,
                "activation_scale": current_activation_scale,
                "normalization_gain": gain,
                "integer_threshold": threshold,
                "float_weight_min": float(np.min(weights)),
                "float_weight_max": float(np.max(weights)),
                "integer_weight_min": int(np.min(quantized)),
                "integer_weight_max": int(np.max(quantized)),
                "integer_nonzero_weights": int(np.count_nonzero(quantized)),
                "integer_zero_weights": int(quantized.size - np.count_nonzero(quantized)),
            }
        )
        previous_activation_scale = current_activation_scale

    integer_model = IntegerModel(
        conv1=integer_weights[0],
        conv2=integer_weights[1],
        dense1=integer_weights[2],
        dense2=integer_weights[3],
        thresholds=tuple(integer_thresholds),  # type: ignore[arg-type]
    )

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    weights_file = output / "p08_integer_weights.npz"
    np.savez_compressed(
        weights_file,
        conv1=integer_model.conv1,
        conv2=integer_model.conv2,
        dense1=integer_model.dense1,
        dense2=integer_model.dense2,
        thresholds=np.asarray(integer_model.thresholds, dtype=np.int64),
    )
    metadata = {
        "schema": "p08-integer-conversion-v1",
        "source_model": str(model_file),
        "source_model_sha256": _sha256(model_file),
        "activation_percentile": float(percentile),
        "calibration_samples": int(len(calibration_images)),
        "calibration_source": "training-validation-split-only",
        "weight_quant_max": WEIGHT_QUANT_MAX,
        "layers": layer_metadata,
        "integer_nonzero_weights": integer_model.nonzero_weights,
        "weights_file": weights_file.name,
    }
    metadata_file = output / "p08_conversion.json"
    metadata_file.write_text(json.dumps(metadata, sort_keys=True, indent=2) + "\n")
    return integer_model, metadata


def load_integer_model(path: str | Path) -> IntegerModel:
    with np.load(path) as payload:
        return IntegerModel(
            conv1=np.asarray(payload["conv1"], dtype=np.int16),
            conv2=np.asarray(payload["conv2"], dtype=np.int16),
            dense1=np.asarray(payload["dense1"], dtype=np.int16),
            dense2=np.asarray(payload["dense2"], dtype=np.int16),
            thresholds=tuple(int(value) for value in payload["thresholds"]),
        )
