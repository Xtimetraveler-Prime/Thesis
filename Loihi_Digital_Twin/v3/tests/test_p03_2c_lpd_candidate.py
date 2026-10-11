"""Guard the opt-in LPD MMIO experiment without changing the frozen FPD ABI."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BD = ROOT / "vivado/create_p03_mmio_impl_project.tcl"
BUILD = ROOT / "vivado/run_p03_mmio_impl.sh"
SMOKE_BUILD = ROOT / "scripts/build_p03_2c_smoke.sh"
READONLY = ROOT / "software/p03/p03_2c_readonly.c"
VERIFY = ROOT / "scripts/p03_2c_verify_readonly.py"
DRIVER = ROOT / "scripts/run_p03_2c_readonly.sh"
HEADER = ROOT / "software/p03/include/p03_mmio.h"


def test_lpd_opt_in_uses_valid_ps_master_and_address_window():
    bd = BD.read_text(encoding="utf-8")
    for fragment in (
        "set p03_ps_mmio_master FPD",
        "P03_PS_MMIO_MASTER",
        "M_AXI_HPM0_FPD", "M_AXI_HPM0_LPD",
        "maxihpm0_fpd_aclk", "maxihpm0_lpd_aclk",
        "CONFIG.PSU__USE__M_AXI_GP2 {1}",
        "CONFIG.PSU__MAXIGP2__DATA_WIDTH {32}",
        "set p03_mmio_base 0x80000000",
        "set p03_mmio_base 0xA4000000",
        "assign_bd_address -offset $p03_mmio_base",
        "p03_ps_mmio_master=$p03_ps_mmio_master",
    ):
        assert fragment in bd
    assert "CONFIG.PSU__SAXIGP2__DATA_WIDTH {128}" in bd
    assert "p02_axi128_burst_adapter_0/M_AXI" in bd


def test_lpd_route_requires_isolated_build_and_checks_recorded_base():
    shell = BUILD.read_text(encoding="utf-8")
    for fragment in (
        'PS_MMIO_MASTER="${P03_PS_MMIO_MASTER:-FPD}"',
        "FPD|LPD",
        "LPD diagnostic requires a fresh explicit P03_MMIO_BUILD_DIR",
        'EXPECTED_MMIO_BASE="0x80000000"',
        '"p03_mmio_base:$EXPECTED_MMIO_BASE"',
        '"p03_ps_mmio_master:$PS_MMIO_MASTER"',
        "LPD diagnostic routed implementation gate completed",
    ):
        assert fragment in shell
    assert 'if [[ -e "$BUILD_DIR" ]]' in shell


def test_frozen_abi_kept_and_only_readonly_candidate_can_relocate():
    hdr = HEADER.read_text(encoding="utf-8")
    assert "#define P03_MMIO_BASE              ((uintptr_t)0xA4000000u)" in hdr
    source = READONLY.read_text(encoding="utf-8")
    assert "#define P03_READONLY_MMIO_BASE P03_MMIO_BASE" in source
    assert "P03_READONLY_MMIO_BASE + (uintptr_t)offset" in source
    build = SMOKE_BUILD.read_text(encoding="utf-8")
    assert "P03_2C_READONLY_MMIO_BASE" in build
    assert 'printf \'#define P03_READONLY_MMIO_BASE' in build
    assert 'APP_NAME" == "p03_2c_readonly"' in build
    verify = VERIFY.read_text(encoding="utf-8")
    assert "0x80000000" in verify
    assert 'parser.add_argument(' in verify and '"--base"' in verify
    driver = DRIVER.read_text(encoding="utf-8")
    assert '--base "$READONLY_MMIO_BASE"' in driver
    assert "P03_2C_EXPECTED_XSA_SHA" in driver
