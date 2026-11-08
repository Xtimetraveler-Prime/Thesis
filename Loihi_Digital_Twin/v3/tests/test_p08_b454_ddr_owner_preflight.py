"""P08-B4.5.4.1 read-only DDR geometry and unproven-master risk gate.

All ELF bytes and paired reports in this test are SYNTHETIC, never board.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
import struct
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import p08_b454_ddr_owner_preflight as gate


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fake_aarch64_elf(base: int = 0x100000) -> bytes:
    # Synthetic only! ELF64 little-endian EXEC AArch64, 1 KiB PT_LOAD.
    ident = b"\x7fELF" + bytes([2, 1, 1]) + bytes(9)
    eh = struct.pack(gate.pair.gate.orig.ELF_HDR, ident, 2, 183, 1,
                     base + 0x100, 64, 0, 0, 64, 56, 1, 64, 0, 0)
    ph = struct.pack(gate.pair.gate.orig.PHDR, 1, 5, 0x1000,
                     base, base, 0x1000, 0x1000, 0x1000)
    image = bytearray(0x2000)
    image[:len(eh)] = eh
    image[64:64 + len(ph)] = ph
    return bytes(image)


@pytest.fixture
def synthetic(tmp_path: Path, monkeypatch):
    pin = {
        "schema": gate.pair.PIN_SCHEMA,
        "variants": {},
    }
    paired = {
        "schema": gate.pair.SCHEMA,
        "each_elf_and_map_cryptographically_reverified": True,
        "both_admission_reports_exactly_recomputed_against_original_inputs": True,
        "both_staged_sources_match_reviewed_offline_branch": True,
        "A53_ELF_artifact_generation_both_modes": "PC_ONLY_VERIFIED",
        "physical_memory_ownership_proven": False,
        "physical_JTAG_authorized": False,
        "backup_protection_adapter_provisioned": False,
        "KV260_neural_parity_verified": False,
        "independent_report_files": {},
    }
    roots = {}
    for mode in ("once", "unchecked"):
        root = tmp_path / mode
        root.mkdir()
        stage = root / "vitis_workspace"
        stage.mkdir()
        app = ("p08_b45_auth_once_1024" if mode == "once"
               else "p08_b45_unchecked_1024")
        elf = stage / (app + ".elf")
        linkmap = stage / (app + ".map")
        admission = root / ("p08_b45_" + mode + "_elf_admission.json")
        elf.write_bytes(fake_aarch64_elf())
        linkmap.write_bytes(b"SYNTHETIC ONLY linker map for " + mode.encode())
        admission.write_text(json.dumps({"synthetic_only": True}) + "\n")
        stage_sources = root / "source"
        stage_sources.mkdir()
        for name in (
            "p08_b45_reset_variants.c", "p08_b45_reset_variants.h",
            "p08_b45_a53_backup_guard.c", "p08_b45_a53_backup_guard.h",
            ("p08_b45_auth_once_full1024_a53.c" if mode == "once"
             else "p08_b45_unchecked_full1024_a53.c"),
        ):
            shutil.copy2(ROOT / "software/p08" / name, stage_sources / name)
        digest = {"elf": sha(elf.read_bytes()),
                  "map": sha(linkmap.read_bytes()),
                  "report": sha(admission.read_bytes())}
        pin["variants"][mode] = {
            "build_root": str(root), **{k + "_sha256": v for k, v in digest.items()}
        }
        paired["independent_report_files"][mode] = digest
        roots[mode] = root
    pinfile = tmp_path / "synthetic_pins.json"
    pinfile.write_text(json.dumps(pin))
    paired["operator_pins_sha256"] = sha(pinfile.read_bytes())
    pairfile = tmp_path / "synthetic_pair.json"
    pairfile.write_text(json.dumps(paired))
    monkeypatch.setattr(gate, "PINS_PATH", pinfile)
    monkeypatch.setattr(gate, "ORIGINAL_PAIR_SHA", sha(pairfile.read_bytes()))
    return pairfile, roots, paired, pin, pinfile


def review(synthetic, out, inventory=None):
    report, roots, _, _, _ = synthetic
    return gate.review(
        paired=report, once_build=roots["once"],
        unchecked_build=roots["unchecked"], out=out,
        inventory=inventory,
    )


def test_pc_gap_report_is_static_pass_and_unconditional_board_no_go(synthetic, tmp_path):
    out = tmp_path / "review.json"
    result = review(synthetic, out)
    assert result["schema"] == gate.SCHEMA
    assert result["decision"] == "PC_STATIC_GEOMETRY_PASS_PHYSICAL_OWNER_NO_GO"
    assert result["original_P03_backing_aperture"] == ["0x40000000", "0x44000000"]
    assert result["backup_original_27_core_range"] == [
        "0x43000000", "0x43d80000",
    ]
    assert result["ddr_xmpu_1MiB_alignment_candidate_only"] == [
        "0x43000000", "0x43e00000",
    ]
    assert result["xmpu_candidate_overprotects_bytes"] == 524288
    assert result["board_contact"] is False
    assert result["operator_authorized_KV260_board_action"] is False
    assert result["all_DDR_port_and_master_permissions_proven"] is False
    assert result["physical_backup_immutable_after_one_time_sha_proven"] is False
    assert result["new_guard_enabled_ELF_built"] is False
    assert len(result["owner_proof_requirements"]) >= 12
    assert all(row["status"] == "NOT_ESTABLISHED"
               for row in result["owner_proof_requirements"])
    assert out.is_file()
    with pytest.raises(gate.DdrGapNoGo, match="non-overwriting"):
        review(synthetic, out)


@pytest.mark.parametrize("bad", (
    "wrong_paired_sha", "paired_claims_physical", "missing_paired",
    "tampered_elf", "overlapping_elf", "out_of_aperture",
    "changed_root", "padded_sha_in_pins", "altered_pair_json",
    "no_src_geometry", "missing_input_elf",
    "changed_map_after_accept", "changed_report_after_accept",
    "changed_stage_guard_after_accept", "changed_pin_manifest_after_accept",
))
def test_fail_closed_on_swapped_pins_sources_elf_or_geometry(
        synthetic, tmp_path, monkeypatch, bad):
    pairfile, roots, paired, pins, pinfile = synthetic
    once = roots["once"] / "vitis_workspace/p08_b45_auth_once_1024.elf"
    if bad == "wrong_paired_sha":
        monkeypatch.setattr(gate, "ORIGINAL_PAIR_SHA", "a" * 64)
    elif bad == "paired_claims_physical":
        paired["physical_JTAG_authorized"] = True
        pairfile.write_text(json.dumps(paired))
        monkeypatch.setattr(gate, "ORIGINAL_PAIR_SHA", sha(pairfile.read_bytes()))
    elif bad == "missing_paired":
        pairfile.unlink()
    elif bad == "tampered_elf":
        once.write_bytes(once.read_bytes() + b"tamper")
    elif bad == "overlapping_elf":
        once.write_bytes(fake_aarch64_elf(0x40000000))
        h = sha(once.read_bytes())
        paired["independent_report_files"]["once"]["elf"] = h
        pins["variants"]["once"]["elf_sha256"] = h
        pairfile.write_text(json.dumps(paired))
        pinfile.write_text(json.dumps(pins))
        monkeypatch.setattr(gate, "ORIGINAL_PAIR_SHA", sha(pairfile.read_bytes()))
    elif bad == "out_of_aperture":
        monkeypatch.setattr(gate, "REGIONS", gate.REGIONS + (
            ("illegal", 0x44000000, 0x44000100, "synthetic"),
        ))
    elif bad == "changed_root":
        pins["variants"]["once"]["build_root"] = str(tmp_path / "incorrect")
        pinfile.write_text(json.dumps(pins))
    elif bad == "padded_sha_in_pins":
        pins["variants"]["once"]["elf_sha256"] += "f"
        pinfile.write_text(json.dumps(pins))
    elif bad == "altered_pair_json":
        paired["KV260_neural_parity_verified"] = True
        pairfile.write_text(json.dumps(paired))
        monkeypatch.setattr(gate, "ORIGINAL_PAIR_SHA", sha(pairfile.read_bytes()))
    elif bad == "no_src_geometry":
        monkeypatch.setattr(gate, "BACKUP", (0x43000000, 0x44000000))
    elif bad == "missing_input_elf":
        once.unlink()
    elif bad == "changed_map_after_accept":
        (roots["once"] / "vitis_workspace/p08_b45_auth_once_1024.map").write_bytes(b"modified map")
    elif bad == "changed_report_after_accept":
        (roots["once"] / "p08_b45_once_elf_admission.json").write_bytes(b"modified report")
    elif bad == "changed_stage_guard_after_accept":
        (roots["once"] / "source/p08_b45_a53_backup_guard.c").write_bytes(b"return 0;")
    elif bad == "changed_pin_manifest_after_accept":
        pins["variants"]["once"]["map_sha256"] = "f" * 64
        pinfile.write_text(json.dumps(pins))
    out = tmp_path / "must_not_exist.json"
    with pytest.raises((gate.DdrGapNoGo, gate.pair.PairElfNoGo,
                        gate.pair.gate.orig.ElfNoGo)):
        review(synthetic, out)
    assert not out.exists()


def test_optional_operator_observations_do_not_forge_protection(synthetic, tmp_path):
    inventory = tmp_path / "operator_supplied_boot_inventory"
    inventory.mkdir()
    (inventory / "proc_iomem.txt").write_text("SYNTHETIC DDR\n")
    (inventory / "xmpu_readback.json").write_text("{}")
    out = tmp_path / "observations.json"
    r = review(synthetic, out, inventory=inventory)
    assert len(r["supplied_boot_observations_not_physical_proof"]) == 2
    assert all(x["authority"] == "UNVERIFIED_OPERATOR_SUPPLIED_SNAPSHOT"
               for x in r["supplied_boot_observations_not_physical_proof"])
    assert r["all_DDR_port_and_master_permissions_proven"] is False
    assert r["board_contact"] is False


def test_missing_or_large_snapshot_rejected(synthetic, tmp_path):
    inventory = tmp_path / "observations"
    inventory.mkdir()
    (inventory / "boot_log.txt").write_bytes(b"A" * (16 * 1024 * 1024 + 1))
    with pytest.raises(gate.DdrGapNoGo, match="size"):
        review(synthetic, tmp_path / "no-output.json", inventory=inventory)
    assert not (tmp_path / "no-output.json").exists()


def test_real_accepted_paired_evidence_pin_and_source_constants():
    assert gate.ORIGINAL_PAIR_SHA == (
        "03b433527901a9d51dfb8a8ca99c0321d81335859d1be14505eb6a7be9369ec1")
    assert gate.XMPU_COVER == (0x43000000, 0x43E00000)
    assert gate.BACKUP[1] - gate.BACKUP[0] == 14155776
    assert gate.XMPU_COVER[1] - gate.BACKUP[1] == 524288
    gate.source_contract()
