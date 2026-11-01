"""B6.1 native host-only original immutable freeze inventory and acceptance gate.

Mock acceptance data deliberately does NOT represent actual board evidence.
Production gate must re-open all genuine B5.4 original physical sessions.
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
import p07_b6_freeze_manifest as b6
import p07_b5_final_acceptance as b5

def args(tmp_path,mode="inventory"):
    r=tmp_path/"numerical_review.json"
    r.write_text(json.dumps({"schema":b5.SCHEMA})+"\n")
    return SimpleNamespace(
        mode=mode,b5_review=r,
        frozen_dir=tmp_path/"no_fake_frozen",
        staged_dir=tmp_path/"no_fake_signed_contexts",
        routes_dir=tmp_path/"no_fake_routes",
        build_dir=tmp_path/"no_fake_elf",
        reports=tmp_path/"no_fake_P03",
        offline_report=tmp_path/"no_fake_offline.json",
        b5_acceptance=None,attestation=None,
        fourrun_report=tmp_path/"fourrun.json",
        raw_evidence=tmp_path/"raw_physical",
        raw_report=tmp_path/"raw_report.json",
        run=[],
    )

def mock_review(tmp_path):
    return {
        "original_4run_report_sha256":"a"*64,
        "B5_RAW_independent_report_sha256":"b"*64,
        "original_V3_evidence_dirs":[str(tmp_path/f"run_{i}") for i in range(4)],
        "B5_RAW_physical_evidence_dir":str(tmp_path/"raw_physical"),
    }

def mock_sources():
    return {
        "source_sha256_manifest":{"original_b24/frozen_manifest.json":"d"*64},
        "immutable_original_B24_33_file_freeze_verified":True,
        "original_27_logical_core_count":27,
    }

def prep(a,monkeypatch):
    monkeypatch.setattr(b6,"verify_b5_review",lambda _:mock_review(a.b5_review.parent))
    monkeypatch.setattr(b6,"validate_source_freeze",lambda _:mock_sources())

def test_B6_candidate_inventory_does_not_close_or_merge_or_open_TEST(tmp_path,monkeypatch):
    a=args(tmp_path)
    prep(a,monkeypatch)
    receipt=b6.build_inventory(a)
    assert receipt["mode"]=="inventory"
    assert receipt["B6_1_host_only_freeze_inventory_completed"] is True
    assert receipt["B5_formal_operator_acceptance_verified"] is False
    assert receipt["B6_final_hardware_freeze_accepted"] is False
    assert receipt["P07_B_complete"] is False
    assert receipt["main_merged"] is False
    assert receipt["official_MNIST_TEST"]=="SEALED_NOT_ACCESSED"
    assert receipt["boot_firmware_DDR_exclusivity_independently_proven"] is False
    assert receipt["main_only_LitReview_md_unchanged_verified_by_this_PC_tool"] is False
    assert receipt["main_only_LitReview_md_expected_blob_SHA"]=="3c45d0a0d0b55378d3564d8f82282803a8eb1a3e"

def test_B6_actual_candidate_with_no_real_frozen_assets_rejected(tmp_path):
    a=args(tmp_path)
    with pytest.raises((ValueError,OSError)):
        b6.build_inventory(a)

def test_B6_inventory_rejects_acceptance_or_session_override(tmp_path,monkeypatch):
    a=args(tmp_path)
    prep(a,monkeypatch)
    a.attestation=tmp_path/"fake.json"
    with pytest.raises(ValueError,match="must not silently"):
        b6.build_inventory(a)

def test_B6_seal_requires_user_physical_acceptance_and_all_five_sessions(tmp_path,monkeypatch):
    a=args(tmp_path,"seal")
    prep(a,monkeypatch)
    with pytest.raises(ValueError,match="requires exact operator-created"):
        b6.build_inventory(a)

def test_B6_seal_rechecks_real_B5_receipt_again_and_rejects_forged_boolean(tmp_path,monkeypatch):
    a=args(tmp_path,"seal")
    prep(a,monkeypatch)
    a.attestation=tmp_path/"attest.json"
    a.attestation.write_text("{}\n")
    a.b5_acceptance=tmp_path/"accepted.json"
    a.run=[f"{i}:{tmp_path}/fake_{i}" for i in [0,1,2,0]]
    fake_accept={"mode":"accept","P07_B5_final_acceptance":True,
                 "operator_attested_cold_boot_and_recovery_all_five_sessions":True,
                 "operator_explicit_final_B5_acceptance":True,
                 "boot_firmware_and_other_DDR_owner_independently_proven":False,
                 "independent_board_powercycle_instrumentation_proof":False}
    a.b5_acceptance.write_text(json.dumps(fake_accept)+"\n")
    replay_calls=[]
    def replay(real):
        replay_calls.append(real)
        assert real.mode=="accept" and real.attestation==a.attestation
        assert real.confirm_final_acceptance==b5.FINAL_CONFIRM
        return fake_accept
    monkeypatch.setattr(b6.b54,"closeout",replay)
    with pytest.raises(ValueError,match="operator attestation must identify five"):
        b6.build_inventory(a)
    assert len(replay_calls)==1
    a.attestation.write_text(json.dumps({
       "sessions":[
          {"evidence_dir":str(tmp_path/f"run_{i}")}
          for i in range(4)
       ]+[{"evidence_dir":str(tmp_path/"raw_physical")}]
    })+"\n")
    sealed=b6.build_inventory(a)
    assert sealed["B5_formal_operator_acceptance_verified"] is True
    assert sealed["B6_final_hardware_freeze_accepted"] is False
    assert sealed["P07_B_complete"] is False
    assert sealed["main_merged"] is False
    assert len(sealed["operator_accepted_B5_4_report_SHA256"])==64

def test_B6_seal_rejects_patched_acceptance_json_even_if_claims_true(tmp_path,monkeypatch):
    a=args(tmp_path,"seal")
    prep(a,monkeypatch)
    a.attestation=tmp_path/"attest.json"
    a.attestation.write_text("{}")
    a.b5_acceptance=tmp_path/"accepted.json"
    a.b5_acceptance.write_text(json.dumps({"P07_B5_final_acceptance":True})+"\n")
    a.run=[f"{i}:{tmp_path}/fake_{i}" for i in [0,1,2,0]]
    monkeypatch.setattr(b6.b54,"closeout",lambda _:{"P07_B5_final_acceptance":False})
    with pytest.raises(ValueError,match="does not match independent"):
        b6.build_inventory(a)

def test_B6_source_sha_gate_symlink_and_mutation_protection(tmp_path):
    file=tmp_path/"real.bin"
    file.write_bytes(b"original immutable real world bytes")
    sha=b6.sha_regular(file)
    assert sha==hashlib.sha256(b"original immutable real world bytes").hexdigest()
    link=tmp_path/"symlink"
    link.symlink_to(file)
    with pytest.raises(ValueError,match="symlinked"):
        b6.sha_regular(link)
    file.write_bytes(b"mutated")
    assert b6.sha_regular(file)!=sha

def test_B6_original_no_FPGA_TOOL_no_git_merge_or_OFFICIAL_TEST():
    source=(ROOT/"scripts/p07_b6_freeze_manifest.py").read_text()
    assert "b4l1.admit_freeze" in source
    assert "routes_gate.require_routes" in source
    assert "raw_gate.admit" in source
    assert "b54.closeout" in source
    assert "P07_B_complete" in source
    assert "main_merged" in source
    assert "SEALED_NOT_ACCESSED" in source
    assert "subprocess" not in source
    assert "xsdb" not in source.lower()
    assert "merge_pull_request" not in source
