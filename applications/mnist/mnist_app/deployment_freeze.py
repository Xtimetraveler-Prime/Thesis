"""Freeze accepted MNIST deployments and a common FPGA-validation corpus."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np

from .accepted_validation import ACCEPTED_VALIDATION_SCHEMA, sha256_file

FREEZE_SCHEMA = "neuromorphic-twin-mnist-deployment-freeze-v1"
FPGA_CORPUS_SCHEMA = "neuromorphic-twin-mnist-fpga-corpus-v1"
PROFILE_ORDER = ("cropped-dense", "native-sparse")


def _read_json(path: str | Path) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _validate_accepted_manifest(payload: dict[str, object]) -> None:
    if payload.get("schema") != ACCEPTED_VALIDATION_SCHEMA:
        raise ValueError("unsupported accepted-validation schema")
    if payload.get("corpus") != "official-mnist-test-full":
        raise ValueError("MNIST-06 requires the full accepted MNIST test validation")
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict) or set(profiles) != set(PROFILE_ORDER):
        raise ValueError("accepted validation must contain both frozen profiles")


def _load_matched_details(
    accepted_manifest_path: Path,
    accepted: dict[str, object],
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    profiles = accepted["profiles"]
    assert isinstance(profiles, dict)
    for profile_name in PROFILE_ORDER:
        record = profiles[profile_name]
        if not isinstance(record, dict):
            raise ValueError(f"invalid accepted record for {profile_name}")
        detail_ref = record.get("matched_comparison")
        if not isinstance(detail_ref, str):
            raise ValueError(f"missing matched comparison for {profile_name}")
        detail_path = Path(detail_ref)
        if not detail_path.is_absolute():
            # The accepted runner normally stores a path relative to the repo
            # working directory. If that no longer resolves, fall back to the
            # accepted manifest directory by basename.
            if not detail_path.is_file():
                detail_path = accepted_manifest_path.parent / detail_path.name
        if not detail_path.is_file():
            raise FileNotFoundError(detail_path)
        expected_hash = record.get("matched_comparison_sha256")
        if expected_hash != sha256_file(detail_path):
            raise ValueError(f"matched comparison hash mismatch for {profile_name}")
        detail = _read_json(detail_path)
        if detail.get("corpus") != "official-mnist-test-full":
            raise ValueError(f"{profile_name} comparison is not the full test corpus")
        result[profile_name] = detail
    return result


def select_fpga_validation_corpus(
    cropped_detail: dict[str, object],
    native_detail: dict[str, object],
) -> dict[str, object]:
    """Select deterministic easy/divergent/hard cases for every digit class."""

    cropped_labels = np.asarray(cropped_detail.get("labels"), dtype=np.int64)
    native_labels = np.asarray(native_detail.get("labels"), dtype=np.int64)
    cropped_pred = np.asarray(
        cropped_detail.get("golden_predictions"), dtype=np.int64
    )
    native_pred = np.asarray(native_detail.get("golden_predictions"), dtype=np.int64)

    if cropped_labels.ndim != 1 or len(cropped_labels) == 0:
        raise ValueError("cropped comparison must contain labels")
    if not np.array_equal(cropped_labels, native_labels):
        raise ValueError("both profile comparisons must use identical source labels")
    if cropped_pred.shape != cropped_labels.shape:
        raise ValueError("cropped golden predictions do not match labels")
    if native_pred.shape != cropped_labels.shape:
        raise ValueError("native golden predictions do not match labels")

    entries: list[dict[str, object]] = []
    used: set[int] = set()

    def first_unused(candidates: np.ndarray) -> int | None:
        for raw in candidates:
            index = int(raw)
            if index not in used:
                return index
        return None

    for digit in range(10):
        class_indices = np.flatnonzero(cropped_labels == digit)
        if len(class_indices) == 0:
            raise ValueError(f"test corpus contains no samples for digit {digit}")

        categories = (
            (
                "both-correct",
                class_indices[
                    (cropped_pred[class_indices] == digit)
                    & (native_pred[class_indices] == digit)
                ],
            ),
            (
                "profile-divergent",
                class_indices[
                    cropped_pred[class_indices] != native_pred[class_indices]
                ],
            ),
            (
                "both-wrong",
                class_indices[
                    (cropped_pred[class_indices] != digit)
                    & (native_pred[class_indices] != digit)
                ],
            ),
        )

        for requested_reason, candidates in categories:
            index = first_unused(candidates)
            selected_reason = requested_reason
            if index is None:
                index = first_unused(class_indices)
                selected_reason = f"fallback-for-{requested_reason}"
            if index is None:
                raise AssertionError("unable to select a unique corpus sample")
            used.add(index)
            entries.append(
                {
                    "mnist_test_index": index,
                    "label": digit,
                    "selection_reason": selected_reason,
                    "cropped_dense_golden_prediction": int(cropped_pred[index]),
                    "native_sparse_golden_prediction": int(native_pred[index]),
                    "cropped_dense_correct": bool(cropped_pred[index] == digit),
                    "native_sparse_correct": bool(native_pred[index] == digit),
                }
            )

    return {
        "schema": FPGA_CORPUS_SCHEMA,
        "source": "official-mnist-test",
        "selection_policy": (
            "per digit: first unused both-correct, first unused profile-divergent, "
            "first unused both-wrong; deterministic class-local fallback when absent"
        ),
        "count": len(entries),
        "indices": [entry["mnist_test_index"] for entry in entries],
        "entries": entries,
    }


def _copy_file_verified(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    source_hash = sha256_file(source)
    if sha256_file(destination) != source_hash:
        raise IOError(f"copy verification failed for {source}")
    return source_hash


def _copy_deployment(
    source_dir: Path,
    destination_dir: Path,
) -> dict[str, str]:
    required = (
        Path("deployment.json"),
        Path("weight_image/weight_storage.json"),
        Path("weight_image/weight_formats.mem"),
        Path("weight_image/weight_synapses.mem"),
        Path("weight_image/weight_axon_rows.mem"),
    )
    hashes: dict[str, str] = {}
    for relative in required:
        source = source_dir / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        hashes[str(relative)] = _copy_file_verified(
            source,
            destination_dir / relative,
        )
    return hashes


def freeze_accepted_deployments(
    accepted_manifest_path: str | Path,
    training_dir: str | Path,
    deployment_root: str | Path,
    output_dir: str | Path,
) -> Path:
    """Copy immutable accepted artifacts and freeze a common FPGA corpus."""

    accepted_path = Path(accepted_manifest_path)
    accepted = _read_json(accepted_path)
    _validate_accepted_manifest(accepted)
    details = _load_matched_details(accepted_path, accepted)

    output = Path(output_dir)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    corpus = select_fpga_validation_corpus(
        details["cropped-dense"],
        details["native-sparse"],
    )
    corpus_path = output / "fpga_validation_corpus.json"
    corpus_path.write_text(
        json.dumps(corpus, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    accepted_copy = output / "accepted_software_validation.json"
    accepted_hash = _copy_file_verified(accepted_path, accepted_copy)

    training = Path(training_dir)
    deployments = Path(deployment_root)
    profiles = accepted["profiles"]
    assert isinstance(profiles, dict)
    frozen_profiles: dict[str, object] = {}

    for profile_name in PROFILE_ORDER:
        record = profiles[profile_name]
        assert isinstance(record, dict)
        checkpoint_record = record.get("checkpoint")
        if not isinstance(checkpoint_record, dict):
            raise ValueError(f"missing checkpoint record for {profile_name}")

        checkpoint = training / f"{profile_name}_snn_float.npz"
        if not checkpoint.is_file():
            raise FileNotFoundError(checkpoint)
        checkpoint_hash = sha256_file(checkpoint)
        if checkpoint_hash != checkpoint_record.get("checkpoint_sha256"):
            raise ValueError(f"checkpoint hash mismatch for {profile_name}")
        frozen_checkpoint = output / "checkpoints" / checkpoint.name
        _copy_file_verified(checkpoint, frozen_checkpoint)

        source_deployment = deployments / profile_name
        frozen_deployment = output / "deployments" / profile_name
        deployment_hashes = _copy_deployment(source_deployment, frozen_deployment)

        expected_hashes = record.get("deployment_hashes")
        if not isinstance(expected_hashes, dict):
            raise ValueError(f"missing deployment hashes for {profile_name}")
        key_map = {
            "deployment.json": "deployment_json",
            "weight_image/weight_storage.json": "weight_storage_json",
            "weight_image/weight_formats.mem": "weight_formats_mem",
            "weight_image/weight_synapses.mem": "weight_synapses_mem",
            "weight_image/weight_axon_rows.mem": "weight_axon_rows_mem",
        }
        for relative, accepted_key in key_map.items():
            if deployment_hashes[relative] != expected_hashes.get(accepted_key):
                raise ValueError(
                    f"accepted deployment hash mismatch for {profile_name}: {relative}"
                )

        summary = record.get("summary")
        if not isinstance(summary, dict):
            raise ValueError(f"missing accepted summary for {profile_name}")
        frozen_profiles[profile_name] = {
            "checkpoint": f"checkpoints/{checkpoint.name}",
            "checkpoint_sha256": checkpoint_hash,
            "deployment": f"deployments/{profile_name}/deployment.json",
            "deployment_hashes": deployment_hashes,
            "accepted_summary": summary,
        }

    freeze_manifest = output / "freeze_manifest.json"
    freeze_manifest.write_text(
        json.dumps(
            {
                "schema": FREEZE_SCHEMA,
                "accepted_validation": "accepted_software_validation.json",
                "accepted_validation_sha256": accepted_hash,
                "fpga_validation_corpus": "fpga_validation_corpus.json",
                "fpga_validation_corpus_sha256": sha256_file(corpus_path),
                "presentation_ticks": 16,
                "profiles": frozen_profiles,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return freeze_manifest
