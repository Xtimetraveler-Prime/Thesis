"""Independent two-real-ELF local evidence verifier: synthetic no-board tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import p08_b45_pair_elf_evidence as pair


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fake_elf(marker: bytes, base: int = 0x100000) -> bytes:
    # Fake ELF64 AArch64 program-header fixture, NOT a Vitis artifact.
    ident = b"\x7fELF" + bytes([2, 1, 1]) + bytes(9)
    head = struct.pack(pair.gate.orig.ELF_HDR, ident, 2, 183, 1,
                       base + 0x100, 64, 0, 0, 64, 56, 1, 64, 0, 0)
    phdr = struct.pack(pair.gate.orig.PHDR, 1, 5, 0x1000,
                       base, base, 0x1000, 0x1000, 0x1000)
    raw = bytearray(0x2000)
    raw[:64] = head
    raw[64:120] = phdr
    raw[0x1000:0x1000 + len(marker)] = marker
    return bytes(raw)


MAP = (b"Linker script and memory map\n.text .bss main\n"
       b"p08_b45_reset_bind p08_b45_reset_image "
       b"p08_b45_a53_backup_lock "
       b"p08_b45_a53_backup_lock_valid "
       b"p07_b4m_full_run p08_b2_meter_start\n")


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    original = tmp_path / "operator_original.elf"
    xsa = tmp_path / "original_p03.xsa"
    pins = tmp_path / "original_contexts.h"
    original.write_bytes(fake_elf(pair.gate.orig.IDENTITY))
    xsa.write_bytes(b"FIXTURE SYNTHETIC P03 XSA ONLY")
    pins.write_bytes(b"FIXTURE SYNTHETIC 27 CORE SHA PINS ONLY")
    monkeypatch.setattr(pair.gate, "ORIGINAL_ELF_SHA", sha(original.read_bytes()))
    monkeypatch.setattr(pair.gate, "XSA_SHA", sha(xsa.read_bytes()))
    monkeypatch.setattr(pair.gate, "PINS_SHA", sha(pins.read_bytes()))
    manifest = {
        "schema": pair.PIN_SCHEMA,
        "evidence_status":
            "OPERATOR_REPORTED_SHA256_ONLY_NOT_YET_INDEPENDENTLY_REVERIFIED",
        "physical_KV260_executed": False,
        "tested_with_original_MNIST_TEST": False,
        "original_B2_3_elf_sha256": pair.gate.ORIGINAL_ELF_SHA,
        "original_P03_XSA_sha256": pair.gate.XSA_SHA,
        "original_B2_2_27_context_pin_sha256": pair.gate.PINS_SHA,
        "variants": {},
    }
    for mode in pair.gate.MODES:
        root = tmp_path / ("build_" + mode)
        workspace = root / "vitis_workspace"
        stage = root / "source"
        workspace.mkdir(parents=True)
        stage.mkdir()
        app = ("p08_b45_auth_once_1024" if mode == "once"
               else "p08_b45_unchecked_1024")
        elf = workspace / (app + ".elf")
        linker = workspace / (app + ".map")
        report = root / ("p08_b45_" + mode + "_elf_admission.json")
        elf.write_bytes(fake_elf(pair.gate.IDENTITIES[mode] +
                                 pair.gate.TERMINAL[mode]))
        linker.write_bytes(MAP)
        for filename in (
            "p08_b45_reset_variants.c", "p08_b45_reset_variants.h",
            "p08_b45_a53_backup_guard.c", "p08_b45_a53_backup_guard.h",
            ("p08_b45_auth_once_full1024_a53.c"
             if mode == "once"
             else "p08_b45_unchecked_full1024_a53.c"),
        ):
            shutil.copy2(ROOT / "software" / "p08" / filename, stage / filename)
        pair.gate.audit(mode, elf, linker, original, xsa, pins, report)
        manifest["variants"][mode] = {
            "build_root": str(root),
            "elf_sha256": sha(elf.read_bytes()),
            "map_sha256": sha(linker.read_bytes()),
            "report_sha256": sha(report.read_bytes()),
        }
    manifest_path = tmp_path / "synthetic_operator_pins.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return original, xsa, pins, manifest_path, manifest


def do_audit(data, out: Path):
    original, xsa, pins, manifest_path, _ = data
    return pair.audit(manifest_path, original, xsa, pins, out)


def test_independent_pair_with_exact_recomputed_elf_geometry(synthetic, tmp_path):
    out = tmp_path / "pair_independent.json"
    result = do_audit(synthetic, out)
    assert out.is_file()
    assert result["schema"] == pair.SCHEMA
    assert result["each_elf_and_map_cryptographically_reverified"] is True
    assert result["both_admission_reports_exactly_recomputed_against_original_inputs"] is True
    assert result["both_staged_sources_match_reviewed_offline_branch"] is True
    assert result["KV260_neural_parity_verified"] is False
    assert result["backup_protection_adapter_provisioned"] is False
    assert result["physical_JTAG_authorized"] is False
    with pytest.raises(pair.PairElfNoGo, match="no-overwrite"):
        do_audit(synthetic, out)


@pytest.mark.parametrize("tamper", (
    "changed_elf", "changed_map", "changed_report",
    "edited_report_with_pins", "edited_guard", "changed_mode",
    "changed_original_xsa", "changed_original_pins",
    "edited_frozen_pin", "replaced_guard_provisioned",
    "wrong_root", "two_same_elves", "physical_claim",
))
def test_cross_mode_fails_closed(synthetic, tmp_path, tamper):
    original, xsa, pins, manifest_path, manifest = synthetic
    once = Path(manifest["variants"]["once"]["build_root"])
    unchecked = Path(manifest["variants"]["unchecked"]["build_root"])
    elf_once = once / "vitis_workspace/p08_b45_auth_once_1024.elf"
    elf_unchecked = unchecked / "vitis_workspace/p08_b45_unchecked_1024.elf"
    map_once = once / "vitis_workspace/p08_b45_auth_once_1024.map"
    report_once = once / "p08_b45_once_elf_admission.json"
    if tamper == "changed_elf":
        elf_once.write_bytes(elf_once.read_bytes() + b"changed")
    elif tamper == "changed_map":
        map_once.write_bytes(map_once.read_bytes() + b"changed")
    elif tamper == "changed_report":
        report_once.write_bytes(report_once.read_bytes() + b"changed")
    elif tamper == "edited_report_with_pins":
        raw = json.loads(report_once.read_text())
        raw["new_elf_sha256"] = "0" * 64
        report_once.write_text(json.dumps(raw))
        manifest["variants"]["once"]["report_sha256"] = sha(report_once.read_bytes())
    elif tamper == "edited_guard":
        (once / "source/p08_b45_a53_backup_guard.c").write_text(
            "int p08_b45_a53_backup_lock(){return 0;}")
    elif tamper == "changed_mode":
        manifest["variants"]["once"]["elf_sha256"] = manifest[
            "variants"]["unchecked"]["elf_sha256"]
    elif tamper == "changed_original_xsa":
        xsa.write_bytes(b"swapped xsa")
    elif tamper == "changed_original_pins":
        pins.write_bytes(b"swapped sha header")
    elif tamper == "edited_frozen_pin":
        manifest["original_B2_3_elf_sha256"] = "1" * 64
    elif tamper == "replaced_guard_provisioned":
        (once / "source/p08_b45_a53_backup_guard.h").write_text(
            "#define P08_B45_A53_GUARD_PROVISIONED 1u")
    elif tamper == "wrong_root":
        manifest["variants"]["once"]["build_root"] = str(tmp_path / "none")
    elif tamper == "two_same_elves":
        elf_unchecked.write_bytes(elf_once.read_bytes())
        manifest["variants"]["unchecked"]["elf_sha256"] = sha(
            elf_unchecked.read_bytes())
    elif tamper == "physical_claim":
        manifest["physical_KV260_executed"] = True
    manifest_path.write_text(json.dumps(manifest))
    out = tmp_path / "must_not_create.json"
    with pytest.raises((pair.PairElfNoGo, pair.gate.VariantElfNoGo)):
        do_audit(synthetic, out)
    assert not out.exists()


def test_original_operator_pins_are_not_synthetic():
    report = json.loads(pair.DEFAULT_MANIFEST.read_text())
    assert report["schema"] == pair.PIN_SCHEMA
    assert report["original_B2_3_elf_sha256"] == (
        "0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1")
    assert report["variants"]["once"]["elf_sha256"] == (
        "70501217482d156d59037a8694b9b837938026cba0d62ccd1f8939bfdd112e04")
    assert report["variants"]["unchecked"]["elf_sha256"] == (
        "f6e09a8cde5ecd05900b30f0cc91d8d9549f2ae1e446157eb2c06024e0fd1655")
    assert report["evidence_status"].startswith("OPERATOR_REPORTED_")
    assert report["physical_KV260_executed"] is False
