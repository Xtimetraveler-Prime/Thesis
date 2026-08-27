from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl" / "core_v1"
SMOKE = RTL / "m11_6_smoke_controller_v1.sv"
SMOKE_BD = RTL / "m11_6_smoke_controller_bd_v1.v"
BITSTREAM_RUNNER = RTL / "run_m11_6_bitstream.sh"
HARDWARE_RUNNER = RTL / "run_m11_6_hardware_smoke.sh"
PROJECT_TCL = RTL / "vivado" / "create_m11_6_project.tcl"
PROGRAM_TCL = RTL / "vivado" / "program_m11_6_smoke.tcl"


def test_m11_6_smoke_reuses_python_golden_recurrent_chain() -> None:
    text = SMOKE.read_text(encoding="utf-8")
    assert '`include "generated_m11_5_4_integrated_vectors.svh"' in text
    assert "M11_5_4I_EXPECTED_STATES" in text
    assert "M11_5_4I_EXPECTED_SPIKES" in text
    assert "M11_5_4I_EXPECTED_CONSUMED_COUNTS" in text
    assert "M11_5_4I_EXPECTED_ROUTED_COUNTS" in text
    assert "M11_5_4I_EXPECTED_CURRENT_EVENT0" in text
    assert "recurrent_integrated_core_controller_v1 core_i" in text

    # The board smoke must validate data rather than treating tick_done as pass.
    for failure in (
        "FAIL_TICK_COUNT",
        "FAIL_CONSUMED_COUNT",
        "FAIL_ROUTED_COUNT",
        "FAIL_CURRENT_BANK",
        "FAIL_CURRENT_COUNT",
        "FAIL_STATE",
        "FAIL_SPIKE",
        "FAIL_RECURRENT_EVENT",
        "FAIL_FINAL_BANK_COUNTS",
    ):
        assert failure in text
    assert "smoke_pass <= 1'b1;" in text
    assert "WAIT_LIMIT" in text


def test_m11_6_smoke_uses_local_reset_heartbeat_and_exports_real_hls_boundary() -> None:
    smoke = SMOKE.read_text(encoding="utf-8")
    wrapper = SMOKE_BD.read_text(encoding="utf-8")
    assert "input  logic         smoke_resetn" in smoke
    assert "reset_sync <= {reset_sync[0], 1'b0};" in smoke
    assert "hls_ap_rst" not in smoke
    assert "hls_ap_start" in smoke
    assert "hls_synaptic_input" in smoke
    assert "hls_spiked_ap_vld" in smoke
    assert "module m11_6_smoke_controller_bd_v1" in wrapper
    assert "m11_6_smoke_controller_v1 smoke_i" in wrapper
    assert "FREQ_HZ 100000000" not in wrapper
    assert "ASSOCIATED_RESET smoke_resetn" in wrapper
    assert "clock_heartbeat" in wrapper
    assert "heartbeat_counter" in wrapper
    assert "POLARITY ACTIVE_LOW" in wrapper


def test_m11_6_project_is_carrier_pin_independent_and_vio_controlled() -> None:
    text = PROJECT_TCL.read_text(encoding="utf-8")
    assert 'set project_name "neuromorphic_twin_m11_6"' in text
    assert "xilinx.com:ip:zynq_ultra_ps_e:3.5" in text
    assert "get_board_parts -quiet xilinx.com:kv260_som:part0:*" in text
    assert "set_property BOARD_PART $kv260_board_part" in text
    assert "apply_bd_automation -rule xilinx.com:bd_rule:zynq_ultra_ps_e" in text
    assert 'apply_board_preset "1"' in text
    assert "CONFIG.PSU__FPGA_PL0_ENABLE {1}" in text
    assert "CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {100}" in text
    assert "KV260/K26 Zynq UltraScale+ MPSoC preset does" in text
    assert "get_bd_intf_ports -quiet -filter" not in text
    assert "make_bd_intf_pins_external $ddr_pin" not in text
    assert "make_bd_intf_pins_external $fixed_pin" not in text
    assert "set pl_clk0_pin [get_bd_pins -quiet zynq_ultra_ps_e_0/pl_clk0]" in text
    assert "pl_resetn0_pin" not in text
    assert "CONFIG.PSU__USE__FABRIC__RST {0}" in text
    assert "M11.6 PS Block Automation configured K26 SOM; PL clock boundary:" in text
    assert "xilinx.com:ip:vio:3.0" in text
    assert "xilinx.com:ip:proc_sys_reset:5.0" in text
    assert "xilinx.com:ip:xlconstant:1.1" in text
    assert "CONFIG.C_NUM_PROBE_IN {14}" in text
    assert "CONFIG.C_NUM_PROBE_OUT {2}" in text
    assert "connect_verified_pair hls_ap_rst ap_rst" not in text
    assert "connect_named_pair smoke_resetn vio_m11_6/probe_out1 proc_sys_reset_m11_6/ext_reset_in" in text
    assert "proc_sys_reset_m11_6/peripheral_aresetn" in text
    assert "proc_sys_reset_m11_6/peripheral_reset" in text
    assert "[get_bd_pins neuron_step_v1_0/ap_rst]" in text
    assert "connect_named_pair clock_heartbeat" in text
    assert "M11.6 local reset/heartbeat boundary:" in text
    assert "connect_named_pair smoke_start" in text
    assert "connect_named_pair smoke_pass" in text

    # No carrier-card PL PACKAGE_PIN constraints are introduced by M11.6.
    assert "PACKAGE_PIN" not in text
    assert "set_property IOSTANDARD" not in text


