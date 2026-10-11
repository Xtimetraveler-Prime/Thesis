"""Regression for the read-only ZynqMP runtime PS AXI width diagnosis."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIDTH = ROOT / "vivado/p03_2c_xsdb_ps_axi_width_diag.tcl"
BD = ROOT / "vivado/create_p03_mmio_impl_project.tcl"


def test_width_diag_reads_correct_zynqmp_slcr_addresses_without_writes():
    source = WIDTH.read_text(encoding="utf-8")
    for token in (
        "p03_physical_read32 0xFD615000",
        "p03_physical_read32 0xFF419000",
        "mrd -force -size w",
        "($fpd_raw >> 8) & 3",
        "($lpd_raw >> 8) & 3",
        '0 { return "32" }',
        '1 { return "64" }',
        '2 { return "128" }',
        "P03_2C_PS_FPD_HPM0_WIDTH_BITS=",
        "P03_2C_PS_LPD_HPM0_WIDTH_BITS=",
        "P03_2C_PS_WIDTH_MISMATCH_",
        "P03_2C_PL_EXPECTED_HPM0_WIDTH_BITS=32",
        "PSU APU",
    ):
        assert token in source
    for forbidden in (
        "mwr ", "Xil_Out32", "psu_init", "rst -system",
        "rst -processor", "program_hw_devices", "dow ",
    ):
        assert forbidden not in source


def test_width_diagnostic_is_compared_to_32_bit_realized_ps_master():
    bd = BD.read_text(encoding="utf-8")
    assert "CONFIG.PSU__MAXIGP0__DATA_WIDTH {32}" in bd
    assert "CONFIG.PSU__MAXIGP2__DATA_WIDTH {32}" in bd
    assert "P03_2C_DIAG_MASTER_DATA_WIDTH=" in bd
    assert 'if {$p03_ps_master_dw != 32}' in bd


def test_reset_widths_in_amd_register_reference_would_mismatch_pl():
    # UG1087 FPD_SLCR.afi_fs reset 0xA00 and LPD_SLCR.afi_fs 0x200:
    # bits 9:8 = 2 -> 128-bit HPM0 vs 32-bit PL.
    assert ((0x00000A00 >> 8) & 0b11) == 2
    assert ((0x00000200 >> 8) & 0b11) == 2
