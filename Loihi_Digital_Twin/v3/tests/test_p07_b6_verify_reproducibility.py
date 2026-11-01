"""B6.2 portable independent SHA audit of copied handoff (SYNTHETIC tests)."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b6_verify_reproducibility as verify
import p07_b6_reproducibility_bundle as pack

def build_synthetic(tmp_path,monkeypatch):
    root=tmp_path/"portable_B6_bundle";root.mkdir()
    files={}
    def add(name,data):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(data)
        files[name]={"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)}
    for i in range(33):
        add(f"source/original_b24/synthetic_file_{i:02d}.bin",bytes([i]))
    add("source/original_b24/frozen_manifest.json",b"fake synthetic frozen B24")
    add("source/new_B5_A53/p07_b5_raw_trace_v1.elf",b"fake new B5 ELF")
    add("source/new_B5_A53/p07_b5_raw_trace_v1.map",b"fake new B5 map")
    add("source/original_P03_XSA/p03_2_ps_mmio.xsa",b"fake P03 XSA")
    add("firmware/original_V3_A53_accepted.elf",b"fake original V3 ELF")
    add("firmware/original_V3_A53_accepted.map",b"fake original V3 map")
    for i in range(4):
        add(f"physical_evidence/original_V3_{i}/fake_board.bin",
            f"NOT_REAL_BOARD_SESSION_{i}".encode())
    raw_bytes=bytes(840320)
    add("physical_evidence/RAW0/b5_raw_physical_trace_840320.bin",raw_bytes)
    add("physical_evidence/RAW0/physical_mailbox.bin",b"synthetic only")
    add("acceptance/B5_4_user_accepted.json",json.dumps({
        "P07_B5_final_acceptance":True,
        "operator_attested_cold_boot_and_recovery_all_five_sessions":True,
        "operator_explicit_final_B5_acceptance":True,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "B5_RAW_physical_trace_SHA256":hashlib.sha256(raw_bytes).hexdigest(),
        "boot_firmware_and_other_DDR_owner_independently_proven":False,
    }).encode())
    add("acceptance/B5_4_operator_attestation.json",b"synthetic not actual attestation")
    add("acceptance/B6_1_accepted_source_freeze.json",b"synthetic not actual seal")
    for path,attribute,module in [
        ("physical_evidence/RAW0/b5_raw_physical_trace_840320.bin","RAW_SHA",verify.b6),
        ("firmware/original_V3_A53_accepted.elf","V3_ELF_SHA",verify.b6),
        ("firmware/original_V3_A53_accepted.map","V3_MAP_SHA",verify.b6),
        ("source/new_B5_A53/p07_b5_raw_trace_v1.elf","ELF_SHA",verify.b6),
        ("source/new_B5_A53/p07_b5_raw_trace_v1.map","MAP_SHA",verify.b6),
        ("source/original_P03_XSA/p03_2_ps_mmio.xsa","P03_XSA_SHA",verify.b6),
        ("source/original_b24/frozen_manifest.json","FROZEN_SHA",verify.b4l1),
    ]:
        monkeypatch.setattr(module,attribute,files[path]["sha256"])
    monkeypatch.setattr(verify.b4l1,"admit_freeze",
        lambda path:{"files_checked":len(list(path.rglob("*.bin")))+1})
    m={
      "schema":pack.SCHEMA,
      "B5_4_real_operator_accepted":True,
      "B6_1_original_hardware_and_sources_signed":True,
      "B6_2_handoff_contains_all_five_board_session_files":True,
      "original_frozen_27core_and_all_routes_copied":True,
      "signed_original_V3_elf_and_map_copied":True,
      "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
      "DDR_owner_exclusivity_independently_proven":False,
      "B6_final_acceptance":False,
      "P07_B_complete":False,
      "main_merged":False,
      "main_only_LitReview_git_blob":verify.lit.EXPECTED_BLOB_SHA,
      "files":files,
    }
    (root/"handoff_manifest.json").write_text(json.dumps(m)+"\n")
    return root

def test_synthetic_complete_SHA_archive_passes_with_explicit_mock_original_freeze(tmp_path,monkeypatch):
    root=build_synthetic(tmp_path,monkeypatch)
    r=verify.verify(root)
    assert r["all_copy_sources_SHA256_and_lengths_independently_verified"] is True
    assert r["original_B24_manifest_and_all_33_assets_independently_admitted"] is True
    assert r["B6_final_acceptance"] is False
    assert r["main_merged"] is False
    assert r["main_current_Git_ref_independently_checked_here"] is False
    assert r["official_MNIST_TEST"]=="SEALED_NOT_ACCESSED"

def test_tampered_raw_archive_file_fails_closed(tmp_path,monkeypatch):
    root=build_synthetic(tmp_path,monkeypatch)
    (root/verify.RAW_FILE).write_bytes(b"fake replaced")
    with pytest.raises(ValueError,match="SHA/size changed"):
        verify.verify(root)

def test_unindexed_added_file_fails_closed(tmp_path,monkeypatch):
    root=build_synthetic(tmp_path,monkeypatch)
    (root/"extra.txt").write_text("not in manifest")
    with pytest.raises(ValueError,match="extra/missing"):
        verify.verify(root)

def test_evidence_symlink_rejected(tmp_path,monkeypatch):
    root=build_synthetic(tmp_path,monkeypatch)
    (root/"new symlink").symlink_to(root/verify.RAW_FILE)
    with pytest.raises(ValueError,match="symlink"):
        verify.verify(root)

def test_attested_B5_acceptance_not_in_bundle_fails(tmp_path,monkeypatch):
    root=build_synthetic(tmp_path,monkeypatch)
    (root/verify.ACCEPT).write_text("{}")
    with pytest.raises(ValueError):
        verify.verify(root)

def test_false_final_acceptance_or_TEST_unseal_markers_fail(tmp_path,monkeypatch):
    root=build_synthetic(tmp_path,monkeypatch)
    manifest=root/"handoff_manifest.json"
    m=json.loads(manifest.read_text());m["official_MNIST_TEST"]="ACCESSED"
    manifest.write_text(json.dumps(m))
    with pytest.raises(ValueError,match="provenance/limitations"):
        verify.verify(root)

def test_no_new_board_execution_or_git_merge():
    s=(ROOT/"scripts/p07_b6_verify_reproducibility.py").read_text()
    assert "b4l1.admit_freeze" in s
    assert "pack.sha" in s
    assert "RAW_FILE" in s and "V3_ELF" in s
    assert "SEALED_NOT_ACCESSED" in s
    assert "subprocess" not in s
    assert "xsdb" not in s.lower()
