#!/usr/bin/env python3
"""Review an already-saved M08 D3.2 PC inventory receipt WITHOUT touching candidates.

This is offline evidence triage, not attestation of boot/firmware/PS state.
Reads only an exclusive owner-PC JSON + SHA receipt. Never scans any new
files, reads boot binaries, invokes device tools, or authorizes AXI access.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

SCHEMA = "m08-d3b-boot-platform-inventory-v2"
REVIEW_SCHEMA = "m08-d3b-offline-provenance-receipt-review-v1"
STATUS = "OFFLINE_PC_CANDIDATES_ONLY_NO_BOOT_OR_HARDWARE_PROOF"
REQUIRED_FALSE = (
    "hardware_mmio_authorized", "physical_programming_authorized",
    "atb4_hardware_proven", "aib13_hardware_proven",
    "linux_clock_afi_proven", "proceed_to_d3b5_native_hpm0",
)
REFERENCE_SHA = {
    "k26_starter_kits.dtbo":
        "1e998ffd5d33a05da3746df3603e65603e1628006bc878209a836cc9bd3c4ae1",
    "m08-v1-fan-page-uio-review.dtbo":
        "2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed",
}
CLASSES = {
    "XSA_HARDWARE_EXPORT_UNATTESTED",
    "GENERATED_PS_INIT_SOURCE_UNATTESTED",
    "BOOT_PACKAGE_METADATA_ONLY",
    "BOOT_COMPONENT_BINARY_UNATTESTED",
    "DEVICE_TREE_BINARY_UNAPPLIED",
    "DEVICE_TREE_SOURCE_UNAPPLIED",
    "BOOT_BUILD_RECIPE_UNATTESTED",
    "PLATFORM_LOG_OR_MANIFEST_UNATTESTED",
}


class ReviewRejected(ValueError):
    pass


def must(value: bool, message: str) -> None:
    if not value:
        raise ReviewRejected(message)


def read_regular(path: Path, maximum: int) -> bytes:
    must(path.is_file() and not path.is_symlink(),
         "missing/symlinked receipt file: " + path.name)
    size = path.stat().st_size
    must(0 < size <= maximum, "receipt file size invalid: " + path.name)
    return path.read_bytes()


def review(run: Path) -> dict:
    must(run.is_dir() and not run.is_symlink(), "invalid evidence directory")
    # The run itself is a local PC evidence directory, not a board path.
    for part in run.absolute().parents:
        must(not part.is_symlink(), "symlinked evidence directory ancestor")
    data = read_regular(run / "00_boot_platform_inventory.json", 6_000_000)
    receipt = read_regular(run / "99_evidence_sha256.txt", 4096).decode("ascii")
    lines = receipt.splitlines()
    must(len(lines) == 1 and re.fullmatch(
         r"[0-9a-f]{64}  00_boot_platform_inventory\.json", lines[0]) is not None,
         "unexpected receipt layout")
    verified = sha256(data).hexdigest()
    must(lines[0][:64] == verified, "inventory SHA256 receipt mismatch")
    obj = json.loads(data)
    must(isinstance(obj, dict) and obj.get("schema") == SCHEMA and
         obj.get("status") == STATUS, "wrong inventory schema or unsupported status")
    must(obj.get("original_m08_image_quarantined") is True,
         "original image quarantine not attested")
    must(obj.get("original_m08_bit_bin_sha256_quarantined") ==
         "a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b",
         "wrong quarantined image digest")
    for key in REQUIRED_FALSE:
        must(obj.get(key) is False, "forbidden hardware proof claim: " + key)
    must(isinstance(obj.get("blocked_requirements"), dict)
         and len(obj["blocked_requirements"]) >= 8
         and all(x == "UNKNOWN_NOT_PROVEN" for x in
                 obj["blocked_requirements"].values()),
         "unproven PS configuration changed to approved")
    must(isinstance(obj.get("candidates"), list)
         and len(obj["candidates"]) <= 50000,
         "invalid inventory candidates")
    must(isinstance(obj.get("coverage"), dict)
         and isinstance(obj["coverage"].get("entries_seen"), int)
         and obj["coverage"]["entries_seen"] >= len(obj["candidates"]),
         "inconsistent inventory coverage")
    counter: Counter[str] = Counter()
    seen_paths: set[str] = set()
    matched: dict[str, list[str]] = {k: [] for k in REFERENCE_SHA}
    different: dict[str, list[str]] = {k: [] for k in REFERENCE_SHA}
    unhashed: dict[str, list[str]] = {k: [] for k in REFERENCE_SHA}
    source_candidates = []
    for item in obj["candidates"]:
        must(isinstance(item, dict), "non-object inventory candidate")
        path = item.get("path")
        cl = item.get("evidence_class")
        digest = item.get("sha256")
        must(isinstance(path, str) and Path(path).is_absolute()
             and path not in seen_paths and len(path) < 4096,
             "duplicate or non-absolute candidate path")
        seen_paths.add(path)
        must(cl in CLASSES, "unknown inventory evidence class")
        must(item.get("ps_runtime_configuration_proven") is False
             and item.get("deployed_or_applied") == "UNKNOWN"
             and item.get("boot_component_version") == "UNKNOWN",
             "candidate falsely claims runtime/deployment")
        must(digest is None or (isinstance(digest, str)
             and re.fullmatch(r"[0-9a-f]{64}", digest) is not None),
             "invalid candidate SHA256")
        name = Path(path).name.lower()
        pin = REFERENCE_SHA.get(name)
        expected_match = bool(pin and digest == pin)
        must(item.get("pinned_original_digest_match") is expected_match,
             "filename promoted to original without SHA match")
        must(item.get("historical_reference_filename_match") is (pin is not None),
             "historical basename classification wrong")
        comparison = ("NOT_A_REFERENCE_FILENAME" if pin is None else
                      "UNHASHED_REFERENCE_NAME_NOT_VERIFIED" if digest is None else
                      "SHA256_MATCH_HISTORICAL_REFERENCE_BYTES_ONLY" if expected_match else
                      "SAME_BASENAME_DIFFERENT_SHA256_CANDIDATE_ONLY")
        must(item.get("historical_reference_comparison") == comparison,
             "historical-reference comparison inconsistent")
        counter[cl] += 1
        if pin:
            if expected_match:
                matched[name].append(path)
            elif digest is None:
                unhashed[name].append(path)
            else:
                different[name].append(path)
        if cl in ("XSA_HARDWARE_EXPORT_UNATTESTED",
                  "GENERATED_PS_INIT_SOURCE_UNATTESTED",
                  "BOOT_BUILD_RECIPE_UNATTESTED"):
            # Only names/digests are printed; owner can select relevant originals.
            source_candidates.append({
                "evidence_class": cl, "filename": name,
                "sha256": digest, "owner_source_reviewed": False,
            })
    refs = obj.get("pinned_originals")
    must(isinstance(refs, dict) and set(refs) == set(REFERENCE_SHA),
         "missing reference summary")
    for name, digest in REFERENCE_SHA.items():
        rec = refs[name]
        must(rec.get("expected_sha256") == digest
             and rec.get("historical_deployment_or_boot_proven") is False,
             "unsupported reference provenance")
        must(sorted(rec.get("sha256_matching_paths", [])) == sorted(matched[name])
             and sorted(rec.get("same_name_different_bytes_paths", [])) ==
             sorted(different[name])
             and sorted(rec.get("same_name_unhashed_paths", [])) == sorted(unhashed[name]),
             "reference summary does not match candidate bytes")
        expected_status = (
            "LOCAL_PATH_AND_SHA256_MATCH_NOT_BOOT_PROOF" if matched[name] else
            "REFERENCE_NOT_FOUND_SAME_NAME_DIFFERENT_BYTES" if different[name] else
            "REFERENCE_NOT_FOUND_NAME_ONLY_UNHASHED" if unhashed[name] else
            "NOT_FOUND_IN_BOUNDED_SCAN_UNKNOWN"
        )
        must(rec.get("status") == expected_status, "false historical reference status")
    source_candidates.sort(key=lambda x: (x["evidence_class"], x["filename"],
                                          x["sha256"] or ""))
    return {
        "schema": REVIEW_SCHEMA,
        "status": "OWNER_PC_INVENTORY_RECEIPT_INTEGRITY_ACCEPTED_BOOT_OWNERSHIP_UNKNOWN",
        "inventory_sha256": verified,
        "candidate_count": len(obj["candidates"]),
        "candidate_class_counts": dict(sorted(counter.items())),
        "possible_boot_source_candidates": source_candidates,
        "historical_reference_matches": {
            name: {
                "sha256_matches": len(matched[name]),
                "same_name_different_bytes": len(different[name]),
                "same_name_unhashed": len(unhashed[name]),
                "proves_loaded_or_applied": False,
            } for name in sorted(REFERENCE_SHA)
        },
        "unresolved": sorted(obj["blocked_requirements"]),
        "accepted_provenance_scope": "INVENTORY_JSON_AND_RECEIPT_ONLY",
        "has_original_boot_config_evidence": False,
        "physical_access_authorized": False,
        "protected_image_authorized": False,
        "original_m08_image_quarantined": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = review(args.run_dir)
    except (ReviewRejected, OSError, UnicodeError, ValueError, KeyError,
            TypeError) as exc:
        print("M08_D3_2_RECEIPT_REVIEW_REJECTED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
