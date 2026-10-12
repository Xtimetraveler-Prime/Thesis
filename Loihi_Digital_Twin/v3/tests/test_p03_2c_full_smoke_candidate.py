"""Guards the corrected FPD128 full P03.2c A53 command smoke.

Static checks only. The KV260 must independently run and pass the command
smoke before this sub-milestone is accepted.
"""

from __future__ import annotations

from pathlib import Path
import json
import struct
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_p03_2c_smoke.sh"
DRIVER = ROOT / "scripts/run_p03_2c_full_smoke.sh"
SMOKE = ROOT / "software/p03/p03_2c_smoke.c"
MANIFEST = ROOT / "scripts/p03_2c_smoke_fixture.py"
VERIFY = ROOT / "scripts/p03_2c_verify_mailbox.py"


def test_candidate_full_smoke_build_keeps_frozen_acceptance_guard():
    text = BUILD.read_text(encoding="utf-8")
    assert 'EXPECTED_XSA_SHA="703fa7a44abc56e88e67e1d09424ac59ea96e53aac1708c2c7e6028dcb616f40"' in text
    for required in (
        "P03_2C_SMOKE_CANDIDATE",
        "P03_2C_EXPECTED_XSA_SHA",
        "P03_XSA",
        "P03_2C_BUILD_DIR",
        'EXPECTED_XSA_SHA="$P03_2C_EXPECTED_XSA_SHA"',
        "full smoke supports only the frozen FPD MMIO base 0xA4000000",
        "corrected candidate full-smoke build directory already exists",
        'if [[ "$APP_NAME" == "p03_2c_smoke" && "${P03_2C_SMOKE_CANDIDATE:-0}" != 1 ]]; then',
        "PASS: P03.2c candidate full A53 smoke build gate completed",
        "read-only build directory already exists",
    ):
        assert required in text


def test_full_smoke_runner_checks_live_width_and_proves_physical_commands():
    text = DRIVER.read_text(encoding="utf-8")
    for required in (
        "P03_2C_SMOKE_CANDIDATE",
        "P03_2C_EXPECTED_XSA_SHA",
        "p03_hpm0_data_width_bits=128",
        "p03_hpm0_transport=smartconnect_width_protocol",
        "p03_mmio_slave_data_width_bits=32",
        "p03_ps_mmio_master=FPD",
        "p03_mmio_base=0xA4000000",
        "p03_2c_xsdb_ps_axi_width_diag.tcl",
        "P03_2C_PS_FPD_HPM0_WIDTH_BITS=128",
        "p03_2c_xsdb_prepare.tcl",
        "p03_2c_program_bitstream.tcl",
        "p03_2c_xsdb_run.tcl",
        "--manifest",
        "p03_2c_verify_mailbox.py",
        "full_physical_evidence_",
        "artifact_identity.txt",
        'VERIFY_EXIT=${PIPESTATUS[0]}',
        "FAIL: P03.2c full A53 physical page/resident/dispatch smoke",
        "reboot KV260",
    ):
        assert required in text
    assert text.index("p03_2c_xsdb_prepare.tcl") < text.index("p03_2c_program_bitstream.tcl")
    assert text.index("p03_2c_program_bitstream.tcl") < text.index("p03_2c_xsdb_run.tcl")
    assert "rm -rf" not in text


def test_a53_full_smoke_is_separate_from_read_only_program():
    text = SMOKE.read_text(encoding="utf-8")
    for token in (
        "P03_REG_PAGE_COMMAND",
        "P03_REG_DEBUG_COMMAND",
        "P03_REG_DISPATCH_COMMAND",
        "P03_REG_PAGE_BYTES",
        "P03_REG_DISPATCH_COMPLETED",
        "Xil_DCacheFlushRange",
    ):
        assert token in text
    assert "0xA4000000" in (
        ROOT / "software/p03/include/p03_mmio.h"
    ).read_text(encoding="utf-8")


def test_full_smoke_fixture_has_required_page_and_dispatch_manifest():
    text = MANIFEST.read_text(encoding="utf-8")
    for token in (
        '"manifest.json"',
        '"expected_config0"',
        '"expected_page_bytes": 438272',
        '"expected_page_read_bursts": 1712',
        '"expected_page_write_bursts": 0',
        '"dispatch_metadata"',
    ):
        assert token in text


def test_existing_manifest_verifier_rejects_one_bad_page_byte(tmp_path: Path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({
        "expected_config0": "0x14001000",
        "expected_page_bytes": 438272,
        "expected_page_read_bursts": 1712,
        "expected_page_write_bursts": 0,
    }), encoding="utf-8")
    words = [
        0x50333243, 1, 0x600D600D, 0,
        0x4C543302, 0x00010000, 0x0001031F, 0,
        0x2, 438271, 1712, 0, 0x6, 0x14001000, 0x2, 1,
    ]
    mailbox = tmp_path / "bad_page.bin"
    mailbox.write_bytes(struct.pack("<16I", *words))
    result = subprocess.run([
        sys.executable, str(VERIFY), "--mailbox", str(mailbox), "--manifest",
        str(path)
    ], capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert "page_bytes" in result.stderr
