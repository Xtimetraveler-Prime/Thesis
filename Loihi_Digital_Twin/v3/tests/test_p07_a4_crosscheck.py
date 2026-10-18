"""Synthetic native fixture for A4.2c physical-to-physical result crosscheck.

No actual board mailboxes and NO t10k TEST data are accessed in CI.
Fixtures emulate evidence formats solely to test integrity rejection,
sample-order discipline, selected-trace equality and first divergence.
"""
from __future__ import annotations

import json
from pathlib import Path
import struct

import pytest

from loihi_twin_v2.p07_a3_validation import ValidationFrame
from loihi_twin_v2.p07_a3_3_protocol import prepare_protocol, write_protocol
from loihi_twin_v2.p07_a2_batch import RESULT_BYTES, parse_batch
from loihi_twin_v2.p07_a4_crosscheck import compare_prior_physical
from loihi_twin_v2.p07_a4_stream import (
    make_stream, initial_journal, encode_result, crc, sha256, SUCCESS, NO_FAILURE,
)

MAPPING=tuple((i*73+17)%4096 for i in range(784))
ZERO_SPIKES=tuple(tuple(0 for _ in range(10)) for _ in range(26))


@pytest.fixture
def evidence(tmp_path):
    # 128 distinct SOURCE INDICES, 128 explicitly artificial black images.
    # Not one image originates from MNIST TEST/TRAIN archives.
    frames=tuple(ValidationFrame(1000+i,bytes(784),i%10) for i in range(128))
    split={"source":"SYNTHETIC_FAKE_TRAIN_ONLY_FIXTURE"}
    plan,batches=prepare_protocol(frames,MAPPING,split)
    old_plan=tmp_path/"synthetic_a3_protocol"
    write_protocol(old_plan,plan,batches)
    a4_stage=tmp_path/"synthetic_a4_stage"
    a4_stage.mkdir()
    stream=make_stream(bytes(128*784),MAPPING)
    inputs={
        "descriptor":("p07_a4_descriptor_256.bin",stream.header),
        "mapping":("p07_a4_mapping_1568.bin",stream.mapping_bytes),
        "pixels":("p07_a4_pixels_raw.bin",stream.images),
        "zero_journal_1m":("p07_a4_journal_initial_1m.bin",initial_journal(stream)),
    }
    for key,(filename,payload) in inputs.items():
        (a4_stage/filename).write_bytes(payload)
    (a4_stage/"p07_a4_2a_stage_manifest.json").write_text(json.dumps({
        "schema":"p07-a4-2a-persistent-ddr-stage-v1",
        "scope":"TRAIN_DERIVED_VALIDATION_FIRST_128",
        "frame_count":128,"trace_index":0,
        "official_mnist_test":"SEALED",
        "sha256":{key:sha256(raw) for key,(_,raw) in inputs.items()},
    }))
    (a4_stage/"p07_a4_2a_validation_labels_HOST_ONLY.json").write_text(json.dumps({
        "official_mnist_test":"SEALED",
        "indices":[x.source_index for x in frames],
        "rows":[{
            "position":i,"source_index":f.source_index,
            "label":f.label,"pixels_sha256":sha256(f.pixels),
        } for i,f in enumerate(frames)],
    }))

    a3_evidence=tmp_path/"synthetic_a3_evidence"
    a3_evidence.mkdir()
    mailbox_shas={}
    report_rows=[]
    for b,batch in enumerate(batches):
        run_id=f"batch_{b:02d}_primary"
        run_dir=a3_evidence/run_id
        run_dir.mkdir()
        (run_dir/"verify.log").write_text(
            "P07_A2_PHYSICAL_TRACES_EXACT=1\nP07_A2_OFFICIAL_TEST=SEALED\n"
        )
        old=bytearray(RESULT_BYTES)
        old[:4]=b"P07R"
        for offset,value in ((4,1),(8,SUCCESS),(24,16),(28,0),(32,16)):
            struct.pack_into("<I",old,offset,value)
        for local,record in enumerate(parse_batch(batch.header,batch.payload)):
            base=256+local*128
            for offset,value in ((0,SUCCESS),(4,0),(8,1),(12,26),
                                 (16,26),(20,26),(84,struct.unpack_from("<I",record,56)[0])):
                struct.pack_into("<I",old,base+offset,value)
            f=frames[b*16+local]
            report_rows.append({
                "frame":b*16+local,
                "source_index":f.source_index,
                "truth":f.label,
                "prediction":0,
                "silent":1,
                "image_sha256":sha256(f.pixels),
            })
        (run_dir/"p07_a2_mailbox.bin").write_bytes(old)
        mailbox_shas[run_id]=sha256(old)
    (a3_evidence/"p07_a3_3_validation128_report.json").write_text(json.dumps({
        "selected_indices_le32_sha256":plan["selected_indices_le32_sha256"],
        "primary_unique_frames":128,"denominator":128,"physical_launches":10,
        "repeat_count":2,"official_mnist_test":"SEALED",
        "mailbox_sha256_by_run":mailbox_shas,
        "frames":report_rows,
    }))
    result=bytearray(initial_journal(stream))
    struct.pack_into("<I",result,16,SUCCESS)
    struct.pack_into("<I",result,24,128)
    struct.pack_into("<I",result,252,crc(result[:252]))
    for i in range(128):
        begin=256+i*96
        result[begin:begin+96]=encode_result(i,stream.image(i),ZERO_SPIKES)
    a4_journal=tmp_path/"synthetic_new_journal.bin"
    a4_journal.write_bytes(result)
    a4_trace=tmp_path/"synthetic_new_trace.bin"
    a4_trace.write_bytes(bytes(65536))
    return {
        "a4_stage":a4_stage,"a4_journal":a4_journal,"a4_trace":a4_trace,
        "a3_protocol":old_plan,"a3_evidence":a3_evidence,
    }


