from __future__ import annotations

import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "examples" / "generate_m11_5_3_vectors.py"
DIFF_TB = ROOT / "rtl" / "core_v1" / "tb" / "tb_phase_b_synapse_accumulator_differential_v1.sv"
DIFF_RUNNER = ROOT / "rtl" / "core_v1" / "run_m11_5_3_differential_sim.sh"


def test_m11_5_3_differential_corpus_is_reproducible_and_nontrivial(tmp_path) -> None:
    module = runpy.run_path(str(GENERATOR))
    write_include = module["write_systemverilog_include"]
    cases = module["m11_5_3_cases"]()

    first = tmp_path / "first.svh"
    second = tmp_path / "second.svh"
    write_include(first)
    write_include(second)

    assert first.read_bytes() == second.read_bytes()
    assert len(cases) == 12
    assert cases[0].name == "directed_extremes"
    assert any(case.external_axons for case in cases)
    assert any(case.recurrent_axons for case in cases)
    assert any(
        axon >= case.storage.axon_count
        for case in cases
        for axon in case.external_axons + case.recurrent_axons
    )
    assert any(
        value < 0
        for case in cases
        for value in case.expected_accumulators
    )
    assert any(
        value > 0
        for case in cases
        for value in case.expected_accumulators
    )

    text = first.read_text(encoding="utf-8")
    assert "M11_5_3_CASE_COUNT = 12" in text
    assert "M11_5_3_SEED = 32'h4d313533" in text
    assert "M11_5_3_FORMAT_WORDS" in text
    assert "M11_5_3_SYNAPSE_WORDS" in text
    assert "M11_5_3_ROW_POINTERS" in text
    assert "M11_5_3_EXTERNAL_EVENTS" in text
    assert "M11_5_3_RECURRENT_EVENTS" in text
    assert "M11_5_3_EXPECTED_ACCUMULATORS" in text


def test_m11_5_3_differential_testbench_checks_complete_accumulator_images() -> None:
    text = DIFF_TB.read_text(encoding="utf-8")
    assert '`include "generated_m11_5_3_vectors.svh"' in text
    assert "for (case_index = 0; case_index < M11_5_3_CASE_COUNT" in text
    assert "M11_5_3_FORMAT_WORDS" in text
    assert "M11_5_3_SYNAPSE_WORDS" in text
    assert "M11_5_3_ROW_POINTERS" in text
    assert "M11_5_3_EXTERNAL_EVENTS" in text
    assert "M11_5_3_RECURRENT_EVENTS" in text
    assert "M11_5_3_EXPECTED_ACCUMULATORS" in text
    assert "M11.5.3 accumulator mismatch:" in text
    assert "M11.5.3 Python/RTL accumulator differential passed:" in text


def test_m11_5_3_differential_runner_regenerates_python_expectations() -> None:
    text = DIFF_RUNNER.read_text(encoding="utf-8")
    assert 'EXPECTED_VERSION="2025.2"' in text
    assert 'STAGE_ROOT="/tmp/neuromorphic_twin_rtl_${UID}/m11_5_3_differential"' in text
    assert "generate_m11_5_3_vectors.py" in text
    assert "generated_m11_5_3_vectors.svh" in text
    assert "m08_weight_decoder_v1.sv" in text
    assert "phase_b_synapse_accumulator_v1.sv" in text
    assert "tb_phase_b_synapse_accumulator_differential_v1.sv" in text
    assert 'grep -Fq "$PASS_MARKER"' in text
