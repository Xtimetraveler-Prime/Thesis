from __future__ import annotations

import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "examples" / "generate_m11_5_3_integrated_vectors.py"
INTEGRATED_RTL = ROOT / "rtl" / "core_v1" / "integrated_core_controller_v1.sv"
BD_WRAPPER = ROOT / "rtl" / "core_v1" / "integrated_core_controller_bd_v1.v"
TB = ROOT / "rtl" / "core_v1" / "tb" / "tb_neuromorphic_twin_m11_5_3.sv"
TCL = ROOT / "rtl" / "core_v1" / "vivado" / "create_m11_5_3_project.tcl"
RUNNER = ROOT / "rtl" / "core_v1" / "run_m11_5_3_real_ip.sh"


def test_m11_5_3_integrated_vectors_are_reproducible_and_composed_from_python(tmp_path) -> None:
    module = runpy.run_path(str(GENERATOR))
    write_include = module["write_systemverilog_include"]
    values = module["integrated_vectors"]()

    first = tmp_path / "first.svh"
    second = tmp_path / "second.svh"
    write_include(first)
    write_include(second)
    assert first.read_bytes() == second.read_bytes()

    assert len(values["config_words"]) == 16
    assert len(values["initial_state_words"]) == 16
    assert len(values["expected_accumulators"]) == 16
    assert len(values["expected_state_words"]) == 16
    assert len(values["expected_spikes"]) == 16
    assert any(value != 0 for value in values["expected_accumulators"])

    text = first.read_text(encoding="utf-8")
    assert "M11_5_3I_NEURON_COUNT = 16" in text
    assert "M11_5_3I_FORMAT_WORDS" in text
    assert "M11_5_3I_SYNAPSE_WORDS" in text
    assert "M11_5_3I_ROW_POINTERS" in text
    assert "M11_5_3I_EXPECTED_ACCUMULATORS" in text
    assert "M11_5_3I_EXPECTED_STATE_WORDS" in text
    assert "M11_5_3I_EXPECTED_SPIKES" in text


def test_m11_5_3_integrated_controller_has_no_host_accumulator_preload() -> None:
    text = INTEGRATED_RTL.read_text(encoding="utf-8")
    assert "module integrated_core_controller_v1" in text
    assert "phase_b_synapse_accumulator_v1" in text
    assert "neuron_array_controller_v1" in text
    assert "S_PHASE_B_START" in text
    assert "S_COPY_READ" in text
    assert "S_COPY_WRITE" in text
    assert "S_NEURON_TICK_START" in text
    assert "phase_b_debug_rdata" in text
    assert "neuron_accum_wdata = copy_data" in text
    assert "input  logic         accum_we" not in text


def test_m11_5_3_real_hls_testbench_never_preloads_accumulators() -> None:
    text = TB.read_text(encoding="utf-8")
    assert '`include "generated_m11_5_3_integrated_vectors.svh"' in text
    assert "M11_5_3I_FORMAT_WORDS" in text
    assert "M11_5_3I_SYNAPSE_WORDS" in text
    assert "M11_5_3I_ROW_POINTERS" in text
    assert "M11_5_3I_EXTERNAL_EVENTS" in text
    assert "M11_5_3I_RECURRENT_EVENTS" in text
    assert "M11_5_3I_EXPECTED_STATE_WORDS" in text
    assert "M11.5.3 packed-M08 + real-HLS integrated tick passed:" in text
    assert "accum_we" not in text
    assert "write_accum" not in text


def test_m11_5_3_vivado_flow_uses_real_packaged_hls_and_explicit_handshake() -> None:
    wrapper = BD_WRAPPER.read_text(encoding="utf-8")
    assert BD_WRAPPER.suffix == ".v"
    assert "module integrated_core_controller_bd_v1" in wrapper
    assert "FREQ_HZ 100000000" in wrapper
    assert "integrated_core_controller_v1" in wrapper

    tcl = TCL.read_text(encoding="utf-8")
    assert "create_bd_cell -type module -reference $controller_name controller_0" in tcl
    assert "create_bd_cell -type ip -vlnv $expected_vlnv neuron_step_v1_0" in tcl
    assert "hls_ap_start ap_start" in tcl
    assert "hls_ap_done  ap_done" in tcl
    assert "hls_ap_idle  ap_idle" in tcl
    assert "hls_ap_ready ap_ready" in tcl
    assert "connect_verified_pair $controller_pin $hls_pin" in tcl
    assert "validate_bd_design" in tcl
    assert "launch_simulation -simset sim_1 -mode behavioral" in tcl


def test_m11_5_3_real_ip_runner_regenerates_composed_python_expectations() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    assert 'EXPECTED_VERSION="2025.2"' in text
    assert 'EXPECTED_PART="xck26-sfvc784-2LV-c"' in text
    assert 'EXPECTED_VLNV="neuromorphic-twin.org:hls:neuron_step_v1:1.0"' in text
    assert "generate_m11_5_3_integrated_vectors.py" in text
    assert "integrated_core_controller_v1.sv" in text
    assert "integrated_core_controller_bd_v1.v" in text
    assert "create_m11_5_3_project.tcl" in text
    assert 'grep -Fq "$PASS_MARKER"' in text
