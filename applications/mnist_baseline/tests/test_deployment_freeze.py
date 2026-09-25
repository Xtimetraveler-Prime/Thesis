import json
from pathlib import Path

import numpy as np
import pytest

from mnist_app.accepted_validation import ACCEPTED_VALIDATION_SCHEMA, sha256_file
from mnist_app.deployment_freeze import (
    FPGA_CORPUS_SCHEMA,
    FREEZE_SCHEMA,
    freeze_accepted_deployments,
    select_fpga_validation_corpus,
)


def _synthetic_details():
    labels = np.repeat(np.arange(10, dtype=np.int64), 4)
    cropped = labels.copy()
    native = labels.copy()
    for digit in range(10):
        base = digit * 4
        # sample 0: both correct
        # sample 1: divergent, cropped wrong/native correct
        cropped[base + 1] = (digit + 1) % 10
        # sample 2: divergent, native wrong/cropped correct
        native[base + 2] = (digit + 2) % 10
        # sample 3: both wrong
        cropped[base + 3] = (digit + 3) % 10
        native[base + 3] = (digit + 4) % 10
    return (
        {
            "corpus": "official-mnist-test-full",
            "labels": labels.tolist(),
            "golden_predictions": cropped.tolist(),
        },
        {
            "corpus": "official-mnist-test-full",
            "labels": labels.tolist(),
            "golden_predictions": native.tolist(),
        },
    )


def test_fpga_corpus_selects_three_unique_samples_per_digit():
    cropped, native = _synthetic_details()
    corpus = select_fpga_validation_corpus(cropped, native)
    assert corpus["schema"] == FPGA_CORPUS_SCHEMA
    assert corpus["count"] == 30
    assert len(set(corpus["indices"])) == 30
    reasons = [entry["selection_reason"] for entry in corpus["entries"]]
    assert reasons.count("both-correct") == 10
    assert reasons.count("profile-divergent") == 10
    assert reasons.count("both-wrong") == 10
    for digit in range(10):
        selected = [entry for entry in corpus["entries"] if entry["label"] == digit]
        assert len(selected) == 3


def test_fpga_corpus_rejects_different_source_labels():
    cropped, native = _synthetic_details()
    native["labels"][0] = 9
    with pytest.raises(ValueError, match="identical source labels"):
        select_fpga_validation_corpus(cropped, native)


def _write_deployment(root: Path, profile: str) -> dict[str, str]:
    target = root / profile
    weight = target / "weight_image"
    weight.mkdir(parents=True)
    files = {
        "deployment_json": target / "deployment.json",
        "weight_storage_json": weight / "weight_storage.json",
        "weight_formats_mem": weight / "weight_formats.mem",
        "weight_synapses_mem": weight / "weight_synapses.mem",
        "weight_axon_rows_mem": weight / "weight_axon_rows.mem",
    }
    for name, path in files.items():
        path.write_text(f"{profile}:{name}\n", encoding="utf-8")
    return {name: sha256_file(path) for name, path in files.items()}


def test_freeze_copies_hash_verified_artifacts(tmp_path: Path):
    training = tmp_path / "training"
    deployment_root = tmp_path / "deployments"
    accepted_dir = tmp_path / "accepted"
    frozen = tmp_path / "frozen"
    training.mkdir()
    accepted_dir.mkdir()

    details = _synthetic_details()
    profiles = {}
    for profile, detail in zip(("cropped-dense", "native-sparse"), details, strict=True):
        checkpoint = training / f"{profile}_snn_float.npz"
        np.savez_compressed(
            checkpoint,
            profile=np.asarray(profile),
            presentation_ticks=np.int32(16),
            weights=np.ones((1, 1), dtype=np.float32),
        )
        detail_path = accepted_dir / f"{profile}_matched_comparison.json"
        detail_path.write_text(json.dumps(detail) + "\n", encoding="utf-8")
        profiles[profile] = {
            "checkpoint": {"checkpoint_sha256": sha256_file(checkpoint)},
            "deployment_hashes": _write_deployment(deployment_root, profile),
            "matched_comparison": str(detail_path),
            "matched_comparison_sha256": sha256_file(detail_path),
            "summary": {"golden_accuracy": 0.9},
        }

    accepted = accepted_dir / "accepted_software_validation.json"
    accepted.write_text(
        json.dumps(
            {
                "schema": ACCEPTED_VALIDATION_SCHEMA,
                "corpus": "official-mnist-test-full",
                "profiles": profiles,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = freeze_accepted_deployments(
        accepted,
        training,
        deployment_root,
        frozen,
    )
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["schema"] == FREEZE_SCHEMA
    assert (frozen / "fpga_validation_corpus.json").is_file()
    for profile in ("cropped-dense", "native-sparse"):
        assert (frozen / "checkpoints" / f"{profile}_snn_float.npz").is_file()
        assert (frozen / "deployments" / profile / "deployment.json").is_file()
