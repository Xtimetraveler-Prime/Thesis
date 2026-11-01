"""B6.2 host-only reproducible evidence copy/integrity safety tests.

All file contents below are SYNTHETIC. No test data is a true KV260 board
record or original B2.4 frozen training asset. The real packager must obtain
its inputs from independently accepted physical B5/B6 evidence.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b6_reproducibility_bundle as pkg

def sha(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()

def create_synthetic(tmp_path,monkeypatch):
    directories={}
    for name in ("frozen","routes","reports","build","acceptance"):
        p=tmp_path/name;p.mkdir();directories[name]=p
    b5=directories["build"]/"vitis_workspace";b5.mkdir()
    blobs={
        "original_b24/frozen_manifest.json":b"synthetic original training proof",
        "original_TRAIN_routes/route_table.bin":b"synthetic routing evidence",
        "original_P03_XSA/p03_2_ps_mmio.xsa":b"synthetic P03 XSA NOT REAL",
        "new_B5_A53/p07_b5_raw_trace_v1.elf":b"synthetic new firmware NOT REAL",
    }
    roots={
        "original_b24":directories["frozen"],
        "original_TRAIN_routes":directories["routes"],
        "original_P03_XSA":directories["reports"],
        "new_B5_A53":b5,
    }
    for name,raw in blobs.items():
        p=roots[name.split("/")[0]]/name.split("/",1)[1]
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(raw)
    v3_elf=tmp_path/"v3.elf";v3_map=tmp_path/"v3.map"
    v3_elf.write_bytes(b"synthetic old V3 ELF")
    v3_map.write_bytes(b"synthetic old V3 GNU linker MAP")
    monkeypatch.setattr(pkg.b6,"V3_ELF_SHA",sha(v3_elf.read_bytes()))
    monkeypatch.setattr(pkg.b6,"V3_MAP_SHA",sha(v3_map.read_bytes()))
    accepted=directories["acceptance"]/"B5_4_accepted.json"
    accepted.write_text('{"B5_4": "SYNTHETIC_ONLY"}\n')
    attested=directories["acceptance"]/"operator_attestation.json"
    attested.write_text('{"5 cold boots": "SYNTHETIC_ONLY"}\n')
    sealed=directories["acceptance"]/"b6_seal.json"
    sealed.write_text('{"B6_1": "SYNTHETIC_ONLY"}\n')
    evidence=[]
    for n in range(5):
        d=tmp_path/f"physical_{n}";d.mkdir()
        (d/"physical_receipt.bin").write_bytes(b"SYNTHETIC fake physical "+bytes([n]))
        evidence.append(d)
    args=SimpleNamespace(
        out_dir=tmp_path/"new_complete_bundle",
        seal=sealed,accept=accepted,attest=attested,
        frozen_dir=directories["frozen"],routes_dir=directories["routes"],
        build_dir=directories["build"],reports=directories["reports"],
        v3_elf=v3_elf,v3_map=v3_map,
    )
    document={
        "source_sha256_manifest":{k:sha(v) for k,v in blobs.items()},
        "operator_original_physical_V3_evidence_dirs":[str(x) for x in evidence[:4]],
        "operator_original_physical_RAW_evidence_dir":str(evidence[4]),
    }
    monkeypatch.setattr(pkg,"validate_sealed_inputs",
        lambda a:(document,{
            "checked_main_tree_literature_blob_sha":pkg.lit.EXPECTED_BLOB_SHA,
        }))
    return args,document,blobs

def test_complete_new_external_copy_and_exact_SHA256_rehash(tmp_path,monkeypatch):
    a,document,blobs=create_synthetic(tmp_path,monkeypatch)
    receipt=pkg.bundle(a)
    manifest=a.out_dir/"handoff_manifest.json"
    assert manifest.is_file()
    assert json.loads(manifest.read_text())==receipt
    assert receipt["B6_final_acceptance"] is False
    assert receipt["P07_B_complete"] is False
    assert receipt["main_merged"] is False
    assert receipt["DDR_owner_exclusivity_independently_proven"] is False
    assert receipt["official_MNIST_TEST"]=="SEALED_NOT_ACCESSED"
    assert receipt["B6_2_handoff_contains_all_five_board_session_files"] is True
    assert receipt["main_only_LitReview_git_blob"]==pkg.lit.EXPECTED_BLOB_SHA
    for name,rec in receipt["files"].items():
        copied=a.out_dir/name
        assert copied.is_file()
        assert pkg.sha(copied)==rec["sha256"]
        assert copied.stat().st_size==rec["bytes"]
    assert len(receipt["files"])==4+2+3+5

def test_realistic_new_external_package_sibling_of_original_operator_seal_is_allowed(tmp_path,monkeypatch):
    a,_,_=create_synthetic(tmp_path,monkeypatch)
    # Operator instructions place new immutable report/package siblings in
    # ~/Thesis_Evidence, not inside an original five-session evidence tree.
    a.out_dir=a.seal.parent/"brand_new_B6_package"
    assert a.seal.parent==a.accept.parent
    receipt=pkg.bundle(a)
    assert (a.out_dir/"handoff_manifest.json").exists()
    assert receipt["P07_B_complete"] is False


def test_existing_output_never_overwritten(tmp_path,monkeypatch):
    a,_,_=create_synthetic(tmp_path,monkeypatch)
    a.out_dir.mkdir()
    marker=a.out_dir/"keep.me"
    marker.write_text("original")
    with pytest.raises(ValueError,match="new external output"):
        pkg.bundle(a)
    assert marker.read_text()=="original"

def test_tampered_signed_source_prevents_any_external_package(tmp_path,monkeypatch):
    a,_,_=create_synthetic(tmp_path,monkeypatch)
    (a.frozen_dir/"frozen_manifest.json").write_text("tampered")
    with pytest.raises(ValueError,match="changed after B6.1 seal"):
        pkg.bundle(a)
    assert not a.out_dir.exists()

def test_tampered_old_V3_ELF_prevents_copy(tmp_path,monkeypatch):
    a,_,_=create_synthetic(tmp_path,monkeypatch)
    a.v3_elf.write_bytes(b"forged")
    with pytest.raises(ValueError,match="accepted original physical V3"):
        pkg.bundle(a)
    assert not a.out_dir.exists()

def test_symlink_in_physical_evidence_is_rejected(tmp_path,monkeypatch):
    a,doc,_=create_synthetic(tmp_path,monkeypatch)
    src=Path(doc["operator_original_physical_V3_evidence_dirs"][0])
    (src/"escape").symlink_to(a.v3_elf)
    with pytest.raises(ValueError,match="contains symlink"):
        pkg.bundle(a)
    assert not a.out_dir.exists()

@pytest.mark.parametrize("relative",[
    "", "../evil", "first/../evil","/absolute","first//second",
    "C:\\windows", "bad/./file",
])
def test_reject_traversal_and_malformed_relative_source_key(relative):
    with pytest.raises(ValueError):
        pkg.validate_relative(relative)

def test_signature_approval_is_not_self_declared_by_unaccepted_JSON(tmp_path):
    a=SimpleNamespace(
        seal=tmp_path/"fake_seal.json",accept=tmp_path/"fake_accept.json",
        attest=tmp_path/"fake_attest.json",v3_elf=tmp_path/"no_real_v3",
        v3_map=tmp_path/"no_real_map",
    )
    for path in (a.seal,a.accept,a.attest):
        path.write_text("{}\n")
    with pytest.raises(ValueError,match="genuine separately approved"):
        pkg.validate_sealed_inputs(a)

def test_packager_no_board_official_TEST_or_merge():
    source=(ROOT/"scripts/p07_b6_reproducibility_bundle.py").read_text()
    assert "shutil.copyfileobj" in source
    assert "b6.V3_ELF_SHA" in source
    assert "origin/main" in source
    assert "main_merged" in source
    assert "SEALED_NOT_ACCESSED" in source
    assert "xsdb" not in source.lower()
    assert "subprocess" not in source.lower()
