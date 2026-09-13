import numpy as np
import pytest

from mnist_app.config import INPUT_AXONS, PRESENTATION_TICKS
from mnist_app.encoding import (
    center_crop_20x20,
    count_events,
    encode_binary_spikes,
    encode_event_schedule,
    quantize_spike_levels,
)


def test_center_crop_is_exact_middle_20_by_20():
    image = np.arange(28 * 28, dtype=np.int64).reshape(28, 28) % 256
    cropped = center_crop_20x20(image)
    assert cropped.shape == (1, 20, 20)
    np.testing.assert_array_equal(cropped[0], image.astype(np.uint8)[4:24, 4:24])


def test_black_image_produces_no_events():
    image = np.zeros((28, 28), dtype=np.uint8)
    schedule = encode_event_schedule(image)
    assert len(schedule) == PRESENTATION_TICKS
    assert all(tick == () for tick in schedule)
    assert count_events(schedule) == 0


def test_white_crop_fires_every_axon_every_tick():
    image = np.zeros((28, 28), dtype=np.uint8)
    image[4:24, 4:24] = 255
    schedule = encode_event_schedule(image)
    expected = tuple(range(INPUT_AXONS))
    assert all(tick == expected for tick in schedule)
    assert count_events(schedule) == INPUT_AXONS * PRESENTATION_TICKS


def test_each_pixel_emits_exact_quantized_spike_count():
    image = np.zeros((28, 28), dtype=np.uint8)
    values = np.linspace(0, 255, 400, dtype=np.uint8).reshape(20, 20)
    image[4:24, 4:24] = values
    levels = quantize_spike_levels(image)[0]
    spikes = encode_binary_spikes(image)[0]
    np.testing.assert_array_equal(spikes.sum(axis=0), levels)


def test_event_schedule_is_repeatable_and_ascending():
    rng = np.random.default_rng(0x4D4E4953)
    image = rng.integers(0, 256, size=(28, 28), dtype=np.uint8)
    first = encode_event_schedule(image)
    second = encode_event_schedule(image.copy())
    assert first == second
    for tick in first:
        assert tuple(sorted(tick)) == tick
        assert len(tick) == len(set(tick))
        assert len(tick) <= INPUT_AXONS


def test_invalid_shape_and_range_are_rejected():
    with pytest.raises(ValueError):
        encode_event_schedule(np.zeros((20, 20), dtype=np.uint8))
    with pytest.raises(ValueError):
        encode_event_schedule(np.full((28, 28), 256, dtype=np.int16))
