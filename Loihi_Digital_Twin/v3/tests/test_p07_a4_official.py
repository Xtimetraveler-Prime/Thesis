"""P07-A4.3/4 full10000 guarded persistent TEST protocol — SYNTHETIC.

NEVER opens, downloads or imports actual MNIST TEST/IDX or TRAIN archive.
Artificial 10000 frames and truth labels only exercise packing/CRC,
source-order preservation, independent score gating and shell refusals.
"""
from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys

import pytest

from loihi_twin_v2.p07_a4_official import (
    FRAME_COUNT, TRACE_INDEX, OfficialTest, STAGE_SCHEMA,
    make_official_stage, write_official_stage, check_official_stage,
    full_score,
)
from loihi_twin_v2.p07_a4_official_verify import PHASE
from loihi_twin_v2.p07_a4_protocol import SCHEMA
from loihi_twin_v2.p07_a4_stream import sha256

ROOT=Path(__file__).resolve().parents[1]
MAPPING=tuple(range(784))


@pytest.fixture(scope="module")
def artificial_10k():
    """Artificial deterministic 7.84MiB source, *not* actual MNIST TEST."""
    pixels=b"".join(bytes([i%256])*784 for i in range(10000))
    labels=bytes(i%10 for i in range(10000))
    provenance={
        "schema":SCHEMA+"-actual-archive-provenance-v1",
        "image_count":10000,
        "pixel_stream_sha256":sha256(pixels),
        "label_stream_sha256":sha256(labels),
        "source":"SYNTHETIC_FIXTURE_ONLY_NOT_ORIGINAL_MNIST_TEST",
        "archives":{
            "images":{"compressed_sha256":"fixture-not-a-real-archive",
                      "decoded_idx_sha256":"synthetic-not-MNIST"},
            "labels":{"compressed_sha256":"fixture-not-a-real-archive",
                      "decoded_idx_sha256":"synthetic-not-MNIST"},
        },
    }
    return OfficialTest(pixels,labels,provenance)


def test_exact_full10000_stage_image_order_host_labels(artificial_10k,tmp_path):
    out=tmp_path/"synthetic_official_wire_fixture"
    manifest=write_official_stage(out,artificial_10k,MAPPING)
    stream,meta,ledger=check_official_stage(out,artificial_10k)
    assert stream.image_count==FRAME_COUNT==10000
    assert stream.trace_index==TRACE_INDEX==9999
    assert len(stream.images)==10000*784
    assert stream.image(0)==artificial_10k.pixels[:784]
    assert stream.image(9999)==artificial_10k.pixels[-784:]
    assert ledger["rows"][0]["index"]==0
    assert ledger["rows"][-1]["index"]==9999
    assert ledger["rows"][9999]["truth"]==artificial_10k.labels[9999]
    assert ledger["labels_host_only"] is True
    assert meta["scope"]=="OFFICIAL_MNIST_TEST_FULL10000"
    assert meta["physical_hardware"]=="NOT_RUN"
    assert "UNSEALED_PREPARED_NOT_SCORED"==meta["official_mnist_test"]
    assert (out/"p07_a4_official_labels_HOST_ONLY.json").is_file()
    assert len((out/"p07_a4_journal_initial_1m.bin").read_bytes())==1048576
    assert len((out/"p07_a4_descriptor_256.bin").read_bytes())==256
    with pytest.raises(FileExistsError,match="already exists"):
        write_official_stage(out,artificial_10k,MAPPING)


def test_original_order_mutated_source_rejected(artificial_10k,tmp_path):
    out=tmp_path/"synthetic_wire"
    write_official_stage(out,artificial_10k,MAPPING)
    path=out/"p07_a4_pixels_raw.bin"
    bad=bytearray(path.read_bytes())
    bad[784],bad[1568]=bad[1568],bad[784]
    path.write_bytes(bad)
    with pytest.raises(ValueError,match="staged bytes SHA mismatch"):
        check_official_stage(out,artificial_10k)


def test_original_order_label_ledger_mutation_rejected(artificial_10k,tmp_path):
    out=tmp_path/"synthetic_wire"
    write_official_stage(out,artificial_10k,MAPPING)
    p=out/"p07_a4_official_labels_HOST_ONLY.json"
    ledger=json.loads(p.read_text())
    ledger["rows"][11]["truth"]=9
    p.write_text(json.dumps(ledger))
    with pytest.raises(ValueError,match="host-only label ledger"):
        check_official_stage(out,artificial_10k)


def test_reject_wrong_image_count_and_absent_archives(artificial_10k):
    with pytest.raises(ValueError,match="provenance mismatch"):
        make_official_stage(replace(
            artificial_10k,pixels=artificial_10k.pixels[:-784]
        ),MAPPING)
    with pytest.raises(ValueError,match="archive SHA256"):
        make_official_stage(replace(
            artificial_10k,manifest={**artificial_10k.manifest,
                                     "archives":{}}
        ),MAPPING)


