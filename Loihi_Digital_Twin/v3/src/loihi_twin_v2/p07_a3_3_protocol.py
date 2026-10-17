"""P07-A3.3 precommitted canonical validation-128 hardware/restart protocol.

No official t10k TEST, no model changes, no board results. Eight batches of
16 UNIQUE frozen TRAIN-derived validation frames, then one repeat of batch
zero and of batch seven in independent, freshly provisioned A53 launches.
The 128 distinct primary frames alone define the diagnostic accuracy
denominator. Repeats are *numerical reproducibility* checks, never scored as
additional independent images.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import struct

from .p07_a1_ingress import decode_ingress, encode_ingress
from .p07_a2_batch import (
    COMPILED_FINGERPRINT, DDR_SHA256, RESULT_BYTES, create_batch, parse_batch,
)
from .p07_a3_validation import (
    SOURCE_COUNT, TRAIN_COUNT, VALIDATION_COUNT, TRAIN_INDICES_SHA,
    VAL_INDICES_SHA, ValidationFrame, indices_sha,
)

SCHEMA = "p07-a3-3-validation128-restart-v1"
BATCH_SCHEMA = "p07-a3-3-validation16-batch-v1"
LABEL_SCHEMA = "p07-a3-3-validation16-labels-v1"
SAMPLE_COUNT = 128
BATCH_SIZE = 16
PRIMARY_BATCH_COUNT = 8
TRACE_FRAME = 0
SELECTION_RULE = "canonical TRAIN-derived 10k validation permutation, first 128 source indices"
REPEAT_BATCHES = (0, 7)
RUN_IDS = tuple(f"batch_{i:02d}_primary" for i in range(PRIMARY_BATCH_COUNT)) + (
    "batch_00_repeat", "batch_07_repeat",
)
XSA_SHA = "52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(data: dict) -> bytes:
    return (json.dumps(data, sort_keys=True, indent=2) + "\n").encode("utf-8")


def split_manifest_sha(manifest: dict) -> str:
    return sha((json.dumps(manifest, sort_keys=True, separators=(",", ":"))+"\n").encode())


def select_frames(split) -> tuple[ValidationFrame, ...]:
    """Selection rule is frozen before opening any P07-A3.3 output."""
    m = split.manifest
    if (m.get("schema") != "p06-a3-mnist-train50000-val10000-seeded-v1" or
            m.get("split_seed") != 20261013 or
            m.get("official_test_set") != "sealed: no t10k archives opened" or
            m.get("train_indices_le32_sha256") != TRAIN_INDICES_SHA or
            m.get("validation_indices_le32_sha256") != VAL_INDICES_SHA or
            split.count != SOURCE_COUNT or len(split.images) != SOURCE_COUNT*784 or
            len(split.labels) != SOURCE_COUNT or
            len(split.train_indices) != TRAIN_COUNT or
            len(split.validation_indices) != VALIDATION_COUNT or
            indices_sha(split.train_indices) != TRAIN_INDICES_SHA or
            indices_sha(split.validation_indices) != VAL_INDICES_SHA):
        raise ValueError("P07-A3.3 requires exact frozen canonical TRAIN-only validation split")
    ids = split.validation_indices[:SAMPLE_COUNT]
    if len(ids) != SAMPLE_COUNT or len(set(ids)) != SAMPLE_COUNT or (
        any(type(i) is not int or not 0 <= i < SOURCE_COUNT for i in ids)):
        raise ValueError("P07-A3.3 invalid first 128 source indices")
    return tuple(ValidationFrame(i, split.images[i*784:(i+1)*784],
                                 split.labels[i]) for i in ids)


@dataclass(frozen=True)
class PreparedBatch:
    header: bytes
    payload: bytes
    manifest: dict
    labels: dict


def prepare_protocol(frames: tuple[ValidationFrame, ...],
                     mapping: tuple[int, ...],
                     split_manifest: dict) -> tuple[dict, tuple[PreparedBatch, ...]]:
    """Build all 8 immutable batches entirely before writing any files."""
    if len(frames) != SAMPLE_COUNT:
        raise ValueError("P07-A3.3 requires exactly 128 prespecified validation frames")
    indices = tuple(f.source_index for f in frames)
    if (len(set(indices)) != SAMPLE_COUNT or
            any(type(i) is not int or not 0 <= i < SOURCE_COUNT for i in indices) or
            any(type(f.label) is not int or not 0 <= f.label <= 9 or
                not isinstance(f.pixels, bytes) or len(f.pixels) != 784 for f in frames)):
        raise ValueError("P07-A3.3 invalid/duplicate frame IDs, images or labels")
    if (not isinstance(mapping, tuple) or len(mapping) != 784):
        raise ValueError("P07-A3.3 requires the frozen 784-axon mapped interface")

    result = []
    split_sha = split_manifest_sha(split_manifest)
    for b in range(PRIMARY_BATCH_COUNT):
        offset = b * BATCH_SIZE
        selected = frames[offset:offset+BATCH_SIZE]
        raw = tuple(encode_ingress(f.pixels, mapping, ddr_sha256=DDR_SHA256,
                                   deployment_fingerprint=COMPILED_FINGERPRINT)
                    for f in selected)
        header, payload = create_batch(raw, trace_frame=TRACE_FRAME)
        assert parse_batch(header, payload) == raw
        batch_name = f"batch_{b:02d}"
        manifest = {
            "schema": BATCH_SCHEMA, "scope": "validation diagnostic / physical NOT RUN",
            "frame_count": BATCH_SIZE, "trace_frame": TRACE_FRAME,
            "batch_index": b, "batch_name": batch_name,
            "selection_rule": SELECTION_RULE,
            "selected_source_indices": [f.source_index for f in selected],
            "source_split_manifest_sha256": split_sha,
            "ddr_sha256": DDR_SHA256,
            "compiled_fingerprint": COMPILED_FINGERPRINT,
            "sha256": {
                "header": sha(header), "payload": sha(payload),
                "records": [sha(r) for r in raw],
                "mailbox_initial": sha(bytes(RESULT_BYTES)),
            },
            "official_mnist_test": "SEALED",
        }
        # Label rows are host-only, never included in any A53-staged file.
        labels = {
            "schema": LABEL_SCHEMA, "batch_index": b,
            "header_sha256": sha(header), "payload_sha256": sha(payload),
            "rows": [
                {"frame": n, "source_index": f.source_index, "label": f.label,
                 "pixels_sha256": sha(f.pixels), "ingress_sha256": sha(raw[n])}
                for n, f in enumerate(selected)
            ],
            "official_mnist_test": "SEALED",
        }
        result.append(PreparedBatch(header, payload, manifest, labels))

    runs = [
        {"order": i, "run_id": f"batch_{i:02d}_primary",
         "batch_name": f"batch_{i:02d}", "role": "primary"}
        for i in range(PRIMARY_BATCH_COUNT)
    ] + [
        {"order": PRIMARY_BATCH_COUNT+i,
         "run_id": f"batch_{b:02d}_repeat", "batch_name": f"batch_{b:02d}",
         "role": "repeat", "byte_identical_to": f"batch_{b:02d}_primary"}
        for i, b in enumerate(REPEAT_BATCHES)
    ]
    plan = {
        "schema": SCHEMA,
        "scope": "P07-A3.3 frozen diagnostic: no official TEST, no training",
        "selection_rule": SELECTION_RULE,
        "source_split_manifest_sha256": split_sha,
        "selected_source_indices": list(indices),
        "selected_indices_le32_sha256": sha(b"".join(struct.pack("<I", i) for i in indices)),
        "primary_unique_frames": SAMPLE_COUNT, "batch_size": BATCH_SIZE,
        "primary_batches": PRIMARY_BATCH_COUNT, "repeat_batches": list(REPEAT_BATCHES),
        "physical_launches": len(runs), "hardware_frame_executions": len(runs)*BATCH_SIZE,
        "scored_frame_denominator": SAMPLE_COUNT,
        "xsa_sha256": XSA_SHA, "ddr_sha256": DDR_SHA256,
        "compiled_fingerprint": COMPILED_FINGERPRINT,
        "acceptance": "all 10 cold-start batches terminal success; exact P03 oracle; two repeats byte-identical to primary; score all 128 unique frames regardless of accuracy",
        "batches": [
            {"name": f"batch_{i:02d}",
             "header_sha256": v.manifest["sha256"]["header"],
             "payload_sha256": v.manifest["sha256"]["payload"],
             "label_ledger_sha256": sha(json_bytes(v.labels))}
            for i, v in enumerate(result)
        ],
        "runs": runs, "official_mnist_test": "SEALED",
    }
    assert [r["run_id"] for r in runs] == list(RUN_IDS)
    return plan, tuple(result)


def write_protocol(directory: Path, plan: dict, batches: tuple[PreparedBatch, ...]) -> None:
    if directory.exists():
        raise FileExistsError("P07-A3.3 protocol destination exists: no overwrite")
    if plan.get("schema") != SCHEMA or len(batches) != PRIMARY_BATCH_COUNT:
        raise ValueError("P07-A3.3 invalid precomputed protocol")
    directory.mkdir(parents=True, exist_ok=False)
    for n, batch in enumerate(batches):
        folder = directory / f"batch_{n:02d}"
        folder.mkdir()
        (folder / "p07_a2_header_64.bin").write_bytes(batch.header)
        (folder / "p07_a2_ingress_payload.bin").write_bytes(batch.payload)
        (folder / "p07_a2_mailbox_zero_64k.bin").write_bytes(bytes(RESULT_BYTES))
        (folder / "p07_a2_manifest.json").write_bytes(json_bytes(batch.manifest))
        (folder / "p07_a3_3_labels.json").write_bytes(json_bytes(batch.labels))
    (directory / "p07_a3_3_protocol.json").write_bytes(json_bytes(plan))


def verify_protocol(directory: Path, split, mapping: tuple[int, ...]) -> tuple[dict, tuple[PreparedBatch, ...]]:
    """Rebuild expected bytes from original TRAIN IDX and compare every file."""
    frames = select_frames(split)
    expected_plan, expected_batches = prepare_protocol(frames, mapping, split.manifest)
    actual_plan = (directory / "p07_a3_3_protocol.json").read_bytes()
    if actual_plan != json_bytes(expected_plan):
        raise ValueError("P07-A3.3 precommitted source IDs, batch hashes or protocol changed")
    for index, b in enumerate(expected_batches):
        folder = directory / f"batch_{index:02d}"
        expected = {
            "p07_a2_header_64.bin": b.header,
            "p07_a2_ingress_payload.bin": b.payload,
            "p07_a2_mailbox_zero_64k.bin": bytes(RESULT_BYTES),
            "p07_a2_manifest.json": json_bytes(b.manifest),
            "p07_a3_3_labels.json": json_bytes(b.labels),
        }
        for name, expected_data in expected.items():
            if (folder / name).read_bytes() != expected_data:
                raise ValueError(f"P07-A3.3 mismatch in immutable batch_{index:02d}/{name}")
    return expected_plan, expected_batches


def validate_evidence_log(run_dir: Path, batch_dir: Path, b: PreparedBatch) -> None:
    """Require real accepted JTAG run-log markers and exact staged input hashes."""
    identity = (run_dir / "physical_identity.txt").read_text(encoding="utf-8")
    logs = {
        name: (run_dir / name).read_text(encoding="utf-8")
        for name in ("a53_run.log", "verify.log", "program.log", "ps_width.log", "provision.log")
    }
    required = {
        "a53_run.log": "P07_A2_KV260_STATUS=TERMINAL_SUCCESS_UNVERIFIED_NUMERICS",
        "verify.log": "P07_A2_PHYSICAL_TRACES_EXACT=1",
        "program.log": "PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released",
        "ps_width.log": "P03_2C_PS_FPD_HPM0_WIDTH_BITS=128",
        "provision.log": "P07_A2_XSDB_PROVISION_PASS=1",
    }
    for filename, marker in required.items():
        if marker not in logs[filename]:
            raise ValueError(f"P07-A3.3 missing physical confirmation in {filename}: {marker}")
    if "status=BOARD_NOT_YET_RUN" not in identity:
        raise ValueError("P07-A3.3 missing original pre-execution physical identity record")
    ledger = {}
    for line in identity.splitlines():
        parts = line.split()
        if len(parts) == 2 and SHA_RE.fullmatch(parts[0]):
            ledger[Path(parts[1]).resolve()] = parts[0]
    for filename, expected_sha in (
        ("p07_a2_header_64.bin", b.manifest["sha256"]["header"]),
        ("p07_a2_ingress_payload.bin", b.manifest["sha256"]["payload"]),
    ):
        path = (batch_dir / filename).resolve()
        if ledger.get(path) != expected_sha:
            raise ValueError(f"P07-A3.3 physical-run provenance wrong for {path}")
    if XSA_SHA not in ledger.values() or DDR_SHA256 not in ledger.values():
        raise ValueError("P07-A3.3 physical run did not pin accepted XSA/master")
