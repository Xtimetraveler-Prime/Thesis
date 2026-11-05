#!/usr/bin/env python3
"""P08-B4.5 independent PC-only re-verification of TWO operator A53 builds.

Reads the *actual* separate genuine local ELF/maps, original pinned inputs,
and the previously generated admission reports. Hashes all six files
against operator-reported SHA pins and independently RE-RUNS each original
ELF admission gate to ensure no fabricated/swapped/stale JSON was accepted.

This checks static artifact provenance, not board ownership, secure boot,
memory protection, neural parity, or authorization for JTAG/DDR.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import p08_b45_elf_admission as gate

V3 = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    V3 / "docs" /
    "P08_B4_5_3_OPERATOR_REPORTED_A53_ARTIFACT_PINS_2026_11_05.json"
)
SCHEMA = "p08-b45-both-a53-artifacts-independent-PC-only-reverification-v1"
PIN_SCHEMA = "p08-b45-operator-reported-two-a53-offline-artifact-pins-v1"


class PairElfNoGo(ValueError):
    pass


def need(ok: bool, why: str) -> None:
    if not ok:
        raise PairElfNoGo("NO-GO: " + why)


def strict_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise PairElfNoGo("duplicate JSON key: " + key)
        obj[key] = value
    return obj


def load_json(path: Path) -> dict:
    need(path.is_absolute() and path.is_file() and not path.is_symlink(),
         "existing non-symlink absolute JSON path required: " + str(path))
    raw = path.read_bytes()
    try:
        data = json.loads(raw, object_pairs_hook=strict_object,
                          parse_constant=lambda v: (_ for _ in ()).throw(
                              PairElfNoGo("non-finite JSON value: " + v)))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PairElfNoGo("invalid JSON: " + str(path)) from exc
    need(type(data) is dict, "JSON object required: " + str(path))
    return data


def hex_sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_guard_audit(root: Path, mode: str) -> None:
    """Check staged source really is the approved offline fail-closed source."""
    source = root / "source"
    need(source.is_dir() and not source.is_symlink(),
         "missing original Vitis source stage")
    files = (
        "p08_b45_reset_variants.c", "p08_b45_reset_variants.h",
        "p08_b45_a53_backup_guard.c", "p08_b45_a53_backup_guard.h",
        "p08_b45_auth_once_full1024_a53.c" if mode == "once"
        else "p08_b45_unchecked_full1024_a53.c",
    )
    for name in files:
        local = V3 / "software" / "p08" / name
        staged = source / name
        need(local.is_file() and staged.is_file() and not staged.is_symlink(),
             "required original staged source missing: " + name)
        need(hex_sha(local.read_bytes()) == hex_sha(staged.read_bytes()),
             "staged C source differs from reviewed B4.5 branch: " + name)
    guard = (source / "p08_b45_a53_backup_guard.c").read_text()
    header = (source / "p08_b45_a53_backup_guard.h").read_text()
    need(guard.count("return -1;") == 2 and
         "#define P08_B45_A53_GUARD_PROVISIONED 0u" in header,
         "offline stage no longer uses the deliberate fail-closed DDR guard")


def audit(manifest: Path, original_elf: Path, xsa: Path, pins: Path,
          out: Path, root_override: dict[str, Path] | None = None) -> dict:
    need(out.is_absolute() and not out.exists() and not out.is_symlink()
         and out.parent.is_dir()
         and not out.resolve().is_relative_to(gate.orig.ROOT),
         "new external no-overwrite independent result path required")
    pin = load_json(manifest)
    need(pin.get("schema") == PIN_SCHEMA,
         "wrong operator-evidence pin schema")
    need(pin.get("evidence_status") ==
         "OPERATOR_REPORTED_SHA256_ONLY_NOT_YET_INDEPENDENTLY_REVERIFIED",
         "original reported evidence classification was changed")
    need(pin.get("physical_KV260_executed") is False and
         pin.get("tested_with_original_MNIST_TEST") is False,
         "operator evidence is not a physical/TEST result")
    need(pin.get("original_B2_3_elf_sha256") == gate.ORIGINAL_ELF_SHA and
         pin.get("original_P03_XSA_sha256") == gate.XSA_SHA and
         pin.get("original_B2_2_27_context_pin_sha256") == gate.PINS_SHA,
         "operator original artifact pins drift from accepted sources")
    for name, file, expected in (
        ("B2.3 original ELF", original_elf, gate.ORIGINAL_ELF_SHA),
        ("P03 routed XSA", xsa, gate.XSA_SHA),
        ("B2.2 context SHA header", pins, gate.PINS_SHA),
    ):
        need(file.is_absolute() and file.is_file() and not file.is_symlink(),
             name + " missing or symlinked")
        need(hex_sha(file.read_bytes()) == expected,
             name + " hash mismatch")

    hashes: dict[str, dict] = {}
    reports = []
    for mode in gate.MODES:
        record = pin.get("variants", {}).get(mode)
        need(type(record) is dict, "missing operator-provided " + mode + " pins")
        expected_root = Path(record.get("build_root", ""))
        need(expected_root.is_absolute() and
             expected_root.is_dir() and not expected_root.is_symlink(),
             "missing absolute build root: " + mode)
        root = root_override.get(mode, expected_root) if root_override else expected_root
        need(root.resolve() == expected_root.resolve(),
             "operator pinned build root differs from requested " + mode + " root")
        app = ("p08_b45_auth_once_1024" if mode == "once"
               else "p08_b45_unchecked_1024")
        files = {
            "elf": root / "vitis_workspace" / (app + ".elf"),
            "map": root / "vitis_workspace" / (app + ".map"),
            "report": root / ("p08_b45_" + mode + "_elf_admission.json"),
        }
        sha_checks = {}
        for kind, file in files.items():
            need(file.is_file() and not file.is_symlink(),
                 "missing actual " + mode + " " + kind)
            actual_sha = hex_sha(file.read_bytes())
            expected_sha = record.get(kind + "_sha256")
            need(type(expected_sha) is str and len(expected_sha) == 64 and
                 actual_sha == expected_sha,
                 "operator-pinned " + mode + " " + kind +
                 " SHA-256 mismatch: expected=" + str(expected_sha) +
                 " actual=" + actual_sha + " file=" + str(file))
            sha_checks[kind] = actual_sha
        source_guard_audit(root, mode)
        admitted = load_json(files["report"])
        # Re-run the actual frozen admission algorithm against REAL on-disk
        # local AArch64 ELF/map and the original 3 pinned external artifacts.
        # Its output must exactly match the earlier JSON, not just fields
        # selected by an external report writer.
        with tempfile.TemporaryDirectory(prefix="p08_b45_offline_") as tmp:
            fresh_report_path = Path(tmp) / (mode + "_recomputed.json")
            recomputed = gate.audit(
                mode, files["elf"], files["map"],
                original_elf, xsa, pins, fresh_report_path,
            )
        need(admitted == recomputed,
             mode + " existing ELF admission JSON differs from recomputed truth")
        need(recomputed["unprovisioned_backup_protection_adapter"] is True and
             recomputed["physical_JTAG_DDR_launch_authorized"] is False and
             recomputed["independent_physical_DDR_owner_and_protection_proven"]
             is False and
             recomputed["new_KV260_neural_parity_verified"] is False and
             recomputed["new_KV260_physical_reset_timing_verified"] is False,
             mode + " report misrepresents physical deployment")
        hashes[mode] = sha_checks
        reports.append(recomputed)

    need(hashes["once"]["elf"] != hashes["unchecked"]["elf"] and
         hashes["once"]["map"] != hashes["unchecked"]["map"] and
         hashes["once"]["report"] != hashes["unchecked"]["report"],
         "the two experimental applications must have distinct artifacts")
    need(reports[0]["original_elf_program_segments"] ==
         reports[1]["original_elf_program_segments"] and
         reports[0]["original_p03_xsa_sha256"] ==
         reports[1]["original_p03_xsa_sha256"] and
         reports[0]["original_27_core_sha_header_sha256"] ==
         reports[1]["original_27_core_sha_header_sha256"],
         "experiment modes do not share identical original provenance")

    result = {
        "schema": SCHEMA,
        "operator_pins_sha256": hex_sha(manifest.read_bytes()),
        "each_elf_and_map_cryptographically_reverified": True,
        "both_admission_reports_exactly_recomputed_against_original_inputs": True,
        "both_staged_sources_match_reviewed_offline_branch": True,
        "independent_report_files": hashes,
        "A53_ELF_artifact_generation_both_modes": "PC_ONLY_VERIFIED",
        "KV260_neural_parity_verified": False,
        "physical_memory_ownership_proven": False,
        "physical_JTAG_authorized": False,
        "backup_protection_adapter_provisioned": False,
        "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
    }
    with out.open("x", encoding="utf-8") as fd:
        json.dump(result, fd, indent=2, sort_keys=True)
        fd.write("\n")
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--original-elf", type=Path, required=True)
    p.add_argument("--xsa", type=Path, required=True)
    p.add_argument("--pins-header", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        result = audit(a.manifest, a.original_elf, a.xsa,
                       a.pins_header, a.out)
        print("P08_B45_TWO_GENUINE_A53_ELFS_INDEPENDENT_OFFLINE_PASS=1")
        print("P08_B45_BOTH_PROVENANCE_AND_SOURCE_GUARD_MATCH=1")
        print("P08_B45_KV260_PHYSICAL_INFERENCE_VERIFIED=0")
        print("P08_B45_DDR_OWNER_INDEPENDENTLY_PROVEN=0")
        print("P08_B45_DESTRUCTIVE_JTAG_AUTHORIZED=0")
        print("P08_B45_PAIR_OFFLINE_REPORT=" + str(a.out))
        return 0
    except (PairElfNoGo, gate.VariantElfNoGo, gate.orig.ElfNoGo,
            TypeError, OSError, KeyError, ValueError) as exc:
        print("P08_B45_TWO_A53_ELFS_INDEPENDENT_OFFLINE_NO_GO=" +
              str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
