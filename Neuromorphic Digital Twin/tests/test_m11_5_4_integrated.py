from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "examples" / "generate_m11_5_4_integrated_vectors.py"
RTL = ROOT / "rtl" / "core_v1" / "recurrent_integrated_core_controller_v1.sv"
BD_RTL = ROOT / "rtl" / "core_v1" / "recurrent_integrated_core_controller_bd_v1.v"
TB = ROOT / "rtl" / "core_v1" / "tb" / "tb_neuromorphic_twin_m11_5_4.sv"
TCL = ROOT / "rtl" / "core_v1" / "vivado" / "create_m11_5_4_project.tcl"
RUNNER = ROOT / "rtl" / "core_v1" / "run_m11_5_4_real_ip.sh"


def _load_generator():
    spec = importlib.util.spec_from_file_location("m11_5_4_integrated_vectors", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_integrated_python_oracle_proves_strict_next_tick_chain(tmp_path: Path) -> None:
    module = _load_generator()
    values = module.integrated_vectors()

    assert values["expected_spikes"] == (
        (1, 0, 0),
        (0, 1, 0),
        (0, 0, 1),
        (0, 0, 0),
    )
    assert values["expected_consumed"] == ((), (1,), (2,), ())
    assert values["expected_routed"] == ((1,), (2,), (), ())
    assert values["expected_current_bank"] == (1, 0, 1, 0)

    output_a = tmp_path / "a.svh"
    output_b = tmp_path / "b.svh"
    module.write_systemverilog_include(output_a)
    module.write_systemverilog_include(output_b)
    assert output_a.read_bytes() == output_b.read_bytes()
    text = output_a.read_text(encoding="utf-8")
    assert "M11_5_4I_TICK_COUNT = 4" in text
    assert "M11_5_4I_TAG = 32'h4d353449" in text


def test_recurrent_integration_orders_copy_core_spike_scan_and_route_commit() -> None:
    text = RTL.read_text(encoding="utf-8")

    assert "S_RECURRENT_READ" in text
    assert "S_RECURRENT_WRITE" in text
    assert "S_CORE_TICK_START" in text
    assert "S_SPIKE_READ" in text
    assert "S_SPIKE_WRITE" in text
    assert "S_ROUTE_START" in text
    assert "latched_recurrent_count  <= recurrent_current_count;" in text
    assert "latched_recurrent_bank   <= recurrent_current_bank;" in text
    assert ".recurrent_event_count(latched_recurrent_count)" in text
    assert ".recurrent_we(core_recurrent_we)" in text
    assert ".spike_we(route_spike_we)" in text
    assert "tick_done <= 1'b1;" in text
    assert "({1'b0, recurrent_copy_index} + 13'd1)" in text

    # The full integration boundary deliberately removes host recurrent preload;
    # recurrence must originate from the internal double-buffered route engine.
    module_header = text.split(");", 1)[0]
    assert "input  logic         recurrent_we" not in module_header
    assert "input  logic [12:0]  recurrent_event_count" not in module_header


def test_real_ip_module_reference_and_vivado_flow_include_recurrence() -> None:
    bd_text = BD_RTL.read_text(encoding="utf-8")
    tcl_text = TCL.read_text(encoding="utf-8")
    runner_text = RUNNER.read_text(encoding="utf-8")
    tb_text = TB.read_text(encoding="utf-8")

    assert "module recurrent_integrated_core_controller_bd_v1" in bd_text
    assert "recurrent_integrated_core_controller_v1 core_i" in bd_text
    assert "recurrent_current_count" in bd_text
    assert "route_row_we" in bd_text

    assert "recurrent_integrated_core_controller_bd_v1" in tcl_text
    assert "recurrent_route_queue_v1" not in tcl_text  # source path is passed, not a second BD cell
    assert "neuron_step_v1_0" in tcl_text
    assert "connect_verified_pair" in tcl_text
    assert "M11.5.4 recurrent packed-M08 real-HLS block design validated successfully." in tcl_text
    assert "tb_neuromorphic_twin_m11_5_4" in tcl_text

    assert "generate_m11_5_4_integrated_vectors.py" in runner_text
    assert "run_m11_5_4_real_ip.sh" not in runner_text
    assert "xck26-sfvc784-2LV-c" in runner_text
    assert "neuromorphic-twin.org:hls:neuron_step_v1:1.0" in runner_text
    assert "M11.5.4 packed-M08 + real-HLS recurrent multi-tick passed:" in runner_text

    assert "M11_5_4I_EXPECTED_SPIKES" in tb_text
    assert "last_consumed_recurrent_count" in tb_text
    assert "last_routed_count" in tb_text
    assert "recurrent_current_bank" in tb_text
    assert "recurrent_current_count" in tb_text
    assert "ticks=4, neurons=3, routes=2" in tb_text
