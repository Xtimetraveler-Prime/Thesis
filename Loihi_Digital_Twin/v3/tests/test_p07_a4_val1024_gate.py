"""A4.2c larger persisted result gate native tests, SYNTHETIC ONLY.

No MNIST TEST/TRAIN archive, no physical FPGA. The existing 128 restart
suite already tests the shared strict real-source/XSDB-evidence verifier;
this file tests 1024 fixed scope, final trace and byte-level divergence.
"""
from __future__ import annotations

import json
from pathlib import Path
import struct
from types import SimpleNamespace

import pytest

from loihi_twin_v2 import p07_a4_val1024_gate as gate
from loihi_twin_v2.p07_a4_stream import (
    make_stream, initial_journal, encode_result, crc, sha256,
    SUCCESS, NO_FAILURE,
)
from loihi_twin_v2.p07_a4_validation import SCOPE, TRACE_FRAME, indices_le32_sha256

MAP=tuple(range(784))
ZERO_SPIKES=tuple(tuple(0 for _ in range(10)) for _ in range(26))


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    n=1024
    stage=tmp_path/"artificial_train_prefix1024"
    stage.mkdir()
    pixels=bytes([9])*784*n
    obj=make_stream(pixels,MAP,trace_index=1023)
    payloads={
        "descriptor":("p07_a4_descriptor_256.bin",obj.header),
        "mapping":("p07_a4_mapping_1568.bin",obj.mapping_bytes),
        "pixels":("p07_a4_pixels_raw.bin",obj.images),
        "zero_journal_1m":("p07_a4_journal_initial_1m.bin",initial_journal(obj)),
    }
    for _,(filename,raw) in payloads.items():
        (stage/filename).write_bytes(raw)
    manifest={
        "schema":"p07-a4-2a-persistent-ddr-stage-v1","scope":SCOPE,
        "frame_count":n,"trace_index":TRACE_FRAME,
        "official_mnist_test":"SEALED","physical_hardware":"NOT_RUN",
        "sha256":{key:sha256(raw) for key,(_,raw) in payloads.items()},
    }
    (stage/"p07_a4_2a_stage_manifest.json").write_text(json.dumps(manifest))
    ids=list(range(1000,1000+n))
    (stage/"p07_a4_2a_validation_labels_HOST_ONLY.json").write_text(json.dumps({
        "scope":SCOPE, "official_mnist_test":"SEALED",
        "source":"canonical TRAIN-only IDX","indices":ids,
        "selected_indices_le32_sha256":indices_le32_sha256(tuple(ids)),
        "rows":[{
            "position":i,"source_index":source,"label":i%10,
            "pixels_sha256":sha256(obj.image(i)),
        } for i,source in enumerate(ids)],
    }))
    journal=bytearray(initial_journal(obj))
    struct.pack_into("<I",journal,16,SUCCESS)
    struct.pack_into("<I",journal,24,n)
    struct.pack_into("<I",journal,252,crc(journal[:252]))
    for i in range(n):
        idx=256+i*96
        journal[idx:idx+96]=encode_result(i,obj.image(i),ZERO_SPIKES)
    paths=[]
    for name in ("primary","repeat"):
        evidence=tmp_path/name
        evidence.mkdir()
        (evidence/"p07_a4_journal_1m.bin").write_bytes(journal)
        (evidence/"p07_a4_trace_64k.bin").write_bytes(bytes(65536))
        paths.append(evidence)

    def verified_run(stage,evidence,stream,*,expected_frames):
        # Shared strict original hardware source-gate is independently
        # covered by test_p07_a4_restart.py, with native tamper tests.
        assert expected_frames==1024
        from loihi_twin_v2.p07_a4_stream import parse_journal
        decoded=parse_journal((evidence/"p07_a4_journal_1m.bin").read_bytes(),stream)
        assert len(decoded)==1024
        return SimpleNamespace(
            complete_frames=1024,
            bit_sha256="fixed-bit-hash",ltx_sha256="fixed-ltx-hash",
            journal_sha256=sha256((evidence/"p07_a4_journal_1m.bin").read_bytes()),
            trace_sha256=sha256((evidence/"p07_a4_trace_64k.bin").read_bytes()),
        )
    monkeypatch.setattr(gate,"_read_run",verified_run)
    return stage,paths[0],paths[1]


def test_first1024_fixed_scope_and_full_journal_repeat_exact(fixture):
    stage,primary,repeat=fixture
    meta,stream,ledger=gate.stage_1024(stage)
    assert len(ledger["rows"])==stream.image_count==1024
    assert stream.trace_index==1023
    one=gate.verify_1024(stage=stage,primary=primary)
    assert one["status"]=="PRIMARY_ACCEPTED_REPEAT_NOT_RUN"
    assert one["unique_train_validation_images"]==1024
    two=gate.verify_1024(stage=stage,primary=primary,repeat=repeat)
    assert two["physical_launches"]==2
    assert two["physical_frame_executions"]==2048
    assert two["full_journal_1m_byte_exact"] and two["selected_trace_64k_byte_exact"]


def test_reject_same_physical_launch_as_repeat(fixture):
    stage,primary,repeat=fixture
    with pytest.raises(ValueError,match="NEW independent evidence"):
        gate.verify_1024(stage=stage,primary=primary,repeat=primary)


def test_reject_1024_distinct_input_index_reorder(fixture):
    stage,primary,repeat=fixture
    ledgerfile=stage/"p07_a4_2a_validation_labels_HOST_ONLY.json"
    ledger=json.loads(ledgerfile.read_text())
    ledger["indices"][33]=ledger["indices"][0]
    ledgerfile.write_text(json.dumps(ledger))
    with pytest.raises(ValueError,match="ledger/order invalid"):
        gate.verify_1024(stage=stage,primary=primary)


def test_reject_non1024_scope_or_trace_selection(fixture):
    stage,primary,repeat=fixture
    p=stage/"p07_a4_2a_stage_manifest.json"
    m=json.loads(p.read_text())
    m["trace_index"]=0
    p.write_text(json.dumps(m))
    with pytest.raises(ValueError,match="requires fixed"):
        gate.verify_1024(stage=stage,primary=primary)


def test_reject_tampered_physical_output_even_with_recomputed_crc(fixture):
    stage,primary,repeat=fixture
    file=repeat/"p07_a4_journal_1m.bin"
    raw=bytearray(file.read_bytes())
    pos=256+999*96
    struct.pack_into("<I",raw,pos+88,15)  # clock cycles, not an output bit
    struct.pack_into("<I",raw,pos+92,crc(raw[pos:pos+92]))
    file.write_bytes(raw)
    with pytest.raises(AssertionError,match="full 1MiB"):
        gate.verify_1024(stage=stage,primary=primary,repeat=repeat)


def test_reject_tampered_last_image_trace(fixture):
    stage,primary,repeat=fixture
    file=repeat/"p07_a4_trace_64k.bin"
    raw=bytearray(file.read_bytes())
    raw[32]=1
    file.write_bytes(raw)
    with pytest.raises(AssertionError,match="full 64KiB"):
        gate.verify_1024(stage=stage,primary=primary,repeat=repeat)


def test_reject_1024_incomplete_journal(fixture):
    stage,primary,repeat=fixture
    p=repeat/"p07_a4_journal_1m.bin"
    raw=bytearray(p.read_bytes())
    struct.pack_into("<I",raw,24,1023)
    struct.pack_into("<I",raw,252,crc(raw[:252]))
    p.write_bytes(raw)
    with pytest.raises(ValueError,match="not entirely completed"):
        gate.verify_1024(stage=stage,primary=primary,repeat=repeat)
