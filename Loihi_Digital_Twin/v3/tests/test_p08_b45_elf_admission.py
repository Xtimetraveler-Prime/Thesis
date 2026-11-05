"""P08-B4.5 synthetic-only negative tests of separate A53 ELF admission."""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import p08_b45_elf_admission as gate


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fake_elf(payload: bytes, base: int = 0x100000, machine: int = 183) -> bytes:
    # ELF64 AArch64 test fixture only: NOT a real Vitis artifact.
    assert len(payload) < 0x1000
    ident = b"\x7fELF" + bytes([2, 1, 1]) + bytes(9)
    header = struct.pack(gate.orig.ELF_HDR, ident, 2, machine, 1,
                         base + 0x100, 64, 0, 0, 64, 56, 1, 64, 0, 0)
    phdr = struct.pack(gate.orig.PHDR, 1, 5, 0x1000, base, base,
                       0x1000, 0x1000, 0x1000)
    out = bytearray(0x2000)
    out[:64] = header
    out[64:120] = phdr
    out[0x1000:0x1000 + len(payload)] = payload
    return bytes(out)


MAP = (
    b"Linker script and memory map\n.text .bss main\n"
    b"p08_b45_reset_bind p08_b45_reset_image\n"
    b"p08_b45_a53_backup_lock p08_b45_a53_backup_lock_valid\n"
    b"p07_b4m_full_run p08_b2_meter_start\n"
)


@pytest.fixture
def stage(tmp_path, monkeypatch):
    original = tmp_path / "original_b23.elf"
    experimental = tmp_path / "variant.elf"
    linker = tmp_path / "variant.map"
    xsa = tmp_path / "original_p03.xsa"
    pins = tmp_path / "original27.h"
    original.write_bytes(fake_elf(gate.orig.IDENTITY))
    linker.write_bytes(MAP)
    xsa.write_bytes(b"SYNTHETIC ROUTED P03 XSA, NOT REAL")
    pins.write_bytes(b"SYNTHETIC P08 B2.2 SHA PIN HEADER, NOT REAL")
    monkeypatch.setattr(gate, "ORIGINAL_ELF_SHA", digest(original.read_bytes()))
    monkeypatch.setattr(gate, "XSA_SHA", digest(xsa.read_bytes()))
    monkeypatch.setattr(gate, "PINS_SHA", digest(pins.read_bytes()))
    return original, experimental, linker, xsa, pins


@pytest.mark.parametrize("mode", gate.MODES)
def test_distinct_variant_elf_source_admission_is_not_physical(stage, tmp_path, mode):
    original, experimental, linker, xsa, pins = stage
    experimental.write_bytes(fake_elf(gate.IDENTITIES[mode] + b"\n" +
                                      gate.TERMINAL[mode]))
    out = tmp_path / ("variant_" + mode + "_admission.json")
    result = gate.audit(mode, experimental, linker, original, xsa, pins, out)
    assert result["schema"] == gate.SCHEMA
    assert result["mode"] == mode
    assert result["new_distinct_A53_identity"] == gate.IDENTITIES[mode].decode()
    assert result["new_elf_sha256"] != result["original_immutable_B2_3_elf_sha256"]
    assert result["proposed_reset_profile_bytes"] == 262144
    assert result["unprovisioned_backup_protection_adapter"] is True
    assert result["independent_physical_DDR_owner_and_protection_proven"] is False
    assert result["physical_JTAG_DDR_launch_authorized"] is False
    assert result["new_KV260_neural_parity_verified"] is False
    with pytest.raises(gate.VariantElfNoGo):
        gate.audit(mode, experimental, linker, original, xsa, pins, out)


@pytest.mark.parametrize("mode", gate.MODES)
@pytest.mark.parametrize("bad", (
    "wrong_mode", "no_terminal", "original_changed", "bad_xsa",
    "bad_pins", "missing_map", "missing_guard_symbol",
    "overlapping_ddr", "wrong_machine", "original_identity_in_new",
    "same_as_original", "missing_frozen_neural_engine",
))
def test_variant_elf_admission_rejects_failures(stage, tmp_path, mode, bad):
    original, experimental, linker, xsa, pins = stage
    data = gate.IDENTITIES[mode] + gate.TERMINAL[mode]
    if bad == "wrong_mode":
        data = gate.IDENTITIES["once" if mode == "unchecked" else "unchecked"]
        data += gate.TERMINAL[mode]
    elif bad == "no_terminal":
        data = gate.IDENTITIES[mode]
    elif bad == "original_changed":
        original.write_bytes(original.read_bytes() + b"tampered")
    elif bad == "bad_xsa":
        xsa.write_bytes(b"changed")
    elif bad == "bad_pins":
        pins.write_bytes(b"changed")
    elif bad == "missing_map":
        linker.write_bytes(b"main")
    elif bad == "missing_guard_symbol":
        linker.write_bytes(MAP.replace(b"p08_b45_a53_backup_lock_valid", b"MISSING"))
    elif bad == "original_identity_in_new":
        data += gate.orig.IDENTITY
    elif bad == "same_as_original":
        data = gate.orig.IDENTITY
    elif bad == "missing_frozen_neural_engine":
        linker.write_bytes(MAP.replace(b"p07_b4m_full_run", b"MISSING"))
    base = 0x40001000 if bad == "overlapping_ddr" else 0x100000
    machine = 62 if bad == "wrong_machine" else 183
    experimental.write_bytes(fake_elf(data, base=base, machine=machine))
    out = tmp_path / ("no_go_" + mode + ".json")
    with pytest.raises((gate.VariantElfNoGo, gate.orig.ElfNoGo)):
        gate.audit(mode, experimental, linker, original, xsa, pins, out)
    assert not out.exists()


def test_pinned_real_baseline_sha_constants_are_not_synthetic_fixtures():
    # Test monkeypatching above does not change the checked-in real pins.
    import ast
    contents = (ROOT / "scripts/p08_b45_elf_admission.py").read_text()
    tree = ast.parse(contents)
    assignments = {}
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            target = node.targets[0].id
            if isinstance(node.value, ast.Constant):
                assignments[target] = node.value.value
    # Source constant is multiline parenthesized string literal.
    assert gate.orig.EXPECTED_PINS_SHA == (
        "5be79b38ec7f42622573a7fa59adb689a65bfcf5d8e5a6e8cdaec0e75c9f7171"
    )
    assert gate.orig.EXPECTED_XSA_SHA == (
        "52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f"
    )
    assert "P08_B45_AUTH_ONCE_ORIGINAL_27CORE_1024_A53_V1" in contents
    assert "P08_B45_UNCHECKED_ORIGINAL_27CORE_1024_A53_V1" in contents
    assert "import socket" not in contents
    assert "import subprocess" not in contents
    assert '"physical_JTAG_DDR_launch_authorized": False' in contents
