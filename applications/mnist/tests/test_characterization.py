from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mnist_app.characterization import (
    CHARACTERIZATION_SCHEMA,
    build_characterization_baseline,
    modeled_cycles_per_image,
    static_profile_bits,
)
from mnist_app.characterization_runtime import (
    expected_tick_cycles,
    patch_runtime_controller_for_timing,
    patch_runtime_tcl_for_timing,
)
from mnist_app.runtime import RuntimeRequest


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


def test_timing_controller_patch_adds_only_passive_cycle_witness() -> None:
    source = (
        Path(__file__).parents[1]
        / "fpga"
        / "mnist_09_runtime_controller_v1.sv"
    ).read_text(encoding="utf-8")
    patched = patch_runtime_controller_for_timing(source)
    assert "module m12_5_characterization_capture_controller_v1" in patched
    assert "output logic [31:0]  observed_last_tick_cycles" in patched
    assert "observed_last_tick_cycles <= tick_cycle_counter + 32'd1" in patched
    assert "module m12_3_multitick_capture_controller_v1" not in patched
    # The computational core remains exactly the same instantiated module.
    assert "recurrent_integrated_core_controller_v1 core_i" in patched


def test_timing_tcl_patch_reads_cycle_probe_and_preserves_runtime_trace_flow() -> None:
    source = (
        Path(__file__).parents[1]
        / "fpga"
        / "vivado"
        / "classify_mnist_09_runtime.tcl"
    ).read_text(encoding="utf-8")
    patched = patch_runtime_tcl_for_timing(source)
    assert "observed_last_tick_cycles" in patched
    assert "set tick_cycles {}" in patched
    assert "lappend tick_cycles [probe_uint $p_tick_cycles]" in patched
    assert '\\"tick_cycles\\"' in patched
    assert "trace_read_space 7" not in patched  # commands use the probe variable, as before
    assert "set_probe_uint $p_trace_space 7" in patched


def test_expected_tick_cycles_uses_exact_csr_row_visits(monkeypatch: pytest.MonkeyPatch) -> None:
    import mnist_app.characterization_runtime as module

    # Row lengths: axon0=2, axon1=0, axon2=3. Multiplicity must count twice.
    monkeypatch.setattr(
        module,
        "load_deployment",
        lambda _path: SimpleNamespace(row_lengths=(2, 0, 3)),
    )
    rows = [() for _ in range(16)]
    rows[0] = (0, 2, 2)
    rows[1] = (1,)
    request = RuntimeRequest(
        profile="cropped-dense",
        profile_id=0,
        mnist_test_index=0,
        label=0,
        external_schedule=tuple(rows),
        golden_prediction=0,
        golden_spike_counts=(0,) * 10,
    )
    cycles = expected_tick_cycles(request, "/unused")
    # tick0: base170 + 3 events*4 + (2+3+3) visits*4 = 214
    assert cycles[0] == 214
    # tick1: base170 + 1 event*4 + 0 visits = 174
    assert cycles[1] == 174
    assert cycles[2:] == (170,) * 14
