"""Quantize a trained MNIST SNN into the project-native FPGA/core format."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from .config import (
    CURRENT_DECAY,
    FLOAT_THRESHOLD,
    INPUT_AXONS,
    OUTPUT_NEURONS,
    PRESENTATION_TICKS,
    REFRACTORY_TICKS,
    RESET_VOLTAGE,
    VOLTAGE_DECAY,
)

STATE_MAX = (1 << 23) - 1
WEIGHT_ALIGNMENT = 64
MAX_MANTISSA_MAGNITUDE = 255


@dataclass(frozen=True, slots=True)
class QuantizationResult:
    mantissas: np.ndarray
    state_scale: float
    threshold: int
    max_abs_weight_error: float
    rmse_weight_error: float
    nonzero_synapses: int
    saturation_safe_bound: float


def _round_half_away_from_zero(values: np.ndarray | float) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    rounded = np.floor(np.abs(array) + 0.5)
    return np.copysign(rounded, array).astype(np.int64)


def quantize_float_weights(
    weights: np.ndarray,
    *,
    threshold: float = FLOAT_THRESHOLD,
    state_headroom: float = 0.90,
) -> QuantizationResult:
    """Map float weights to exponent-0 signed mantissas and scaled state units."""

    matrix = np.asarray(weights, dtype=np.float64)
    expected = (INPUT_AXONS, OUTPUT_NEURONS)
    if matrix.shape != expected:
        raise ValueError(f"weights must have shape {expected}; got {matrix.shape}")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("weights must be finite")
    if threshold <= 0:
        raise ValueError("threshold must be positive")
    if not 0 < state_headroom <= 1:
        raise ValueError("state_headroom must be in (0, 1]")

    max_abs = float(np.max(np.abs(matrix)))
    if max_abs == 0.0:
        raise ValueError("cannot quantize an all-zero network")

    mantissa_scale_limit = MAX_MANTISSA_MAGNITUDE / max_abs
    max_l1 = float(np.max(np.sum(np.abs(matrix), axis=0)))
    safe_state_scale = (STATE_MAX * state_headroom) / (PRESENTATION_TICKS * max_l1)
    safe_mantissa_scale = safe_state_scale / WEIGHT_ALIGNMENT
    threshold_scale_limit = (STATE_MAX * state_headroom) / (
        threshold * WEIGHT_ALIGNMENT
    )
    mantissa_scale = min(
        mantissa_scale_limit,
        safe_mantissa_scale,
        threshold_scale_limit,
    )
    if mantissa_scale <= 0:
        raise ValueError("no positive quantization scale is available")

    mantissas = _round_half_away_from_zero(matrix * mantissa_scale)
    mantissas = np.clip(
        mantissas,
        -MAX_MANTISSA_MAGNITUDE,
        MAX_MANTISSA_MAGNITUDE,
    ).astype(np.int16)
    state_scale = mantissa_scale * WEIGHT_ALIGNMENT
    threshold_int = int(_round_half_away_from_zero(threshold * state_scale))
    if not 0 < threshold_int <= STATE_MAX:
        raise ValueError("quantized threshold is outside signed-24-bit range")

    reconstructed = mantissas.astype(np.float64) / mantissa_scale
    error = reconstructed - matrix
    conservative_bound = state_scale * PRESENTATION_TICKS * max_l1
    return QuantizationResult(
        mantissas=mantissas,
        state_scale=state_scale,
        threshold=threshold_int,
        max_abs_weight_error=float(np.max(np.abs(error))),
        rmse_weight_error=float(np.sqrt(np.mean(np.square(error)))),
        nonzero_synapses=int(np.count_nonzero(mantissas)),
        saturation_safe_bound=conservative_bound,
    )


def write_deployment(
    checkpoint_path: str | Path,
    output_dir: str | Path,
) -> Path:
    """Write project-native neuron configuration and frozen M08 weight images."""

    from neuromorphic_twin import (
        FrozenWeightStorage,
        NeuronConfig,
        Synapse,
        WeightFormat,
        WeightSignMode,
        freeze_encoded_synapses,
        write_weight_storage_image,
    )

    checkpoint = np.load(checkpoint_path)
    weights = np.asarray(checkpoint["weights"], dtype=np.float64)
    threshold_float = float(checkpoint.get("threshold", FLOAT_THRESHOLD))
    quantized = quantize_float_weights(weights, threshold=threshold_float)

    positive_format = WeightFormat(
        exponent=0,
        num_weight_bits=8,
        sign_mode=WeightSignMode.EXCITATORY,
    )
    negative_format = WeightFormat(
        exponent=0,
        num_weight_bits=8,
        sign_mode=WeightSignMode.INHIBITORY,
    )
    synapses = []
    for axon_id in range(INPUT_AXONS):
        for neuron_id in range(OUTPUT_NEURONS):
            mantissa = int(quantized.mantissas[axon_id, neuron_id])
            if mantissa == 0:
                continue
            fmt = positive_format if mantissa > 0 else negative_format
            synapses.append(
                Synapse.encoded(
                    axon_id=axon_id,
                    target_neuron=neuron_id,
                    mantissa=mantissa,
                    weight_format=fmt,
                )
            )

    storage = freeze_encoded_synapses(synapses)
    if storage.axon_count < INPUT_AXONS:
        missing = INPUT_AXONS - storage.axon_count
        storage = FrozenWeightStorage(
            format_words=storage.format_words,
            synapse_words=storage.synapse_words,
            axon_row_pointers=(
                storage.axon_row_pointers
                + (storage.synapse_count,) * missing
            ),
        )

    if storage.synapse_count > 4096:
        raise ValueError("deployment exceeds the physical 4096-synapse limit")
    if storage.axon_count != INPUT_AXONS:
        raise AssertionError("deployment must expose exactly 400 axon rows")

    neuron_configs = [
        NeuronConfig(
            current_decay=CURRENT_DECAY,
            voltage_decay=VOLTAGE_DECAY,
            threshold=quantized.threshold,
            bias=0,
            reset_voltage=RESET_VOLTAGE,
            refractory_ticks=REFRACTORY_TICKS,
        )
        for _ in range(OUTPUT_NEURONS)
    ]

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    weight_dir = output / "weight_image"
    write_weight_storage_image(storage, weight_dir)

    manifest = output / "deployment.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": "neuromorphic-twin-mnist-deployment-v1",
                "architecture": {
                    "source_image": [28, 28],
                    "center_crop": [20, 20],
                    "input_axons": INPUT_AXONS,
                    "output_neurons": OUTPUT_NEURONS,
                    "presentation_ticks": PRESENTATION_TICKS,
                    "routes": 0,
                },
                "decoder": "argmax-output-spike-count-lowest-id-tie-break",
                "neuron_config": {
                    "current_decay": CURRENT_DECAY,
                    "voltage_decay": VOLTAGE_DECAY,
                    "threshold": quantized.threshold,
                    "bias": 0,
                    "reset_voltage": RESET_VOLTAGE,
                    "refractory_ticks": REFRACTORY_TICKS,
                },
                "quantization": {
                    "state_scale": quantized.state_scale,
                    "threshold_float": threshold_float,
                    "effective_weight_quantum": WEIGHT_ALIGNMENT,
                    "nonzero_synapses": quantized.nonzero_synapses,
                    "max_abs_weight_error": quantized.max_abs_weight_error,
                    "rmse_weight_error": quantized.rmse_weight_error,
                    "conservative_abs_voltage_bound": quantized.saturation_safe_bound,
                    "state_max": STATE_MAX,
                },
                "weight_storage": "weight_image/weight_storage.json",
                "neuron_configs": [asdict(config) for config in neuron_configs],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest
