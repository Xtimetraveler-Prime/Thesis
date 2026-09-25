import numpy as np
import pytest

from mnist_app.training import (
    analyze_predictions,
    magnitude_pruning_mask,
    stratified_train_validation_indices,
)


def test_magnitude_pruning_mask_keeps_exact_budget():
    weights = np.arange(20, dtype=np.float32).reshape(4, 5) - 10
    mask = magnitude_pruning_mask(weights, 7)
    assert mask.shape == weights.shape
    assert int(mask.sum()) == 7


def test_magnitude_pruning_tie_break_is_deterministic():
    weights = np.ones((2, 3), dtype=np.float32)
    mask = magnitude_pruning_mask(weights, 2).reshape(-1)
    np.testing.assert_array_equal(mask, [1, 1, 0, 0, 0, 0])


def test_prediction_analysis_matches_notebook_argmax_pattern():
    scores = np.array(
        [
            [0, 4, 1, 0, 0, 0, 0, 0, 0, 0],
            [5, 1, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 3, 1, 0, 0],
        ]
    )
    labels = np.array([1, 2, 6])
    predictions, incorrect = analyze_predictions(scores, labels)
    np.testing.assert_array_equal(predictions, [1, 0, 6])
    np.testing.assert_array_equal(incorrect, [1])


def test_validation_split_is_deterministic_disjoint_and_stratified():
    labels = np.repeat(np.arange(10), 20)
    train_a, validation_a = stratified_train_validation_indices(
        labels,
        validation_size=50,
        seed=1234,
    )
    train_b, validation_b = stratified_train_validation_indices(
        labels,
        validation_size=50,
        seed=1234,
    )

    np.testing.assert_array_equal(train_a, train_b)
    np.testing.assert_array_equal(validation_a, validation_b)
    assert len(train_a) == 150
    assert len(validation_a) == 50
    assert set(train_a).isdisjoint(set(validation_a))
    assert sorted(np.bincount(labels[validation_a], minlength=10)) == [5] * 10


def test_validation_split_rejects_invalid_sizes():
    labels = np.arange(10)
    with pytest.raises(ValueError):
        stratified_train_validation_indices(labels, validation_size=0)
    with pytest.raises(ValueError):
        stratified_train_validation_indices(labels, validation_size=10)
