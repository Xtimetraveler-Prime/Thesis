"""Validation for a source-controlled MNIST deployment freeze package."""

from __future__ import annotations

import json
from pathlib import Path

from .accepted_validation import sha256_file
from .deployment_freeze import FPGA_CORPUS_SCHEMA, FREEZE_SCHEMA, PROFILE_ORDER


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _require_hash(root: Path, relative: str, expected: object) -> None:
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError(f"invalid SHA-256 for {relative}")
    path = root / relative
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(
            f"SHA-256 mismatch for {relative}: expected {expected}, got {actual}"
        )


def validate_frozen_deployment(root: str | Path) -> dict[str, object]:
    """Validate hashes, profile artifacts, and the common FPGA corpus."""

    frozen = Path(root)
    manifest_path = frozen / "freeze_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = _read_json(manifest_path)
    if manifest.get("schema") != FREEZE_SCHEMA:
        raise ValueError("unsupported MNIST deployment-freeze schema")
    if manifest.get("presentation_ticks") != 16:
        raise ValueError("frozen MNIST deployment must use 16 presentation ticks")

    accepted_ref = manifest.get("accepted_validation")
    corpus_ref = manifest.get("fpga_validation_corpus")
    if not isinstance(accepted_ref, str) or not isinstance(corpus_ref, str):
        raise ValueError("freeze manifest is missing validation/corpus paths")
    _require_hash(
        frozen,
        accepted_ref,
        manifest.get("accepted_validation_sha256"),
    )
    _require_hash(
        frozen,
        corpus_ref,
        manifest.get("fpga_validation_corpus_sha256"),
    )

    corpus = _read_json(frozen / corpus_ref)
    if corpus.get("schema") != FPGA_CORPUS_SCHEMA:
        raise ValueError("unsupported FPGA validation-corpus schema")
    entries = corpus.get("entries")
    indices = corpus.get("indices")
    if not isinstance(entries, list) or not isinstance(indices, list):
        raise ValueError("FPGA corpus must contain entries and indices")
    if corpus.get("count") != 30 or len(entries) != 30 or len(indices) != 30:
        raise ValueError("FPGA validation corpus must contain exactly 30 cases")
    if len(set(indices)) != 30:
        raise ValueError("FPGA validation corpus indices must be unique")
    label_counts = {digit: 0 for digit in range(10)}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("FPGA corpus entries must be objects")
        label = entry.get("label")
        if label not in label_counts:
            raise ValueError(f"invalid FPGA corpus label: {label!r}")
        label_counts[label] += 1
    if any(count != 3 for count in label_counts.values()):
        raise ValueError("FPGA corpus must contain exactly three cases per digit")

    profiles = manifest.get("profiles")
    if not isinstance(profiles, dict) or set(profiles) != set(PROFILE_ORDER):
        raise ValueError("freeze manifest must contain both MNIST profiles")

    checked_files = 2
    profile_summary: dict[str, object] = {}
    for profile_name in PROFILE_ORDER:
        record = profiles[profile_name]
        if not isinstance(record, dict):
            raise ValueError(f"invalid freeze record for {profile_name}")

        checkpoint_ref = record.get("checkpoint")
        if not isinstance(checkpoint_ref, str):
            raise ValueError(f"missing checkpoint path for {profile_name}")
        _require_hash(
            frozen,
            checkpoint_ref,
            record.get("checkpoint_sha256"),
        )
        checked_files += 1

        deployment_ref = record.get("deployment")
        if not isinstance(deployment_ref, str):
            raise ValueError(f"missing deployment path for {profile_name}")
        deployment_hashes = record.get("deployment_hashes")
        if not isinstance(deployment_hashes, dict):
            raise ValueError(f"missing deployment hashes for {profile_name}")

        deployment_dir = Path(deployment_ref).parent
        for relative, expected_hash in deployment_hashes.items():
            if not isinstance(relative, str):
                raise ValueError("deployment hash keys must be strings")
            _require_hash(
                frozen,
                str(deployment_dir / relative),
                expected_hash,
            )
            checked_files += 1

        summary = record.get("accepted_summary")
        if not isinstance(summary, dict):
            raise ValueError(f"missing accepted summary for {profile_name}")
        profile_summary[profile_name] = {
            "golden_accuracy": summary.get("golden_accuracy"),
            "stored_synapses": summary.get("deployment_stored_synapses"),
            "checkpoint_sha256": record.get("checkpoint_sha256"),
        }

    return {
        "schema": FREEZE_SCHEMA,
        "valid": True,
        "checked_files": checked_files,
        "corpus_cases": 30,
        "cases_per_digit": label_counts,
        "profiles": profile_summary,
    }
