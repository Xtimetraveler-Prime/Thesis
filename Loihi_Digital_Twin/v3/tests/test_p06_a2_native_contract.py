"""A2.2 integration gate: preserve accepted P06-A1 input and readout behavior."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from loihi_twin_v2.p06_input_contract import (
    classify_spike_counts, image_event_schedule, pixel_spikes,
)


def _old_probe():
    path = Path(__file__).resolve().parents[1] / "scripts" / "p06_lif_input_probe.py"
    spec = importlib.util.spec_from_file_location("p06_a1_accepted_input", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a2_encoder_equals_accepted_a1_rate_quota_formula_on_diverse_frames():
    accepted = _old_probe()
    images = [
        [0] * 784,
        [255] * 784,
        [128] * 784,
        [(i * 43 + 7) % 256 for i in range(784)],
        [((255 - i) % 256) for i in range(784)],
    ]
    for pixels in images:
        schedule = image_event_schedule(pixels)
        assert len(schedule) == 26
        for tick, events in enumerate(schedule):
            assert events == accepted.rate_coded_pixel_indices(pixels, tick)
            assert events == pixel_spikes(pixels, tick)


def test_a2_readout_preserves_accepted_a1_tie_and_silence_rules():
    accepted = _old_probe()
    for counts in [
        [0] * 10, [1, 4, 3, 4] + [0] * 6,
        [0] * 9 + [3], [8] + [9] * 9,
    ]:
        assert classify_spike_counts(counts) == accepted.class_from_output_spike_counts(counts)
