"""Backend-neutral request bundles for matched MNIST reference experiments."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable, Sequence

from .brian2loihi_matched import MatchedImageInput
from .matched_reference import PROFILE, frozen_corpus_indices
from .runtime import build_runtime_request


BUNDLE_SCHEMA = "neuromorphic-twin-mnist-matched-request-bundle-v1"


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


def build_matched_request_bundle(
    frozen_root: str | Path,
    indices: Sequence[int],
) -> dict[str, object]:
    root = Path(frozen_root)
    deployment = root / "deployments" / PROFILE / "deployment.json"
    storage = root / "deployments" / PROFILE / "weight_image" / "weight_storage.json"
    freeze_manifest = root / "freeze_manifest.json"
    unique = tuple(int(index) for index in indices)
    if not unique or len(set(unique)) != len(unique):
        raise ValueError("matched bundle requires one or more unique MNIST test indices")

    cases: list[dict[str, object]] = []
    for index in unique:
        request = build_runtime_request(root, profile=PROFILE, mnist_test_index=index)
        cases.append(
            {
                "mnist_test_index": request.mnist_test_index,
                "label": request.label,
                "external_schedule": [list(row) for row in request.external_schedule],
                "total_input_events": request.total_events,
                "golden_prediction": request.golden_prediction,
                "golden_spike_counts": list(request.golden_spike_counts),
            }
        )

    return {
        "schema": BUNDLE_SCHEMA,
        "profile": PROFILE,
        "case_count": len(cases),
        "presentation_ticks": 16,
        "provenance": {
            "freeze_manifest_sha256": _sha256(freeze_manifest),
            "deployment_sha256": _sha256(deployment),
            "weight_storage_sha256": _sha256(storage),
            "source": "frozen mnist-v1 native-sparse deployment and deterministic encoder",
        },
        "cases": cases,
    }


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
