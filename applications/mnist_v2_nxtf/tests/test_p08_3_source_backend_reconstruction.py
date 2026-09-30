import numpy as np

from mnist_v2_nxtf.policy import CONVERSION_POLICY, OFFICIAL_TEST_POLICY
from mnist_v2_nxtf.source_backend_reconstruction import (
    SOURCE_ACTIVATION_PERCENTILE,
    SOURCE_BIAS_MAX,
    SOURCE_INPUT_SCALE,
    SOURCE_PARAM_PERCENTILE,
    SOURCE_WEIGHT_MAX,
    source_parameter_scale,
    source_to_int,
    source_to_mantexp,
)


def test_source_recovered_policy_constants_are_frozen():
    assert SOURCE_PARAM_PERCENTILE == 100.0
    assert SOURCE_ACTIVATION_PERCENTILE == 99.999
    assert SOURCE_INPUT_SCALE == 255
    assert SOURCE_WEIGHT_MAX == 255
    assert SOURCE_BIAS_MAX == 4095
    assert CONVERSION_POLICY.threshold_normalization is True
    assert CONVERSION_POLICY.desired_threshold_to_input_ratio == 8
    assert OFFICIAL_TEST_POLICY == "LOCKED_UNTIL_P08_3_CHECKPOINT_AND_CONVERSION_FREEZE"


def test_source_to_mantexp_matches_public_backend_rule():
    # A full-scale unsigned input has dV/dt near 255. Hard-reset DThIR=8
    # therefore asks for a threshold near 2040, exactly representable as
    # mantissa=255 and exponent=3.
    mantissa, exponent = source_to_mantexp(255.0 * 8.0, 256, 7)
    assert mantissa == 255
    assert exponent == 3
    assert mantissa * (2**exponent) == 2040


def test_source_parameter_scale_uses_weight_and_bias_limits():
    weights = np.asarray([-0.5, 0.25], dtype=np.float64)
    biases = np.asarray([0.0, 0.1], dtype=np.float64)
    scale = source_parameter_scale(weights, biases)
    # Weight range is limiting: 255 / 0.5.
    assert np.isclose(scale, 510.0)


def test_source_to_int_matches_public_clip_bounds_and_reports_clip_count():
    values = np.asarray([-2.0, -1.0, 0.0, 1.0, 2.0])
    quantized, clipped = source_to_int(values, 128.0, 8)
    assert quantized.tolist() == [-256, -128, 0, 128, 255]
    assert clipped == 1


def test_source_to_int_no_clip_when_scale_is_within_dynamic_range():
    values = np.asarray([-1.0, -0.5, 0.5, 1.0])
    quantized, clipped = source_to_int(values, 200.0, 8)
    assert quantized.tolist() == [-200, -100, 100, 200]
    assert clipped == 0
