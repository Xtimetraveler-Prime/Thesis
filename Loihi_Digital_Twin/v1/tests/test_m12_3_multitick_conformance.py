from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from neuromorphic_twin.fpga_multitick_conformance import (
    M12_MULTITICK_CORPUS_SCHEMA,
    build_m12_multitick_cases,
    compare_m12_multitick_capture,
    write_m12_multitick_corpus,
)
from neuromorphic_twin.fpga_physical_trace import PhysicalFpgaTraceArtifact


def _cases_by_name():
    return {case.name: case for case in build_m12_multitick_cases()}


def test_m12_3_corpus_is_dense_unique_and_covers_planned_stateful_classes() -> None:
    cases = build_m12_multitick_cases()
    assert len(cases) == 10
    assert sum(case.tick_count for case in cases) == 40
    assert tuple(case.case_id for case in cases) == tuple(range(10))
    assert len({case.name for case in cases}) == len(cases)

    coverage = {tag for case in cases for tag in case.coverage}
    assert {
        "feedforward_chain",
        "self_recurrent",
        "recurrent_loop",
        "recurrent_fanout",
        "recurrent_fanin",
        "same_target_multiplicity",
        "external_plus_recurrent",
        "simultaneous_spikes",
        "source_order",
        "route_declaration_order",
        "quiescent_period",
        "renewed_external_input",
        "multi_tick_decay",
        "refractory_entry_hold_release",
        "reset_replay_anchor",
    } <= coverage


def test_feedforward_chain_proves_next_tick_only_delivery() -> None:
    case = _cases_by_name()["feedforward-recurrent-chain"]
    ticks = case.expected_ticks
    assert tuple(t.snapshot.spikes for t in ticks) == (
        (True, False, False),
        (False, True, False),
        (False, False, True),
        (False, False, False),
    )
    assert tuple(t.snapshot.recurrent_input_axons for t in ticks) == (
        (),
        (1,),
        (2,),
        (),
    )
    assert tuple(t.snapshot.routed_output_axons for t in ticks) == (
        (1,),
        (2,),
        (),
        (),
    )


def test_self_recurrence_swaps_queue_every_tick_without_same_tick_feedback() -> None:
    case = _cases_by_name()["self-recurrent-oscillator"]
    assert tuple(t.snapshot.external_input_axons for t in case.expected_ticks) == (
        (0,), (), (), ()
    )
    assert tuple(t.snapshot.recurrent_input_axons for t in case.expected_ticks) == (
        (), (0,), (0,), (0,)
    )
    assert all(t.snapshot.spikes == (True,) for t in case.expected_ticks)
    assert tuple(t.recurrent_current_bank for t in case.expected_ticks) == (
        True, False, True, False
    )


def test_recurrent_loop_alternates_spikes_and_queue_bank() -> None:
    case = _cases_by_name()["two-neuron-recurrent-loop"]
    assert tuple(t.snapshot.spikes for t in case.expected_ticks) == (
        (True, False),
        (False, True),
        (True, False),
        (False, True),
        (True, False),
        (False, True),
    )
    assert tuple(t.recurrent_current_bank for t in case.expected_ticks) == (
        True, False, True, False, True, False
    )


def test_fanout_and_fanin_have_expected_physical_event_sequences() -> None:
    cases = _cases_by_name()
    fanout = cases["recurrent-fanout"]
    assert fanout.expected_ticks[0].snapshot.routed_output_axons == (1, 2)
    assert fanout.expected_ticks[1].snapshot.recurrent_input_axons == (1, 2)
    assert fanout.expected_ticks[1].snapshot.spikes == (False, True, True)

    fanin = cases["recurrent-fanin"]
    assert fanin.expected_ticks[0].snapshot.routed_output_axons == (2, 3)
    assert fanin.expected_ticks[1].snapshot.recurrent_input_axons == (2, 3)
    assert fanin.expected_ticks[1].snapshot.synaptic_input[2] == 128
    assert fanin.expected_ticks[1].snapshot.spikes[2] is True


