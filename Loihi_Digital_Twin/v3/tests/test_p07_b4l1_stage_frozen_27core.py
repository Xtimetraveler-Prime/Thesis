"""B4l.1 offline original 27-core P02 stage; no torch, KV260 or TEST."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b4l1_stage_frozen_27core as stage


def fake_freeze(tmp_path):
    """Synthetic raw blobs ONLY: real production path runs accepted B2.4
    header/payload/manifest verifier first. No model bytes generated here."""
    frozen=tmp_path/"frozen"
    rawdir=frozen/"initial_ddr"
    rawdir.mkdir(parents=True)
    assets=[]
    core_shas=[]
    for cid in range(stage.RECORDS):
        rel=stage.record_filename(cid)
        data=bytes([cid])*stage.STRIDE
        file=frozen/rel
        file.write_bytes(data)
        sha=hashlib.sha256(data).hexdigest()
        assets.append({"path":rel,"sha256":sha,"bytes":len(data)})
        core_shas.append(sha)
    return frozen,{
        "assets":assets,
        "ddr_context_sha256":core_shas,
    }


def test_all_27_original_records_have_pinned_geometry():
    assert stage.RECORDS==27
    assert stage.SLOTS==3
    assert stage.STRIDE==524288
    assert stage.TOTAL_BYTES==14155776
    assert stage.DDR_BASE==0x40000000
    assert stage.DDR_END==0x40D80000
    assert stage.record_filename(26).endswith("core_026_initial_p02_512k.bin")
    assert (stage.DDR_END<=0x43F00000<0x43FF0000<0x44000000)


def test_host_stage_prepare_then_verify_original_byte_exact(tmp_path,monkeypatch):
    frozen,obj=fake_freeze(tmp_path)
    monkeypatch.setattr(stage,"admit_freeze",lambda _:obj)
    original=[stage.file_sha(frozen/stage.record_filename(i)) for i in range(27)]
    out=tmp_path/"new_stage"
    report=stage.prepare(frozen,out)
    assert report["bundle_sha256"]==stage.file_sha(out/stage.BUNDLE_NAME)
    assert report["bytes"]==27*524288
    assert report["physical_end_exclusive"]=="0x40D80000"
    assert stage.verify_bundle(frozen,out)==report
    manifest=json.loads((out/stage.INDEX_NAME).read_text())
    assert manifest["schema"]==stage.SCHEMA
    assert manifest["logical_core_count"]==27
    assert manifest["resident_slot_count"]==3
    assert manifest["physical_engine_count"]==1
    assert manifest["physical_ddr_staged"] is False
    assert manifest["official_mnist_test"]=="SEALED_NOT_ACCESSED"
    assert manifest["records"][0]["physical_address"]=="0x40000000"
    assert manifest["records"][26]["physical_address"]=="0x40D00000"
    assert [r["logical_core_id"] for r in manifest["records"]]==list(range(27))
    assert [r["byte_offset"] for r in manifest["records"]]==[
        i*524288 for i in range(27)]
    assert original==[stage.file_sha(frozen/stage.record_filename(i)) for i in range(27)]
    assert not list(tmp_path.glob(".p07_b4l1_*"))


def test_changed_source_rejected_without_creating_stage(tmp_path,monkeypatch):
    frozen,obj=fake_freeze(tmp_path)
    monkeypatch.setattr(stage,"admit_freeze",lambda _:obj)
    (frozen/stage.record_filename(2)).write_bytes(b"\xff"*stage.STRIDE)
    out=tmp_path/"stage_output"
    with pytest.raises(stage.StageError,match="record SHA mismatch"):
        stage.prepare(frozen,out)
    assert not out.exists()


def test_missing_core_rejected_without_creating_stage(tmp_path,monkeypatch):
    frozen,obj=fake_freeze(tmp_path)
    monkeypatch.setattr(stage,"admit_freeze",lambda _:obj)
    (frozen/stage.record_filename(26)).unlink()
    with pytest.raises(stage.StageError,match="core 26"):
        stage.prepare(frozen,tmp_path/"out")
    assert not (tmp_path/"out").exists()


def test_manifest_crosscore_swap_rejected(tmp_path,monkeypatch):
    frozen,obj=fake_freeze(tmp_path)
    obj["ddr_context_sha256"][1],obj["ddr_context_sha256"][2]=(
        obj["ddr_context_sha256"][2],obj["ddr_context_sha256"][1])
    monkeypatch.setattr(stage,"admit_freeze",lambda _:obj)
    with pytest.raises(stage.StageError,match="original asset mismatch"):
        stage.prepare(frozen,tmp_path/"out")


def test_corrupted_staged_binary_fails_verification(tmp_path,monkeypatch):
    frozen,obj=fake_freeze(tmp_path)
    monkeypatch.setattr(stage,"admit_freeze",lambda _:obj)
    out=tmp_path/"out"
    stage.prepare(frozen,out)
    file=out/stage.BUNDLE_NAME
    with file.open("r+b") as f:
        f.seek(stage.STRIDE+8)
        f.write(b"\xde")
    with pytest.raises(stage.StageError,match="staged record addresses"):
        stage.verify_bundle(frozen,out)


def test_corrupted_stage_index_fails_without_rewriting(tmp_path,monkeypatch):
    frozen,obj=fake_freeze(tmp_path)
    monkeypatch.setattr(stage,"admit_freeze",lambda _:obj)
    out=tmp_path/"out"
    stage.prepare(frozen,out)
    index=out/stage.INDEX_NAME
    data=json.loads(index.read_text())
    data["records"][5]["physical_address"]="0x43FF0000"
    index.write_text(json.dumps(data))
    with pytest.raises(stage.StageError,match="index self-hash"):
        stage.verify_bundle(frozen,out)


def test_silent_extra_staged_output_is_forbidden(tmp_path,monkeypatch):
    frozen,obj=fake_freeze(tmp_path)
    monkeypatch.setattr(stage,"admit_freeze",lambda _:obj)
    out=tmp_path/"out"
    stage.prepare(frozen,out)
    (out/"extra_model.pt").write_bytes(b"ignored")
    with pytest.raises(stage.StageError,match="missing/extra"):
        stage.verify_bundle(frozen,out)


def test_reprepare_refuses_to_overwrite_evidence(tmp_path,monkeypatch):
    frozen,obj=fake_freeze(tmp_path)
    monkeypatch.setattr(stage,"admit_freeze",lambda _:obj)
    out=tmp_path/"out"
    stage.prepare(frozen,out)
    with pytest.raises(stage.StageError,match="output must be new"):
        stage.prepare(frozen,out)


def test_freeze_source_directory_cannot_be_output(tmp_path):
    frozen,_=fake_freeze(tmp_path)
    with pytest.raises(stage.StageError,match="independent"):
        stage.path_guard(frozen,frozen,True)
    with pytest.raises(stage.StageError,match="inside frozen"):
        stage.path_guard(frozen,frozen/"new_output",True)


def test_stage_never_has_jtag_firmware_or_dataset_actions():
    source=(ROOT/"scripts/p07_b4l1_stage_frozen_27core.py").read_text()
    assert "from loihi_twin_v2.p06_b24_freeze import verify_frozen_directory" in source
    assert "source_manifest_file_sha256" in source
    assert "official_mnist_test" in source
    assert "physical_ddr_staged" in source
    assert "subprocess" not in source
    assert "xsdb" not in source.lower()
    assert "vivado" not in source.lower()
    assert "torch." not in source
