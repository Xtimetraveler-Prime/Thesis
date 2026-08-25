from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE_B = ROOT / "rtl" / "core_v1" / "phase_b_synapse_accumulator_v1.sv"
INTEGRATED = ROOT / "rtl" / "core_v1" / "integrated_core_controller_v1.sv"
RECURRENT = ROOT / "rtl" / "core_v1" / "recurrent_integrated_core_controller_v1.sv"
BD_WRAPPER = ROOT / "rtl" / "core_v1" / "recurrent_integrated_core_controller_bd_v1.v"
TCL = ROOT / "rtl" / "core_v1" / "vivado" / "create_m11_5_5_project.tcl"
XDC = ROOT / "rtl" / "core_v1" / "vivado" / "m11_5_5_timing.xdc"
RUNNER = ROOT / "rtl" / "core_v1" / "run_m11_5_5_synth.sh"


def test_phase_b_exposes_actual_external_event_memory_and_accumulator() -> None:
    text = PHASE_B.read_text(encoding="utf-8")
    assert "input  logic         debug_external_re" in text
    assert "input  logic [11:0]  debug_external_addr" in text
    assert "debug_external_rdata  <= external_event_mem[debug_external_addr];" in text
    assert "debug_accum_rdata  <= accumulator_mem[debug_accum_addr];" in text
    assert "if (!busy) begin" in text


def test_integrated_core_returns_pre_state_synaptic_sum_and_external_events() -> None:
    text = INTEGRATED.read_text(encoding="utf-8")
    assert "output logic [63:0]  debug_state_before_rdata" in text
    assert "output logic signed [63:0] debug_synaptic_input_rdata" in text
    assert "output logic [12:0]  trace_external_event_count" in text
    assert "assign debug_synaptic_input_rdata = phase_b_debug_rdata;" in text
    assert ".debug_state_before_rdata(debug_state_before_rdata)" in text
    assert ".debug_external_rdata(debug_external_rdata)" in text

    # Internal accumulator copy and host trace reads share the same verified
    # Phase-B debug port; the busy copy operation must retain priority.
    assert "(integration_state == S_COPY_READ)" in text
    assert "(debug_re && (integration_state == S_IDLE))" in text


def test_recurrent_top_exposes_complete_post_phase_f_trace_sources() -> None:
    text = RECURRENT.read_text(encoding="utf-8")
    for token in (
        "trace_external_event_count",
        "debug_state_before_rdata",
        "debug_synaptic_input_rdata",
        "external_debug_rvalid",
        "last_consumed_recurrent_count",
        "last_routed_count",
        "recurrent_current_bank",
        "recurrent_debug_rdata",
    ):
        assert token in text

    assert "assign trace_external_event_count = latched_external_count;" in text
    assert "assign external_debug_rvalid = (state == S_IDLE)" in text
    assert "assign recurrent_debug_rvalid = (state == S_IDLE)" in text
    assert "tick      <= core_tick;" in text
    assert "tick_done <= 1'b1;" in text


def test_vivado_module_reference_propagates_trace_ports() -> None:
    text = BD_WRAPPER.read_text(encoding="utf-8")
    for token in (
        "debug_state_before_rdata",
        "debug_synaptic_input_rdata",
        "trace_external_event_count",
        "external_debug_re",
        "external_debug_rdata",
        "recurrent_debug_rdata",
    ):
        assert token in text
    assert "recurrent_integrated_core_controller_v1 core_i" in text


def test_m11_5_5_synthesis_flow_records_resource_memory_and_timing_reports() -> None:
    tcl = TCL.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    xdc = XDC.read_text(encoding="utf-8")

    assert "create_clock -name ap_clk -period 10.000" in xdc
    assert 'set project_name "neuromorphic_twin_m11_5_5"' in tcl
    assert "trace_external_event_count" in tcl
    assert "debug_state_before_rdata" in tcl
    assert "debug_synaptic_input_rdata" in tcl
    assert "external_debug_rdata" in tcl
    assert "launch_runs synth_1" in tcl
    assert "wait_on_run synth_1" in tcl
    assert "report_utilization -file" in tcl
    assert "report_utilization -hierarchical" in tcl
    assert "report_ram_utilization -include_lutram" in tcl
    assert "report_timing_summary -file" in tcl
    assert "report_methodology -file" in tcl
    assert "write_checkpoint -force" in tcl

    assert 'EXPECTED_VERSION="2025.2"' in runner
    assert 'EXPECTED_PART="xck26-sfvc784-2LV-c"' in runner
    assert 'EXPECTED_VLNV="neuromorphic-twin.org:hls:neuron_step_v1:1.0"' in runner
    assert "m11_5_5_timing.xdc" in runner
    assert "create_m11_5_5_project.tcl" in runner
    assert "ram_utilization.csv" in runner
    assert "timing_summary_synth.rpt" in runner
    assert "M11.5.5 complete-core synthesis and reporting completed successfully." in runner
