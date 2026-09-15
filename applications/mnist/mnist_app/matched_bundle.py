"""Backend-neutral request bundles for matched MNIST reference experiments."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterator, Sequence

import numpy as np

from .brian2loihi_matched import MatchedImageInput
from .matched_reference import PROFILE, frozen_corpus_indices


BUNDLE_SCHEMA = "neuromorphic-twin-mnist-matched-request-bundle-v1"
SHARD_MANIFEST_SCHEMA = "neuromorphic-twin-mnist-matched-request-shards-v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scope_indices(scope: str, frozen_root: str | Path) -> tuple[int, ...]:
    if scope == "anchor":
        return (3, 1)
    if scope == "corpus":
        return frozen_corpus_indices(frozen_root)
    if scope == "full":
        return tuple(range(10_000))
    raise ValueError("scope must be one of: anchor, corpus, full")


def _load_generation_context(frozen_root: str | Path):
    """Load dataset/deployment once for a potentially large matched scope."""

    from .dataset import load_mnist
    from .inference import load_deployment

    root = Path(frozen_root)
    deployment_path = root / "deployments" / PROFILE / "deployment.json"
    dataset = load_mnist()
    runtime = load_deployment(deployment_path)
    if runtime.profile.name != PROFILE:
        raise ValueError("matched bundle generation loaded the wrong frozen profile")
    return root, dataset, runtime


def _provenance(root: Path) -> dict[str, object]:
    deployment = root / "deployments" / PROFILE / "deployment.json"
    storage = root / "deployments" / PROFILE / "weight_image" / "weight_storage.json"
    freeze_manifest = root / "freeze_manifest.json"
    return {
        "freeze_manifest_sha256": _sha256(freeze_manifest),
        "deployment_sha256": _sha256(deployment),
        "weight_storage_sha256": _sha256(storage),
        "source": "frozen mnist-v1 native-sparse deployment and deterministic encoder",
    }


def _build_cases(dataset, runtime, indices: Sequence[int]) -> list[dict[str, object]]:
    from .encoding import encode_event_schedule
    from .inference import infer_image

    unique = tuple(int(index) for index in indices)
    if not unique or len(set(unique)) != len(unique):
        raise ValueError("matched bundle requires one or more unique MNIST test indices")

    cases: list[dict[str, object]] = []
    for index in unique:
        if not 0 <= index < len(dataset.x_test):
            raise ValueError(f"MNIST test index {index} is outside the official test split")
        image = np.asarray(dataset.x_test[index])
        label = int(dataset.y_test[index])
        result = infer_image(
            runtime.core,
            image,
            profile=runtime.profile,
            row_lengths=runtime.row_lengths,
        )
        schedule = encode_event_schedule(image, profile=runtime.profile)
        cases.append(
            {
                "mnist_test_index": index,
                "label": label,
                "external_schedule": [list(row) for row in schedule],
                "total_input_events": sum(len(row) for row in schedule),
                "golden_prediction": int(result.prediction),
                "golden_spike_counts": list(result.spike_counts),
            }
        )
    return cases


def _bundle_payload(
    root: Path,
    cases: Sequence[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": BUNDLE_SCHEMA,
        "profile": PROFILE,
        "case_count": len(cases),
        "presentation_ticks": 16,
        "provenance": _provenance(root),
        "cases": list(cases),
    }


def build_matched_request_bundle(
    frozen_root: str | Path,
    indices: Sequence[int],
) -> dict[str, object]:
    root, dataset, runtime = _load_generation_context(frozen_root)
    cases = _build_cases(dataset, runtime, indices)
    return _bundle_payload(root, cases)


def write_matched_request_bundle(
    frozen_root: str | Path,
    indices: Sequence[int],
    output: str | Path,
) -> Path:
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(build_matched_request_bundle(frozen_root, indices), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return target


def write_matched_request_shards(
    frozen_root: str | Path,
    indices: Sequence[int],
    output_dir: str | Path,
    *,
    shard_size: int = 100,
) -> Path:
    """Write deterministic bounded-size bundles plus a verified manifest.

    Full-test execution uses shards so external environments never need to load
    one giant 10,000-image JSON object. Dataset and deployment are loaded once
    during generation, and the golden core is reset by ``infer_image`` per case.
    """

    if shard_size <= 0:
        raise ValueError("shard_size must be positive")
    ordered = tuple(int(index) for index in indices)
    if not ordered or len(set(ordered)) != len(ordered):
        raise ValueError("matched shard generation requires unique indices")

    root, dataset, runtime = _load_generation_context(frozen_root)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    provenance = _provenance(root)
    shard_records: list[dict[str, object]] = []

    for shard_id, start in enumerate(range(0, len(ordered), shard_size)):
        chunk = ordered[start : start + shard_size]
        cases = _build_cases(dataset, runtime, chunk)
        payload = {
            "schema": BUNDLE_SCHEMA,
            "profile": PROFILE,
            "case_count": len(cases),
            "presentation_ticks": 16,
            "provenance": provenance,
            "cases": cases,
        }
        name = f"shard-{shard_id:05d}.json"
        path = output / name
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        shard_records.append(
            {
                "path": name,
                "case_count": len(cases),
                "first_index": int(chunk[0]),
                "last_index": int(chunk[-1]),
                "sha256": _sha256(path),
            }
        )

    manifest = {
        "schema": SHARD_MANIFEST_SCHEMA,
        "profile": PROFILE,
        "case_count": len(ordered),
        "presentation_ticks": 16,
        "shard_size": shard_size,
        "shard_count": len(shard_records),
        "provenance": provenance,
        "indices_sha256": hashlib.sha256(
            json.dumps(list(ordered), separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "shards": shard_records,
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def read_matched_request_bundle(path: str | Path) -> tuple[MatchedImageInput, ...]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("unsupported matched request-bundle schema")
    if payload.get("profile") != PROFILE:
        raise ValueError("matched bundle must use native-sparse profile")
    cases = payload.get("cases")
    if not isinstance(cases, list) or int(payload.get("case_count", -1)) != len(cases):
        raise ValueError("matched request-bundle case count is inconsistent")

    result: list[MatchedImageInput] = []
    seen: set[int] = set()
    for row in cases:
        index = int(row["mnist_test_index"])
        if index in seen:
            raise ValueError("matched request bundle contains duplicate index")
        seen.add(index)
        schedule = tuple(tuple(int(axon) for axon in tick) for tick in row["external_schedule"])
        if len(schedule) != 16:
            raise ValueError("matched request bundle case must contain exactly 16 ticks")
        if int(row["total_input_events"]) != sum(len(tick) for tick in schedule):
            raise ValueError("matched request bundle total_input_events is inconsistent")
        result.append(
            MatchedImageInput(
                mnist_test_index=index,
                label=int(row["label"]),
                schedule=schedule,
                golden_prediction=int(row["golden_prediction"]),
                golden_spike_counts=tuple(int(value) for value in row["golden_spike_counts"]),
            )
        )
    return tuple(result)


def iter_matched_request_shards(
    manifest_path: str | Path,
) -> Iterator[tuple[MatchedImageInput, ...]]:
    """Yield one verified request shard at a time in frozen manifest order."""

    source = Path(manifest_path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("schema") != SHARD_MANIFEST_SCHEMA:
        raise ValueError("unsupported matched shard-manifest schema")
    if payload.get("profile") != PROFILE:
        raise ValueError("matched shard manifest must use native-sparse profile")
    shards = payload.get("shards")
    if not isinstance(shards, list) or int(payload.get("shard_count", -1)) != len(shards):
        raise ValueError("matched shard-manifest shard count is inconsistent")

    seen: set[int] = set()
    yielded = 0
    for shard in shards:
        path = source.parent / str(shard["path"])
        if _sha256(path) != str(shard["sha256"]):
            raise ValueError(f"matched request shard hash mismatch: {path}")
        cases = read_matched_request_bundle(path)
        if len(cases) != int(shard["case_count"]):
            raise ValueError(f"matched request shard case count mismatch: {path}")
        for case in cases:
            if case.mnist_test_index in seen:
                raise ValueError("matched shard manifest repeats an MNIST index")
            seen.add(case.mnist_test_index)
        yielded += len(cases)
        yield cases

    if yielded != int(payload.get("case_count", -1)):
        raise ValueError("matched shard-manifest total case count is inconsistent")
