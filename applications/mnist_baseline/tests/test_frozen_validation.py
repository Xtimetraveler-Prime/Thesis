import json
from pathlib import Path

import pytest

from mnist_app.accepted_validation import sha256_file
from mnist_app.deployment_freeze import FPGA_CORPUS_SCHEMA, FREEZE_SCHEMA
from mnist_app.frozen_validation import validate_frozen_deployment


def _write(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return sha256_file(path)


def _build_frozen_fixture(root: Path) -> None:
    accepted_hash = _write(root / "accepted.json", "{}\n")
    entries = []
    indices = []
    for digit in range(10):
        for offset in range(3):
            index = digit * 3 + offset
            indices.append(index)
            entries.append({"mnist_test_index": index, "label": digit})
    corpus_hash = _write(
        root / "corpus.json",
        json.dumps(
            {
                "schema": FPGA_CORPUS_SCHEMA,
                "count": 30,
                "indices": indices,
                "entries": entries,
            }
        )
        + "\n",
    )

    profiles = {}
    for profile in ("cropped-dense", "native-sparse"):
        checkpoint_rel = f"checkpoints/{profile}.npz"
        checkpoint_hash = _write(root / checkpoint_rel, f"{profile}:checkpoint\n")
        deployment_dir = root / "deployments" / profile
        deployment_hashes = {}
        for relative in (
            "deployment.json",
            "weight_image/weight_storage.json",
            "weight_image/weight_formats.mem",
            "weight_image/weight_synapses.mem",
            "weight_image/weight_axon_rows.mem",
        ):
            deployment_hashes[relative] = _write(
                deployment_dir / relative,
                f"{profile}:{relative}\n",
            )
        profiles[profile] = {
            "checkpoint": checkpoint_rel,
            "checkpoint_sha256": checkpoint_hash,
            "deployment": f"deployments/{profile}/deployment.json",
            "deployment_hashes": deployment_hashes,
            "accepted_summary": {
                "golden_accuracy": 0.9,
                "deployment_stored_synapses": 4000,
            },
        }

    (root / "freeze_manifest.json").write_text(
        json.dumps(
            {
                "schema": FREEZE_SCHEMA,
                "accepted_validation": "accepted.json",
                "accepted_validation_sha256": accepted_hash,
                "fpga_validation_corpus": "corpus.json",
                "fpga_validation_corpus_sha256": corpus_hash,
                "presentation_ticks": 16,
                "profiles": profiles,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_validate_frozen_deployment_checks_complete_package(tmp_path: Path):
    _build_frozen_fixture(tmp_path)
    result = validate_frozen_deployment(tmp_path)
    assert result["valid"] is True
    assert result["corpus_cases"] == 30
    assert result["checked_files"] == 14
    assert result["cases_per_digit"] == {digit: 3 for digit in range(10)}


def test_validate_frozen_deployment_detects_tampering(tmp_path: Path):
    _build_frozen_fixture(tmp_path)
    target = tmp_path / "deployments/cropped-dense/weight_image/weight_synapses.mem"
    target.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        validate_frozen_deployment(tmp_path)
