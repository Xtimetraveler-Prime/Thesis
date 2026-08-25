from __future__ import annotations

import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "examples" / "generate_m11_5_4_vectors.py"
TB = ROOT / "rtl" / "core_v1" / "tb" / "tb_recurrent_route_queue_differential_v1.sv"
RUNNER = ROOT / "rtl" / "core_v1" / "run_m11_5_4_differential_sim.sh"
RTL = ROOT / "rtl" / "core_v1" / "recurrent_route_queue_v1.sv"


def test_m11_5_4_differential_vectors_are_reproducible(tmp_path: Path) -> None:
    module = runpy.run_path(str(GENERATOR))
    cases = module["m11_5_4_cases"]()
    write_include = module["write_systemverilog_include"]

    assert module["M11_5_4_SEED"] == 0x4D313534
    assert len(cases) == 16
    assert all(len(case.spike_vectors) == 4 for case in cases)
    assert all(len(case.results) == 4 for case in cases)

    first = tmp_path / "first.svh"
    second = tmp_path / "second.svh"
    write_include(first)
    write_include(second)
    assert first.read_bytes() == second.read_bytes()

    text = first.read_text(encoding="utf-8")
    assert "M11_5_4_CASE_COUNT = 16" in text
    assert "M11_5_4_TICKS_PER_CASE = 4" in text
    assert "32'h4d313534" in text
    assert "M11_5_4_ROUTE_ROWS" in text
    assert "M11_5_4_ROUTE_TARGETS" in text
    assert "M11_5_4_SPIKES" in text
    assert "M11_5_4_EXPECTED_CONSUMED" in text
    assert "M11_5_4_EXPECTED_ROUTED" in text
    assert "M11_5_4_EXPECTED_CURRENT_BANKS" in text
    assert "M11_5_4_EXPECTED_BANK0_COUNTS" in text
    assert "M11_5_4_EXPECTED_BANK1_COUNTS" in text


def test_m11_5_4_directed_differential_case_proves_multi_tick_bank_semantics() -> None:
    module = runpy.run_path(str(GENERATOR))
    directed = module["m11_5_4_cases"]()[0]

    assert directed.storage.row_pointers == (0, 1, 3, 5)
    assert directed.storage.target_axons == (6, 8, 7, 9, 6)

    tick0, tick1, tick2, tick3 = directed.results
    assert tick0.consumed_recurrent_axons == ()
    assert tick0.routed_output_axons == (6, 8, 7, 9, 6)
    assert tick0.queue_after_commit.current_bank == 1

    assert tick1.consumed_recurrent_axons == (6, 8, 7, 9, 6)
    assert tick1.routed_output_axons == (8, 7)
    assert tick1.queue_after_commit.current_bank == 0

    assert tick2.consumed_recurrent_axons == (8, 7)
    assert tick2.routed_output_axons == ()
    assert tick2.queue_after_commit.current_bank == 1

    assert tick3.consumed_recurrent_axons == ()
    assert tick3.routed_output_axons == (6, 9, 6)
    assert tick3.queue_after_commit.current_bank == 0


def test_m11_5_4_random_corpus_covers_empty_ticks_and_multiplicity() -> None:
    module = runpy.run_path(str(GENERATOR))
    cases = module["m11_5_4_cases"]()
    results = [result for case in cases for result in case.results]

    assert any(not result.routed_output_axons for result in results)
    assert any(
        len(result.routed_output_axons) != len(set(result.routed_output_axons))
        for result in results
    )
    assert any(result.consumed_recurrent_axons for result in results)

    for result in results:
        assert result.queue_after_commit.current_events == result.routed_output_axons
        assert len(result.queue_after_commit.current_events) <= 32


def test_m11_5_4_differential_tb_checks_both_sides_of_each_bank_swap() -> None:
    text = TB.read_text(encoding="utf-8")
    assert '`include "generated_m11_5_4_vectors.svh"' in text
    assert "M11_5_4_EXPECTED_CONSUMED" in text
    assert "read_bank(current_bank, i, observed)" in text
    assert "M11_5_4_EXPECTED_ROUTED" in text
    assert "M11_5_4_EXPECTED_CURRENT_BANKS" in text
    assert "M11_5_4_EXPECTED_BANK0_COUNTS" in text
    assert "M11_5_4_EXPECTED_BANK1_COUNTS" in text
    assert "M11.5.4 Python/RTL routing differential passed:" in text


def test_m11_5_4_differential_runner_regenerates_python_expectations() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    assert 'EXPECTED_VERSION="2025.2"' in text
    assert "generate_m11_5_4_vectors.py" in text
    assert "recurrent_route_queue_v1.sv" in text
    assert "tb_recurrent_route_queue_differential_v1.sv" in text
    assert 'PASS_MARKER="M11.5.4 Python/RTL routing differential passed:"' in text
    assert 'grep -Fq "$PASS_MARKER"' in text


def test_m11_5_4_differential_uses_same_rtl_as_directed_gate() -> None:
    text = RTL.read_text(encoding="utf-8")
    assert "module recurrent_route_queue_v1" in text
    assert "current_bank      <= ~current_bank;" in text
    assert "last_consumed_count   <= current_bank ? bank1_count : bank0_count;" in text
    assert "recurrent_bank0[next_count[11:0]] <= work_target;" in text
    assert "recurrent_bank1[next_count[11:0]] <= work_target;" in text
