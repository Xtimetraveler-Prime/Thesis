from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE_B = ROOT / "rtl" / "core_v1" / "phase_b_synapse_accumulator_v1.sv"
NEURON = ROOT / "rtl" / "core_v1" / "neuron_array_controller_v1.sv"
ROUTE = ROOT / "rtl" / "core_v1" / "recurrent_route_queue_v1.sv"
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
    assert "external_mem_rdata <= external_event_mem[external_mem_raddr];" in text
    assert "accumulator_mem_rdata <= accumulator_mem[accumulator_mem_raddr];" in text
    assert "assign debug_external_rdata = external_mem_rdata;" in text
    assert "assign debug_accum_rdata = accumulator_mem_rdata;" in text


def test_large_runtime_memories_use_synchronous_bram_friendly_ports() -> None:
    phase_b = PHASE_B.read_text(encoding="utf-8")
    neuron = NEURON.read_text(encoding="utf-8")
    route = ROUTE.read_text(encoding="utf-8")

    # Phase-B accumulation used to read accumulator_mem asynchronously, which
    # prevents dedicated block-RAM inference and creates a deep LUT read mux.
    assert "S_ACCUM_READ" in phase_b
    assert "accumulator_mem_re" in phase_b
    assert "accumulator_mem_rdata" in phase_b
    assert "current_accumulator = accumulator_mem" not in phase_b
    assert "external_mem_rdata <= external_event_mem[external_mem_raddr];" in phase_b
    assert "recurrent_mem_rdata <= recurrent_event_mem[recurrent_mem_raddr];" in phase_b

    # Neuron state and copied Phase-B accumulators likewise use registered RAM
    # outputs before HLS launch.
    assert "S_TICK_CAPTURE" in neuron
    assert "state_mem_rdata <= neuron_state_mem[state_mem_raddr];" in neuron
    assert "accum_mem_rdata <= synaptic_accum_mem[accum_mem_raddr];" in neuron
    assert "work_state       <= state_mem_rdata;" in neuron
    assert "work_accum       <= accum_mem_rdata;" in neuron

    # Both physical recurrent banks have one synchronous write/read process.
    assert "bank0_mem_rdata <= recurrent_bank0[bank0_mem_raddr];" in route
    assert "bank1_mem_rdata <= recurrent_bank1[bank1_mem_raddr];" in route
    assert "assign debug_rdata = debug_bank ? bank1_mem_rdata : bank0_mem_rdata;" in route


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
    assert "report_timing -delay_type max" in tcl
    assert "report_timing -delay_type min" in tcl
    assert "report_methodology -file" in tcl
    assert "write_checkpoint -force" in tcl

    assert 'EXPECTED_VERSION="2025.2"' in runner
    assert 'EXPECTED_PART="xck26-sfvc784-2LV-c"' in runner
    assert 'EXPECTED_VLNV="neuromorphic-twin.org:hls:neuron_step_v1:1.0"' in runner
    assert "m11_5_5_timing.xdc" in runner
    assert "create_m11_5_5_project.tcl" in runner
    assert "ram_utilization.csv" in runner
    assert "timing_summary_synth.rpt" in runner
    assert 'require_tool python3' in runner
    assert 'checks = (' in runner
    assert '("CLB LUTs", "CLB_LUT")' in runner
    assert '("Block RAM Tile", "BRAM_TILE")' in runner
    assert "used > available" in runner
    assert "M11.5.5 resource capacity check passed:" in runner
    assert "M11.5.5 complete-core synthesis and reporting completed successfully." in runner
