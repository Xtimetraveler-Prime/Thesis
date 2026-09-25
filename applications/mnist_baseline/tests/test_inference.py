from types import SimpleNamespace

import numpy as np
import pytest

from mnist_app.inference import evaluate_dataset, infer_image


class SilentCore:
    def reset(self):
        pass

    def step(self, events):
        return SimpleNamespace(spikes=())


@pytest.mark.parametrize(
    ("profile", "expected_events", "row_count"),
    [
        ("native-sparse", 16, 784),
        ("cropped-dense", 0, 400),
    ],
)
def test_infer_image_uses_selected_profile(profile, expected_events, row_count):
    image = np.zeros((28, 28), dtype=np.uint8)
    image[0, 0] = 255
    row_lengths = (2,) * row_count
    result = infer_image(
        SilentCore(),
        image,
        profile=profile,
        row_lengths=row_lengths,
    )
    assert result.prediction == 0
    assert result.no_spike
    assert result.tied_winners == 10
    assert result.total_input_events == expected_events
    assert result.synaptic_visits == expected_events * 2
    assert len(result.predictions_by_tick) == 16


def test_evaluation_retains_notebook_style_prediction_and_error_indices():
    images = np.zeros((2, 28, 28), dtype=np.uint8)
    labels = np.array([0, 1])
    result = evaluate_dataset(
        SilentCore(),
        images,
        labels,
        profile="native-sparse",
        row_lengths=(0,) * 784,
    )
    assert result["predictions"] == [0, 0]
    assert result["incorrect_indices"] == [1]
    assert result["accuracy"] == 0.5
    assert result["accuracy_by_tick"] == [0.5] * 16
    assert result["mean_synaptic_visits"] == 0.0
