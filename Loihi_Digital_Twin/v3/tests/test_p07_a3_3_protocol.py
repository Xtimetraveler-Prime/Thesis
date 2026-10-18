"""A3.3 protocol and repeatability gate host fixtures are SYNTHETIC.

No actual MNIST archives, test set, checkpoint or physical mailbox are
used here; native CI only verifies fail-closed evidence/provenance logic.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from loihi_twin_v2.p07_a2_batch import parse_batch
from loihi_twin_v2.p07_a3_validation import ValidationFrame
from loihi_twin_v2 import p07_a3_3_protocol as p

MAPPING = tuple(range(784))


@pytest.fixture
def corpus(tmp_path):
    frames = tuple(ValidationFrame(
        source_index=i * 3, pixels=bytes([i]) * 784, label=i % 10)
        for i in range(p.SAMPLE_COUNT))
    manifest = {"source": "synthetic / no MNIST data"}
    plan, batches = p.prepare_protocol(frames, MAPPING, manifest)
    root = tmp_path/"protocol"
    p.write_protocol(root, plan, batches)
    return root, frames, SimpleNamespace(manifest=manifest), plan, batches


def test_prespecified_first128_and_ten_launch_plan(corpus):
    root, frames, split, plan, batches = corpus
    assert plan["primary_unique_frames"] == 128
    assert plan["physical_launches"] == 10
    assert plan["hardware_frame_executions"] == 160
    assert plan["scored_frame_denominator"] == 128
    assert [x["run_id"] for x in plan["runs"]] == list(p.RUN_IDS)
    assert [x["byte_identical_to"] for x in plan["runs"][-2:]] == [
        "batch_00_primary", "batch_07_primary",
    ]
    for index, b in enumerate(batches):
        assert len(parse_batch(b.header, b.payload)) == 16
        assert b.manifest["selected_source_indices"] == [
            frames[j].source_index for j in range(index*16,(index+1)*16)
        ]
        assert "label" not in (root/f"batch_{index:02d}"/"p07_a2_manifest.json").read_text()
        assert b.labels["official_mnist_test"] == "SEALED"
        assert (root/f"batch_{index:02d}"/"p07_a2_mailbox_zero_64k.bin").stat().st_size == 65536
    assert plan["official_mnist_test"] == "SEALED"
    with pytest.raises(FileExistsError):
        p.write_protocol(root, plan, batches)


def test_full_reconstruction_rejects_manifest_label_or_pixel_tamper(monkeypatch, corpus):
    root, frames, split, plan, batches = corpus
    monkeypatch.setattr(p, "select_frames", lambda _: frames)
    recovered, rebuilt = p.verify_protocol(root, split, MAPPING)
    assert recovered == plan and len(rebuilt) == 8
    label = root/"batch_05"/"p07_a3_3_labels.json"
    original = label.read_bytes()
    changed = json.loads(original)
    changed["rows"][2]["label"] ^= 1
    label.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="batch_05/p07_a3_3_labels"):
        p.verify_protocol(root, split, MAPPING)
    label.write_bytes(original)
    payload = root/"batch_04"/"p07_a2_ingress_payload.bin"
    original = payload.read_bytes()
    payload.write_bytes(original[:-1])
    with pytest.raises(ValueError, match="batch_04/p07_a2_ingress_payload"):
        p.verify_protocol(root, split, MAPPING)
    payload.write_bytes(original)
    plan_file = root/"p07_a3_3_protocol.json"
    original = plan_file.read_bytes()
    changed = json.loads(original)
    changed["scored_frame_denominator"] = 160
    plan_file.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="precommitted"):
        p.verify_protocol(root, split, MAPPING)


def test_reject_duplicate_or_bad_frame_identity():
    frames = tuple(ValidationFrame(i if i!=22 else 21, bytes(784), i%10)
                   for i in range(128))
    with pytest.raises(ValueError, match="invalid/duplicate"):
        p.prepare_protocol(frames, MAPPING, {})
    with pytest.raises(ValueError, match="exactly 128"):
        p.prepare_protocol(frames[:16], MAPPING, {})


def test_selection_rejects_fake_training_provenance():
    split = SimpleNamespace(manifest={"schema": "synthetic-not-accepted"},
                            count=60000, images=bytes(784), labels=bytes(1),
                            train_indices=tuple(), validation_indices=tuple())
    with pytest.raises(ValueError, match="exact frozen canonical"):
        p.select_frames(split)


def test_log_identity_and_outcome_checks(corpus, tmp_path):
    root, frames, split, plan, batches = corpus
    batch = root/"batch_00"
    run = tmp_path/"batch_00_primary"
    run.mkdir()
    logs = {
        "a53_run.log": "P07_A2_KV260_STATUS=TERMINAL_SUCCESS_UNVERIFIED_NUMERICS",
        "verify.log": "P07_A2_PHYSICAL_TRACES_EXACT=1",
        "program.log": "PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released",
        "ps_width.log": "P03_2C_PS_FPD_HPM0_WIDTH_BITS=128",
        "provision.log": "P07_A2_XSDB_PROVISION_PASS=1",
    }
    for name, marker in logs.items():
        (run/name).write_text(marker+"\n")
    (run/"physical_identity.txt").write_text(
        "status=BOARD_NOT_YET_RUN\n"+
        p.XSA_SHA+" /tmp/accepted/p03_2_ps_mmio.xsa\n"+
        p.DDR_SHA256+" /tmp/frozen/master.bin\n"+
        batches[0].manifest["sha256"]["header"]+" "+str(batch.resolve()/"p07_a2_header_64.bin")+"\n"+
        batches[0].manifest["sha256"]["payload"]+" "+str(batch.resolve()/"p07_a2_ingress_payload.bin")+"\n"
    )
    p.validate_evidence_log(run, batch, batches[0])
    (run/"verify.log").write_text("P07_A2_PHYSICAL_TRACES_EXACT=0\n")
    with pytest.raises(ValueError, match="verify.log"):
        p.validate_evidence_log(run, batch, batches[0])


def test_dry_run_wrapper_pins_selected_batch_before_fpga(monkeypatch, corpus, tmp_path):
    import os
    import subprocess
    import sys
    root, frames, split, plan, batches = corpus
    v3 = Path(__file__).resolve().parents[1]
    result = subprocess.run([
        sys.executable, str(v3/"scripts/p07_a3_3_one.py"),
        "--protocol-dir", str(root.resolve()),
        "--evidence-root", str((tmp_path/"runs").resolve()),
        "--run-id", "batch_00_primary",
    ], env={**os.environ,"PYTHONPATH":str(v3/"src")},
       capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "P07_A3_3_DRY_RUN=1" in result.stdout
    assert "P07_A3_3_NEXT_RUN=batch_00_primary" in result.stdout
    assert not (tmp_path/"runs").exists()
