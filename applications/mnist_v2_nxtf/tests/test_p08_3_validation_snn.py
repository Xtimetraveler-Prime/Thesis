from __future__ import annotations

import numpy as np
import pytest

from loihi_twin_v2.compartment import CompartmentConfig, CompartmentState, step_compartment
from mnist_v2_nxtf.accepted_conversion import (
    ACCEPTED_COMPILED_FINGERPRINT,
    ACCEPTED_CONVERSION_FINGERPRINT,
    ACCEPTED_NETWORK_FINGERPRINT,
)
from mnist_v2_nxtf.policy import CONVERSION_POLICY
from mnist_v2_nxtf.validation_snn import (
    RATE_ENCODER,
    _build_tf_simulator,
    compartment_update,
    rate_spike_counts,
    rate_spikes_at_tick,
)


def test_p08_3_4_accepted_conversion_identity_is_frozen():
    assert ACCEPTED_CONVERSION_FINGERPRINT == (
        "686e801cf2459d66772a3517cfff0411746ce97d7a84fb45554ca3ee8345cb75"
    )
    assert ACCEPTED_NETWORK_FINGERPRINT == (
        "4f7dc2b2ecfd4db7c347fc8c846aed3ad5f03d57ceb48ed973530e77865bc211"
    )
    assert ACCEPTED_COMPILED_FINGERPRINT == (
        "1dc5191354566e9e40cdfe624ff6fc48528d1b78a91d2a16a4336d12b1a4296c"
    )


def test_rate_encoder_has_exact_count_and_zero_phase_bresenham_schedule():
    images = np.asarray([[[[0.0], [0.25], [0.5], [1.0]]]], dtype=np.float32)
    counts = rate_spike_counts(images, 8)
    assert counts.reshape(-1).tolist() == [0, 2, 4, 8]
    schedule = np.stack(
        [rate_spikes_at_tick(counts, tick, 8) for tick in range(8)], axis=0
    )
    assert np.sum(schedule, axis=0).reshape(-1).tolist() == [0, 2, 4, 8]
    assert RATE_ENCODER == "zero_phase_bresenham_exact_count"


def test_vectorized_compartment_update_matches_frozen_scalar_primitive():
    config = CompartmentConfig(
        current_decay=4096,
        voltage_decay=0,
        threshold=512,
        bias=3,
        reset_voltage=0,
        refractory_ticks=0,
    )
    voltages = np.asarray([0, 400, 500, -100], dtype=np.int64)
    inputs = np.asarray([20, 100, 9, -50], dtype=np.int64)
    next_voltage, spikes = compartment_update(voltages, inputs, 3, 512)
    for index, (voltage, delivered) in enumerate(zip(voltages, inputs, strict=True)):
        result = step_compartment(
            CompartmentState(voltage=int(voltage)),
            config,
            int(delivered),
        )
        assert int(next_voltage[index]) == result.state.voltage
        assert bool(spikes[index]) is result.spiked


def _zero_parameters() -> dict[str, np.ndarray]:
    return {
        "conv1_kernel_integer": np.zeros((5, 5, 1, 14), dtype=np.int16),
        "conv1_bias_integer": np.zeros((14,), dtype=np.int16),
        "conv2_kernel_integer": np.zeros((3, 3, 14, 20), dtype=np.int16),
        "conv2_bias_integer": np.zeros((20,), dtype=np.int16),
        "conv3_kernel_integer": np.zeros((3, 3, 20, 12), dtype=np.int16),
        "conv3_bias_integer": np.zeros((12,), dtype=np.int16),
        "conv4_kernel_integer": np.zeros((4, 4, 12, 10), dtype=np.int16),
        "conv4_bias_integer": np.zeros((10,), dtype=np.int16),
    }


def test_tensorflow_vectorized_pipeline_smoke_is_deterministic_and_quiet():
    pytest.importorskip("tensorflow")
    simulator = _build_tf_simulator(_zero_parameters(), timesteps=4)
    counts = np.full((2, 28, 28, 1), 4, dtype=np.int32)
    first = np.asarray(simulator(counts).numpy())
    second = np.asarray(simulator(counts).numpy())
    assert first.shape == (2, 10)
    assert np.array_equal(first, second)
    assert np.all(first == 0)
    assert CONVERSION_POLICY.threshold_mantissa == 512
