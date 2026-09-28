from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "examples" / "generate_m11_5_5_trace_vectors.py"
TB = ROOT / "rtl" / "core_v1" / "tb" / "tb_neuromorphic_twin_m11_5_5_trace.sv"
TCL = ROOT / "rtl" / "core_v1" / "vivado" / "create_m11_5_5_trace_project.tcl"
RUNNER = ROOT / "rtl" / "core_v1" / "run_m11_5_5_trace_sim.sh"
SYNTH_TCL = ROOT / "rtl" / "core_v1" / "vivado" / "create_m11_5_5_project.tcl"
SYNTH_RUNNER = ROOT / "rtl" / "core_v1" / "run_m11_5_5_synth.sh"


def _load_generator():
    spec = importlib.util.spec_from_file_location("m11_5_5_trace_vectors", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_trace_state_before_is_previous_committed_state() -> None:
    module = _load_generator()
    values = module.integrated_vectors()
    words = module.trace_state_before_words()
    neurons = module.M11_5_4I_NEURON_COUNT
    ticks = module.M11_5_4I_TICK_COUNT

    assert len(words) == neurons * ticks
    assert words[:neurons] == tuple(values["initial_state_words"])
    states = tuple(values["expected_states"])
    for tick_index in range(1, ticks):
        start = tick_index * neurons
        assert words[start : start + neurons] == tuple(states[tick_index - 1])


def test_trace_testbench_checks_every_m10_hardware_source() -> None:
    text = TB.read_text(encoding="utf-8")
    for token in (
        "debug_state_before_rdata",
        "debug_state_rdata",
        "debug_synaptic_input_rdata",
        "debug_spike_rdata",
        "trace_external_event_count",
        "external_debug_rdata",
        "last_consumed_recurrent_count",
        "last_routed_count",
        "recurrent_debug_rdata",
        "M11_5_5_EXPECTED_STATE_BEFORE",
        "M11_5_4I_EXPECTED_ACCUMULATORS",
    ):
        assert token in text

    assert "consumed_bank = ~recurrent_current_bank;" in text
    assert "if ((tick-1) !== t)" in text
    assert "observed_cleared_accum !== 64'sd0" in text
    assert "M11.5.5 trace snapshot + real-HLS recurrent regression passed" in text


def test_trace_vivado_flow_uses_real_packaged_hls_and_all_trace_ports() -> None:
    tcl = TCL.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")

    assert "create_bd_cell -type ip -vlnv $expected_vlnv neuron_step_v1_0" in tcl
    assert "connect_verified_pair" in tcl
    assert "trace_external_event_count" in tcl
    assert "debug_state_before_rdata" in tcl
    assert "debug_synaptic_input_rdata" in tcl
    assert "external_debug_rdata" in tcl
    assert "recurrent_debug_rdata" in tcl
    assert "launch_simulation -simset sim_1 -mode behavioral" in tcl
    assert "run all" in tcl

    assert 'EXPECTED_VERSION="2025.2"' in runner
    assert 'EXPECTED_PART="xck26-sfvc784-2LV-c"' in runner
    assert 'EXPECTED_VLNV="neuromorphic-twin.org:hls:neuron_step_v1:1.0"' in runner
    assert "generate_m11_5_4_integrated_vectors.py" in runner
    assert "generate_m11_5_5_trace_vectors.py" in runner
    assert "M11.5.5 trace snapshot + real packaged HLS IP simulation completed successfully." in runner


def test_synthesis_flow_records_explicit_setup_and_hold_paths() -> None:
    tcl = SYNTH_TCL.read_text(encoding="utf-8")
    runner = SYNTH_RUNNER.read_text(encoding="utf-8")

    assert "report_timing -delay_type max" in tcl
    assert "setup_paths_synth.rpt" in tcl
    assert "report_timing -delay_type min" in tcl
    assert "hold_paths_synth.rpt" in tcl
    assert "M11.5.5 synthesis worst hold slack:" in tcl
    assert "setup_paths_synth.rpt" in runner
    assert "hold_paths_synth.rpt" in runner
