from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("tensorflow")

from mnist_v2_nxtf.activity_diagnostic import _build_diagnostic_simulator


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


def test_p08_3_5a_diagnostic_localizes_zero_network_activity():
    simulator = _build_diagnostic_simulator(_zero_parameters(), timesteps=4)
    encoded = np.zeros((2, 28, 28, 1), dtype=np.int32)
    encoded[:, 0, 0, 0] = 4

    result = simulator(encoded)
    input_total = int(result[0].numpy())
    layer_totals = np.asarray(result[1].numpy())
    active_examples = np.asarray(result[2].numpy())
    max_candidate = np.asarray(result[4].numpy())
    first_spike_tick = np.asarray(result[5].numpy())

    assert input_total == 8
    assert layer_totals.tolist() == [0, 0, 0, 0]
    assert active_examples.tolist() == [0, 0, 0, 0]
    assert max_candidate.tolist() == [0, 0, 0, 0]
    assert first_spike_tick.tolist() == [-1, -1, -1, -1]
