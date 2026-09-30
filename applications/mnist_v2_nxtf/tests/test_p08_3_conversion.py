from __future__ import annotations

import numpy as np
import pytest

from mnist_v2_nxtf.accepted_ann import (
    ACCEPTED_ANN_BEST_EPOCH,
    ACCEPTED_ANN_BEST_VAL_ACCURACY,
    ACCEPTED_ANN_CHECKPOINT_SHA256,
    ACCEPTED_ANN_WEIGHTS_FINGERPRINT,
)
from mnist_v2_nxtf.conversion import (
    INTEGER_THRESHOLD_SCALE,
    NORMALIZATION_PERCENTILE,
    build_converted_network,
    conv_geometries,
    normalize_layer_parameters,
    quantize_normalized_parameters,
)
from mnist_v2_nxtf.policy import CONVERSION_POLICY
from mnist_v2_nxtf.reconstruction import PROPOSED_METRICS


def test_p08_3_3_accepted_ann_identity_is_frozen():
    assert ACCEPTED_ANN_BEST_EPOCH == 13
    assert ACCEPTED_ANN_BEST_VAL_ACCURACY == 0.992600
    assert ACCEPTED_ANN_CHECKPOINT_SHA256 == (
        "61f60eaa789dcf04131f658edb86db880999a5f0ad2c8f1bd06426d464dba7d2"
    )
    assert ACCEPTED_ANN_WEIGHTS_FINGERPRINT == (
        "e5c07133b8d534d29596cbde9d637db695942dfb224a82c2533f59a17f1c74ce"
    )


def test_p08_3_4_normalization_formula_matches_rueckauer_rule():
    kernel = np.asarray([[-2.0, 4.0]], dtype=np.float32)
    bias = np.asarray([3.0], dtype=np.float32)
    normalized_kernel, normalized_bias = normalize_layer_parameters(
        kernel,
        bias,
        lambda_previous=2.0,
        lambda_current=8.0,
    )
    assert np.allclose(normalized_kernel, [[-0.5, 1.0]])
    assert np.allclose(normalized_bias, [0.375])
    assert NORMALIZATION_PERCENTILE == 100.0


def test_p08_3_4_integer_quantization_uses_threshold_scale_without_clipping():
    kernel = np.asarray([-0.125, 0.0, 0.125], dtype=np.float64)
    bias = np.asarray([-1.0, 0.0, 1.0], dtype=np.float64)
    q_kernel, q_bias = quantize_normalized_parameters(kernel, bias)
    assert INTEGER_THRESHOLD_SCALE == 512
    assert q_kernel.tolist() == [-64, 0, 64]
    assert q_bias.tolist() == [-512, 0, 512]

    with pytest.raises(OverflowError):
        quantize_normalized_parameters(np.asarray([0.5]), np.asarray([0.0]))
    with pytest.raises(OverflowError):
        quantize_normalized_parameters(np.asarray([0.0]), np.asarray([4.0]))


def _zero_integer_arrays() -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {}
    for geometry in conv_geometries():
        arrays[f"{geometry.name}_kernel_integer"] = np.zeros(
            (
                geometry.kernel,
                geometry.kernel,
                geometry.input_channels,
                geometry.output_channels,
            ),
            dtype=np.int16,
        )
        arrays[f"{geometry.name}_bias_integer"] = np.zeros(
            (geometry.output_channels,), dtype=np.int16
        )
    return arrays


def test_p08_3_4_converted_network_preserves_frozen_graph_shape_and_neuron_policy():
    network = build_converted_network(_zero_integer_arrays())
    assert sum(population.size for population in network.populations) == PROPOSED_METRICS.neuron_count
    assert sum(
        len(projection.connections)
        for projection in (*network.projections, *network.input_projections)
    ) == PROPOSED_METRICS.expanded_connections
    assert len(network.populations) == sum(geometry.output_channels for geometry in conv_geometries())
    for population in network.populations:
        assert population.compartment.threshold == CONVERSION_POLICY.threshold_mantissa
        assert population.compartment.current_decay == CONVERSION_POLICY.current_decay
        assert population.compartment.voltage_decay == CONVERSION_POLICY.voltage_decay
        assert population.compartment.reset_voltage == 0
        assert population.compartment.bias == 0
