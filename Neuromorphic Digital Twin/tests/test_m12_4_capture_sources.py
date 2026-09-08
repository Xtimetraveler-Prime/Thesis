from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl" / "core_v1"
EXAMPLES = ROOT / "examples"


def test_m12_4_generator_uses_packed_offsets_and_input_only_boundary() -> None:
    text = (EXAMPLES / "generate_m12_4_broad_corpus.py").read_text(encoding="utf-8")
    assert "M12_4_CONFIG_OFFSETS" in text
    assert "M12_4_STATE_OFFSETS" in text
    assert "M12_4_ROUTE_TARGET_OFFSETS" in text
    assert "M12_4_CASE_TICK_BASES" in text
    assert "M12_4_EXTERNAL_TICK_OFFSETS" in text
    assert "M12_4_EXTERNAL_EVENTS" in text
    assert "_pad(" not in text
    assert "M12_4_MAX_EXTERNAL_EVENTS" not in text
    assert "M12_4_EXPECTED" not in text
    assert "RECURRENT_SCHEDULE" not in text


def test_m12_4_controller_consumes_packed_offsets_and_full_case_witness() -> None:
    text = (RTL / "m12_4_broad_capture_controller_v1.sv").read_text(encoding="utf-8")
    assert '`include "generated_m12_4_broad_cases.svh"' in text
    assert "case_config_offset + load_index" in text
    assert "case_state_offset + load_index" in text
    assert "case_format_offset + load_index" in text
    assert "case_synapse_offset + load_index" in text
    assert "case_weight_row_offset + load_index" in text
    assert "case_route_row_offset + load_index" in text
    assert "case_route_target_offset + load_index" in text
    assert "case_external_offset + load_index" in text
    assert "M12_4_CASE_TICK_BASES[active_case_id] + tick_index + 8'd1" in text
    assert "assign capture_phase = active_case_id;" in text
    assert "M12_4_MAX_TICKS" not in text
    assert "M12_4_MAX_EXTERNAL_EVENTS" not in text
    assert "M12_4_EXPECTED" not in text


def test_m12_4_controller_preserves_reset_then_arbitrary_state_contract() -> None:
    text = (RTL / "m12_4_broad_capture_controller_v1.sv").read_text(encoding="utf-8")
    reset_wait = text.index("S_RESET_WAIT: begin")
    load_state_transition = text.index("state <= S_LOAD_STATE;", reset_wait)
    load_state = text.index("S_LOAD_STATE: begin", load_state_transition)
    ready = text.index("state <= S_READY_TICK;", load_state)
    assert reset_wait < load_state_transition < load_state < ready
    assert "Configuration/weight/route memories are loaded first" in text


def test_m12_4_capture_tcl_accepts_22_case_metadata_and_full_case_id() -> None:
    text = (RTL / "vivado" / "capture_m12_4_broad.tcl").read_text(encoding="utf-8")
    assert (
        'case_id\\tcase_name\\tsource_kind\\tseed\\tconfiguration_sha256\\t'
        'neuron_count\\taxon_count\\tsynapse_count\\troute_count\\ttick_count'
    ) in text
    assert "if {[llength $fields] != 10}" in text
    assert "set selected_case $phase" in text
    assert "($phase >> 4)" not in text
    assert "source_kind=$source_kind seed=$seed config=$configuration_sha256" in text
    assert "M12.4 physical broad deterministic suite capture completed successfully:" in text


def test_m12_4_vivado_project_reuses_validated_vio_observation_shape() -> None:
    text = (RTL / "vivado" / "create_m12_4_project.tcl").read_text(encoding="utf-8")
    assert 'set capture_module "m12_4_broad_capture_controller_bd_v1"' in text
    assert "CONFIG.C_NUM_PROBE_IN {35}" in text
    assert "CONFIG.C_NUM_PROBE_OUT {6}" in text
    assert "observed_route_target_write_seen" in text
    assert "observed_recurrent_bank_write_data" in text
    assert "capture_m12_4_broad.tcl" in text


def test_m12_4_build_and_board_runners_have_frozen_case_tick_markers() -> None:
    bitstream = (RTL / "run_m12_4_bitstream.sh").read_text(encoding="utf-8")
    hardware = (RTL / "run_m12_4_hardware_suite.sh").read_text(encoding="utf-8")
    targeted = (RTL / "run_m12_4_case.sh").read_text(encoding="utf-8")

    assert "M12.4 broad cases: 22" in bitstream
    assert "M12.4 broad committed ticks: 166" in bitstream
    assert "generate_m12_4_broad_corpus.py" in bitstream
    assert "M12.4 routed bitstream flow completed successfully." in bitstream

    assert "cases=22 ticks=166" in hardware
    assert "M12.4 physical broad deterministic regression completed successfully." in hardware
    assert "validate_m12_4_physical_suite.py" in hardware

    assert "usage: $0 <case-id 0..21>" in targeted
    assert "configuration_sha256" in targeted
    assert "validate_m12_4_physical_case.py" in targeted
