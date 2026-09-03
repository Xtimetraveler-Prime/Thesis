from __future__ import annotations

import re
from pathlib import Path

from neuromorphic_twin.fpga_physical_trace import FpgaTraceReadSpace


ROOT = Path(__file__).resolve().parents[1]
BRIDGE_RTL = ROOT / "rtl" / "core_v1" / "m12_trace_read_bridge_v1.sv"
TB_RTL = ROOT / "rtl" / "core_v1" / "tb" / "tb_m12_trace_read_bridge_v1.sv"
RUNNER = ROOT / "rtl" / "core_v1" / "run_m12_1_2_trace_bridge_sim.sh"


def test_rtl_read_space_ids_match_frozen_python_transport_contract() -> None:
    text = BRIDGE_RTL.read_text(encoding="utf-8")
    names = {
        "TRACE_SPACE_STATE_BEFORE": FpgaTraceReadSpace.STATE_BEFORE,
        "TRACE_SPACE_STATE_AFTER": FpgaTraceReadSpace.STATE_AFTER,
        "TRACE_SPACE_SYNAPTIC_INPUT": FpgaTraceReadSpace.SYNAPTIC_INPUT,
        "TRACE_SPACE_SPIKE": FpgaTraceReadSpace.SPIKE,
        "TRACE_SPACE_EXTERNAL_EVENT": FpgaTraceReadSpace.EXTERNAL_EVENT,
        "TRACE_SPACE_RECURRENT_BANK0_EVENT": FpgaTraceReadSpace.RECURRENT_BANK0_EVENT,
        "TRACE_SPACE_RECURRENT_BANK1_EVENT": FpgaTraceReadSpace.RECURRENT_BANK1_EVENT,
    }
    for rtl_name, read_space in names.items():
        pattern = rf"localparam logic \[2:0\] {rtl_name}\s*=\s*3'd{int(read_space)};"
        assert re.search(pattern, text), f"missing frozen RTL selector for {read_space.name}"


def test_bridge_is_read_only_and_idle_gated() -> None:
    text = BRIDGE_RTL.read_text(encoding="utf-8")

    assert "assign req_ready = !pending && !core_busy;" in text
    assert "if (core_busy) begin" in text
    assert "request_addr_valid = !request_is_neuron_space || (req_addr[11:8] == 4'b0000);" in text

    # M12.1.2 must not gain a route into any architectural preload/write path.
    for forbidden_signal in (
        "config_we",
        "state_we",
        "format_we",
        "synapse_we",
        "row_we",
        "external_we",
        "route_row_we",
        "route_target_we",
        "spike_we",
    ):
        assert forbidden_signal not in text


def test_bridge_routes_only_to_existing_m11_debug_interfaces() -> None:
    text = BRIDGE_RTL.read_text(encoding="utf-8")

    assert "debug_re = 1'b1;" in text
    assert "external_debug_re = 1'b1;" in text
    assert "recurrent_debug_re   = 1'b1;" in text
    assert "recurrent_debug_bank = 1'b0;" in text
    assert "recurrent_debug_bank = 1'b1;" in text

    # All public payloads fit the single 64-bit transport word without changing
    # the underlying signed/two's-complement bit patterns.
    assert "pending_response_data  = debug_state_before_rdata;" in text
    assert "pending_response_data  = debug_state_rdata;" in text
    assert "pending_response_data  = debug_synaptic_input_rdata;" in text
    assert "pending_response_data  = {63'b0, debug_spike_rdata};" in text
    assert "pending_response_data  = {48'b0, external_debug_rdata};" in text
    assert "pending_response_data  = {48'b0, recurrent_debug_rdata};" in text


def test_xsim_regression_covers_all_spaces_and_protocol_guards() -> None:
    tb = TB_RTL.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")

    for selector in range(7):
        assert f"issue_and_check(3'd{selector}," in tb

    assert "issue_and_check(3'd7," in tb
    assert "req_ready asserted while core_busy" in tb
    assert "aliased neuron address touched the neuron debug interface" in tb
    assert "pending-read abort returned malformed error response" in tb
    assert "M12.1.2 trace-read bridge RTL tests passed:" in tb

    assert "EXPECTED_VERSION=\"2025.2\"" in runner
    assert "xvlog --sv" in runner
    assert "xelab tb_m12_trace_read_bridge_v1" in runner
    assert "xsim \"$SNAPSHOT\" -runall" in runner
    assert "PASS_MARKER=\"M12.1.2 trace-read bridge RTL tests passed:\"" in runner
