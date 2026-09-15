import numpy as np

from mnist_app.training import analyze_predictions, magnitude_pruning_mask


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
