"""P07-A3 validation-only, label-provenance and tamper tests.

All fixtures here are SYNTHETIC and are not board or MNIST accuracy data.
No training/official test archives or torch dependencies are needed.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import json

import pytest

from loihi_twin_v2.p07_a2_batch import parse_batch
from loihi_twin_v2 import p07_a3_validation as val


def fixture_bundle(tmp_path):
    mapping = tuple(range(784))
    frames = tuple(val.ValidationFrame(
        source_index=i, pixels=bytes([i]) * 784, label=i % 10)
        for i in range(16))
    fake_split = SimpleNamespace(manifest={"fixture": "synthetic-NOT-MNIST"})
    header, payload, manifest, ledger = val.make_validation_bundle(
        frames, mapping, split_manifest=fake_split.manifest)
    target = tmp_path / "a3"
    val.write_validation_bundle(target, header, payload, manifest, ledger)
    return target, frames, fake_split


def test_exact_a2_wire_capacity_and_label_separation(tmp_path):
    target, frames, split = fixture_bundle(tmp_path)
    head = (target / "p07_a2_header_64.bin").read_bytes()
    data = (target / "p07_a2_ingress_payload.bin").read_bytes()
    raw = parse_batch(head, data)
    assert len(raw) == 16
    assert len(data) == 16*2480
    assert len(head) == 64
    assert (target / "p07_a2_mailbox_zero_64k.bin").stat().st_size == 65536
    for n, record in enumerate(raw):
        assert record[-784:] == frames[n].pixels
    manifest = json.loads((target / "p07_a2_manifest.json").read_text())
    assert manifest["trace_frame"] == 0
    assert manifest["selected_source_indices"] == list(range(16))
    assert "label" not in (target / "p07_a2_manifest.json").read_text()
    assert manifest["official_mnist_test"] == "SEALED"
    with pytest.raises(FileExistsError):
        val.write_validation_bundle(target, head, data, manifest,
                                    json.loads((target / "p07_a3_validation_labels.json").read_text()))


def test_verify_manifest_rows_bound_to_canonical_reload(monkeypatch, tmp_path):
    target, frames, split = fixture_bundle(tmp_path)
    monkeypatch.setattr(val, "extract_validation_frames", lambda _: frames)
    header, body, ledger = val.verify_validation_provenance(target, split)
    assert len(parse_batch(header, body)) == 16
    assert len(ledger["rows"]) == 16
    label_path = target / "p07_a3_validation_labels.json"
    tampered = json.loads(label_path.read_text())
    tampered["rows"][1]["label"] ^= 1
    label_path.write_text(json.dumps(tampered))
    with pytest.raises(ValueError, match="label/image mismatch"):
        val.verify_validation_provenance(target, split)


def test_wrong_dataset_manifest_and_payload_rejected(monkeypatch, tmp_path):
    target, frames, split = fixture_bundle(tmp_path)
    monkeypatch.setattr(val, "extract_validation_frames", lambda _: frames)
    wrong = SimpleNamespace(manifest={"fixture": "DIFFERENT"})
    with pytest.raises(ValueError, match="canonical training split"):
        val.verify_validation_provenance(target, wrong)
    payload = target / "p07_a2_ingress_payload.bin"
    old = payload.read_bytes()
    payload.write_bytes(old[:-1])
    with pytest.raises(ValueError):
        val.verify_validation_provenance(target, split)


def test_index_hash_pins_and_validation_provenance_reject_fake_split():
    training = tuple(range(50000))
    validation = tuple(range(50000,60000))
    with pytest.raises(ValueError, match="frozen validation partition changed"):
        val.select_validation_sources(training, validation)
    with pytest.raises(ValueError, match="50k train / 10k validation"):
        val.select_validation_sources(training[:2], validation)
    fake = SimpleNamespace(
        manifest={"schema":"synthetic-idx-test-not-benchmark"},
        count=60000, images=bytes(60000*784), labels=bytes(60000),
        train_indices=training, validation_indices=validation)
    with pytest.raises(ValueError, match="exact accepted canonical train-only"):
        val.extract_validation_frames(fake)


def test_reject_duplicate_validation_ids_and_bad_frames():
    mapping = tuple(range(784))
    frames = tuple(val.ValidationFrame(
        source_index=0, pixels=bytes(784), label=i%10)
        for i in range(16))
    with pytest.raises(ValueError, match="duplicate"):
        val.make_validation_bundle(frames, mapping, split_manifest={})
    bad = tuple(val.ValidationFrame(
        source_index=i, pixels=bytes(784), label=10 if i==2 else i%10)
        for i in range(16))
    with pytest.raises(ValueError, match="invalid validation frame"):
        val.make_validation_bundle(bad, mapping, split_manifest={})
