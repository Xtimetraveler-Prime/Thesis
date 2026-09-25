import numpy as np
import pytest

from mnist_app.comparison import summarize_prediction_comparison


def test_prediction_comparison_reports_accuracy_delta_and_agreement():
    labels = np.array([0, 1, 2, 3])
    float_predictions = np.array([0, 1, 0, 3])
    golden_predictions = np.array([0, 2, 2, 3])

    result = summarize_prediction_comparison(
        float_predictions,
        golden_predictions,
        labels,
    )

    assert result["images"] == 4
    assert result["float_accuracy"] == pytest.approx(0.75)
    assert result["golden_accuracy"] == pytest.approx(0.75)
    assert result["golden_minus_float_accuracy"] == pytest.approx(0.0)
    assert result["prediction_agreement"] == pytest.approx(0.5)
    assert result["prediction_disagreements"] == 2
    assert result["float_correct_golden_wrong"] == 1
    assert result["float_wrong_golden_correct"] == 1


def test_prediction_comparison_rejects_mismatched_shapes():
    with pytest.raises(ValueError):
        summarize_prediction_comparison(
            np.array([0, 1]),
            np.array([0]),
            np.array([0, 1]),
        )
