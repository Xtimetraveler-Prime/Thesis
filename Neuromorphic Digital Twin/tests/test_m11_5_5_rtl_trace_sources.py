from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEURON_RTL = ROOT / "rtl" / "core_v1" / "neuron_array_controller_v1.sv"


def test_neuron_controller_captures_passive_pre_tick_state_image() -> None:
    text = NEURON_RTL.read_text(encoding="utf-8")

    assert 'logic [63:0]  trace_state_before_mem [0:MAX_NEURONS-1];' in text
    assert 'output logic [63:0]  debug_state_before_rdata' in text
    assert 'debug_state_before_rdata <= trace_state_before_mem[debug_addr];' in text
    assert 'trace_state_before_mem[active_neuron] <= work_state;' in text

    # Capture occurs only after the existing configuration-validity check and
    # before the HLS launch state. It is not allowed to replace work_state or
    # participate in state writeback.
    validate = text.index('S_TICK_VALIDATE: begin')
    capture = text.index('trace_state_before_mem[active_neuron] <= work_state;', validate)
    launch = text.index('controller_state <= S_HLS_WAIT_READY;', validate)
    assert validate < capture < launch

    commit = text.index('S_HLS_COMMIT: begin')
    commit_end = text.index('default: begin', commit)
    assert 'trace_state_before_mem' not in text[commit:commit_end]


def test_trace_state_memory_is_not_used_as_hls_input() -> None:
    text = NEURON_RTL.read_text(encoding="utf-8")
    hls_assignments = text[text.index('assign hls_current_before'):text.index('wire unused_hls_idle')]
    assert 'trace_state_before_mem' not in hls_assignments
    assert 'assign hls_current_before      = $signed(work_state[23:0]);' in hls_assignments
    assert 'assign hls_voltage_before      = $signed(work_state[47:24]);' in hls_assignments
