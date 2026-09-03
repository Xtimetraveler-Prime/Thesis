from __future__ import annotations

from dataclasses import replace
import json

from neuromorphic_twin.fpga_core_capacity import unpack_neuron_state_word
from neuromorphic_twin.fpga_physical_trace import PhysicalFpgaTraceArtifact
from neuromorphic_twin.fpga_single_tick_conformance import (
    M12_SINGLE_TICK_CORPUS_SCHEMA,
    build_m12_single_tick_cases,
    compare_m12_single_tick_capture,
    write_m12_single_tick_corpus,
)
from neuromorphic_twin.specification import STATE_MAX, STATE_MIN


def _cases_by_name():
    return {case.name: case for case in build_m12_single_tick_cases()}


def test_m12_2_corpus_has_dense_stable_ids_and_required_coverage() -> None:
    cases = build_m12_single_tick_cases()
    assert len(cases) == 16
    assert tuple(case.case_id for case in cases) == tuple(range(16))
    assert len({case.name for case in cases}) == 16

    coverage = {tag for case in cases for tag in case.coverage}
    required = {
        "positive_synaptic_input",
        "negative_synaptic_input",
        "mixed_excitation_inhibition",
        "current_decay",
        "voltage_decay",
        "positive_state_saturation",
        "negative_state_saturation",
        "threshold_equality",
        "threshold_just_over",
        "refractory_entry",
        "refractory_hold",
        "refractory_countdown",
        "refractory_release",
        "multiple_neurons",
        "multiple_axons",
        "event_multiplicity",
        "empty_csr_row",
        "encoded_excitatory",
        "encoded_inhibitory",
        "encoded_positive_exponent",
        "encoded_negative_exponent",
        "encoded_reduced_precision",
        "encoded_mixed_sign_mode",
    }
    assert required <= coverage


def test_representative_golden_results_cover_arithmetic_and_weight_boundaries() -> None:
    cases = _cases_by_name()

    positive = cases["positive-synaptic-input"].expected.snapshot
    assert positive.synaptic_input == (128,)
    positive_state = unpack_neuron_state_word(positive.state_after_words[0])
    assert positive_state.current == 128
    assert positive_state.voltage == 128

    negative = cases["negative-synaptic-rounding"].expected.snapshot
    assert negative.synaptic_input == (-64,)
    negative_state = unpack_neuron_state_word(negative.state_after_words[0])
    assert negative_state.current == -32
    assert negative_state.voltage == -65

    voltage = unpack_neuron_state_word(
        cases["voltage-decay-rounding"].expected.snapshot.state_after_words[0]
    )
    assert voltage.voltage == 50

    positive_sat = unpack_neuron_state_word(
        cases["positive-state-saturation"].expected.snapshot.state_after_words[0]
    )
    assert positive_sat.current == STATE_MAX
    assert positive_sat.voltage == STATE_MAX

    negative_sat = unpack_neuron_state_word(
        cases["negative-state-saturation"].expected.snapshot.state_after_words[0]
    )
    assert negative_sat.current == STATE_MIN
    assert negative_sat.voltage == STATE_MIN

    assert cases["encoded-positive-exponent"].expected.snapshot.synaptic_input == (768,)
    assert cases["encoded-negative-exponent"].expected.snapshot.synaptic_input == (-128,)
    assert cases["encoded-reduced-precision-mixed"].expected.snapshot.synaptic_input == (512,)


def test_threshold_refractory_routing_and_multiplicity_golden_results() -> None:
    cases = _cases_by_name()

    equality = cases["threshold-equality"].expected
    assert equality.snapshot.spikes == (False,)
    assert unpack_neuron_state_word(equality.snapshot.state_after_words[0]).voltage == 64

    entry = cases["threshold-over-refractory-entry"].expected
    assert entry.snapshot.spikes == (True,)
    entry_state = unpack_neuron_state_word(entry.snapshot.state_after_words[0])
    assert entry_state.voltage == -7
    assert entry_state.refractory_remaining == 2
    assert entry.snapshot.routed_output_axons == (1,)
    assert entry.recurrent_current_bank is True
    assert entry.recurrent_bank1_count == 1

    hold = unpack_neuron_state_word(
        cases["refractory-hold"].expected.snapshot.state_after_words[0]
    )
    assert hold.current == 50
    assert hold.voltage == -9
    assert hold.refractory_remaining == 1

    released = cases["refractory-release-boundary"].expected
    assert released.snapshot.spikes == (True,)
    assert unpack_neuron_state_word(
        released.snapshot.state_after_words[0]
    ).refractory_remaining == 1

    multi = cases["multi-neuron-multi-axon"].expected.snapshot
    assert multi.synaptic_input == (128, 192, 128)

    repeated = cases["repeated-event-multiplicity"].expected.snapshot
    assert repeated.external_input_axons == (0, 0, 0)
    assert repeated.synaptic_input == (192,)

    empty = cases["empty-csr-row"].expected.snapshot
    assert empty.external_input_axons == (1,)
    assert empty.synaptic_input == (0,)


def test_single_tick_comparator_is_exact_and_reports_first_level_fields() -> None:
    case = build_m12_single_tick_cases()[0]
    good = PhysicalFpgaTraceArtifact(
        scenario_id=case.name,
        transport="jtag-vio",
        device="xck26_0",
        ticks=(case.expected,),
    )
    report = compare_m12_single_tick_capture(case, good)
    assert report.passed
    assert report.mismatches == ()

    wrong_snapshot = replace(
        case.expected.snapshot,
        synaptic_input=(case.expected.snapshot.synaptic_input[0] + 1,),
    )
    wrong_tick = replace(case.expected, snapshot=wrong_snapshot)
    bad = PhysicalFpgaTraceArtifact(
        scenario_id="wrong-case",
        transport="jtag-vio",
        device="xck26_0",
        ticks=(wrong_tick,),
    )
    report = compare_m12_single_tick_capture(case, bad)
    assert not report.passed
    fields = {mismatch.field for mismatch in report.mismatches}
    assert "scenario_id" in fields
    assert "snapshot.synaptic_input" in fields


def test_m12_2_golden_artifacts_are_deterministic_and_machine_readable(tmp_path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    manifest_a = write_m12_single_tick_corpus(first)
    manifest_b = write_m12_single_tick_corpus(second)

    assert manifest_a.read_bytes() == manifest_b.read_bytes()
    assert sorted(path.name for path in first.iterdir()) == sorted(
        path.name for path in second.iterdir()
    )
    for path_a in first.iterdir():
        assert path_a.read_bytes() == (second / path_a.name).read_bytes()

    payload = json.loads(manifest_a.read_text(encoding="utf-8"))
    assert payload["schema"] == M12_SINGLE_TICK_CORPUS_SCHEMA
    assert payload["case_count"] == 16
    assert payload["cases"][0]["name"] == "positive-synaptic-input"

    golden = json.loads(
        (first / payload["cases"][7]["golden_file"]).read_text(encoding="utf-8")
    )
    assert golden["schema"] == M12_SINGLE_TICK_CORPUS_SCHEMA
    assert golden["expected_tick"]["committed_tick"] == 1
    assert golden["expected_tick"]["routed_output_axons"] == [1]
