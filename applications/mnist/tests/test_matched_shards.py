from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from mnist_app.matched_bundle import (
    BUNDLE_SCHEMA,
    SHARD_MANIFEST_SCHEMA,
    iter_matched_request_shards,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _case(index: int) -> dict[str, object]:
    return {
        "mnist_test_index": index,
        "label": index % 10,
        "external_schedule": [[] for _ in range(16)],
        "total_input_events": 0,
        "golden_prediction": index % 10,
        "golden_spike_counts": [0] * 10,
    }


def _write_shard(path: Path, indices: tuple[int, ...]) -> None:
    payload = {
        "schema": BUNDLE_SCHEMA,
        "profile": "native-sparse",
        "case_count": len(indices),
        "presentation_ticks": 16,
        "provenance": {"test": True},
        "cases": [_case(index) for index in indices],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_iter_matched_request_shards_preserves_manifest_order(tmp_path: Path) -> None:
    first = tmp_path / "shard-00000.json"
    second = tmp_path / "shard-00001.json"
    _write_shard(first, (3, 1))
    _write_shard(second, (7, 9))
    manifest = {
        "schema": SHARD_MANIFEST_SCHEMA,
        "profile": "native-sparse",
        "case_count": 4,
        "presentation_ticks": 16,
        "shard_size": 2,
        "shard_count": 2,
        "provenance": {"test": True},
        "indices_sha256": "unused-by-reader",
        "shards": [
            {"path": first.name, "case_count": 2, "sha256": _sha256(first)},
            {"path": second.name, "case_count": 2, "sha256": _sha256(second)},
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")

    shards = list(iter_matched_request_shards(manifest_path))
    assert [[case.mnist_test_index for case in shard] for shard in shards] == [[3, 1], [7, 9]]


def test_iter_matched_request_shards_rejects_tampering(tmp_path: Path) -> None:
    shard = tmp_path / "shard-00000.json"
    _write_shard(shard, (3,))
    original_hash = _sha256(shard)
    manifest = {
        "schema": SHARD_MANIFEST_SCHEMA,
        "profile": "native-sparse",
        "case_count": 1,
        "presentation_ticks": 16,
        "shard_size": 1,
        "shard_count": 1,
        "provenance": {"test": True},
        "indices_sha256": "unused-by-reader",
        "shards": [{"path": shard.name, "case_count": 1, "sha256": original_hash}],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    shard.write_text(shard.read_text(encoding="utf-8") + " ", encoding="utf-8")

    with pytest.raises(ValueError, match="hash mismatch"):
        list(iter_matched_request_shards(manifest_path))
