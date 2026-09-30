from __future__ import annotations

import numpy as np

from mnist_v2_nxtf.accepted_ann import (
    ACCEPTED_ANN_BEST_VAL_ACCURACY,
    ACCEPTED_ANN_VAL_ACCURACY,
)
from mnist_v2_nxtf.source_recovered_validation import (
    ACCEPTED_HIDDEN_THRESHOLDS,
    ACCEPTED_INPUT_THRESHOLD,
    ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
    ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
    ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
    VALIDATION_EXAMPLES,
    VALIDATION_TIMESTEPS,
    _class_accuracy,
    _confusion_matrix,
    _input_bias_frames,
    _results_fingerprint,
)


def test_p08_3_5d_is_bound_to_accepted_source_recovered_artifact() -> None:
    assert ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT == (
        "9169939821201e4764813dbb17e254b796cd952e4707315eb61ecd0e0082926e"
    )
    assert ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT == (
        "6e47dc0c37d2f05828f0a0231406c7df8e4bf83652300fde0df1a0b8f9d83f13"
    )
    assert ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT == (
        "5dc7c9af692ca375283ede186b81d135bd1c76708b114cc64e3f99c085cd856b"
    )
    assert ACCEPTED_INPUT_THRESHOLD == 2040
    assert ACCEPTED_HIDDEN_THRESHOLDS == (556, 512, 672)


def test_p08_3_5d_keeps_frozen_measurement_horizon() -> None:
    assert VALIDATION_EXAMPLES == 5000
    assert VALIDATION_TIMESTEPS == 100


def test_accepted_ann_validation_alias_is_read_only_identity() -> None:
    assert ACCEPTED_ANN_VAL_ACCURACY == ACCEPTED_ANN_BEST_VAL_ACCURACY == 0.992600


def test_full_corpus_input_scaling_is_integer_8bit_and_not_batch_local() -> None:
    images = np.zeros((VALIDATION_EXAMPLES, 28, 28, 1), dtype=np.float32)
    images[0, 0, 0, 0] = 1.0
    images[-1, 0, 0, 0] = 0.5
    encoded, global_max = _input_bias_frames(images)
    assert global_max == 1.0
    assert encoded.dtype == np.int32
    assert int(encoded[0, 0, 0, 0]) == 255
    # Public NxTF-style cast truncates 127.5 toward zero.
    assert int(encoded[-1, 0, 0, 0]) == 127
    assert int(encoded.min()) == 0
    assert int(encoded.max()) == 255


def test_confusion_matrix_and_class_accuracy() -> None:
    labels = np.repeat(np.arange(10, dtype=np.int64), 2)
    predictions = labels.copy()
    predictions[1] = 1
    matrix = _confusion_matrix(labels, predictions)
    assert matrix.shape == (10, 10)
    assert int(matrix.sum()) == 20
    assert matrix[0, 0] == 1
    assert matrix[0, 1] == 1
    accuracies = _class_accuracy(matrix)
    assert accuracies.shape == (10,)
    assert accuracies[0] == 0.5
    assert np.all(accuracies[1:] == 1.0)


def test_result_fingerprint_is_deterministic_and_order_sensitive() -> None:
    a = np.asarray([1, 2, 3], dtype=np.int64)
    b = np.asarray([3, 2, 1], dtype=np.int64)
    assert _results_fingerprint(a, b) == _results_fingerprint(a.copy(), b.copy())
    assert _results_fingerprint(a, b) != _results_fingerprint(b, a)
