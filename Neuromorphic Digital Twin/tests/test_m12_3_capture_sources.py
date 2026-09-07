from __future__ import annotations

from pathlib import Path

from examples.generate_m12_3_multitick_corpus import write_systemverilog_include


ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl" / "core_v1"
CONTROLLER = RTL / "m12_3_multitick_capture_controller_v1.sv"
WRAPPER = RTL / "m12_3_multitick_capture_controller_bd_v1.v"
PROJECT_TCL = RTL / "vivado" / "create_m12_3_project.tcl"
CAPTURE_TCL = RTL / "vivado" / "capture_m12_3_multitick.tcl"
BITSTREAM_RUNNER = RTL / "run_m12_3_bitstream.sh"
HARDWARE_RUNNER = RTL / "run_m12_3_hardware_suite.sh"
ROUTE = RTL / "recurrent_route_queue_v1.sv"


def test_generated_m12_3_include_contains_inputs_only(tmp_path: Path) -> None:
    output = write_systemverilog_include(tmp_path / "generated_m12_3_multitick_cases.svh")
    text = output.read_text(encoding="utf-8")
    assert "M12_3_CASE_COUNT = 10" in text
    assert "M12_3_MAX_TICKS = 6" in text
    assert "M12_3_TICK_COUNTS" in text
    assert "M12_3_EXTERNAL_COUNTS" in text
    assert "M12_3_EXTERNAL_EVENTS" in text
    assert "M12_3_ROUTE_TARGETS" in text
    assert "INPUTS ONLY" in text
    for forbidden in (
        "M12_3_EXPECTED",
        "RECURRENT_SCHEDULE",
        "RECURRENT_EVENTS",
        "EXPECTED_SPIKES",
        "EXPECTED_STATES",
    ):
        assert forbidden not in text


def test_controller_is_case_selectable_multitick_and_never_embeds_golden_outputs() -> None:
    text = CONTROLLER.read_text(encoding="utf-8")
    assert '`include "generated_m12_3_multitick_cases.svh"' in text
    assert "logic [7:0]  tick_index;" in text
    assert "case_tick_count     = M12_3_TICK_COUNTS[active_case_id];" in text
    assert "(active_case_id * M12_3_MAX_TICKS) + tick_index" in text
    assert "core_tick != ({24'd0, tick_index} + 32'd1)" in text
    assert "(tick_index + 8'd1) >= case_tick_count" in text
    assert "capture_step_pulse && !capture_done" in text
    assert "tick_index <= tick_index + 8'd1;" in text
    assert "M12_3_EXTERNAL_COUNTS[" in text
    assert "M12_3_EXTERNAL_EVENTS[" in text
    assert "M12_3_EXPECTED" not in text
    assert "RECURRENT_SCHEDULE" not in text
    assert "RECURRENT_EVENTS" not in text


def test_next_tick_external_events_are_loaded_only_after_host_releases_trace_window() -> None:
    text = CONTROLLER.read_text(encoding="utf-8")
    # Initial state load reaches READY without touching external memory.
    assert "S_LOAD_STATE: begin" in text
    state_block = text.split("S_LOAD_STATE: begin", 1)[1].split("S_LOAD_EXTERNAL: begin", 1)[0]
    assert "state <= S_READY_TICK;" in state_block
    assert "S_LOAD_EXTERNAL" not in state_block

    # A step from READY decides whether to load the current tick's external
    # events; a step from CAPTURE_HOLD advances the tick and does the same.
    ready_block = text.split("S_READY_TICK: begin", 1)[1].split("S_TICK_PULSE: begin", 1)[0]
    assert "if (case_external_count == 0)" in ready_block
    assert "state <= S_LOAD_EXTERNAL;" in ready_block
    hold_block = text.split("S_CAPTURE_HOLD: begin", 1)[1].split("S_FAIL: begin", 1)[0]
    assert "capture_step_pulse && !capture_done" in hold_block
    assert "state <= S_LOAD_EXTERNAL;" in hold_block
    assert "external-event loading and tick launch" in hold_block


