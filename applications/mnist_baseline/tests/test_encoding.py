import numpy as np
import pytest

from mnist_app.config import (
    CROPPED_DENSE,
    NATIVE_SPARSE,
    PRESENTATION_TICKS,
    get_profile,
)
from mnist_app.encoding import (
    center_crop_20x20,
    count_events,
    encode_binary_spikes,
    encode_event_schedule,
    normalize_pixels,
    preprocess_images,
    quantize_spike_levels,
)


def test_profiles_fit_frozen_capacities():
    assert NATIVE_SPARSE.input_axons == 784
    assert NATIVE_SPARSE.max_synapses == 4096
    assert CROPPED_DENSE.input_axons == 400
    assert CROPPED_DENSE.dense_synapses == 4000


def test_profile_lookup_rejects_unknown_name():
    with pytest.raises(ValueError):
        get_profile("other")


def test_native_profile_preserves_entire_image():
    image = np.arange(28 * 28, dtype=np.int64).reshape(28, 28) % 256
    selected = preprocess_images(image, profile="native-sparse")
    assert selected.shape == (1, 28, 28)
    np.testing.assert_array_equal(selected[0], image.astype(np.uint8))


def test_center_crop_is_exact_middle_20_by_20():
    image = np.arange(28 * 28, dtype=np.int64).reshape(28, 28) % 256
    cropped = center_crop_20x20(image)
    assert cropped.shape == (1, 20, 20)
    np.testing.assert_array_equal(cropped[0], image.astype(np.uint8)[4:24, 4:24])


@pytest.mark.parametrize("profile", ["native-sparse", "cropped-dense"])
def test_black_image_produces_no_events(profile):
    image = np.zeros((28, 28), dtype=np.uint8)
    schedule = encode_event_schedule(image, profile=profile)
    assert len(schedule) == PRESENTATION_TICKS
    assert all(tick == () for tick in schedule)
    assert count_events(schedule) == 0


@pytest.mark.parametrize(
    ("profile", "axon_count"),
    [("native-sparse", 784), ("cropped-dense", 400)],
)
def test_white_image_fires_every_selected_axon_every_tick(profile, axon_count):
    image = np.full((28, 28), 255, dtype=np.uint8)
    schedule = encode_event_schedule(image, profile=profile)
    expected = tuple(range(axon_count))
    assert all(tick == expected for tick in schedule)
    assert count_events(schedule) == axon_count * PRESENTATION_TICKS


@pytest.mark.parametrize("profile", ["native-sparse", "cropped-dense"])
def test_each_pixel_emits_exact_quantized_spike_count(profile):
    rng = np.random.default_rng(7)
    image = rng.integers(0, 256, size=(28, 28), dtype=np.uint8)
    levels = quantize_spike_levels(image, profile=profile)[0]
    spikes = encode_binary_spikes(image, profile=profile)[0]
    np.testing.assert_array_equal(spikes.sum(axis=0), levels)


@pytest.mark.parametrize(
    ("profile", "max_axons"),
    [("native-sparse", 784), ("cropped-dense", 400)],
)
def test_event_schedule_is_repeatable_sorted_and_unique(profile, max_axons):
    rng = np.random.default_rng(0x4D4E4953)
    image = rng.integers(0, 256, size=(28, 28), dtype=np.uint8)
    first = encode_event_schedule(image, profile=profile)
    second = encode_event_schedule(image.copy(), profile=profile)
    assert first == second
    for tick in first:
        assert tuple(sorted(tick)) == tick
        assert len(tick) == len(set(tick))
        assert len(tick) <= max_axons


def test_outer_border_affects_native_but_not_crop():
    image = np.zeros((28, 28), dtype=np.uint8)
    image[0, 0] = 255
    assert count_events(
        encode_event_schedule(image, profile="native-sparse")
    ) == PRESENTATION_TICKS
    assert count_events(
        encode_event_schedule(image, profile="cropped-dense")
    ) == 0


def test_normalization_matches_notebook_pixel_divide_by_255():
    image = np.zeros((28, 28), dtype=np.uint8)
    image[5, 5] = 255
    normalized = normalize_pixels(image, profile="native-sparse")
    assert normalized.dtype == np.float32
    assert normalized[0, 5, 5] == pytest.approx(1.0)


def test_invalid_shape_and_range_are_rejected():
    with pytest.raises(ValueError):
        encode_event_schedule(
            np.zeros((20, 20), dtype=np.uint8),
            profile="native-sparse",
        )
    with pytest.raises(ValueError):
        encode_event_schedule(
            np.full((28, 28), 256, dtype=np.int16),
            profile="cropped-dense",
        )
