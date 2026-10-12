"""Guard the opt-in 128-bit HPM0-to-32-bit AXI-Lite boot-matched candidate.

No physical pass is inferred: run Vivado BD/route and Cortex-A53 mailbox
checks on the user's KV260 before claiming P03.2c has been fixed.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BD = (ROOT / "vivado/create_p03_mmio_impl_project.tcl").read_text(encoding="utf-8")
SHELL = (ROOT / "vivado/run_p03_mmio_impl.sh").read_text(encoding="utf-8")
PREFLIGHT = (ROOT / "scripts/run_p03_2_preflight.sh").read_text(encoding="utf-8")
ABI = (ROOT / "software/p03/include/p03_mmio.h").read_text(encoding="utf-8")


def test_default_preserved_and_boot_matched_candidate_is_opt_in():
    for fragment in (
        "set p03_ps_mmio_master FPD",
        "set p03_ps_hpm0_width 32",
        "P03_PS_HPM0_DATA_WIDTH",
        "if {$p03_ps_hpm0_width ni {32 128}}",
        "CONFIG.PSU__MAXIGP0__DATA_WIDTH $p03_ps_hpm0_width",
        "CONFIG.PSU__MAXIGP2__DATA_WIDTH $p03_ps_hpm0_width",
        'if {$p03_ps_hpm0_width == 128}',
        "p03_hpm0_transport smartconnect_width_protocol",
        "p03_hpm0_transport axi_protocol_converter",
        "P03_2C_DIAG_MASTER_DATA_WIDTH_REQUESTED=",
        "P03_2C_DIAG_BRIDGE=",
        "if {$p03_ps_master_dw != $p03_ps_hpm0_width}",
    ):
        assert fragment in BD
    assert "#define P03_MMIO_BASE              ((uintptr_t)0xA4000000u)" in ABI


def test_smartconnect_128_to_32_bridge_has_realized_pin_gates():
    for fragment in (
        "p03_hpm0_width_smartconnect_0/S00_AXI",
        "p03_hpm0_width_smartconnect_0/M00_AXI",
        "CONFIG.NUM_SI {1}",
        "CONFIG.NUM_MI {1}",
        "set p03_bridge_s_axis",
        "set p03_bridge_m_axis",
        "[get_bd_intf_pins $p03_bridge_s_axis]",
        "[get_bd_intf_pins $p03_bridge_m_axis]",
        "P03_2C_WIDTH_BRIDGE_INPUT_BITS=",
        "P03_2C_WIDTH_BRIDGE_OUTPUT_BITS=",
        "P03_2C_WIDTH_MMIO_SLAVE_BITS=",
        "P03_2C_WIDTH_BRIDGE_INPUT_PROTOCOL=",
        "P03_2C_WIDTH_BRIDGE_OUTPUT_PROTOCOL=",
        '$bridge_s_width != 128 || $bridge_m_width != 32 || $slave_width != 32',
        'PASS: P03.2c 128-bit boot-matched PS master / 32-bit MMIO SmartConnect validated.',
        "p03_mmio_slave_data_width_bits=32",
    ):
        assert fragment in BD
    assert "p02_axi128_burst_adapter_0/M_AXI" in BD
    assert "p02_hp0_smartconnect_0/M00_AXI" in BD


def test_route_gate_checks_runtime_width_matching_candidate():
    for fragment in (
        'PS_HPM0_DATA_WIDTH="${P03_PS_HPM0_DATA_WIDTH:-32}"',
        "32|128",
        'EXPECTED_HPM_TRANSPORT=smartconnect_width_protocol',
        'p03_hpm0_data_width_bits:$PS_HPM0_DATA_WIDTH',
        'p03_hpm0_transport:$EXPECTED_HPM_TRANSPORT',
        'p03_mmio_slave_data_width_bits:32',
        'LPD or 128-bit diagnostic requires a fresh explicit P03_MMIO_BUILD_DIR',
        'PASS: P03.2c boot-matched 128-bit PS master / 32-bit MMIO diagnostic routed',
    ):
        assert fragment in SHELL
    for fragment in (
        "smartconnect_width_protocol",
        "p03_hpm0_width_smartconnect_0/S00_AXI",
        "P03_2C_WIDTH_BRIDGE_INPUT_BITS=",
    ):
        assert fragment in PREFLIGHT
