from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl" / "core_v1"
CONTROLLER = RTL / "m12_2_single_tick_capture_controller_v1.sv"
WRAPPER = RTL / "m12_2_single_tick_capture_controller_bd_v1.v"
GENERATOR = ROOT / "examples" / "generate_m12_2_single_tick_corpus.py"


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
    assert "expected outputs stay host-side" in generator
    assert 'emit("M12_2_CONFIG_WORDS"' in generator
    assert 'emit("M12_2_INITIAL_STATE_WORDS"' in generator
    assert 'emit("M12_2_EXTERNAL_EVENTS"' in generator
    assert 'emit("M12_2_EXPECTED' not in generator


def test_case_selection_reuses_existing_vio_address_and_is_physically_witnessed() -> None:
    text = CONTROLLER.read_text(encoding="utf-8")

    assert "active_case_id <= trace_read_addr[7:0];" in text
    assert "if (trace_read_addr >= M12_2_CASE_COUNT)" in text
    assert "CAPTURE_FAULT_CASE_SELECT" in text
    assert "assign capture_phase = {active_case_id[3:0], state};" in text


def test_arbitrary_initial_state_is_loaded_only_after_architectural_reset() -> None:
    text = CONTROLLER.read_text(encoding="utf-8")

    reset_wait = text.index("S_RESET_WAIT: begin")
    load_state = text.index("S_LOAD_STATE: begin", reset_wait)
    load_external = text.index("S_LOAD_EXTERNAL: begin", load_state)
    ready = text.index("S_READY_TICK: begin", load_external)
    assert reset_wait < load_state < load_external < ready

    reset_block = text[reset_wait:load_state]
    assert "core_reset_done" in reset_block
    assert "state <= S_LOAD_STATE;" in reset_block
    assert "M12.2 initial state is intentionally loaded AFTER" in text


def test_zero_route_and_zero_external_cases_skip_empty_loads() -> None:
    text = CONTROLLER.read_text(encoding="utf-8")

    assert "if (case_route_count == 0)" in text
    assert "state <= S_RESET_PULSE;" in text
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


def test_m12_2_wrapper_keeps_m12_1_vio_compatible_port_shape() -> None:
    text = WRAPPER.read_text(encoding="utf-8")

    assert "module m12_2_single_tick_capture_controller_bd_v1" in text
    assert "m12_2_single_tick_capture_controller_v1 capture_i" in text
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
        assert signal in text
