from __future__ import annotations

import numpy as np

from mnist_v2_nxtf.official_test_evaluation import (
    OFFICIAL_TEST_EXAMPLES,
    OFFICIAL_TEST_TIMESTEPS,
    P08_3_ACCEPTANCE_STATUS,
    _class_accuracy,
    _confusion_matrix,
    _input_bias_frames,
)
from mnist_v2_nxtf.source_recovered_validation import (
    ACCEPTED_HIDDEN_THRESHOLDS,
    ACCEPTED_INPUT_THRESHOLD,
    ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
    ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
    ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
)


def test_official_test_gate_is_bound_to_accepted_p08_3_artifacts() -> None:
    assert OFFICIAL_TEST_EXAMPLES == 10_000
    assert OFFICIAL_TEST_TIMESTEPS == 100
    assert P08_3_ACCEPTANCE_STATUS == "P08_3_ACCEPTED_OFFICIAL_TEST_UNLOCKED"
    assert ACCEPTED_INPUT_THRESHOLD == 2040
    assert ACCEPTED_HIDDEN_THRESHOLDS == (556, 512, 672)
    assert ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT == (
        "9169939821201e4764813dbb17e254b796cd952e4707315eb61ecd0e0082926e"
    )
    assert ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT == (
        "6e47dc0c37d2f05828f0a0231406c7df8e4bf83652300fde0df1a0b8f9d83f13"
    )
    assert ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT == (
        "5dc7c9af692ca375283ede186b81d135bd1c76708b114cc64e3f99c085cd856b"
    )


def test_official_test_input_scaling_is_corpus_scoped_and_unsigned_8bit() -> None:
    images = np.zeros((2, 28, 28, 1), dtype=np.float32)
    images[0, 0, 0, 0] = 0.5
    images[1, 0, 0, 0] = 1.0
    encoded, global_max = _input_bias_frames(images, expected_examples=2)
    assert global_max == 1.0
    assert encoded.dtype == np.int32
    assert encoded[0, 0, 0, 0] == 127
    assert encoded[1, 0, 0, 0] == 255
    assert int(encoded.min()) == 0
    assert int(encoded.max()) == 255


def test_official_test_input_scaling_rejects_wrong_shape() -> None:
    images = np.zeros((1, 28, 28, 1), dtype=np.float32)
    try:
        _input_bias_frames(images, expected_examples=2)
    except AssertionError as exc:
        assert "shape drifted" in str(exc)
    else:
        raise AssertionError("wrong corpus size should be rejected")


def test_confusion_and_class_accuracy_are_deterministic() -> None:
    labels = np.repeat(np.arange(10, dtype=np.int64), 2)
    predictions = labels.copy()
    predictions[1] = 1
    confusion = _confusion_matrix(labels, predictions)
    assert confusion.shape == (10, 10)
    assert int(confusion.sum()) == 20
    assert confusion[0, 0] == 1
    assert confusion[0, 1] == 1
    accuracy = _class_accuracy(confusion)
    assert accuracy.shape == (10,)
    assert accuracy[0] == 0.5
    assert np.all(accuracy[1:] == 1.0)
