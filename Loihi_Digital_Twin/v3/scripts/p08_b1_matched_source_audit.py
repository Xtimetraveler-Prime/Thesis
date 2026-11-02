#!/usr/bin/env python3
"""P08-B1 read-only gate: exact P08-A first1024 raw TRAIN pixels against B2.4.

Requires original canonical TRAIN-only IDX, accepted A stage and original B2.4
33-asset freeze. This NEVER builds a B input stream or contacts KV260.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

from loihi_twin_v2.p06_a3_data import load_train_validation
from loihi_twin_v2.p07_a3_validation import TRAIN_INDICES_SHA, VAL_INDICES_SHA
from loihi_twin_v2.p07_a4_validation import (
    select_validation_prefix, validate_ledger, indices_le32_sha256,
)
from loihi_twin_v2.p07_a4_stream import parse_stream

COUNT = 1024
TRACE_FRAME = 1023
PREFIX_INDICES_SHA = "8414a9f0f6f2e0f61ccd87ce2f43b972a8d0d8342702d3f2e8ac9351574d2aab"
B24_COMPILED_SHA = "02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a"
STAGE_FILES = {
    "descriptor": "p07_a4_descriptor_256.bin",
    "mapping": "p07_a4_mapping_1568.bin",
    "pixels": "p07_a4_pixels_raw.bin",
    "zero_journal_1m": "p07_a4_journal_initial_1m.bin",
}
STAGE_MANIFEST = "p07_a4_2a_stage_manifest.json"
STAGE_LEDGER = "p07_a4_2a_validation_labels_HOST_ONLY.json"


class P08B1Error(ValueError):
    """Strict source/provenance/ordering/physical-scope rejection."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_sha256(document: dict) -> str:
    return sha256(json.dumps(document, sort_keys=True, separators=(",", ":")).encode())


def indices_digest(indices) -> str:
    return sha256(b"".join(struct.pack("<I", i) for i in indices))


def check_membership_indices(train_indices, validation_indices) -> dict:
    """Reconstruct pinned A/B shared split, reject any B train leakage."""
    train, validation = tuple(train_indices), tuple(validation_indices)
    if (len(train) != 50000 or len(validation) != 10000
            or any(type(i) is not int or i < 0 or i >= 60000 for i in train + validation)
            or len(set(train)) != len(train) or len(set(validation)) != len(validation)
            or indices_digest(train) != TRAIN_INDICES_SHA
            or indices_digest(validation) != VAL_INDICES_SHA):
        raise P08B1Error("not the original pinned A/B 50k/10k source-index split")
    prefix = validation[:COUNT]
    if (indices_le32_sha256(prefix) != PREFIX_INDICES_SHA
            or prefix[:3] != (37384, 27347, 20178)
            or prefix[-1] != 42925):
        raise P08B1Error("first1024 image-ID order changed from accepted Track A")
    overlap = set(prefix).intersection(train)
    if overlap:
        raise P08B1Error("Track B training-index leakage into first1024 benchmark")
    return {
        "train_indices_le32_sha256": TRAIN_INDICES_SHA,
        "validation_indices_le32_sha256": VAL_INDICES_SHA,
        "selected_indices_le32_sha256": PREFIX_INDICES_SHA,
        "overlap_with_B_training_indices": 0,
        "first_three_source_indices": list(prefix[:3]),
        "last_source_index": prefix[-1],
    }


def read_regular(root: Path, filename: str) -> bytes:
    path = root / filename
    if path.is_symlink() or not path.is_file():
        raise P08B1Error(f"missing/symlinked source file: {filename}")
    return path.read_bytes()


def validate_a_stage(stage: Path, source_manifest: dict, frames) -> dict:
    """Independent exact 1024 frame ID/label/raw pixel/descriptor digest gate."""
    manifest = json.loads(read_regular(stage, STAGE_MANIFEST))
    ledger = json.loads(read_regular(stage, STAGE_LEDGER))
    if (manifest.get("schema") != "p07-a4-2a-persistent-ddr-stage-v1"
            or manifest.get("scope") != "TRAIN_DERIVED_VALIDATION_FIRST_1024"
            or manifest.get("frame_count") != COUNT
            or manifest.get("trace_index") != TRACE_FRAME
            or manifest.get("image_stride_bytes") != 784
            or manifest.get("official_mnist_test") != "SEALED"
            or manifest.get("physical_hardware") != "NOT_RUN"):
        raise P08B1Error("P08-A canonical original-first1024 stage manifest mismatch")
    files = {key: read_regular(stage, filename) for key, filename in STAGE_FILES.items()}
    if (not isinstance(manifest.get("sha256"), dict)
            or any(manifest["sha256"].get(key) != sha256(data)
                   for key, data in files.items())):
        raise P08B1Error("P08-A stage file SHA256 mismatch")
    if (len(files["pixels"]) != COUNT * 784
            or len(files["descriptor"]) != 256
            or len(files["mapping"]) != 1568
            or len(files["zero_journal_1m"]) != 1024 * 1024):
        raise P08B1Error("P08-A 1024 stage buffer geometry mismatch")
    stream = parse_stream(files["descriptor"], files["mapping"], files["pixels"])
    if stream.image_count != COUNT or stream.trace_index != TRACE_FRAME:
        raise P08B1Error("P08-A descriptor has wrong image/selected-trace index")
    validate_ledger(ledger, frames, files["pixels"])
    if (ledger.get("source_dataset_sha256") != canonical_json_sha256(source_manifest)
            or ledger.get("selected_indices_le32_sha256") != PREFIX_INDICES_SHA):
        raise P08B1Error("P08-A source dataset/split ledger identity drift")
    return {
        "original_A_stage_sha256": {key: sha256(data) for key, data in files.items()},
        "original_A_manifest_sha256": sha256(read_regular(stage, STAGE_MANIFEST)),
        "original_A_ledger_sha256": sha256(read_regular(stage, STAGE_LEDGER)),
        "selected_trace_frame": TRACE_FRAME,
        "ordinary_frame_count": COUNT - 1,
    }


