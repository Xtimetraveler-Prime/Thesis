"""P07-B6.3 native test policy for strict PC-only final P07-B handoff.

All synthetic source outputs here are mocked, NEVER evidence of real
KV260 original board execution. Only actual operator files and
independent B6.2 archive re-read can satisfy production acceptance.
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
import p07_b6_final_handoff as b63

def fixture(tmp_path,monkeypatch,mode="review"):
    archive=tmp_path/"bundle"
    archive.mkdir()
    a=SimpleNamespace(
        mode=mode,seal=tmp_path/"B6_1_seal.json",
        b5_accept=tmp_path/"B5_4_accepted.json",
        bundle_audit=tmp_path/"B6_2_audit.json",
        package=archive,confirm_final_acceptance=None,
    )
    b63.B5_ACCEPT_SHA=hashlib.sha256(b"FAKE operator B5 receipt").hexdigest()
    a.b5_accept.write_bytes(b"FAKE operator B5 receipt")
    b63.B5_ATTEST_SHA="a"*64
    b63.B5_REVIEW_SHA="b"*64
    seal={
        "schema":b63.freeze.SCHEMA,
        "mode":"seal",
        "B5_formal_operator_acceptance_verified":True,
        "B6_1_host_only_freeze_inventory_completed":True,
        "B6_final_hardware_freeze_accepted":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "operator_accepted_B5_4_report_SHA256":b63.B5_ACCEPT_SHA,
        "operator_attestation_source_SHA256":b63.B5_ATTEST_SHA,
        "operator_original_5run_numerical_review_sha256":b63.B5_REVIEW_SHA,
        "B5_original_five_physical_numerical_validation_pass":True,
        "B5_raw_neuron_bytewise_scalar_parity_pass":True,
        "immutable_original_B24_33_file_freeze_verified":True,
        "original_B24_manifest_entries_individually_SHA256_revalidated":33,
        "P07_B_complete":False,
        "main_merged":False,
    }
    a.seal.write_text(json.dumps(seal)+"\n")
    b5={
       "P07_B5_final_acceptance":True,
       "operator_explicit_final_B5_acceptance":True,
       "operator_attested_cold_boot_and_recovery_all_five_sessions":True,
       "B5_RAW_physical_trace_SHA256":b63.freeze.RAW_SHA,
       "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
       "independent_board_powercycle_instrumentation_proof":False,
       "boot_firmware_and_other_DDR_owner_independently_proven":False,
    }
    monkeypatch.setattr(b63.old,"read_json",
        lambda p: {str(a.b5_accept):b5,str(a.seal):seal,
                   str(a.bundle_audit):{"report":"FAKE"},
                   str(archive/"handoff_manifest.json"):{
                     "files":{
                       "acceptance/B6_1_accepted_source_freeze.json":{"sha256":hashlib.sha256(a.seal.read_bytes()).hexdigest()},
                       "acceptance/B5_4_user_accepted.json":{"sha256":b63.B5_ACCEPT_SHA},
                       "acceptance/B5_4_operator_attestation.json":{"sha256":b63.B5_ATTEST_SHA},
                       "physical_evidence/RAW0/b5_raw_physical_trace_840320.bin":{
                         "bytes":840320,"sha256":b63.freeze.RAW_SHA}
                      },
                      "main_only_LitReview_git_blob":b63.freeze.MAIN_LITERATURE_BLOB_SHA,
                    },
                   str(archive/"acceptance/B6_1_accepted_source_freeze.json"):seal}.get(str(p),{}))
    # fake archive is NOT board; source recheck integration tested separately
    fake={
        "bundle_handoff_manifest_SHA256":"c"*64,
        "all_copy_sources_SHA256_and_lengths_independently_verified":True,
        "original_B24_manifest_and_all_33_assets_independently_admitted":True,
        "B5_formal_five_session_acceptance_archived":True,
        "B6_final_acceptance":False,
        "P07_B_complete":False,
        "main_merged":False,
    }
    monkeypatch.setattr(b63.audit,"verify",lambda p:fake)
    monkeypatch.setattr(b63.bundle,"sha",lambda p:
       b63.B5_ACCEPT_SHA if p==a.b5_accept else
       hashlib.sha256(a.seal.read_bytes()).hexdigest() if p==a.seal else
       "d"*64)
    monkeypatch.setattr(b63.lit,"verify_literature",lambda *args:{
        "checked_main_tree_literature_blob_sha":b63.freeze.MAIN_LITERATURE_BLOB_SHA})
    a.bundle_audit.write_text("{}\n")
    # Patch fake audit source JSON output as actual freshly reverified object
    original=b63.old.read_json
    monkeypatch.setattr(b63.old,"read_json",
        lambda p:fake if p==a.bundle_audit else original(p))
    (archive/"handoff_manifest.json").write_text("{}\n")
    (archive/"acceptance").mkdir()
    (archive/"acceptance/B6_1_accepted_source_freeze.json").write_text("{}\n")
    return a,seal,fake

def test_review_only_is_PC_without_auto_final_acceptance(tmp_path,monkeypatch):
    a,_,_=fixture(tmp_path,monkeypatch)
    receipt=b63.review(a)
    assert receipt["P07_B5_final_operator_acceptance_revalidated"] is True
    assert receipt["P07_B6_2_full_portable_archive_independent_bytewise_verifier_pass"] is True
    assert receipt["P07_B6_final_hardware_freeze_accepted"] is False
    assert receipt["P07_B_complete"] is False
    assert receipt["github_main_merged"] is False
    assert receipt["P08_B_started"] is False
    assert receipt["boot_firmware_and_other_DDR_owner_exclusivity_independently_proven"] is False
    assert receipt["every_individual_packet_word_physically_verified"] is False
    assert receipt["official_MNIST_TEST"]=="SEALED_NOT_ACCESSED"

def test_accept_requires_independent_explicit_consent(tmp_path,monkeypatch):
    a,_,_=fixture(tmp_path,monkeypatch,"accept")
    with pytest.raises(b63.HandoffNoGo,match="separate explicit"):
        b63.review(a)
    a.confirm_final_acceptance=b63.CONFIRM_TOKEN
    report=b63.review(a)
    assert report["P07_B_complete"] is True
    assert report["P07_B6_final_hardware_freeze_accepted"] is True
    assert report["operator_final_P07_B_acceptance"] is True
    assert report["github_main_merged"] is False
    assert report["P08_B_started"] is False

def test_missing_real_external_acceptance_receipt_fails_closed(tmp_path):
    a=SimpleNamespace(
        mode="accept",seal=tmp_path/"no_seal",
        b5_accept=tmp_path/"no_operator_B5",
        bundle_audit=tmp_path/"no_physical_audit",
        package=tmp_path/"no_portable_original_source",
        confirm_final_acceptance=b63.CONFIRM_TOKEN,
    )
    with pytest.raises(b63.HandoffNoGo,match="genuine external"):
        b63.review(a)

def test_drifted_cold_cycle_or_boot_risk_disclosure_rejected(tmp_path,monkeypatch):
    a,_,_=fixture(tmp_path,monkeypatch)
    base=b63.old.read_json
    def mutated(p):
        x=base(p)
        if p==a.b5_accept:
            return dict(x,independent_board_powercycle_instrumentation_proof=True)
        return x
    monkeypatch.setattr(b63.old,"read_json",mutated)
    with pytest.raises(b63.HandoffNoGo,match="scope changed"):
        b63.review(a)

def test_fake_different_copy_sha_fails_archive_acceptance(tmp_path,monkeypatch):
    a,_,_=fixture(tmp_path,monkeypatch)
    base=b63.old.read_json
    def mutated(p):
        x=base(p)
        if p==a.package/"handoff_manifest.json":
            x=json.loads(json.dumps(x))
            x["files"]["acceptance/B6_1_accepted_source_freeze.json"]["sha256"]="0"*64
        return x
    monkeypatch.setattr(b63.old,"read_json",mutated)
    with pytest.raises(b63.HandoffNoGo,match="isn't bound"):
        b63.review(a)

def test_original_lit_review_drift_rejected(tmp_path,monkeypatch):
    a,_,_=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(b63.lit,"verify_literature",lambda *a:{
       "checked_main_tree_literature_blob_sha":"0"*40})
    with pytest.raises(b63.HandoffNoGo,match="no longer byte-identical"):
        b63.review(a)

def test_no_p07_developer_script_can_merge_or_program_board():
    source=(ROOT/"scripts/p07_b6_final_handoff.py").read_text()
    assert 'audit.verify(args.package)' in source
    assert 'lit.verify_literature' in source
    assert 'mode=="review"' in source
    assert "P07_B_complete" in source
    assert "SEALED_NOT_ACCESSED" in source
    assert "subprocess" not in source
    assert "xsdb" not in source.lower()
    # Policy prose may mention future Git merges; this script must not
    # execute any Git commands or subprocesses.
    assert "import subprocess" not in source
    assert 'os.system(' not in source
