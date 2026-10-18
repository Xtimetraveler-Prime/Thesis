"""A4.2c first1024 TRAIN-prefix regression: SYNTHETIC ONLY.

No official TEST or actual TRAIN archives opened by this test.
The real canonical 50k/10k provenance is checked on user's machine by
the sealed-TRAIN-only CLI's first1024 selection and per-image ledger.
"""
from __future__ import annotations

import json
from pathlib import Path
import struct
from types import SimpleNamespace
import zlib

import pytest

from loihi_twin_v2 import p07_a4_validation as v
from loihi_twin_v2 import p07_a4_stream as stream
from loihi_twin_v2.p07_a3_validation import ValidationFrame

MAPPING=tuple(range(784))


def synthetic_1100(monkeypatch):
    """Exercise the 1024-prefix selection with tiny custom manifest identities."""
    n=1100
    training=tuple(range(76))
    validating=tuple(range(76,1100))
    images=b"".join(bytes([i%256])*784 for i in range(n))
    labels=bytes(i%10 for i in range(n))
    monkeypatch.setattr(v,"SOURCE_COUNT",n)
    monkeypatch.setattr(v,"TRAIN_COUNT",len(training))
    monkeypatch.setattr(v,"VALIDATION_COUNT",len(validating))
    monkeypatch.setattr(v,"TRAIN_INDICES_SHA",v.indices_sha(training))
    monkeypatch.setattr(v,"VAL_INDICES_SHA",v.indices_sha(validating))
    split=SimpleNamespace(
        images=images,labels=labels,count=n,
        train_indices=training,validation_indices=validating,
        manifest={
            "schema":"p06-a3-mnist-train50000-val10000-seeded-v1",
            "split_seed":20261013,
            "official_test_set":"sealed: no t10k archives opened",
            "train_indices_le32_sha256":v.TRAIN_INDICES_SHA,
            "validation_indices_le32_sha256":v.VAL_INDICES_SHA,
        },
    )
    monkeypatch.setattr(v,"accepted_first128",
                        lambda x: tuple(ValidationFrame(i,
                            x.images[i*784:(i+1)*784],x.labels[i])
                            for i in x.validation_indices[:128]))
    return split


def test_first1024_source_ids_exact_and_matches_original_128_prefix(monkeypatch):
    split=synthetic_1100(monkeypatch)
    first=v.select_validation_prefix(split,128)
    big=v.select_validation_prefix(split,1024)
    assert len(big)==1024
    assert len({frame.source_index for frame in big})==1024
    assert big[:128]==first
    assert big[0].source_index==76
    assert big[-1].source_index==1099
    assert big[-1].pixels==bytes([1099%256])*784
    assert v.indices_le32_sha256(tuple(f.source_index for f in big))==stream.sha256(
        b"".join(struct.pack("<I",i) for i in range(76,1100))
    )
    with pytest.raises(ValueError,match="precommitted"):
        v.select_validation_prefix(split,1023)


def test_first1024_split_tamper_rejected(monkeypatch):
    split=synthetic_1100(monkeypatch)
    split.manifest["official_test_set"]="SEALED BUT DIFFERENT"
    with pytest.raises(ValueError,match="split identity"):
        v.select_validation_prefix(split,1024)


def test_first1024_ledger_independent_original_idx_provenance(monkeypatch):
    split=synthetic_1100(monkeypatch)
    frames=v.select_validation_prefix(split,1024)
    pixels=b"".join(f.pixels for f in frames)
    mapping=MAPPING
    obj=stream.make_stream(pixels,mapping,trace_index=v.TRACE_FRAME)
    assert obj.image_count==1024 and obj.trace_index==1023
    assert stream.parse_stream(obj.header,obj.mapping_bytes,obj.images)==obj
    ledger={
        "scope":v.SCOPE,"source":"canonical TRAIN-only IDX",
        "official_mnist_test":"SEALED",
        "indices":[f.source_index for f in frames],
        "selected_indices_le32_sha256":v.indices_le32_sha256(
            tuple(f.source_index for f in frames)),
        "rows":[{
            "position":i,"source_index":f.source_index,
            "label":f.label,"pixels_sha256":stream.sha256(f.pixels)
        } for i,f in enumerate(frames)],
    }
    v.validate_ledger(ledger,frames,obj.images)
    ledger["rows"][512]["label"]^=1
    with pytest.raises(ValueError,match="source index/label/image hash mismatch"):
        v.validate_ledger(ledger,frames,obj.images)
    ledger["rows"][512]["label"]^=1
    ledger["indices"][10],ledger["indices"][11]=ledger["indices"][11],ledger["indices"][10]
    with pytest.raises(ValueError,match="ledger"):
        v.validate_ledger(ledger,frames,obj.images)


def test_v3_staging_and_oracle_explicitly_support_only_sealed_1024():
    root=Path(__file__).resolve().parents[1]
    prep=(root/"scripts/p07_a4_2_prepare.py").read_text()
    check=(root/"scripts/p07_a4_2_check.py").read_text()
    oracle=(root/"scripts/p07_a4_2_verify.py").read_text()
    assert "choices=(16,128,1024)" in prep
    assert "args.trace_index != 1023" in prep
    assert "selected_indices_le32_sha256" in prep
    assert "select_validation_prefix" in prep
    assert "select_validation_prefix" in oracle
    assert "validate_ledger" in oracle
    assert '"TRAIN_DERIVED_VALIDATION_FIRST_1024"' in check
    assert "stream.trace_index!=1023" in check
    assert "replay_p03_image" in oracle
    assert "p07_a4_2_restart_verify.py" not in oracle  # old fixed-128 checker separate