def test_controller_preserves_corrected_recurrent_debug_readback_path() -> None:
    controller = CONTROLLER.read_text(encoding="utf-8")
    route = ROUTE.read_text(encoding="utf-8")
    for signal in (
        "observed_route_target_write_seen",
        "observed_route_target_read_data",
        "observed_recurrent_bank_write_seen",
        "observed_recurrent_bank_write_bank",
        "observed_recurrent_bank_write_addr",
        "observed_recurrent_bank_write_data",
    ):
        assert signal in controller
    assert "logic        debug_bank_latched;" in route
    assert "assign debug_rdata = debug_bank_latched ? bank1_mem_rdata : bank0_mem_rdata;" in route
    assert "debug_bank_latched <= debug_bank;" in route


def test_vivado_project_reuses_proven_35_input_vio_and_k26_clock_reset_shell() -> None:
    project = PROJECT_TCL.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")
    assert 'set project_name "neuromorphic_twin_m12_3"' in project
    assert 'set capture_module "m12_3_multitick_capture_controller_bd_v1"' in project
    assert "CONFIG.C_NUM_PROBE_IN {35}" in project
    assert "CONFIG.C_NUM_PROBE_OUT {6}" in project
    assert "CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {100}" in project
    assert "proc_sys_reset_m12_3" in project
    assert "vio_m12_3" in project
    assert "m12_3_multitick_capture_controller_v1 capture_i" in wrapper


def test_hardware_capture_loops_every_committed_tick_and_reads_both_recurrent_roles() -> None:
    text = CAPTURE_TCL.read_text(encoding="utf-8")
    assert "case_id\\tcase_name\\tneuron_count\\ttick_count" in text
    assert "for {set expected_tick 1} {$expected_tick <= $tick_count} {incr expected_tick}" in text
    assert "[probe_uint $p_tick] == $expected_tick" in text
    assert "set expected_done [expr {$expected_tick == $tick_count ? 1 : 0}]" in text
    assert "set routed_space 5" in text
    assert "set consumed_space 6" in text
    assert "set routed_space 6" in text
    assert "set consumed_space 5" in text
    assert "for {set idx 0} {$idx < $consumed_count} {incr idx}" in text
    assert "for {set idx 0} {$idx < $routed_count} {incr idx}" in text
    assert 'puts $fh "    \\{"' in text
    assert 'puts $fh "    \\},"' in text
    assert "M12.3 captured physical case $case_id tick $expected_tick/$tick_count:" in text
    assert "cases=$captured_cases ticks=$captured_ticks" in text


def test_bitstream_runner_generates_input_only_corpus_and_expected_artifacts() -> None:
    text = BITSTREAM_RUNNER.read_text(encoding="utf-8")
    assert 'LOCAL_BUILD_DIR="$SCRIPT_DIR/build/m12_3"' in text
    assert "m12_3_multitick_capture_controller_v1.sv" in text
    assert "m12_3_multitick_capture_controller_bd_v1.v" in text
    assert "generated_m12_3_multitick_cases.svh" in text
    assert "generate_m12_3_multitick_corpus.py" in text
    assert "M12.3 directed cases: 10" in text
    assert "M12.3 directed committed ticks: 40" in text
    assert "RECURRENT_SCHEDULE" in text
    assert "neuromorphic_twin_m12_3.bit" in text
    assert "neuromorphic_twin_m12_3.ltx" in text
    assert "M12.3 routed bitstream flow completed successfully." in text


def test_hardware_suite_requires_10_cases_40_ticks_zero_diff_and_independent_replay() -> None:
    text = HARDWARE_RUNNER.read_text(encoding="utf-8")
    assert "capture_m12_3_multitick.tcl" in text
    assert "validate_m12_3_physical_suite.py" in text
    assert "validate_m12_3_physical_case.py" in text
    assert "validate_m12_3_reset_replay.py" in text
    assert "cases=10 ticks=40" in text
    assert '"${#physical_files[@]}" -ne 10' in text
    assert "REPLAY_CASE_ID=2" in text
    assert 'REPLAY_CASE_NAME="two-neuron-recurrent-loop"' in text
    assert "reset_replay_case.tsv" in text
    assert "m12_3_reset_replay.log" in text
    assert "M12.3 physical multi-tick/recurrent suite completed successfully." in text
