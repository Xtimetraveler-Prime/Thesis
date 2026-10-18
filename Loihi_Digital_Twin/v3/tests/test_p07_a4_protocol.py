"""P07-A4.1 OFFICIAL TEST MUST STAY SEALED in this entire test module.

Only SYNTHETIC in-memory IDX/test-record fixtures are used here.
No download, no t10k file opening, no actual TEST predictions or labels.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from loihi_twin_v2.p07_a1_ingress import decode_ingress
from loihi_twin_v2.p07_a2_batch import parse_batch
from loihi_twin_v2 import p07_a4_protocol as a4

MAP = tuple(range(784))
ROOT = Path(__file__).resolve().parents[1]


def test_precommitted_full_population_and_md5_constants():
    assert a4.FRAME_COUNT == 10000
    assert a4.BATCH_COUNT == 625
    assert a4.BATCH_COUNT*a4.BATCH_SIZE == a4.FRAME_COUNT
    assert a4.SCHEMA == "p07-a4-mnist-canonical-full10000-v1"
    assert a4.TEST_FILES["images"][1] == "9fb629c4189551a2d022fa330f9573f3"
    assert a4.TEST_FILES["labels"][1] == "ec29112dd5afa0611ce80d1b7f02629c"


@pytest.mark.parametrize("kind,count,header", [
    ("images", 2, struct.pack(">4I",2051,2,28,28)),
    ("labels", 2, struct.pack(">2I",2049,2)),
])
def test_idx_strict_parser_synthetic_only(kind,count,header):
    payload = bytes(784*count if kind == "images" else count)
    assert a4._idx_payload(header+payload,kind=kind,count=count) == payload
    with pytest.raises(ValueError):
        a4._idx_payload(header+payload+b"X",kind=kind,count=count)
    with pytest.raises(ValueError):
        a4._idx_payload(header+payload[:-1],kind=kind,count=count)
    with pytest.raises(ValueError):
        a4._idx_payload(bytes([header[0]^1])+header[1:]+payload,
                        kind=kind,count=count)
    with pytest.raises(ValueError):
        a4._idx_payload(header+payload,kind=kind,count=count+1)


def test_labels_reject_range_and_image_dimensions():
    head = struct.pack(">2I",2049,2)
    with pytest.raises(ValueError,match="uint8 class"):
        a4._idx_payload(head+bytes([1,255]),kind="labels",count=2)
    bad_image = struct.pack(">4I",2051,2,27,28)+bytes(2*784)
    with pytest.raises(ValueError,match="shape"):
        a4._idx_payload(bad_image,kind="images",count=2)
    with pytest.raises(ValueError):
        a4._idx_payload(bytes(3),kind="images",count=2)


def _synthetic_complete_dataset():
    # Genuine size/protocol, but explicitly NOT any MNIST data.
    pixel = b"".join(bytes([index%256])*784 for index in range(10000))
    labels = bytes(i%10 for i in range(10000))
    return a4.OfficialTest(pixel,labels,{
        "schema":"SYNTHETIC_OFFICIAL_TEST_FIXTURE_NEVER_REAL_MNIST",
        "image_count":10000,"pixel_stream_sha256":a4.sha(pixel),
        "label_stream_sha256":a4.sha(labels),
    })


@pytest.fixture(scope="module")
def test_fixture():
    return _synthetic_complete_dataset()


def test_wire_protocol_indices_labels_and_no_wire_label_leak(test_fixture):
    first = a4.make_batch(test_fixture,0,MAP)
    last = a4.make_batch(test_fixture,624,MAP)
    for batch,expected_start in ((first,0),(last,9984)):
        records = parse_batch(batch.header,batch.payload)
        assert len(records) == 16
        assert len(batch.payload) == 16*2480
        assert len(batch.header) == 64
        assert batch.manifest["frame_count"] == 16
        assert batch.manifest["trace_frame"] == 0
        assert batch.manifest["first_test_index"] == expected_start
        assert batch.manifest["last_test_index"] == expected_start+15
        assert [row["test_index"] for row in batch.labels["rows"]] == list(
            range(expected_start,expected_start+16))
        for local,record in enumerate(records):
            assert decode_ingress(record).pixels == bytes([(expected_start+local)%256])*784
        assert "truth" not in a4.encode_json(batch.manifest).decode()
        assert batch.labels["labels_host_only"] is True


def test_no_truncated_scored_denominator_and_batch_limits(test_fixture):
    with pytest.raises(ValueError,match="complete canonical"):
        a4.make_batch(a4.OfficialTest(bytes(32*784),bytes(32),{}),0,MAP)
    with pytest.raises(ValueError,match="0..624"):
        a4.make_batch(test_fixture,625,MAP)
    with pytest.raises(ValueError,match="exactly 784"):
        a4.make_batch(test_fixture,0,MAP[:783])


def test_plan_fixes_all_625_indices_without_source_data_mutation(test_fixture):
    plan,batches = a4.immutable_plan(test_fixture,MAP)
    assert len(batches) == plan["physical_batches"] == 625
    assert plan["official_test_count"] == plan["predictions_required"] == 10000
    assert plan["batches"][0]["indices"] == [0,15]
    assert plan["batches"][-1]["indices"] == [9984,9999]
    assert len(set(x["payload_sha256"] for x in plan["batches"])) >= 2
    assert plan["dataset"]["schema"] == "SYNTHETIC_OFFICIAL_TEST_FIXTURE_NEVER_REAL_MNIST"
    assert "KV260_NOT_YET_RUN" in plan["status"]
    assert "625" in plan["physical_launch_mode"]


def test_canonical_loader_rejects_synthetic_archive_before_idx(tmp_path):
    for kind,(name,md5) in a4.TEST_FILES.items():
        (tmp_path/name).write_bytes(b"completely synthetic; not real test archive")
    with pytest.raises(ValueError,match="noncanonical"):
        a4.load_canonical_official_test(tmp_path)


def test_review_safe_and_unseal_requires_explicit_consent(tmp_path):
    script = ROOT/"scripts/p07_a4_prepare.py"
    env = {**os.environ,"PYTHONPATH":str(ROOT/"src")}
    missing_test = tmp_path/"THIS_TEST_DATA_MUST_NOT_BE_OPENED"
    reviewed = subprocess.run([sys.executable,str(script),"--review",
                               "--test-data-dir",str(missing_test)],
                              env=env,text=True,capture_output=True)
    assert reviewed.returncode == 0, reviewed.stderr
    assert "P07_A4_TEST_STATUS=SEALED_NOT_OPENED" in reviewed.stdout
    assert "P07_A4_REVIEW_PASS=1" in reviewed.stdout
    assert "P07_A4_PHYSICAL_BATCHES=625" in reviewed.stdout
    assert not missing_test.exists()
    refused = subprocess.run([sys.executable,str(script),"--download-test",
                              "--test-data-dir",str(missing_test)],
                              env=env,text=True,capture_output=True)
    assert refused.returncode != 0
    assert "--i-accept-unseal" in refused.stderr
    assert not missing_test.exists()
