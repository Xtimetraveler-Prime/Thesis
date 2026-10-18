"""P07-A4.2c frozen, original-order TRAIN-derived validation1024 selection.

Uses only the 10k held-out validation partition of the canonical 60k
TRAIN corpus. The official independent MNIST t10k TEST is NEVER opened.
1024 indices and trace frame 1023 are precommitted before physical run.
"""
from __future__ import annotations

import struct

from .p07_a3_validation import (
    SOURCE_COUNT, TRAIN_COUNT, VALIDATION_COUNT, TRAIN_INDICES_SHA,
    VAL_INDICES_SHA, ValidationFrame, indices_sha,
)
from .p07_a3_3_protocol import select_frames as accepted_first128

FRAME_COUNT = 1024
TRACE_FRAME = 1023
SPLIT_SEED = 20261013
SCOPE = "TRAIN_DERIVED_VALIDATION_FIRST_1024"
SELECTION_RULE = "canonical MNIST TRAIN-seeded 50k/10k validation indices, FIRST 1024 in original frozen shuffle order; NO t10k TEST"


def select_validation_prefix(split, count: int = FRAME_COUNT) -> tuple[ValidationFrame, ...]:
    """Fail closed if TRAIN IDX or seeded partition deviates from acceptance.

    The original accepted P07-A3.3 first 128 MUST be byte-identical
    prefix of any future validation subset.
    """
    if type(count) is not int or count not in (16, 128, FRAME_COUNT):
        raise ValueError("A4.2c only precommitted 16/128/1024 validation prefixes permitted")
    m=split.manifest
    if (m.get("schema")!="p06-a3-mnist-train50000-val10000-seeded-v1" or
        m.get("split_seed")!=SPLIT_SEED or
        m.get("official_test_set")!="sealed: no t10k archives opened" or
        m.get("train_indices_le32_sha256")!=TRAIN_INDICES_SHA or
        m.get("validation_indices_le32_sha256")!=VAL_INDICES_SHA or
        split.count!=SOURCE_COUNT or len(split.images)!=SOURCE_COUNT*784 or
        len(split.labels)!=SOURCE_COUNT or
        len(split.train_indices)!=TRAIN_COUNT or
        len(split.validation_indices)!=VALIDATION_COUNT or
        indices_sha(split.train_indices)!=TRAIN_INDICES_SHA or
        indices_sha(split.validation_indices)!=VAL_INDICES_SHA):
        raise ValueError("A4.2c frozen TRAIN-only source split identity mismatch")
    ids=tuple(split.validation_indices[:count])
    if (len(ids)!=count or len(set(ids))!=count or
        any(type(i) is not int or not 0 <= i < SOURCE_COUNT for i in ids)):
        raise ValueError("A4.2c validation first1024 index prefix invalid")
    selected=tuple(
        ValidationFrame(index,split.images[index*784:(index+1)*784],split.labels[index])
        for index in ids
    )
    prefix=accepted_first128(split)
    if selected[:min(count,128)]!=prefix[:min(count,128)]:
        raise ValueError("A4.2c first128 predecessor identity/order changed")
    return selected


def indices_le32_sha256(indices: tuple[int, ...]) -> str:
    from .p07_a4_stream import sha256
    return sha256(b"".join(struct.pack("<I", i) for i in indices))


def validate_ledger(ledger: dict, frames: tuple[ValidationFrame, ...],
                    image_bytes: bytes) -> None:
    from .p07_a4_stream import sha256
    ids=[f.source_index for f in frames]
    if (ledger.get("scope") not in {
            "TRAIN_DERIVED_VALIDATION_FIRST_16",
            "TRAIN_DERIVED_VALIDATION_FIRST_128",
            SCOPE} or
        ledger.get("official_mnist_test")!="SEALED" or
        ledger.get("source")!="canonical TRAIN-only IDX" or
        ledger.get("indices")!=ids or
        ledger.get("selected_indices_le32_sha256") not in (
            None,indices_le32_sha256(tuple(ids))) or
        len(ledger.get("rows",[]))!=len(frames) or
        image_bytes!=b"".join(f.pixels for f in frames)):
        raise ValueError("A4.2c original TRAIN validation ledger or pixel bytes mutated")
    for i,f in enumerate(frames):
        row=ledger["rows"][i]
        if (row.get("position")!=i or row.get("source_index")!=f.source_index or
            row.get("label")!=f.label or
            row.get("pixels_sha256")!=sha256(f.pixels)):
            raise ValueError(f"A4.2c source index/label/image hash mismatch image={i}")
