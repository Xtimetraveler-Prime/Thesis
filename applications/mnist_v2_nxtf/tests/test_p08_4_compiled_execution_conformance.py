from __future__ import annotations

import numpy as np

from mnist_v2_nxtf.compiled_execution_conformance import (
    CONFORMANCE_TIMESTEPS,
    FORWARD_ORDER,
    REPRESENTATIVE_SELECTION_RULE,
    REPRESENTATIVE_TEST_INDEX,
    REVERSE_ORDER,
    bias_input_spike_schedule,
)
from mnist_v2_nxtf.source_recovered_validation import ACCEPTED_INPUT_THRESHOLD


def test_representative_corpus_is_fixed_by_index_not_result():
    assert REPRESENTATIVE_TEST_INDEX == 0
    assert REPRESENTATIVE_SELECTION_RULE == "fixed_test_index_0_not_conditioned_on_result"
    assert FORWARD_ORDER == (0, 1, 2, 3, 4)
    assert REVERSE_ORDER == (4, 3, 2, 1, 0)
    assert CONFORMANCE_TIMESTEPS == 100


def test_bias_input_spike_schedule_uses_strict_threshold_and_hard_reset():
    image = np.zeros((28, 28, 1), dtype=np.int32)
    image[0, 0, 0] = 255
    schedule = bias_input_spike_schedule(image)

    assert schedule.shape == (100, 784)
    assert schedule.dtype == np.bool_
    observed = tuple(np.flatnonzero(schedule[:, 0]))
    # 8 * 255 == 2040 does not spike because the project/source boundary uses
    # strict greater-than. The ninth accumulation reaches 2295 and hard-resets.
    assert observed == (8, 17, 26, 35, 44, 53, 62, 71, 80, 89, 98)
    assert not np.any(schedule[:, 1:])


def test_bias_input_spike_schedule_rejects_out_of_domain_values():
    image = np.zeros((28, 28, 1), dtype=np.int32)
    image[0, 0, 0] = 256
    try:
        bias_input_spike_schedule(image)
    except ValueError as exc:
        assert "[0,255]" in str(exc)
    else:
        raise AssertionError("out-of-domain pixel bias was accepted")


def test_input_threshold_is_the_accepted_source_recovered_value():
    assert ACCEPTED_INPUT_THRESHOLD == 2040