def test_10000_host_only_score_exact_denominator_after_oracle(artificial_10k):
    records=tuple(SimpleNamespace(
        image_index=i,predicted=artificial_10k.labels[i],
        counts=tuple(1 if j==artificial_10k.labels[i] else 0 for j in range(10)),
        all_silent=False,
    ) for i in range(10000))
    report=full_score(records,artificial_10k)
    assert report["test_samples"]==10000
    assert report["correct"]==10000
    assert report["accuracy_percent"]==100
    assert report["all_silent"]==0
    assert sum(map(sum,report["confusion_matrix_rows_truth_columns_predicted"]))==10000
    assert sum(report["class_support"])==10000
    assert len(report["rows"])==10000
    with pytest.raises(ValueError,match="no partial score denominator"):
        full_score(records[:-1],artificial_10k)


def test_official_sealed_review_never_accesses_real_data(tmp_path):
    script=ROOT/"scripts/p07_a4_official_prepare.py"
    env={**os.environ,"PYTHONPATH":str(ROOT/"src")}
    cmd=[sys.executable,str(script),"--review",
         "--test-data-dir",str(tmp_path/"NO_ACTUAL_T10K_FILES"),
         "--fault-evidence-dir",str(tmp_path/"NO_HARDWARE")]
    got=subprocess.run(cmd,env=env,capture_output=True,text=True)
    assert got.returncode==0,got.stderr
    assert "P07_A4_OFFICIAL_TEST=SEALED" in got.stdout
    assert "P07_A4_3_SEALED_REVIEW_PASS=1" in got.stdout
    assert not (tmp_path/"NO_ACTUAL_T10K_FILES").exists()


def test_official_prepare_rejects_unseal_without_actual_fault(tmp_path):
    script=ROOT/"scripts/p07_a4_official_prepare.py"
    env={**os.environ,"PYTHONPATH":str(ROOT/"src")}
    stage=tmp_path/"NO_UNSEAL_OFFICIAL"
    cmd=[sys.executable,str(script),"--prepare",
         "--test-data-dir",str(tmp_path/"NONEXISTENT_REAL_OFFICIAL_TEST"),
         "--fault-stage-dir",str(tmp_path/"NONEXISTENT_FAULT_STAGE"),
         "--fault-evidence-dir",str(tmp_path/"NONEXISTENT_FAULT_EVIDENCE"),
         "--out",str(stage)]
    got=subprocess.run(cmd,env=env,capture_output=True,text=True)
    assert got.returncode!=0
    assert "official TEST remains sealed" in got.stderr
    assert not stage.exists()
    cmd.extend(["--i-accept-unseal","--i-accept-one-trace-policy"])
    got=subprocess.run(cmd,env=env,capture_output=True,text=True)
    assert got.returncode!=0
    assert not stage.exists()
    assert not (tmp_path/"NONEXISTENT_REAL_OFFICIAL_TEST").exists()


def test_official_physical_is_separate_and_requires_three_approvals(tmp_path):
    shell=ROOT/"scripts/run_p07_a4_official_physical.sh"
    proc=subprocess.run(["bash","-n",str(shell)],capture_output=True,text=True)
    assert proc.returncode==0,proc.stderr
    text=shell.read_text()
    assert "P07_A4_CONFIRM_KV260_DDR_OVERWRITE" in text
    assert "P07_A4_CONFIRM_OFFICIAL_TEST_PHYSICAL" in text
    assert "P07_A4_CONFIRM_UNSEALED_TEST" in text
    assert "P07_A4_ACCEPT_ONE_TRACE_POLICY" in text
    assert "P07_A4_OFFICIAL_TEST_DATA_DIR" in text
    assert "p07_a4_official_check.py" in text
    assert "p07_a4_official_verify.py" in text
    assert "P07_A4_4_FULL_CANONICAL_TEST_PASS=1" in text
    assert PHASE in text
    assert "p07_a4_2_verify.py" not in text
    # Reject fake inputs before any hardware or output directory access:
    p=subprocess.run(["bash",str(shell)],env={
        **os.environ,"P07_A4_OFFICIAL_RUN_DIR":str(tmp_path/"result"),
        "P07_A4_BUILD_DIR":str(tmp_path),
        "P03_DIAG_REPORTS":str(tmp_path),
        "P03_2C_EXPECTED_XSA_SHA":"52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f",
        "P07_A4_OFFICIAL_STAGE_DIR":str(tmp_path),
        "P07_A4_CONFIRM_KV260_DDR_OVERWRITE":"NO",
    },capture_output=True,text=True)
    assert p.returncode!=0
    assert not (tmp_path/"result").exists()


def test_all_new_official_scripts_syntax_only_and_no_hidden_test_download():
    for script in ("p07_a4_official_prepare.py","p07_a4_official_check.py",
                   "p07_a4_official_verify.py"):
        p=subprocess.run([sys.executable,"-m","py_compile",str(ROOT/"scripts"/script)],
                         capture_output=True,text=True)
        assert p.returncode==0,p.stderr
    verify=(ROOT/"src/loihi_twin_v2/p07_a4_official_verify.py").read_text()
    assert "check_trace(trace,image,oracle)" in verify
    assert "full_score(results,official)" in verify
    assert verify.index("check_trace(trace,image,oracle)") < verify.index("full_score(results,official)")
    assert "results=parse_journal(journal,stream)" in verify
    assert "P07_A4_4_FULL10000_KV260_INDEPENDENT_CLOSEOUT_PASS=1" in (
        ROOT/"scripts/p07_a4_official_verify.py").read_text()
