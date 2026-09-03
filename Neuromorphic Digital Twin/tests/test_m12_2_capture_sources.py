from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl" / "core_v1"
CONTROLLER = RTL / "m12_2_single_tick_capture_controller_v1.sv"
WRAPPER = RTL / "m12_2_single_tick_capture_controller_bd_v1.v"
GENERATOR = ROOT / "examples" / "generate_m12_2_single_tick_corpus.py"
PROJECT_TCL = RTL / "vivado" / "create_m12_2_project.tcl"
CAPTURE_TCL = RTL / "vivado" / "capture_m12_2_single_tick.tcl"
BITSTREAM_SH = RTL / "run_m12_2_bitstream.sh"
HARDWARE_SH = RTL / "run_m12_2_hardware_suite.sh"
VALIDATOR = ROOT / "examples" / "validate_m12_2_physical_suite.py"


def test_m12_2_fpga_source_cannot_consult_python_golden_outputs() -> None:
    controller = CONTROLLER.read_text(encoding="utf-8")
    generator = GENERATOR.read_text(encoding="utf-8")

    assert '`include "generated_m12_2_single_tick_cases.svh"' in controller
    assert "M12_2_CONFIG_WORDS" in controller
    assert "M12_2_INITIAL_STATE_WORDS" in controller
    assert "M12_2_FORMAT_WORDS" in controller
    assert "M12_2_EXTERNAL_EVENTS" in controller
    assert "M12_2_EXPECTED" not in controller

    # The SV generator is intentionally input-only. Golden values are written to
    # host JSON by write_m12_single_tick_corpus(), never emitted as SV arrays.
    assert "write_m12_single_tick_corpus" in generator
    assert "Python-golden outputs stay host-side" in generator
    assert "expected outputs are deliberately kept out of FPGA-visible source" in generator
    for array_name in (
        "M12_2_CONFIG_WORDS",
        "M12_2_INITIAL_STATE_WORDS",
        "M12_2_FORMAT_WORDS",
        "M12_2_SYNAPSE_WORDS",
        "M12_2_WEIGHT_ROWS",
        "M12_2_ROUTE_ROWS",
        "M12_2_ROUTE_TARGETS",
        "M12_2_EXTERNAL_EVENTS",
    ):
        assert f'"{array_name}"' in generator
    assert '"M12_2_EXPECTED' not in generator
    assert "hardware_cases.tsv" in generator


def test_case_selection_reuses_existing_vio_address_and_is_physically_witnessed() -> None:
    text = CONTROLLER.read_text(encoding="utf-8")

    assert "active_case_id <= trace_read_addr[7:0];" in text
    assert "if (trace_read_addr >= M12_2_CASE_COUNT)" in text
    assert "CAPTURE_FAULT_CASE_SELECT" in text
    assert "assign capture_phase = {active_case_id[3:0], state};" in text


def test_each_case_resets_before_static_reload_and_initial_state() -> None:
    text = CONTROLLER.read_text(encoding="utf-8")

    reset_wait = text.index("S_RESET_WAIT: begin")
    reset_block = text[reset_wait:text.index("S_LOAD_STATE: begin", reset_wait)]
    assert "core_reset_done" in reset_block
    assert "state <= S_LOAD_CONFIG;" in reset_block
    assert "reconfiguration begins only AFTER architectural" in text
    assert "state <= S_LOAD_STATE;" in text[text.index("S_LOAD_ROUTE_TARGET: begin"):reset_wait]


def test_zero_route_and_zero_external_cases_skip_empty_loads() -> None:
    text = CONTROLLER.read_text(encoding="utf-8")

    assert "if (case_route_count == 0)" in text
    assert "state <= S_LOAD_STATE;" in text
    assert "if (case_external_count == 0)" in text
    assert "state <= S_READY_TICK;" in text


def test_single_tick_capture_uses_existing_passive_trace_bridge_and_atomic_hold() -> None:
    text = CONTROLLER.read_text(encoding="utf-8")

    assert "recurrent_integrated_core_controller_v1 core_i" in text
    assert "m12_trace_read_bridge_v1 trace_bridge_i" in text
    assert "assign trace_window_open = (state == S_CAPTURE_HOLD);" in text
    assert "assign bridge_busy_guard = core_busy || !trace_window_open;" in text
    assert "wire trace_read_req_pulse = trace_read_req && !trace_read_req_d;" in text
    assert ".req_valid(trace_read_req_pulse)" in text
    assert "if (core_tick != 32'd1)" in text
    assert "capture_done <= 1'b1;" in text


def test_m12_2_wrapper_and_vivado_project_keep_m12_1_vio_shape() -> None:
    wrapper = WRAPPER.read_text(encoding="utf-8")
    project = PROJECT_TCL.read_text(encoding="utf-8")

    assert "module m12_2_single_tick_capture_controller_bd_v1" in wrapper
    assert "m12_2_single_tick_capture_controller_v1 capture_i" in wrapper
    for signal in (
        "capture_start",
        "capture_step",
        "trace_read_req",
        "trace_read_space",
        "trace_read_addr",
        "trace_response_seq",
        "trace_response_data",
        "observed_recurrent_bank0_count",
        "observed_recurrent_bank1_count",
    ):
        assert signal in wrapper
        assert signal in project

    assert 'set project_name "neuromorphic_twin_m12_2"' in project
    assert 'set capture_module "m12_2_single_tick_capture_controller_bd_v1"' in project
    assert "CONFIG.C_NUM_PROBE_IN {26}" in project
    assert "CONFIG.C_NUM_PROBE_OUT {6}" in project
    assert "neuromorphic_twin_m12_2.bit" in project
    assert "M12.2 routed timing check passed:" in project


def test_hardware_capture_programs_once_then_selects_and_captures_all_cases() -> None:
    text = CAPTURE_TCL.read_text(encoding="utf-8")

    assert text.count("program_hw_devices $dev") == 1
    assert r"case_id\tcase_name\tneuron_count" in text
    assert "foreach record $case_lines" in text
    assert "set_probe_uint $p_trace_addr $case_id" in text
    assert "set selected_case [expr {($phase >> 4) & 0xF}]" in text
    assert "M12.2 captured physical case $case_id:" in text
    assert "M12.2 physical directed suite capture completed successfully:" in text
    for space in range(4):
        assert f"$p_trace_addr {space} $neuron]" in text
    assert "$p_trace_addr 4 $idx]" in text
    assert "$p_trace_addr $consumed_space $idx]" in text
    assert "$p_trace_addr $routed_space $idx]" in text


def test_build_and_suite_wrappers_enforce_physical_zero_mismatch_gate() -> None:
    build = BITSTREAM_SH.read_text(encoding="utf-8")
    hardware = HARDWARE_SH.read_text(encoding="utf-8")
    validator = VALIDATOR.read_text(encoding="utf-8")

    assert "generate_m12_2_single_tick_corpus.py" in build
    assert "generated_m12_2_single_tick_cases.svh" in build
    assert "M12_2_EXPECTED" in build  # forbidden-array grep guard
    assert "create_m12_2_project.tcl" in build
    assert "M12.2 routed bitstream flow completed successfully." in build

    assert "capture_m12_2_single_tick.tcl" in hardware
    assert "hardware_cases.tsv" in hardware
    assert "expected 16 physical JSON artifacts" in hardware
    assert "validate_m12_2_physical_suite.py" in hardware
    assert "M12.2 physical directed single-tick suite completed successfully." in hardware

    assert "compare_m12_single_tick_capture" in validator
    assert "mismatch_total" in validator
    assert "M12.2 exact physical single-tick differential passed:" in validator
    assert "mismatches=0" in validator
