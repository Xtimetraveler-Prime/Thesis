import numpy as np
import pytest

from mnist_app.config import CROPPED_DENSE, NATIVE_SPARSE, OUTPUT_NEURONS
from mnist_app.export import STATE_MAX, quantize_float_weights


def test_cropped_dense_quantization_shape_range_and_headroom():
    rng = np.random.default_rng(1234)
    weights = rng.normal(
        0.0,
        0.05,
        size=(CROPPED_DENSE.input_axons, OUTPUT_NEURONS),
    )
    result = quantize_float_weights(weights, profile=CROPPED_DENSE)
    assert result.mantissas.shape == weights.shape
    assert np.max(result.mantissas) <= 255
    assert np.min(result.mantissas) >= -255
    assert 0 < result.threshold <= STATE_MAX
    assert result.saturation_safe_bound <= STATE_MAX * 0.9000001
    assert result.nonzero_synapses <= CROPPED_DENSE.max_synapses


def test_native_sparse_quantization_preserves_budget():
    rng = np.random.default_rng(5)
    weights = np.zeros((NATIVE_SPARSE.input_axons, OUTPUT_NEURONS))
    flat = weights.reshape(-1)
    flat[: NATIVE_SPARSE.max_synapses] = rng.normal(
        0.0,
        0.05,
        size=NATIVE_SPARSE.max_synapses,
    )
    result = quantize_float_weights(weights, profile=NATIVE_SPARSE)
    assert result.mantissas.shape == weights.shape
    assert result.nonzero_synapses <= NATIVE_SPARSE.max_synapses


def test_native_sparse_rejects_unpruned_dense_matrix():
    weights = np.ones((NATIVE_SPARSE.input_axons, OUTPUT_NEURONS))
    with pytest.raises(ValueError, match="nonzero float connections"):
        quantize_float_weights(weights, profile=NATIVE_SPARSE)


def test_quantization_rejects_bad_shape_and_zero_network():
    with pytest.raises(ValueError):
        quantize_float_weights(
            np.zeros((CROPPED_DENSE.input_axons, OUTPUT_NEURONS)),
            profile=CROPPED_DENSE,
        )
    with pytest.raises(ValueError):
        quantize_float_weights(np.zeros((10, 10)), profile=CROPPED_DENSE)
