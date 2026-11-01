"""B5.4 final acceptance unit tests: mocked receipts are NEVER board proof.

The production B5.4 reviewer reopens original V3 0/1/2/0 and the distinct
840320B genuine B5 RAW physical session. These pure native tests only prove
the closeout policy and signoff gates reject missing/false attestations.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b5_final_acceptance as final

def mock_args(tmp_path,mode="review"):
    files=[]
    for n,x in enumerate([0,1,2,0]):
        p=tmp_path/f"v3_run{n}"
        p.mkdir()
        files.append(f"{x}:{p}")
    raw=tmp_path/"NEW_physical_B5_raw0"
    raw.mkdir()
    orig=tmp_path/"original_fourrun.json"
    raw_report=tmp_path/"independent_raw.json"
    orig.write_text("{}\n")
    raw_report.write_text("{}\n")
    return SimpleNamespace(
        mode=mode,frozen_dir=tmp_path/"freeze",
        staged_dir=tmp_path/"signed_original_27core",
        routes_dir=tmp_path/"signed_original_training_routes",
        build_dir=tmp_path/"new_elf",
        reports=tmp_path/"P03_original_bitstream",
        offline_report=tmp_path/"new_real_elf_map_admission.json",
        raw_evidence=raw,raw_report=raw_report,fourrun_report=orig,
        run=files,attestation=None,confirm_final_acceptance=None,
    )

def fake_four(args):
    return {
        "genuine_independently_verified_sessions":4,
        "distinct_train_validation_frames":3,
        "required_ordinal_sequence":[0,1,2,0],
        "train0_repeat_physical_metrics_and_FNV64_equal":True,
        "all_independent_fingerprint_gate_conditions_pass":True,
        "P07_B5_final_full_parity_and_acceptance":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    },0

def fake_raw(**kwargs):
    return {
        "schema":"p07-b5-original-raw-physical-by-neuron-authenticated-scalar-gate-v1",
        "original_official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "original_signed_model_modified":False,
        "original_V3_ELF_modified":False,
        "P07_B5_final_acceptance":False,
        "raw_neuron_original_26x1010_bytes_exactly_equal":True,
        "same_session_original_27core_and_route_stage_verified":True,
        "actual_physical_trace_size":840320,
        "physical_raw_trace_sha256":final.PINNED_RAW_SHA,
        "independent_original_raw_trace_sha256":final.PINNED_RAW_SHA,
        "physical_B5_mailbox_sha256":final.PINNED_MAILBOX_SHA,
        "physical_raw_FNV64":final.PINNED_RAW_FNV,
        "new_B5_ELF_sha256":final.PINNED_B5_ELF,
        "new_B5_map_sha256":final.PINNED_B5_MAP,
        "physical_B5_mailbox":{
            "physical_dispatches":702,
            "physical_barriers_acked":26,
            "B5_capture_neurons":26260,
        },
        "physical_per_tick_FNV64":[f"0x{i:016X}" for i in range(26)],
        "independent_scalar_checks":{str(i):True for i in range(7)},
    }

def prepare_unit_evidence(args):
    """This fixture is synthetic and is NEVER asserted to be board evidence."""
    args.fourrun_report.write_text(json.dumps(fake_four(None)[0])+"\n")
    args.raw_report.write_text(json.dumps(fake_raw())+"\n")

def mock_signed_review(args,monkeypatch):
    prepare_unit_evidence(args)
    monkeypatch.setattr(final.b5,"run",fake_four)
    monkeypatch.setattr(final.raw,"verify_session",fake_raw)

def test_b54_review_reopens_both_signed_physical_sources_and_does_not_auto_accept(tmp_path,monkeypatch):
    a=mock_args(tmp_path)
    mock_signed_review(a,monkeypatch)
    out=final.closeout(a)
    assert out["all_required_B5_numerical_gates_pass"] is True
    assert out["genuine_original_V3_27core_physical_sessions"]==4
    assert out["genuine_new_B5_raw_26tick_physical_sessions"]==1
    assert out["B5_RAW_physical_neuron_records"]==26260
    assert out["B5_RAW_physical_840320_bytes_exactly_equal_original_scalar"] is True
    assert out["operator_attested_cold_boot_and_recovery_all_five_sessions"] is False
    assert out["operator_explicit_final_B5_acceptance"] is False
    assert out["P07_B5_final_acceptance"] is False
    assert out["boot_firmware_and_other_DDR_owner_independently_proven"] is False
    assert out["packet_level_every_word_numerical_parity_independently_proven"] is False
    assert out["main_merged"] is False
    assert out["board_contact_this_PC_reviewer"] is False

@pytest.mark.parametrize("indices",[(0,1,2),(0,1,2,2),(0,1,0,2),(0,1,2,0,0)])
def test_final_reviewer_refuses_missing_duplicate_or_out_of_order_V3_runs(tmp_path,indices):
    a=mock_args(tmp_path)
    a.run=[f"{x}:{tmp_path}/run_{i}" for i,x in enumerate(indices)]
    with pytest.raises(ValueError,match="four original V3 runs"):
        final.ordered_runs(a)

def test_final_reviewer_refuses_reused_B5_raw_evidence(tmp_path):
    a=mock_args(tmp_path)
    a.raw_evidence=Path(a.run[0].partition(":")[2])
    with pytest.raises(ValueError,match="fifth distinct"):
        final.ordered_runs(a)

def test_final_reviewer_requires_existing_unmodified_user_reports(tmp_path,monkeypatch):
    a=mock_args(tmp_path)
    mock_signed_review(a,monkeypatch)
    a.raw_report.write_text("{}\n")
    with pytest.raises(ValueError,match="raw-neuron report differs"):
        final.closeout(a)

def test_final_reviewer_refuses_bad_real_raw_data_even_if_saved_report_says_pass(tmp_path,monkeypatch):
    a=mock_args(tmp_path)
    mock_signed_review(a,monkeypatch)
    broken=fake_raw()
    broken["physical_raw_trace_sha256"]="0"*64
    monkeypatch.setattr(final.raw,"verify_session",lambda **kw:broken)
    with pytest.raises(ValueError,match="strict original B5 physical RAW"):
        final.closeout(a)

def make_attestation(args):
    locations=[Path(part.partition(":")[2]).resolve() for part in args.run]
    locations.append(args.raw_evidence.resolve())
    return {
        "schema":final.ATTEST_SCHEMA,
        "sessions":[{
            "evidence_dir":str(folder),
            "ordinal":[0,1,2,0,0][i],
            "fresh_cold_power_cycle_before":True,
            "cold_power_cycle_after":True,
            "dedicated_JTAG_ownership":True,
            "no_resume_of_halted_Linux":True,
        } for i,folder in enumerate(locations)],
        "understands_original_boot_firmware_DDR_exclusivity_UNPROVEN":True,
        "understands_B5_raw_sidecar_mailbox_DDR_ownership_UNPROVEN":True,
        "accepts_documented_residual_destructive_DDR_risks":True,
        "operator_independently_rechecked_B5_2_and_B5_3_evidence":True,
        "explicitly_accepts_P07_B5_bounded_numerical_completion":True,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }

def save_attest(args,data):
    path=args.raw_evidence.parent/"user_attestation.json"
    path.write_text(json.dumps(data)+"\n")
    args.attestation=path
    return path

def test_accept_mode_requires_separate_operator_attestation_even_with_five_numerical_passes(tmp_path,monkeypatch):
    a=mock_args(tmp_path,mode="accept")
    mock_signed_review(a,monkeypatch)
    a.confirm_final_acceptance=final.FINAL_CONFIRM
    with pytest.raises(ValueError,match="operator-signed attestation"):
        final.closeout(a)

@pytest.mark.parametrize("change",[
    lambda d:d["sessions"].pop(),
    lambda d:d["sessions"][3].update({"evidence_dir":d["sessions"][0]["evidence_dir"]}),
    lambda d:d["sessions"][1].update({"fresh_cold_power_cycle_before":False}),
    lambda d:d["sessions"][4].update({"cold_power_cycle_after":False}),
    lambda d:d["sessions"][2].update({"dedicated_JTAG_ownership":False}),
    lambda d:d["sessions"][0].update({"no_resume_of_halted_Linux":False}),
    lambda d:d.update({"understands_original_boot_firmware_DDR_exclusivity_UNPROVEN":False}),
    lambda d:d.update({"understands_B5_raw_sidecar_mailbox_DDR_ownership_UNPROVEN":False}),
    lambda d:d.update({"explicitly_accepts_P07_B5_bounded_numerical_completion":False}),
])
def test_accept_rejects_any_unattested_reboot_source_risk_or_consent(tmp_path,monkeypatch,change):
    a=mock_args(tmp_path,mode="accept")
    mock_signed_review(a,monkeypatch)
    data=make_attestation(a)
    change(data)
    save_attest(a,data)
    a.confirm_final_acceptance=final.FINAL_CONFIRM
    with pytest.raises(ValueError):
        final.closeout(a)

def test_accept_does_not_silently_treat_user_reboot_attestation_as_instrumentation_proof(tmp_path,monkeypatch):
    a=mock_args(tmp_path,mode="accept")
    mock_signed_review(a,monkeypatch)
    save_attest(a,make_attestation(a))
    with pytest.raises(ValueError,match="exact final acceptance command"):
        final.closeout(a)
    a.confirm_final_acceptance=final.FINAL_CONFIRM
    report=final.closeout(a)
    assert report["P07_B5_final_acceptance"] is True
    assert report["operator_attested_cold_boot_and_recovery_all_five_sessions"] is True
    assert report["operator_explicit_final_B5_acceptance"] is True
    assert report["independent_board_powercycle_instrumentation_proof"] is False
    assert report["boot_firmware_and_other_DDR_owner_independently_proven"] is False
    assert report["P07_B6_started"] is False
    assert report["main_merged"] is False

def test_operator_attestation_template_does_not_invent_cold_powercycles():
    template=json.loads(
        (ROOT/"docs/P07_B5_4_OPERATOR_ATTESTATION_TEMPLATE.json").read_text()
    )
    assert template["schema"]==final.ATTEST_SCHEMA
    assert [x["ordinal"] for x in template["sessions"]]==[0,1,2,0,0]
    for session in template["sessions"]:
        for key in ("fresh_cold_power_cycle_before",
                    "cold_power_cycle_after","dedicated_JTAG_ownership",
                    "no_resume_of_halted_Linux"):
            assert session[key] is None
    for key in (
        "understands_original_boot_firmware_DDR_exclusivity_UNPROVEN",
        "understands_B5_raw_sidecar_mailbox_DDR_ownership_UNPROVEN",
        "accepts_documented_residual_destructive_DDR_risks",
        "operator_independently_rechecked_B5_2_and_B5_3_evidence",
        "explicitly_accepts_P07_B5_bounded_numerical_completion",
    ):
        assert template[key] is None


def test_code_never_contacts_KV260_writes_source_or_changes_TEST():
    source=(ROOT/"scripts/p07_b5_final_acceptance.py").read_text()
    assert 'mode="consolidate"' in source
    assert "raw.verify_session(" in source
    assert "verify_immutable_user_report(" in source
    assert 'if args.mode=="review"' in source
    assert "P07_B5_final_acceptance" in source
    assert 'main_merged":False' in source
    assert "xsdb" not in source.lower()
    assert "subprocess" not in source
    assert "SEALED_NOT_ACCESSED" in source