def test_m11_6_requires_routed_timing_drc_and_bitstream_artifacts() -> None:
    text = PROJECT_TCL.read_text(encoding="utf-8")
    assert "launch_runs impl_1 -to_step write_bitstream" in text
    assert "report_timing_summary -delay_type min_max -report_unconstrained" in text
    assert "report_route_status -file" in text
    assert "report_drc -file" in text
    assert "get_timing_paths -quiet -delay_type max" in text
    assert "get_timing_paths -quiet -delay_type min" in text
    assert "if {$wns < 0.0 || $whs < 0.0}" in text
    assert "M11.6 routed timing check passed:" in text
    assert "get_drc_violations -quiet -filter {SEVERITY == Error}" in text
    assert "write_debug_probes -force" in text
    assert "write_hw_platform -fixed -include_bit -force" in text
    assert "M11.6 bitstream generated successfully." in text


def test_m11_6_bitstream_runner_preserves_k26_capacity_gate() -> None:
    text = BITSTREAM_RUNNER.read_text(encoding="utf-8")
    assert 'EXPECTED_VERSION="2025.2"' in text
    assert 'EXPECTED_PART="xck26-sfvc784-2LV-c"' in text
    assert 'EXPECTED_VLNV="neuromorphic-twin.org:hls:neuron_step_v1:1.0"' in text
    assert "generate_m11_5_4_integrated_vectors.py" in text
    assert "create_m11_6_project.tcl" in text
    assert "M11.6 routed timing check passed:" in text
    assert "neuromorphic_twin_m11_6.bit" in text
    assert "neuromorphic_twin_m11_6.ltx" in text
    assert "neuromorphic_twin_m11_6.xsa" in text
    assert 'check_m11_6_resources.py' in text
    assert '"$REPORT_DIR/utilization_impl.rpt"' in text
    assert '"$REPORT_DIR/ram_utilization_impl.rpt"' in text


def test_m11_6_hardware_runner_programs_and_executes_vio_smoke() -> None:
    tcl = PROGRAM_TCL.read_text(encoding="utf-8")
    runner = HARDWARE_RUNNER.read_text(encoding="utf-8")
    for token in (
        "open_hw_manager",
        "connect_hw_server",
        "open_hw_target",
        "program_hw_devices",
        "refresh_hw_device",
        "get_hw_vios",
        "get_hw_probes",
        "OUTPUT_VALUE",
        "commit_hw_vio",
        "refresh_hw_vio",
        "smoke_start",
        "smoke_resetn",
        "clock_heartbeat",
        "M11.6 PL clock heartbeat advanced:",
        "M11.6 local smoke reset released through VIO.",
        "smoke_done",
        "smoke_pass",
        "M11.6 physical VIO smoke passed:",
    ):
        assert token in tcl
    assert "open_hw\n" not in tcl
    assert "sudo xmutil unloadapp" in runner
    assert "Run bash run_m11_6_bitstream.sh successfully first." in runner
    assert "M11.6 physical-board smoke completed successfully." in runner
