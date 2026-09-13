import numpy as np
import pytest

from mnist_app.config import INPUT_AXONS, OUTPUT_NEURONS
from mnist_app.export import STATE_MAX, quantize_float_weights


def test_quantization_shape_range_and_state_headroom():
    rng = np.random.default_rng(1234)
    weights = rng.normal(0.0, 0.05, size=(INPUT_AXONS, OUTPUT_NEURONS))
    result = quantize_float_weights(weights)
    assert result.mantissas.shape == weights.shape
    assert np.max(result.mantissas) <= 255
    assert np.min(result.mantissas) >= -255
    assert 0 < result.threshold <= STATE_MAX
    assert result.saturation_safe_bound <= STATE_MAX * 0.9000001
    assert result.nonzero_synapses <= INPUT_AXONS * OUTPUT_NEURONS


def test_quantization_rejects_bad_networks():
    with pytest.raises(ValueError):
        quantize_float_weights(np.zeros((INPUT_AXONS, OUTPUT_NEURONS)))
    with pytest.raises(ValueError):
        quantize_float_weights(np.zeros((10, 10)))