def check_b_candidate(candidate: dict, source_manifest: dict) -> None:
    if (candidate.get("schema") != "p06-b2.2-canonical-train-validation-candidate-v1"
            or candidate.get("architecture") != [784, 1000, 10]
            or candidate.get("source_dataset") != source_manifest
            or candidate.get("official_mnist_test_status") != "SEALED_NOT_ACCESSED"
            or candidate.get("official_mnist_test_images_evaluated") != 0
            or candidate.get("candidate_go") is not True):
        raise P08B1Error("frozen Track B checkpoint has different TRAIN source/split or scope")


def generate_report(stage_dir: Path, train_data_dir: Path, frozen_dir: Path) -> dict:
    from loihi_twin_v2.p06_b24_freeze import verify_frozen_directory

    if not stage_dir.is_dir() or not frozen_dir.is_dir():
        raise P08B1Error("actual accepted stage and frozen checkpoint directories required")
    # Strict=True independently authenticates both canonical TRAIN IDX gzip
    # checksums and re-creates the exact original 50k/10k seeded partition.
    split = load_train_validation(train_data_dir, strict=True)
    membership = check_membership_indices(split.train_indices, split.validation_indices)
    frames = select_validation_prefix(split, COUNT)
    stage = validate_a_stage(stage_dir, split.manifest, frames)
    # All 33 original B2.4 assets are checked read-only, not just a copied
    # source-manifest claim. Original freeze has historical status fields.
    frozen = verify_frozen_directory(frozen_dir, deep=False)
    candidate = json.loads(read_regular(frozen_dir / "checkpoint", "candidate_manifest.json"))
    check_b_candidate(candidate, split.manifest)
    return {
        "schema": "p08-b1-canonical-matched-a-stage-b24-train-audit-v1",
        "scope": "READ_ONLY_PC_DATASET_AND_FROZEN_SOURCE_ADMISSION",
        "original_track_A_frame_count": COUNT,
        "original_frame_order_preserved": True,
        "membership": membership,
        "source_dataset_sha256": canonical_json_sha256(split.manifest),
        "source_archives": split.manifest["archives"],
        "track_A_stage": stage,
        "B24_original_frozen_manifest_sha256": frozen["manifest_sha256"],
        "B24_original_33_assets_verified": frozen["files_checked"] == 33,
        "B24_compiled_model_sha256": B24_COMPILED_SHA,
        "B24_candidate_checkpoint_sha256": candidate["weights_file_sha256"],
        "frames": [
            {"frame": i, "TRAIN_source_index": f.source_index,
             "label": f.label, "raw_pixels_sha256": sha256(f.pixels),
             "in_B_training_partition": False, "selected_trace": i == TRACE_FRAME}
            for i, f in enumerate(frames)
        ],
        "B_own_ingress_encoded": False,
        "B_independent_1024_scalar_oracle_completed": False,
        "B_KV260_physical_run_completed": False,
        "original_MNIST_TEST": "SEALED_NOT_ACCESSED",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage-dir", type=Path, required=True)
    p.add_argument("--train-data-dir", type=Path, required=True)
    p.add_argument("--frozen-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True, help="fresh absolute JSON path OUTSIDE checkout")
    a = p.parse_args()
    try:
        root = Path(__file__).resolve().parents[3]  # Thesis repository
        out = a.out
        if (not out.is_absolute() or out.exists() or out.is_symlink()
                or not out.parent.is_dir()
                or out.resolve().is_relative_to(root)):
            raise P08B1Error("must use a NEW absolute output JSON path outside Git checkout")
        report = generate_report(a.stage_dir, a.train_data_dir, a.frozen_dir)
        # No writing of source, original stage or accepted freeze.
        with out.open("x", encoding="utf-8") as f:
            json.dump(report, f, sort_keys=True, indent=2)
            f.write("\n")
        print("P08_B1_MATCHED_DATASET_OFFLINE_PASS=1")
        print("P08_B1_B_TRAIN_MEMBERSHIP_OVERLAP=0")
        print("P08_B1_1024_RAW_PIXEL_IDENTITIES=PASS")
        print("P08_B1_PHYSICAL_KV260_RUN=NOT_RUN")
        print("P08_B1_REPORT=" + str(out))
    except (P08B1Error, ValueError, TypeError, KeyError, OSError) as exc:
        print("P08_B1_NO_GO=" + str(exc), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
