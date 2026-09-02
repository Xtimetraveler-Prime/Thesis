from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl" / "core_v1"
CAPTURE = RTL / "m12_1_capture_controller_v1.sv"
CAPTURE_BD = RTL / "m12_1_capture_controller_bd_v1.v"
PROJECT_TCL = RTL / "vivado" / "create_m12_1_3_project.tcl"
CAPTURE_TCL = RTL / "vivado" / "capture_m12_1_3_trace.tcl"
BITSTREAM_SH = RTL / "run_m12_1_3_bitstream.sh"
HARDWARE_SH = RTL / "run_m12_1_3_hardware_capture.sh"


def test_capture_shell_uses_inputs_but_never_embeds_golden_outputs() -> None:
    text = CAPTURE.read_text(encoding="utf-8")

    assert '`include "generated_m11_5_4_integrated_vectors.svh"' in text
    assert "M11_5_4I_CONFIG_WORDS" in text
    assert "M11_5_4I_INITIAL_STATE_WORDS" in text
    assert "M11_5_4I_EXTERNAL_COUNTS" in text
    assert "M11_5_4I_ROUTE_TARGETS" in text
    assert "M11_5_4I_EXPECTED" not in text

    assert "recurrent_integrated_core_controller_v1 core_i" in text
    assert "m12_trace_read_bridge_v1 trace_bridge_i" in text


def test_capture_shell_holds_an_atomic_post_tick_trace_window() -> None:
    text = CAPTURE.read_text(encoding="utf-8")

    assert "assign trace_window_open = (state == S_CAPTURE_HOLD);" in text
    assert "assign bridge_busy_guard = core_busy || !trace_window_open;" in text
    assert "if (capture_step_pulse && !capture_done)" in text
    assert "wire capture_step_pulse = capture_step && !capture_step_d;" in text

    tick_wait = text.index("S_TICK_WAIT: begin")
    hold = text.index("S_CAPTURE_HOLD: begin")
    assert tick_wait < hold


def test_slow_vio_trace_requests_and_responses_are_edge_and_sequence_guarded() -> None:
    text = CAPTURE.read_text(encoding="utf-8")

    assert "wire trace_read_req_pulse = trace_read_req && !trace_read_req_d;" in text
    assert ".req_valid(trace_read_req_pulse)" in text
    assert "trace_response_seq   <= trace_response_seq + 16'd1;" in text
    assert "trace_response_data  <= bridge_rsp_data;" in text
    assert "trace_response_error <= bridge_rsp_error;" in text


def test_vivado_shell_exposes_complete_capture_and_trace_api() -> None:
    wrapper = CAPTURE_BD.read_text(encoding="utf-8")
    tcl = PROJECT_TCL.read_text(encoding="utf-8")

    for signal in (
        "trace_window_open",
        "observed_recurrent_bank0_count",
        "observed_recurrent_bank1_count",
        "observed_consumed_recurrent_count",
        "observed_routed_recurrent_count",
        "observed_external_event_count",
        "trace_response_seq",
        "trace_response_space",
        "trace_response_addr",
        "trace_response_data",
        "trace_response_error",
    ):
        assert signal in wrapper
        assert signal in tcl

    assert "CONFIG.C_NUM_PROBE_IN {26}" in tcl
    assert "CONFIG.C_NUM_PROBE_OUT {6}" in tcl
    assert "connect_named_pair capture_resetn" in tcl
    assert "connect_named_pair trace_read_space" in tcl
    assert "connect_named_pair trace_read_addr" in tcl


def test_host_capture_emits_versioned_machine_readable_artifact() -> None:
    text = CAPTURE_TCL.read_text(encoding="utf-8")

    assert 'set SCENARIO_ID "m11_5_4_recurrent_chain_physical_trace_v1"' in text
    assert "set NEURON_COUNT 3" in text
    assert "set TICK_COUNT 4" in text
    # The JSON is emitted from Tcl double-quoted strings, so the source file
    # necessarily contains escaped quote characters even though the resulting
    # artifact contains ordinary JSON string literals.
    assert r'\"neuromorphic-twin-physical-fpga-trace-v1\"' in text
    assert r'\"jtag-vio\"' in text
    assert "trace_response_seq" in text
    assert "Trace response tag mismatch" in text

    # Per-neuron spaces 0-3 are explicit numeric trace_read_word calls. Assert
    # the stable tail of each call rather than assuming a Tcl loop variable named
    # $space exists in the capture script.
    for space in range(4):
        assert f"$p_trace_addr {space} $neuron]" in text
    assert "$p_trace_addr 4 $idx]" in text

    # Recurrent spaces 5 and 6 are selected dynamically from current_bank so the
    # current-bank prefix is routed output and the opposite prefix is consumed input.
    assert "set routed_space 5" in text
    assert "set consumed_space 6" in text
    assert "set routed_space 6" in text
    assert "set consumed_space 5" in text
    assert "$p_trace_addr $consumed_space $idx]" in text
    assert "$p_trace_addr $routed_space $idx]" in text


def test_m12_1_3_build_and_physical_scripts_are_source_controlled() -> None:
    build = BITSTREAM_SH.read_text(encoding="utf-8")
    hardware = HARDWARE_SH.read_text(encoding="utf-8")

    assert "create_m12_1_3_project.tcl" in build
    assert "m12_trace_read_bridge_v1.sv" in build
    assert "m12_1_capture_controller_v1.sv" in build
    assert "M12.1.3 routed timing check passed:" in build

    assert "capture_m12_1_3_trace.tcl" in hardware
    assert "validate_m12_1_3_physical_trace.py" in hardware
    assert "m11_5_4_recurrent_chain_physical_trace_v1.json" in hardware
