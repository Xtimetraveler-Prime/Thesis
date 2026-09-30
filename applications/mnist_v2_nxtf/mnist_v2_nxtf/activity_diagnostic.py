"""P08.3.5a validation-only activity diagnostic for the frozen converted SNN.

This module does not alter any conversion or execution parameter. It profiles
where spike activity disappears in the accepted P08.3.4 network by recording
per-layer spike totals, active-example counts, maximum synaptic input, and
maximum pre-threshold candidate voltage over a fixed validation-only sample.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from .accepted_conversion import validate_accepted_conversion
from .policy import CONVERSION_POLICY
from .training import prepare_full_training_arrays
from .validation_snn import rate_spike_counts

DIAGNOSTIC_SCHEMA = "p08-snn-activity-diagnostic-v1"
DIAGNOSTIC_FILENAME = "activity_diagnostic.json"
DIAGNOSTIC_EXAMPLES = 100


def _build_diagnostic_simulator(parameters: dict[str, np.ndarray], timesteps: int):
    try:
        import tensorflow as tf
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("TensorFlow is required for P08.3.5a diagnostics") from exc

    threshold = int(CONVERSION_POLICY.threshold_mantissa)
    weights = [
        tf.constant(parameters[f"conv{i}_kernel_integer"].astype(np.float32))
        for i in range(1, 5)
    ]
    biases = [
        tf.constant(parameters[f"conv{i}_bias_integer"].astype(np.int32))
        for i in range(1, 5)
    ]
    strides = (2, 1, 2, 1)

    @tf.function(
        input_signature=[tf.TensorSpec(shape=[None, 28, 28, 1], dtype=tf.int32)],
        reduce_retracing=True,
    )
    def simulate(encoded_counts):
        batch = tf.shape(encoded_counts)[0]
        v1 = tf.zeros([batch, 12, 12, 14], dtype=tf.int32)
        v2 = tf.zeros([batch, 10, 10, 20], dtype=tf.int32)
        v3 = tf.zeros([batch, 4, 4, 12], dtype=tf.int32)
        v4 = tf.zeros([batch, 1, 1, 10], dtype=tf.int32)
        p1 = tf.zeros_like(v1, dtype=tf.bool)
        p2 = tf.zeros_like(v2, dtype=tf.bool)
        p3 = tf.zeros_like(v3, dtype=tf.bool)

        input_total = tf.constant(0, dtype=tf.int64)
        layer_totals = [tf.constant(0, dtype=tf.int64) for _ in range(4)]
        active_masks = [tf.zeros([batch], dtype=tf.bool) for _ in range(4)]
        max_syn = [tf.constant(-(2**31), dtype=tf.int32) for _ in range(4)]
        max_candidate = [tf.constant(-(2**31), dtype=tf.int32) for _ in range(4)]
        first_spike_tick = [tf.constant(-1, dtype=tf.int32) for _ in range(4)]

        for tick in tf.range(timesteps):
            before = tf.math.floordiv(tick * encoded_counts, timesteps)
            after = tf.math.floordiv((tick + 1) * encoded_counts, timesteps)
            input_spikes_bool = after > before
            input_spikes = tf.cast(input_spikes_bool, tf.float32)
            input_total += tf.reduce_sum(tf.cast(input_spikes_bool, tf.int64))

            syn1 = tf.cast(tf.nn.conv2d(input_spikes, weights[0], [1, 2, 2, 1], "VALID"), tf.int32)
            syn2 = tf.cast(tf.nn.conv2d(tf.cast(p1, tf.float32), weights[1], [1, 1, 1, 1], "VALID"), tf.int32)
            syn3 = tf.cast(tf.nn.conv2d(tf.cast(p2, tf.float32), weights[2], [1, 2, 2, 1], "VALID"), tf.int32)
            syn4 = tf.cast(tf.nn.conv2d(tf.cast(p3, tf.float32), weights[3], [1, 1, 1, 1], "VALID"), tf.int32)
            syns = [syn1, syn2, syn3, syn4]

            c1 = v1 + syn1 + biases[0]
            c2 = v2 + syn2 + biases[1]
            c3 = v3 + syn3 + biases[2]
            c4 = v4 + syn4 + biases[3]
            candidates = [c1, c2, c3, c4]
            spikes = [c1 > threshold, c2 > threshold, c3 > threshold, c4 > threshold]

            for i in range(4):
                count = tf.reduce_sum(tf.cast(spikes[i], tf.int64))
                layer_totals[i] += count
                axes = tf.range(1, tf.rank(spikes[i]))
                active_masks[i] = tf.logical_or(active_masks[i], tf.reduce_any(spikes[i], axis=axes))
                max_syn[i] = tf.maximum(max_syn[i], tf.reduce_max(syns[i]))
                max_candidate[i] = tf.maximum(max_candidate[i], tf.reduce_max(candidates[i]))
                first_spike_tick[i] = tf.where(
                    tf.logical_and(first_spike_tick[i] < 0, count > 0),
                    tf.cast(tick, tf.int32),
                    first_spike_tick[i],
                )

            v1 = tf.where(spikes[0], tf.zeros_like(c1), c1)
            v2 = tf.where(spikes[1], tf.zeros_like(c2), c2)
            v3 = tf.where(spikes[2], tf.zeros_like(c3), c3)
            v4 = tf.where(spikes[3], tf.zeros_like(c4), c4)
            p1, p2, p3 = spikes[0], spikes[1], spikes[2]

        return (
            input_total,
            tf.stack(layer_totals),
            tf.stack([tf.reduce_sum(tf.cast(mask, tf.int32)) for mask in active_masks]),
            tf.stack(max_syn),
            tf.stack(max_candidate),
            tf.stack(first_spike_tick),
            tf.stack([tf.reduce_max(v1), tf.reduce_max(v2), tf.reduce_max(v3), tf.reduce_max(v4)]),
        )

    return simulate


def diagnose_activity(
    conversion_dir: str | Path,
    output_dir: str | Path,
    *,
    examples: int = DIAGNOSTIC_EXAMPLES,
) -> dict[str, Any]:
    if examples <= 0 or examples > 5000:
        raise ValueError("examples must be in 1..5000")
    if CONVERSION_POLICY.primary_timesteps != 100:
        raise AssertionError("P08.3.5a diagnostic assumes frozen 100-timestep horizon")

    parameters, manifest = validate_accepted_conversion(conversion_dir)
    arrays = prepare_full_training_arrays()
    images = arrays.x_validation[:examples]
    encoded = rate_spike_counts(images, CONVERSION_POLICY.primary_timesteps)
    simulator = _build_diagnostic_simulator(parameters, CONVERSION_POLICY.primary_timesteps)
    results = simulator(encoded)
    input_total = int(results[0].numpy())
    layer_totals = np.asarray(results[1].numpy(), dtype=np.int64)
    active_examples = np.asarray(results[2].numpy(), dtype=np.int64)
    max_syn = np.asarray(results[3].numpy(), dtype=np.int64)
    max_candidate = np.asarray(results[4].numpy(), dtype=np.int64)
    first_spike_tick = np.asarray(results[5].numpy(), dtype=np.int64)
    final_max_voltage = np.asarray(results[6].numpy(), dtype=np.int64)

    layers: list[dict[str, Any]] = []
    for index, name in enumerate(("conv1", "conv2", "conv3", "conv4")):
        layers.append(
            {
                "name": name,
                "total_spikes": int(layer_totals[index]),
                "active_examples": int(active_examples[index]),
                "max_synaptic_input": int(max_syn[index]),
                "max_candidate_voltage": int(max_candidate[index]),
                "first_spike_tick": int(first_spike_tick[index]),
                "final_max_voltage": int(final_max_voltage[index]),
                "threshold": int(CONVERSION_POLICY.threshold_mantissa),
            }
        )

    first_dead_layer = None
    for layer in layers:
        if layer["total_spikes"] == 0:
            first_dead_layer = layer["name"]
            break

    payload: dict[str, Any] = {
        "schema": DIAGNOSTIC_SCHEMA,
        "status": "DIAGNOSTIC_ONLY_NO_POLICY_CHANGE",
        "examples": examples,
        "timesteps": CONVERSION_POLICY.primary_timesteps,
        "input_total_spikes": input_total,
        "layers": layers,
        "first_dead_layer": first_dead_layer,
        "accepted_conversion_fingerprint": manifest["conversion_fingerprint"],
        "official_test_used": False,
        "test_examples_observed": 0,
        "conversion_or_execution_parameters_changed": False,
    }
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / DIAGNOSTIC_FILENAME).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Profile P08.3.5 SNN activity without changing policy")
    parser.add_argument("--conversion-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--examples", type=int, default=DIAGNOSTIC_EXAMPLES)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = diagnose_activity(args.conversion_dir, args.output_dir, examples=args.examples)
    print(
        "PASS: P08.3.5a diagnostic input "
        f"examples={payload['examples']} timesteps={payload['timesteps']} "
        f"input_spikes={payload['input_total_spikes']}"
    )
    for layer in payload["layers"]:
        print(
            "PASS: P08.3.5a layer activity "
            f"layer={layer['name']} spikes={layer['total_spikes']} "
            f"active_examples={layer['active_examples']} "
            f"max_syn={layer['max_synaptic_input']} "
            f"max_candidate={layer['max_candidate_voltage']} "
            f"threshold={layer['threshold']} first_spike_tick={layer['first_spike_tick']} "
            f"final_max_voltage={layer['final_max_voltage']}"
        )
    print(
        "PASS: P08.3.5a localization "
        f"first_dead_layer={payload['first_dead_layer']} policy_changed=false"
    )
    print("PASS: P08.3.5a test lock official_test_used=false test_examples_observed=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
