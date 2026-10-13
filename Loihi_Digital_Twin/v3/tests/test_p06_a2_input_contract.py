"""P06-A2.2 independent input-contract invariants, no official dataset labels."""

import hashlib
import struct

import pytest

from loihi_twin_v2.p06_input_contract import (
    ENCODER_PROFILE,
    INPUT_CHANNELS,
    INPUT_TICKS,
    OUTPUT_CLASSES,
    TOTAL_TICKS,
    classify_spike_counts,
    event_schedule_sha256,
    image_event_schedule,
    pixel_spikes,
)


def test_fixed_profile_dimensions_and_drain():
    assert ENCODER_PROFILE == "p06-uint8-quota-phase17-v1"
    assert (INPUT_CHANNELS, INPUT_TICKS, TOTAL_TICKS, OUTPUT_CLASSES) == (784, 25, 26, 10)
    assert image_event_schedule([0] * 784) == ((),) * 26
    assert image_event_schedule(bytes([255] * 784)) == (tuple(range(784)),) * 25 + ((),)


def test_exhaustive_byte_quota_for_several_pixel_positions():
    for i in (0, 1, 17, 23, 101, 783):
        image = [0] * 784
        for value in range(256):
            image[i] = value
            schedule = image_event_schedule(image)
            assert sum(i in schedule[t] for t in range(25)) == 25 * value // 255
            assert all(tuple(sorted(set(active))) == active for active in schedule)
            assert schedule[-1] == ()


def test_exact_phase_formula_and_pixel_order():
    image = [0] * 784
    image[0], image[1], image[101], image[783] = (128, 128, 128, 128)
    for tick in range(26):
        expected = []
        if tick < 25:
            for index in (0, 1, 101, 783):
                phase = (tick + (index * 17) % 25) % 25
                if ((phase + 1) * 128) // 255 > (phase * 128) // 255:
                    expected.append(index)
        assert pixel_spikes(image, tick) == tuple(expected)


def test_canonical_event_hash_is_deterministic_and_phase_sensitive():
    image = bytes(index % 256 for index in range(784))
    schedule = image_event_schedule(image)
    packed = b"".join(struct.pack("<H", len(row)) + b"".join(
        struct.pack("<H", index) for index in row) for row in schedule)
    assert event_schedule_sha256(image) == hashlib.sha256(packed).hexdigest()
    assert event_schedule_sha256(list(image)) == event_schedule_sha256(image)
    assert event_schedule_sha256(bytes(reversed(image))) != event_schedule_sha256(image)


@pytest.mark.parametrize("image,tick", [
    ([0] * 783, 0), ([0] * 785, 0),
    ([0] * 783 + [-1], 0), ([0] * 783 + [256], 0),
    ([False] + [0] * 783, 0), ([0.0] + [0] * 783, 0),
    ([0] * 784, -1), ([0] * 784, 26), ([0] * 784, True),
])
def test_invalid_input_rejected(image, tick):
    with pytest.raises(ValueError):
        pixel_spikes(image, tick)


def test_readout_ties_silence_and_strict_validity():
    assert classify_spike_counts([0] * 10) == 0
    assert classify_spike_counts([1, 4, 3, 4] + [0] * 6) == 1
    assert classify_spike_counts([0] * 9 + [5]) == 9
    for invalid in ([0] * 9, [0] * 11, [True] + [0] * 9, [-1] + [0] * 9):
        with pytest.raises(ValueError):
            classify_spike_counts(invalid)