def test_same_target_multiplicity_is_preserved_not_deduplicated() -> None:
    case = _cases_by_name()["same-target-recurrent-multiplicity"]
    assert case.expected_ticks[0].snapshot.routed_output_axons == (2, 2)
    assert case.expected_ticks[1].snapshot.recurrent_input_axons == (2, 2)
    assert case.expected_ticks[1].snapshot.synaptic_input[2] == 128
    assert case.expected_ticks[1].snapshot.spikes[2] is True


def test_external_and_recurrent_inputs_are_separate_and_accumulate_same_tick() -> None:
    case = _cases_by_name()["external-plus-recurrent-same-tick"]
    tick2 = case.expected_ticks[1]
    assert tick2.snapshot.external_input_axons == (2,)
    assert tick2.snapshot.recurrent_input_axons == (1,)
    assert tick2.snapshot.synaptic_input[1] == 128
    assert tick2.snapshot.spikes == (False, True)


def test_simultaneous_routes_preserve_source_then_declaration_order() -> None:
    case = _cases_by_name()["simultaneous-routing-order"]
    assert case.expected_ticks[0].snapshot.spikes == (True, True)
    assert case.expected_ticks[0].snapshot.routed_output_axons == (3, 2, 4)
    assert case.expected_ticks[1].snapshot.recurrent_input_axons == (3, 2, 4)


def test_quiescence_then_renewed_input_is_visible_in_committed_timeline() -> None:
    case = _cases_by_name()["quiescence-then-renewed-input"]
    assert tuple(t.snapshot.external_input_axons for t in case.expected_ticks) == (
        (0,), (), (), (0,), ()
    )
    assert tuple(t.snapshot.spikes for t in case.expected_ticks) == (
        (True,), (False,), (False,), (True,), (False,)
    )


def test_decay_refractory_case_carries_state_across_multiple_ticks() -> None:
    case = _cases_by_name()["decay-refractory-history"]
    ticks = case.expected_ticks
    assert ticks[0].snapshot.spikes == (True,)
    assert ticks[0].snapshot.state_after_words != ticks[0].snapshot.state_before_words
    assert ticks[1].snapshot.state_before_words == ticks[0].snapshot.state_after_words
    assert ticks[2].snapshot.external_input_axons == (0,)
    assert ticks[2].snapshot.state_before_words == ticks[1].snapshot.state_after_words
    assert ticks[-1].snapshot.committed_tick == 6


def test_exact_multitick_comparator_accepts_full_expected_timeline() -> None:
    for case in build_m12_multitick_cases():
        artifact = PhysicalFpgaTraceArtifact(
            scenario_id=case.name,
            transport="jtag-vio",
            device="test-device",
            ticks=case.expected_ticks,
        )
        report = compare_m12_multitick_capture(case, artifact)
        assert report.passed
        assert report.mismatches == ()


def test_exact_multitick_comparator_reports_tick_and_field() -> None:
    case = _cases_by_name()["feedforward-recurrent-chain"]
    bad_tick = replace(
        case.expected_ticks[1],
        snapshot=replace(case.expected_ticks[1].snapshot, routed_output_axons=(99,)),
    )
    artifact = PhysicalFpgaTraceArtifact(
        scenario_id=case.name,
        transport="jtag-vio",
        device="test-device",
        ticks=(case.expected_ticks[0], bad_tick, *case.expected_ticks[2:]),
    )
    report = compare_m12_multitick_capture(case, artifact)
    assert not report.passed
    assert len(report.mismatches) == 1
    mismatch = report.mismatches[0]
    assert mismatch.tick == 2
    assert mismatch.field == "snapshot.routed_output_axons"
    assert mismatch.expected == (2,)
    assert mismatch.actual == (99,)


def test_corpus_artifacts_are_deterministic_and_identify_total_ticks(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    manifest_a = write_m12_multitick_corpus(a)
    manifest_b = write_m12_multitick_corpus(b)
    assert manifest_a.read_bytes() == manifest_b.read_bytes()
    assert f'"schema": "{M12_MULTITICK_CORPUS_SCHEMA}"' in manifest_a.read_text()
    assert '"case_count": 10' in manifest_a.read_text()
    assert '"total_ticks": 40' in manifest_a.read_text()
    for left in sorted(a.glob("*.golden.json")):
        assert left.read_bytes() == (b / left.name).read_bytes()
