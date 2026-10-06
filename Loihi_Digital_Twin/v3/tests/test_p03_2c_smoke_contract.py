from __future__ import annotations

import json
from pathlib import Path
import struct
import subprocess
import sys


def test_p03_2c_mailbox_verifier_accepts_frozen_pass_record(tmp_path: Path):
    manifest = {
        "expected_config0": "0x14001000",
        "expected_page_bytes": 438272,
        "expected_page_read_bursts": 1712,
        "expected_page_write_bursts": 0,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    capabilities = 0x0001031F
    words = (
        0x50333243,
        1,
        0x600D600D,
        0,
        0x4C543302,
        0x00010000,
        capabilities,
        0,
        0x2,
        438272,
        1712,
        0,
        0x6,
        0x14001000,
        0x2,
        1,
    )
    mailbox = tmp_path / "mailbox.bin"
    mailbox.write_bytes(struct.pack("<16I", *words))

    repo = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts/p03_2c_verify_mailbox.py"),
            "--mailbox",
            str(mailbox),
            "--manifest",
            str(manifest_path),
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert "PASS: P03.2c mailbox verified" in result.stdout


def test_p03_2c_mailbox_verifier_rejects_fault(tmp_path: Path):
    manifest = {
        "expected_config0": "0x14001000",
        "expected_page_bytes": 438272,
        "expected_page_read_bursts": 1712,
        "expected_page_write_bursts": 0,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    words = [0] * 16
    words[0] = 0x50333243
    words[1] = 1
    words[2] = 0xDEAD0004
    words[3] = 4
    mailbox = tmp_path / "mailbox.bin"
    mailbox.write_bytes(struct.pack("<16I", *words))

    repo = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts/p03_2c_verify_mailbox.py"),
            "--mailbox",
            str(mailbox),
            "--manifest",
            str(manifest_path),
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "FAIL: P03.2c" in result.stderr
