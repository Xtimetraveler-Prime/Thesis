from __future__ import annotations

from pathlib import Path

import pytest

from neuromorphic_twin.fpga_broad_regression import build_m12_broad_cases
from neuromorphic_twin.fpga_characterization import (
    CharacterizationSummary,
    ImplementationCharacterization,
    RawTickCycleMeasurement,
    characterize_ticks,
    read_cycle_measurements,
    synapse_visits_for_tick,
    write_characterization,
)


def test_synapse_visit_count_uses_exact_event_multiplicity_and_csr_rows() -> None:
    cases = build_m12_broad_cases()
    case = cases[16]  # high external-event multiplicity stress
    expected = case.workload.expected_ticks[0]
    visits = synapse_visits_for_tick(case, 1)
    manual = 0
    rows = case.workload.storage.axon_row_pointers
    for axon in expected.snapshot.input_axons:
        if axon < case.workload.storage.axon_count:
            manual += rows[axon + 1] - rows[axon]
    assert visits == manual
    assert visits > 0


def test_characterize_ticks_derives_clock_latency_and_throughput() -> None:
    case = build_m12_broad_cases()[0]
    tick = case.workload.expected_ticks[0]
    raw = (
        RawTickCycleMeasurement(
            case_id=case.case_id,
            case_name=case.name,
            tick=1,
            cycles=1000,
            external_events=tick.external_event_count,
            recurrent_events=tick.consumed_recurrent_count,
            routed_events=tick.routed_recurrent_count,
        ),
    )
    row = characterize_ticks(raw)[0]
    assert row.latency_ns == pytest.approx(10_000.0)
    assert row.ticks_per_second == pytest.approx(100_000.0)
    assert row.neuron_updates_per_second == pytest.approx(case.workload.neuron_count * 100_000.0)
    assert row.synapse_visits == synapse_visits_for_tick(case, 1)


def test_characterize_ticks_rejects_metadata_disagreement() -> None:
    case = build_m12_broad_cases()[0]
    tick = case.workload.expected_ticks[0]
    raw = (
        RawTickCycleMeasurement(
            case_id=case.case_id,
            case_name=case.name,
            tick=1,
            cycles=10,
            external_events=tick.external_event_count + 1,
            recurrent_events=tick.consumed_recurrent_count,
            routed_events=tick.routed_recurrent_count,
        ),
    )
    with pytest.raises(ValueError, match="external-event"):
        characterize_ticks(raw)


def test_cycle_tsv_reader_requires_frozen_header(tmp_path: Path) -> None:
    path = tmp_path / "cycles.tsv"
    path.write_text(
        "case_id\tcase_name\ttick\tcycles\texternal_events\trecurrent_events\trouted_events\n"
        "0\tseeded-00\t1\t123\t2\t0\t1\n",
        encoding="utf-8",
    )
    rows = read_cycle_measurements(path)
    assert rows[0].cycles == 123


def test_characterization_artifacts_are_machine_readable_and_thesis_friendly(tmp_path: Path) -> None:
    case = build_m12_broad_cases()[0]
    tick = case.workload.expected_ticks[0]
    rows = characterize_ticks((
        RawTickCycleMeasurement(
            case_id=case.case_id,
            case_name=case.name,
            tick=1,
            cycles=100,
            external_events=tick.external_event_count,
            recurrent_events=tick.consumed_recurrent_count,
            routed_events=tick.routed_recurrent_count,
        ),
    ))
    impl = ImplementationCharacterization(
        target_part="xck26-sfvc784-2LV-c",
        target_clock_hz=100_000_000,
        target_period_ns=10.0,
        worst_setup_slack_ns=1.0,
        worst_hold_slack_ns=0.1,
        clb_luts=3000,
        clb_luts_available=117120,
        clb_registers=4000,
        clb_registers_available=234240,
        bram_tiles_upper_bound=14,
        bram_tiles_available=144,
        ramb36=10,
        ramb18=7,
        dsps=2,
        dsps_available=1248,
        uram=0,
        uram_available=64,
    )
    paths = write_characterization(CharacterizationSummary(impl, rows), tmp_path)
    for path in paths:
        assert path.is_file() and path.stat().st_size > 0
    assert "M12.5 FPGA Characterization Summary" in paths[2].read_text(encoding="utf-8")
