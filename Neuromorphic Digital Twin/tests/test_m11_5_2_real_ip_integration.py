from __future__ import annotations

import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "examples" / "generate_m11_5_2_vectors.py"
BD_WRAPPER = ROOT / "rtl" / "core_v1" / "neuron_array_controller_bd_v1.v"
VIVADO_TCL = ROOT / "rtl" / "core_v1" / "vivado" / "create_m11_5_2_project.tcl"
REAL_IP_RUNNER = ROOT / "rtl" / "core_v1" / "run_m11_5_2_real_ip.sh"
REAL_IP_TB = ROOT / "rtl" / "core_v1" / "tb" / "tb_neuromorphic_twin_m11_5_2.sv"


def test_m11_5_2_vector_include_is_byte_reproducible(tmp_path) -> None:
    module = runpy.run_path(str(GENERATOR))
    write_include = module["write_systemverilog_include"]

    first = tmp_path / "first.svh"
    second = tmp_path / "second.svh"
    write_include(first)
    write_include(second)

    assert first.read_bytes() == second.read_bytes()
    text = first.read_text(encoding="utf-8")
    assert "M11_5_2_NEURON_COUNT = 64" in text
    assert "M11_5_2_SEED = 32'h4d313132" in text
    assert "M11_5_2_CONFIG_WORDS" in text
    assert "M11_5_2_INITIAL_STATE_WORDS" in text
    assert "M11_5_2_RESET_STATE_WORDS" in text
    assert "M11_5_2_ACCUM_WORDS" in text
    assert "M11_5_2_EXPECTED_STATE_WORDS" in text
    assert "M11_5_2_EXPECTED_SPIKES" in text
    assert "threshold_equality" in text
    assert "random_0039" in text


def test_m11_5_2_bd_wrapper_is_verilog_and_keeps_hls_control_scalar() -> None:
    assert BD_WRAPPER.suffix == ".v"
    text = BD_WRAPPER.read_text(encoding="utf-8")

    assert "module neuron_array_controller_bd_v1" in text
    assert "input  wire" in text
    assert "output wire" in text
    assert "output wire         hls_ap_start" in text
    assert "input  wire         hls_ap_done" in text
    assert "input  wire         hls_ap_idle" in text
    assert "input  wire         hls_ap_ready" in text
    assert "xilinx.com:interface:acc_handshake" not in text
    assert "neuron_array_controller_v1" in text


def test_m11_5_2_vivado_flow_uses_explicit_four_signal_hls_handshake() -> None:
    text = VIVADO_TCL.read_text(encoding="utf-8")

    assert "set_property file_type SystemVerilog [get_files $controller_rtl]" in text
    assert "set_property file_type Verilog [get_files $controller_bd_rtl]" in text
    assert "create_bd_cell -type module -reference $controller_name controller_0" in text
    assert "create_bd_cell -type ip -vlnv $expected_vlnv neuron_step_v1_0" in text
    assert "connect_bd_intf_net" not in text
    assert "hls_ap_start ap_start" in text
    assert "hls_ap_done  ap_done" in text
    assert "hls_ap_idle  ap_idle" in text
    assert "hls_ap_ready ap_ready" in text
    assert "connect_verified_pair $controller_pin $hls_pin" in text
    assert "get_bd_nets -quiet -of_objects $cp" in text
    assert "get_bd_nets -quiet -of_objects $hp" in text
    assert "create_bd_port -dir I -type clk -freq_hz 100000000 ap_clk" in text
    assert "validate_bd_design" in text
    assert "launch_simulation -simset sim_1 -mode behavioral" in text
    assert "run all" in text


def test_m11_5_2_real_ip_testbench_compares_packed_python_expectations() -> None:
    text = REAL_IP_TB.read_text(encoding="utf-8")

    assert '`include "generated_m11_5_2_vectors.svh"' in text
    assert "M11_5_2_RESET_STATE_WORDS[index]" in text
    assert "M11_5_2_EXPECTED_STATE_WORDS[index]" in text
    assert "M11_5_2_EXPECTED_SPIKES[index]" in text
    assert "observed_accum !== 64'sd0" in text
    assert "tick !== 32'd1" in text
    assert "M11.5.2 real packaged-IP integration passed:" in text


def test_m11_5_2_real_ip_runner_requires_packaged_ip_and_no_space_staging() -> None:
    text = REAL_IP_RUNNER.read_text(encoding="utf-8")

    assert 'EXPECTED_VERSION="2025.2"' in text
    assert 'EXPECTED_PART="xck26-sfvc784-2LV-c"' in text
    assert 'EXPECTED_VLNV="neuromorphic-twin.org:hls:neuron_step_v1:1.0"' in text
    assert 'IP_REPO_DIR="$HLS_DIR/build/m11_4/ip_repo"' in text
    assert 'SOURCE_CONTROLLER_BD_RTL="$SCRIPT_DIR/neuron_array_controller_bd_v1.v"' in text
    assert 'STAGE_ROOT="/tmp/neuromorphic_twin_rtl_${UID}/m11_5_2_real_ip"' in text
    assert 'CONTROLLER_RTL="$STAGE_ROOT/neuron_array_controller_v1.sv"' in text
    assert 'CONTROLLER_BD_RTL="$STAGE_ROOT/neuron_array_controller_bd_v1.v"' in text
    assert 'TB_FILE="$STAGE_ROOT/tb_neuromorphic_twin_m11_5_2.sv"' in text
    assert 'VECTOR_FILE="$STAGE_ROOT/generated_m11_5_2_vectors.svh"' in text
    assert 'cp "$SOURCE_CONTROLLER_RTL" "$CONTROLLER_RTL"' in text
    assert 'cp "$SOURCE_CONTROLLER_BD_RTL" "$CONTROLLER_BD_RTL"' in text
    assert 'cp "$SOURCE_TB_FILE" "$TB_FILE"' in text
    assert "generate_m11_5_2_vectors.py" in text
    assert "create_m11_5_2_project.tcl" in text
    assert 'grep -Fq "$PASS_MARKER"' in text
