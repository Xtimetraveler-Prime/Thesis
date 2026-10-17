"""P07-A3.1 fixed, validation-only 16-image KV260 diagnostic corpus.

The canonical TRAIN-derived validation slice is preselected independently of
predictions. The official t10k MNIST test archives are NEVER opened. Scoring
is strictly downstream of accepted physical P07-A2 oracle equivalence.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct

from .p07_a1_ingress import encode_ingress
from .p07_a2_batch import (
    COMPILED_FINGERPRINT, DDR_SHA256, RESULT_BYTES, create_batch, parse_batch,
)

FRAME_COUNT = 16
TRACE_FRAME = 0
SELECTION_RULE = "canonical TRAIN-derived held-out validation order: first 16 indices"
SCHEMA = "p07-a3-validation16-probe-v1"
TRAIN_COUNT = 50000
VALIDATION_COUNT = 10000
SOURCE_COUNT = 60000
# Independently pinned at accepted P06-A4 freeze.
TRAIN_INDICES_SHA = "1cbcb0b2bf481958d6c917ea6d70fa44a20839406f0c824540f8e691edfdd851"
VAL_INDICES_SHA = "3b9520013f30742c3818f55024ea39e3e0632113c487c589fdfbb73c7d274831"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def indices_sha(indices: tuple[int, ...]) -> str:
    return sha(b"".join(struct.pack("<I", i) for i in indices))


def select_validation_sources(train_indices: tuple[int, ...],
                              validation_indices: tuple[int, ...]) -> tuple[int, ...]:
    """Choose only the first 16 of the PINNED validation partition; no labels.

    Recompute the index hashes instead of trusting the caller's manifest.
    Never sort by class, model prediction, difficulty or observed accuracy.
    """
    if len(train_indices) != TRAIN_COUNT or len(validation_indices) != VALIDATION_COUNT:
        raise ValueError("P07-A3 requires accepted 50k train / 10k validation split")
    if (indices_sha(train_indices) != TRAIN_INDICES_SHA or
            indices_sha(validation_indices) != VAL_INDICES_SHA):
        raise ValueError("P07-A3 frozen validation partition changed")
    selected = validation_indices[:FRAME_COUNT]
    if len(set(selected)) != FRAME_COUNT or any(not 0 <= i < SOURCE_COUNT for i in selected):
        raise ValueError("P07-A3 selected invalid or duplicate image IDs")
    return selected


@dataclass(frozen=True)
class ValidationFrame:
    source_index: int
    pixels: bytes
    label: int


def extract_validation_frames(split) -> tuple[ValidationFrame, ...]:
    """Fail closed on noncanonical data/split and select without label peeking."""
    manifest = split.manifest
    if (manifest.get("schema") != "p06-a3-mnist-train50000-val10000-seeded-v1" or
            manifest.get("split_seed") != 20261013 or
            manifest.get("official_test_set") != "sealed: no t10k archives opened" or
            manifest.get("train_indices_le32_sha256") != TRAIN_INDICES_SHA or
            manifest.get("validation_indices_le32_sha256") != VAL_INDICES_SHA or
            split.count != SOURCE_COUNT or len(split.images) != SOURCE_COUNT*784 or
            len(split.labels) != SOURCE_COUNT):
        raise ValueError("P07-A3 requires exact accepted canonical train-only data provenance")
    indices = select_validation_sources(split.train_indices, split.validation_indices)
    return tuple(
        ValidationFrame(source_index=i, pixels=split.images[i*784:(i+1)*784],
                        label=split.labels[i]) for i in indices
    )


def make_validation_bundle(frames: tuple[ValidationFrame, ...],
                           pixel_to_axon: tuple[int, ...],
                           *, split_manifest: dict) -> tuple[bytes, bytes, dict, dict]:
    """Serialize accepted A1/A2 wire bytes; labels never enter the A53 payload."""
    if len(frames) != FRAME_COUNT:
        raise ValueError("P07-A3 requires exactly 16 fixed validation frames")
    ids = tuple(f.source_index for f in frames)
    if len(set(ids)) != FRAME_COUNT or any(type(i) is not int or not 0 <= i < SOURCE_COUNT for i in ids):
        raise ValueError("duplicate or invalid validation source IDs")
    if any(type(f.label) is not int or not 0 <= f.label <= 9 or
           not isinstance(f.pixels, bytes) or len(f.pixels) != 784 for f in frames):
        raise ValueError("invalid validation frame pixels or label")
    raw = tuple(encode_ingress(f.pixels, pixel_to_axon,
                              ddr_sha256=DDR_SHA256,
                              deployment_fingerprint=COMPILED_FINGERPRINT)
                for f in frames)
    header, payload = create_batch(raw, trace_frame=TRACE_FRAME)
    assert parse_batch(header, payload) == raw
    main = {
        "schema": SCHEMA, "scope": "frozen validation diagnostic / KV260 NOT RUN",
        "frame_count": FRAME_COUNT, "trace_frame": TRACE_FRAME,
        "selection_rule": SELECTION_RULE, "selected_source_indices": list(ids),
        "source_split_manifest_sha256": sha(
            (json.dumps(split_manifest, sort_keys=True, separators=(",",":"))+"\n").encode()),
        "ddr_sha256": DDR_SHA256, "compiled_fingerprint": COMPILED_FINGERPRINT,
        "sha256": {
            "header": sha(header), "payload": sha(payload),
            "mailbox_initial": sha(bytes(RESULT_BYTES)),
            "records": [sha(r) for r in raw],
        },
        "official_mnist_test": "SEALED",
    }
    # Keep labels in a separate ledger. Both must be checked against a fresh
    # canonical TRAIN-only reload during scoring, never just self-reported.
    ledger = {
        "schema": SCHEMA, "selection_rule": SELECTION_RULE,
        "batch_header_sha256": sha(header), "batch_payload_sha256": sha(payload),
        "rows": [
            {"frame": n, "source_index": f.source_index, "label": f.label,
             "pixels_sha256": sha(f.pixels), "ingress_sha256": sha(raw[n])}
            for n, f in enumerate(frames)
        ],
        "official_mnist_test": "SEALED",
    }
    return header, payload, main, ledger


def write_validation_bundle(output_dir: Path, header: bytes, payload: bytes,
                            manifest: dict, ledger: dict) -> None:
    """Never clobber an older batch or a local physical evidence record."""
    if output_dir.exists():
        raise FileExistsError("P07-A3 refuses to overwrite validation bundle")
    records = parse_batch(header, payload)
    if len(records) != FRAME_COUNT or manifest["sha256"]["header"] != sha(header) or (
        manifest["sha256"]["payload"] != sha(payload)):
        raise ValueError("P07-A3 failed batch digest preflight")
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "p07_a2_header_64.bin").write_bytes(header)
    (output_dir / "p07_a2_ingress_payload.bin").write_bytes(payload)
    (output_dir / "p07_a2_mailbox_zero_64k.bin").write_bytes(bytes(RESULT_BYTES))
    (output_dir / "p07_a2_manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    (output_dir / "p07_a3_validation_labels.json").write_text(
        json.dumps(ledger, sort_keys=True, indent=2)+"\n", encoding="utf-8")


def verify_validation_provenance(output_dir: Path, split):
    """Independently tie predictions and labels to canonical train IDX bytes."""
    header = (output_dir / "p07_a2_header_64.bin").read_bytes()
    payload = (output_dir / "p07_a2_ingress_payload.bin").read_bytes()
    main = json.loads((output_dir / "p07_a2_manifest.json").read_text())
    ledger = json.loads((output_dir / "p07_a3_validation_labels.json").read_text())
    raw = parse_batch(header, payload)
    expected = extract_validation_frames(split)
    if (main.get("schema") != SCHEMA or ledger.get("schema") != SCHEMA or
            main.get("frame_count") != FRAME_COUNT or main.get("trace_frame") != TRACE_FRAME or
            main.get("selection_rule") != SELECTION_RULE or
            main.get("selected_source_indices") != [f.source_index for f in expected] or
            main.get("ddr_sha256") != DDR_SHA256 or
            main.get("compiled_fingerprint") != COMPILED_FINGERPRINT or
            main.get("official_mnist_test") != "SEALED" or
            ledger.get("official_mnist_test") != "SEALED" or
            ledger.get("selection_rule") != SELECTION_RULE or
            ledger.get("batch_header_sha256") != sha(header) or
            ledger.get("batch_payload_sha256") != sha(payload) or
            main.get("sha256", {}).get("header") != sha(header) or
            main.get("sha256", {}).get("payload") != sha(payload) or
            main.get("sha256", {}).get("records") != [sha(r) for r in raw]):
        raise ValueError("P07-A3 validation manifest/provenance mismatch")
    expected_manifest_sha = sha(
        (json.dumps(split.manifest, sort_keys=True, separators=(",",":"))+"\n").encode())
    if main["source_split_manifest_sha256"] != expected_manifest_sha:
        raise ValueError("P07-A3 canonical training split SHA256 differs")
    if len(ledger.get("rows", [])) != FRAME_COUNT:
        raise ValueError("P07-A3 missing validation label rows")
    from .p07_a1_ingress import decode_ingress
    for n, (record, frame, row) in enumerate(zip(raw, expected, ledger["rows"])):
        pixels = decode_ingress(record).pixels
        if (row != {"frame": n, "source_index": frame.source_index, "label": frame.label,
                    "pixels_sha256": sha(frame.pixels), "ingress_sha256": sha(record)}
                or pixels != frame.pixels):
            raise ValueError(f"P07-A3 validation label/image mismatch at frame={n}")
    return header, payload, ledger
