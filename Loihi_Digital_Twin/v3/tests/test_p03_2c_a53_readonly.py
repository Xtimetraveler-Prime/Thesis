"""Host-side regression for the A53-only P03.2c read-only MMIO diagnostic."""

from __future__ import annotations

from pathlib import Path
import struct
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "scripts/p03_2c_verify_readonly.py"
SOURCE = ROOT / "software/p03/p03_2c_readonly.c"
BUILD = ROOT / "scripts/build_p03_2c_smoke.sh"
DRIVER = ROOT / "scripts/run_p03_2c_readonly.sh"
VITIS = ROOT / "software/p03/build_p03_2c_smoke.py"

EXPECTED = (0x4C543302, 0x00010000, 0x0001031F, 0xD1A60018)


def _mailbox(path: Path, actual: tuple[int, ...], complete: bool = True) -> None:
    mask = sum(1 << i for i, value in enumerate(actual) if value == EXPECTED[i])
    words = (
        0x50335244, 1, 0x600D600D if mask == 0xF else 0xDEAD0000 | mask, 4,
        *actual, *EXPECTED, mask,
        0xC0DEF00D if complete else 0, 0xA4000000, 0x43FF0000,
    )
    assert len(words) == 16
    path.write_bytes(struct.pack("<16I", *words))


def _verify(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VERIFY), "--mailbox", str(path)],
        text=True, capture_output=True, check=False,
    )


def test_readonly_probe_verifier_accepts_expected_cortex_a53_values(tmp_path: Path):
    mailbox = tmp_path / "result.bin"
    _mailbox(mailbox, EXPECTED)
    result = _verify(mailbox)
    assert result.returncode == 0, result.stderr
    assert "PASS: P03.2c read-only Cortex-A53 MMIO diagnostic" in result.stdout


def test_readonly_probe_reports_all_values_on_version_failure(tmp_path: Path):
    mailbox = tmp_path / "result.bin"
    _mailbox(mailbox, (EXPECTED[0], 0, EXPECTED[2], EXPECTED[3]))
    result = _verify(mailbox)
    assert result.returncode != 0
    assert "Cortex-A53 MMIO 0xA4000004 returned 0x00000000" in result.stdout
    assert "Cortex-A53 MMIO 0xA4000018 returned 0xD1A60018" in result.stdout


def test_readonly_probe_rejects_missing_completion_marker(tmp_path: Path):
    mailbox = tmp_path / "result.bin"
    _mailbox(mailbox, EXPECTED, complete=False)
    result = _verify(mailbox)
    assert result.returncode != 0
    assert "may not have executed to completion" in result.stderr


def test_readonly_c_has_no_mmio_write_or_page_dispatch_command():
    source = SOURCE.read_text(encoding="utf-8")
    for forbidden in ("Xil_Out32", "reg_write(", "P03_REG_PAGE_COMMAND",
                      "P03_REG_DISPATCH_COMMAND", "P03_REG_DEBUG_COMMAND"):
        assert forbidden not in source
    for required in ("Xil_In32", "Xil_DCacheFlushRange",
                     "P03_REG_VERSION", "READONLY_COUNT", "READONLY_MAGIC"):
        assert required in source


def test_readonly_build_is_explicit_and_preserves_accepted_xsa_gate():
    build = BUILD.read_text(encoding="utf-8")
    vitis = VITIS.read_text(encoding="utf-8")
    driver = DRIVER.read_text(encoding="utf-8")
    assert 'EXPECTED_XSA_SHA="703fa7a44abc56e88e67e1d09424ac59ea96e53aac1708c2c7e6028dcb616f40"' in build
    for token in ("P03_2C_EXPECTED_XSA_SHA", "P03_2C_APP_NAME", "P03_2C_SOURCE_FILE",
                  "P03_2C_BUILD_DIR"):
        assert token in build
    assert "read-only build directory already exists" in build
    for token in ('--source-file', '--app-name', 'p03_2c_readonly.c'):
        assert token in vitis
    for token in ("p03_2c_xsdb_prepare.tcl", "p03_2c_xsdb_run.tcl",
                  "p03_2c_verify_readonly.py", "P03_2C_SKIP_PROGRAM"):
        assert token in driver