def test_all_128_matches_between_synthetic_format_fixtures(evidence):
    result=compare_prior_physical(**evidence)
    assert result.frames==128
    assert result.prior_primary_batches==8
    assert result.selected_trace_exact


def test_reject_mutated_original_evidence_even_when_old_parser_accepts(evidence):
    old=(evidence["a3_evidence"]/"batch_03_primary"/"p07_a2_mailbox.bin")
    raw=bytearray(old.read_bytes())
    # Old physical packet-routes field changed, preserving valid result
    # shape; independently hashed original must be immutable.
    struct.pack_into("<I",raw,256+6*128+24,1)
    old.write_bytes(raw)
    with pytest.raises(ValueError,match="mailbox digest changed"):
        compare_prior_physical(**evidence)


def test_reject_new_result_mismatch_with_recomputed_valid_crc(evidence):
    path=evidence["a4_journal"]
    raw=bytearray(path.read_bytes())
    index=33
    start=256+index*96
    struct.pack_into("<I",raw,start+20,11)  # routed packets only
    struct.pack_into("<I",raw,start+92,crc(raw[start:start+92]))
    path.write_bytes(raw)
    with pytest.raises(AssertionError,match="frame=33 field=routes"):
        compare_prior_physical(**evidence)


def test_reject_order_mismatch_before_numerical_evidence(evidence):
    path=evidence["a4_stage"]/"p07_a4_2a_validation_labels_HOST_ONLY.json"
    ledger=json.loads(path.read_text())
    ledger["indices"][4],ledger["indices"][5]=ledger["indices"][5],ledger["indices"][4]
    path.write_text(json.dumps(ledger))
    with pytest.raises(ValueError,match="source order differs"):
        compare_prior_physical(**evidence)


def test_reject_selected_trace_divergence(evidence):
    trace=evidence["a4_trace"]
    raw=bytearray(trace.read_bytes())
    raw[10]=1
    trace.write_bytes(raw)
    with pytest.raises(AssertionError,match="full 26x42 trace"):
        compare_prior_physical(**evidence)


def test_reject_incomplete_physical_journal(evidence):
    path=evidence["a4_journal"]
    raw=bytearray(path.read_bytes())
    struct.pack_into("<I",raw,24,127)
    struct.pack_into("<I",raw,252,crc(raw[:252]))
    path.write_bytes(raw)
    with pytest.raises(ValueError,match="not entirely completed"):
        compare_prior_physical(**evidence)
