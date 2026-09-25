"""Accepted MNIST-04/05 export, matched comparison, and artifact provenance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from .comparison import compare_float_checkpoint_to_golden
from .config import PRESENTATION_TICKS, PROFILES, get_profile
from .export import write_deployment

ACCEPTED_VALIDATION_SCHEMA = "neuromorphic-twin-mnist-accepted-validation-v1"


def sha256_file(path: str | Path) -> str:
    """Return a stable SHA-256 digest for one artifact."""

    target = Path(path)
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_accepted_checkpoint(
    checkpoint_path: str | Path,
    expected_profile: str,
) -> dict[str, object]:
    """Validate the immutable application contract embedded in a checkpoint."""

    selected = get_profile(expected_profile)
    path = Path(checkpoint_path)
    checkpoint = np.load(path)
    if "profile" not in checkpoint:
        raise ValueError("accepted checkpoint must contain an explicit profile")
    profile = str(np.asarray(checkpoint["profile"]).item())
    if profile != selected.name:
        raise ValueError(
            f"checkpoint profile {profile!r} does not match {selected.name!r}"
        )

    ticks = int(np.asarray(checkpoint["presentation_ticks"]).item())
    if ticks != PRESENTATION_TICKS:
        raise ValueError(
            f"checkpoint presentation_ticks={ticks} does not match {PRESENTATION_TICKS}"
        )

    weights = np.asarray(checkpoint["weights"], dtype=np.float32)
    expected_shape = (selected.input_axons, 10)
    if weights.shape != expected_shape:
        raise ValueError(
            f"checkpoint weights must have shape {expected_shape}; got {weights.shape}"
        )
    if not np.all(np.isfinite(weights)):
        raise ValueError("checkpoint weights must be finite")

    nonzero = int(np.count_nonzero(weights))
    if nonzero > selected.max_synapses:
        raise ValueError(
            f"checkpoint has {nonzero} nonzero weights, exceeding "
            f"{selected.name} limit {selected.max_synapses}"
        )

    return {
        "profile": selected.name,
        "input_axons": selected.input_axons,
        "presentation_ticks": ticks,
        "nonzero_weights": nonzero,
        "checkpoint_sha256": sha256_file(path),
    }


def _deployment_hashes(manifest_path: Path) -> dict[str, str]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    weight_manifest = manifest_path.parent / payload["weight_storage"]
    weight_dir = weight_manifest.parent
    paths = {
        "deployment_json": manifest_path,
        "weight_storage_json": weight_manifest,
        "weight_formats_mem": weight_dir / "weight_formats.mem",
        "weight_synapses_mem": weight_dir / "weight_synapses.mem",
        "weight_axon_rows_mem": weight_dir / "weight_axon_rows.mem",
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "deployment is missing expected artifacts: " + ", ".join(missing)
        )
    return {name: sha256_file(path) for name, path in paths.items()}


def _compact_comparison(result: dict[str, object]) -> dict[str, object]:
    excluded = {
        "labels",
        "float_predictions",
        "float_incorrect_indices",
        "golden_predictions",
        "golden_incorrect_indices",
        "golden_confusion_matrix",
    }
    return {key: value for key, value in result.items() if key not in excluded}


def run_accepted_software_validation(
    training_dir: str | Path,
    deployment_root: str | Path,
    output_dir: str | Path,
    *,
    limit: int | None = None,
    batch_size: int = 128,
) -> Path:
    """Export and compare both accepted profiles on one matched MNIST corpus."""

    training = Path(training_dir)
    deployments = Path(deployment_root)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    profile_records: dict[str, object] = {}
    for profile_name in ("cropped-dense", "native-sparse"):
        checkpoint = training / f"{profile_name}_snn_float.npz"
        if not checkpoint.is_file():
            raise FileNotFoundError(f"missing accepted checkpoint: {checkpoint}")

        checkpoint_info = validate_accepted_checkpoint(checkpoint, profile_name)
        deployment_manifest = write_deployment(
            checkpoint,
            deployments / profile_name,
        )
        comparison = compare_float_checkpoint_to_golden(
            checkpoint,
            deployment_manifest,
            limit=limit,
            batch_size=batch_size,
            include_details=True,
        )

        detail_path = output / f"{profile_name}_matched_comparison.json"
        detail_path.write_text(
            json.dumps(comparison, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        profile_records[profile_name] = {
            "checkpoint": checkpoint_info,
            "deployment_manifest": str(deployment_manifest),
            "deployment_hashes": _deployment_hashes(deployment_manifest),
            "matched_comparison": str(detail_path),
            "matched_comparison_sha256": sha256_file(detail_path),
            "summary": _compact_comparison(comparison),
        }

    manifest = output / "accepted_software_validation.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": ACCEPTED_VALIDATION_SCHEMA,
                "corpus": (
                    "official-mnist-test-full"
                    if limit is None
                    else f"official-mnist-test-first-{limit}"
                ),
                "profiles": profile_records,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest
