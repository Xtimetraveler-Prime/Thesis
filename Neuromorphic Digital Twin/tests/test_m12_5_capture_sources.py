from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl" / "core_v1"
DOCS = ROOT / "docs"
EXAMPLES = ROOT / "examples"


def test_m12_5_counter_is_passive_and_reuses_frozen_m12_4_corpus() -> None:
    text = (RTL / "m12_5_characterization_capture_controller_v1.sv").read_text(encoding="utf-8")
    assert '`include "generated_m12_4_broad_cases.svh"' in text
    assert "M12_5_CONFIG_WORDS" not in text
    assert "output logic [31:0]  observed_last_tick_cycles" in text
    assert "logic [31:0] tick_cycle_counter" in text
    assert "else if (tick_start) begin" in text
    assert "if (tick_done) begin" in text
    assert "observed_last_tick_cycles <= tick_cycle_counter + 32'd1" in text
    core_instance = text.split("recurrent_integrated_core_controller_v1 core_i", 1)[1].split(");", 1)[0]
    assert ".observed_last_tick_cycles" not in core_instance
    assert "tick_cycle_counter" not in core_instance


def test_m12_5_vivado_adds_only_one_32_bit_measurement_probe() -> None:
    text = (RTL / "vivado" / "create_m12_5_project.tcl").read_text(encoding="utf-8")
    assert 'set capture_module "m12_5_characterization_capture_controller_bd_v1"' in text
    assert "CONFIG.C_NUM_PROBE_IN {36}" in text
    assert "CONFIG.C_NUM_PROBE_OUT {6}" in text
    assert "CONFIG.C_PROBE_IN35_WIDTH {32}" in text
    assert (
        "connect_named_pair observed_last_tick_cycles        "
        "capture_0/observed_last_tick_cycles vio_m12_5/probe_in35"
    ) in text


def test_m12_5_capture_writes_exact_cycle_tsv_and_full_physical_trace() -> None:
    text = (RTL / "vivado" / "capture_m12_5_characterization.tcl").read_text(encoding="utf-8")
    assert "if {$argc != 5}" in text
    assert "observed_last_tick_cycles" in text
    assert (
        'case_id\\tcase_name\\ttick\\tcycles\\texternal_events\\t'
        'recurrent_events\\trouted_events'
    ) in text
    assert "set tick_cycles [probe_uint $p_tick_cycles]" in text
    assert "if {$tick_cycles <= 0}" in text
    assert "$case_id\\t$case_name\\t$expected_tick\\t$tick_cycles" in text
    assert "trace_read_word" in text
    assert "state_before_words" in text
    assert "state_after_words" in text
    assert "synaptic_input" in text
    assert "M12.5 physical characterization capture completed successfully:" in text


def test_m12_5_hardware_runner_requires_exact_behavior_before_characterization() -> None:
    text = (RTL / "run_m12_5_hardware_characterization.sh").read_text(encoding="utf-8")
    validator_call = text.index('python3 "$SUITE_VALIDATOR"')
    exact_marker = text.index("M12.4 exact broad physical differential passed: cases=22 ticks=166 mismatches=0")
    analyzer_call = text.index('python3 "$ANALYZER"')
    assert validator_call < exact_marker < analyzer_call
    assert "cycle_rows" in text and "166" in text
    assert '"$CHAR_DIR/case_scaling.csv"' in text
    assert "M12.5 physical characterization completed successfully." in text


def test_m12_5_bitstream_reuses_m12_4_workload_authority_and_has_own_artifacts() -> None:
    text = (RTL / "run_m12_5_bitstream.sh").read_text(encoding="utf-8")
    assert 'LOCAL_BUILD_DIR="$SCRIPT_DIR/build/m12_5"' in text
    assert 'LOG_FILE="$LOCAL_BUILD_DIR/m12_5_vivado.log"' in text
    assert "generate_m12_4_broad_corpus.py" in text
    assert "generated_m12_4_broad_cases.svh" in text
    assert "m12_5_characterization_capture_controller_v1.sv" in text
    assert "create_m12_5_project.tcl" in text
    assert "neuromorphic_twin_m12_5.bit" in text
    assert "M12.5 routed bitstream flow completed successfully." in text


def test_m12_5_analysis_and_documentation_freeze_scaling_and_claim_boundaries() -> None:
    analyzer = (EXAMPLES / "analyze_m12_5_characterization.py").read_text(encoding="utf-8")
    doc = (DOCS / "M12_5_CHARACTERIZATION.md").read_text(encoding="utf-8")
    assert 'output_dir / "case_scaling.csv"' in analyzer
    assert "total_synapse_visits" in analyzer
    assert "mean_cycles" in analyzer
    assert "maximum Fmax" in doc
    assert "Power/energy is intentionally outside" in doc
    assert "Supported feature matrix" in doc
    assert "Explicit limitations" in doc
