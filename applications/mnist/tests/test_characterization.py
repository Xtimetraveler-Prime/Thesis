from __future__ import annotations

import json
from pathlib import Path

import pytest

from mnist_app.characterization import (
    CHARACTERIZATION_SCHEMA,
    build_characterization_baseline,
    modeled_cycles_per_image,
    static_profile_bits,
)


def _accepted_payload() -> dict[str, object]:
    return {
        "schema": "neuromorphic-twin-mnist-accepted-validation-v1",
        "corpus": "official-mnist-test-full",
        "profiles": {
            "cropped-dense": {
                "checkpoint": {
                    "input_axons": 400,
                    "presentation_ticks": 16,
                },
                "summary": {
                    "golden_accuracy": 0.90,
                    "deployment_stored_synapses": 4000,
                    "golden_mean_input_events": 100.0,
                    "golden_mean_synaptic_visits": 800.0,
                    "golden_mean_output_spikes": 20.0,
                    "images": 10000,
                },
            },
            "native-sparse": {
                "checkpoint": {
                    "input_axons": 784,
                    "presentation_ticks": 16,
                },
                "summary": {
                    "golden_accuracy": 0.92,
                    "deployment_stored_synapses": 4090,
                    "golden_mean_input_events": 120.0,
                    "golden_mean_synaptic_visits": 400.0,
                    "golden_mean_output_spikes": 15.0,
                    "images": 10000,
                },
            },
        },
    }


def test_modeled_cycles_matches_m12_5_quiescent_base() -> None:
    # Ten MNIST output neurons, 16 ticks, no events/visits:
    # 16 * (16*10 + 10) = 2720 cycles.
    assert modeled_cycles_per_image(
        presentation_ticks=16,
        mean_input_events=0.0,
        mean_synaptic_visits=0.0,
    ) == pytest.approx(2720.0)


def test_modeled_cycles_adds_event_and_visit_costs() -> None:
    assert modeled_cycles_per_image(
        presentation_ticks=1,
        mean_input_events=3.0,
        mean_synaptic_visits=5.0,
    ) == pytest.approx(170.0 + 12.0 + 20.0)


def test_static_profile_bits_is_logical_storage_not_device_resource_count() -> None:
    expected = (
        10 * 128
        + 10 * 64
        + 2 * 16
        + 100 * 32
        + (20 + 1) * 32
        + (10 + 1) * 32
    )
    assert static_profile_bits(input_axons=20, stored_synapses=100) == expected


def test_characterization_baseline_marks_timing_as_model_derived(tmp_path: Path) -> None:
    source = tmp_path / "accepted.json"
    source.write_text(json.dumps(_accepted_payload()), encoding="utf-8")
    result = build_characterization_baseline(source)

    assert result["schema"] == CHARACTERIZATION_SCHEMA
    assert result["corpus"] == "official-mnist-test-full"
    cropped = result["profiles"]["cropped-dense"]
    native = result["profiles"]["native-sparse"]
    assert cropped["accuracy"]["status"] == "measured-software-golden"
    assert "model-derived" in cropped["architectural_timing_model"]["status"]
    assert native["architectural_timing_model"]["mean_cycles_per_image"] < cropped["architectural_timing_model"]["mean_cycles_per_image"]
    assert result["comparison"]["native_minus_cropped_accuracy_pp"] == pytest.approx(2.0)
    assert result["measurement_policy"]["energy"].startswith("not claimed")


def test_frozen_accepted_baseline_regression() -> None:
    source = (
        Path(__file__).parents[1]
        / "frozen"
        / "mnist-v1"
        / "accepted_software_validation.json"
    )
    result = build_characterization_baseline(source)
    cropped = result["profiles"]["cropped-dense"]
    native = result["profiles"]["native-sparse"]

    assert cropped["accuracy"]["golden"] == pytest.approx(0.9024)
    assert native["accuracy"]["golden"] == pytest.approx(0.9171)
    assert cropped["workload"]["mean_synaptic_visits_per_image"] == pytest.approx(15678.9456)
    assert native["workload"]["mean_synaptic_visits_per_image"] == pytest.approx(6132.8319)
    assert cropped["architectural_timing_model"]["mean_cycles_per_image"] == pytest.approx(71893.614)
    assert native["architectural_timing_model"]["mean_cycles_per_image"] == pytest.approx(33925.6324)
    assert result["comparison"]["native_to_cropped_modeled_cycle_ratio"] == pytest.approx(0.4718865906504575)
