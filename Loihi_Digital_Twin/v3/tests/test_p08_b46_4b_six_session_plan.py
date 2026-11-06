"""P08-B4.6.4b native synthetic-only source/evidence and no-JTAG gates."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import p08_b46_4b_six_session_plan as gate


def save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


@pytest.fixture
def sources(tmp_path, monkeypatch):
    paths = {
        "boundary": tmp_path / "boundary.json",
        "matched_source": tmp_path / "matched_source.json",
        "a_prior_independent": tmp_path / "a_prior.json",
        "b_prior_independent": tmp_path / "b_prior.json",
        "a_rebuilt_elf": tmp_path / "p08_a2_board.elf",
        "b_auth_once_elf": tmp_path / "p08_b45_perf_once_full1024.elf",
    }
    schedule = []
    for i, arm in enumerate(gate.ORDER):
        schedule.append({
            "sequence_number": i + 1, "pair": i // 2 + 1,
            "arm": ("A_REBUILT_A21_CANDIDATE_42_NEURONS_26_DISPATCHES"
                    if arm == "A" else gate.B_ARM),
            "fresh_coldboot_required": True,
            "individual_physical_JTAG_permission_granted": False,
            "new_signed_physical_capture_accepted": False,
        })
    save(paths["boundary"], {
        "schema":gate.BOUNDARY_SCHEMA, "source_only_static_audit_pass":True,
        "both_broad_entry_to_neural_journal_commit_scope_present":True,
        "A_B_physical_timer_boundary_equivalence_proven":False,
        "new_A_B_physical_sessions_performed":False,
        "new_six_session_hardware_authorization_granted":False,
        "prior_A21_standalone_run_is_one_of_six_future_counterbalanced_sessions":False,
        "rebuilt_A21_new_accepted_ELF_SHA256":"AELF",
        "prior_A21_rebuilt_one_1024_physical_report_SHA256":"APRIOR",
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    })
    save(paths["matched_source"], {
        "schema":gate.SOURCE_SCHEMA,"selected_A_real_elf_sha256":"AELF",
        "optimized_B_once_full1024_elf_sha256":"BELF",
        "identical_original_TRAIN_1024_source_index_and_raw_pixel_SHA":True,
        "frame_count_each":1024,"ordinary_frames_each":1023,
        "excluded_trace_ordinal":1023,
        "planned_six_independently_rebooted_sessions":schedule,
        "six_new_physical_JTAG_runs_authorized":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    })
    save(paths["a_prior_independent"], {
        "schema":gate.A_SCHEMA,
        "new_rebuilt_A2_1_distinct_ELF_SHA256":"AELF",
        "original_P07_all_1024_independent_packed_neural_oracle":"PASS",
        "original_P07_selected_26x42_neural_trace":"EXACT",
        "new_A53_image_sidecar_crc_and_cntfrq":"PASS",
        "ordinary_frames":1023,
        "special_trace_ordinal_excluded":1023,
        "new_A_candidate_physically_revalidated_for_THIS_1024_session":True,
        "old_original_historical_A21_ELF_reproduced":False,
        "A_vs_B_auth_once_service_timer_boundaries_matched":False,
        "B46_six_repeated_A_B_auth_once_sessions_accepted":False,
        "original_A53_observed_CNTFRQ_EL0_hz":99999001,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    })
    save(paths["b_prior_independent"], {
        "schema":gate.B_SCHEMA, "experiment":"once",
        "genuine_new_mode_specific_A53_ELF_sha256":"BELF",
        "new_all_1024_original_classifier_spikes_26tick_FNV_equal_scalar":True,
        "new_all_1024_A53_timing_and_reset_profiles_valid":True,
        "new_all_27_post_run_backup_records_identical_to_original":True,
        "last_trace_ordinal_1023_excluded_from_ordinary_performance":True,
        "hardware_DDR_backup_protection_proven":False,
        "paired_AB_BA_AB_six_session_speedup_not_established":True,
        "actual_A53_CNTFRQ_hz":99999001,
        "whole_image_service_descriptive_1023":{"ordinary_frames":1023},
        "original_OFFICIAL_MNIST_TEST":"SEALED_NOT_ACCESSED",
    })
    paths["a_rebuilt_elf"].write_bytes(gate.A_MARKER + b"\0synthetic fixture A")
    paths["b_auth_once_elf"].write_bytes(gate.B_MARKER + b"\0synthetic fixture B")
    sha = lambda name: hashlib.sha256(paths[name].read_bytes()).hexdigest()
    pins = {key:sha(key) for key in paths}
    monkeypatch.setattr(gate,"PINS",pins)
    # Preserve referencing synthetic SHA pins, WITHOUT mocking true oracle/CI.
    for label, key, target in (
        ("a_prior_independent","new_rebuilt_A2_1_distinct_ELF_SHA256","a_rebuilt_elf"),
        ("b_prior_independent","genuine_new_mode_specific_A53_ELF_sha256","b_auth_once_elf"),
        ("boundary","rebuilt_A21_new_accepted_ELF_SHA256","a_rebuilt_elf"),
        ("boundary","prior_A21_rebuilt_one_1024_physical_report_SHA256","a_prior_independent"),
        ("matched_source","selected_A_real_elf_sha256","a_rebuilt_elf"),
        ("matched_source","optimized_B_once_full1024_elf_sha256","b_auth_once_elf"),
    ):
        doc = json.loads(paths[label].read_text())
        doc[key] = sha(target)
        save(paths[label],doc)
    monkeypatch.setattr(gate,"PINS",{key:sha(key) for key in paths})
    return paths


def run(sources):
    return gate.prepare(
        sources["boundary"],sources["matched_source"],
        sources["a_prior_independent"],sources["b_prior_independent"],
        sources["a_rebuilt_elf"],sources["b_auth_once_elf"])


def repin(sources, monkeypatch):
    monkeypatch.setattr(gate, "PINS", {
        key:hashlib.sha256(path.read_bytes()).hexdigest()
        for key,path in sources.items()})


def test_real_protocol_shape_is_six_new_discrete_coldboots(sources):
    result = run(sources)
    slots = result["proposed_six_slots"]
    assert result["schema"] == gate.SCHEMA
    assert len(slots) == 6
    assert [s["pair"] for s in slots] == [1,1,2,2,3,3]
    assert [s["arm"] == gate.A_ARM for s in slots] == [True,False,False,True,True,False]
    assert result["accepted_old_standalone_sessions_count_toward_NEW_ABBAAB"] == 0
    assert result["all_new_session_authorizations_granted"] is False
    assert result["any_new_B46_AB_physical_session_executed"] is False
    assert result["paired_study_statistics_accepted"] is False
    assert all(not s["new_independently_accepted_session_receipt"] and
               not s["operator_specific_destructive_approval_granted"]
               for s in slots)
    assert result["official_MNIST_TEST"] == "SEALED_NOT_ACCESSED"


@pytest.mark.parametrize("key",list(gate.PINS))
def test_any_previous_acceptance_source_digest_tampering_rejected(sources,key):
    target=sources[key]
    target.write_bytes(target.read_bytes()+b"\0modified")
    with pytest.raises(gate.StudyNoGo,match="original signed SHA drift"):
        run(sources)


@pytest.mark.parametrize("key,field,value,why",[
    ("boundary","new_six_session_hardware_authorization_granted",True,"static boundary"),
    ("matched_source","identical_original_TRAIN_1024_source_index_and_raw_pixel_SHA",False,"matched TRAIN"),
    ("a_prior_independent","new_A_candidate_physically_revalidated_for_THIS_1024_session",False,"prior independent"),
    ("b_prior_independent","hardware_DDR_backup_protection_proven",True,"B4.5 V2"),
    ("b_prior_independent","experiment","unchecked","B4.5 V2"),
    ("a_prior_independent","B46_six_repeated_A_B_auth_once_sessions_accepted",True,"prior independent"),
])
def test_false_frozen_physical_claims_rejected_even_if_digests_replaced(
        sources,monkeypatch,key,field,value,why):
    doc=json.loads(sources[key].read_text())
    doc[field]=value
    save(sources[key],doc)
    if key == "a_prior_independent":
        boundary=json.loads(sources["boundary"].read_text())
        boundary["prior_A21_rebuilt_one_1024_physical_report_SHA256"] = (
            hashlib.sha256(sources[key].read_bytes()).hexdigest())
        save(sources["boundary"],boundary)
    repin(sources,monkeypatch)
    with pytest.raises(gate.StudyNoGo,match=why):
        run(sources)


def test_pre_registered_session_order_cannot_be_swapped(sources,monkeypatch):
    doc=json.loads(sources["matched_source"].read_text())
    doc["planned_six_independently_rebooted_sessions"][0]["arm"]=gate.B_ARM
    save(sources["matched_source"],doc)
    repin(sources,monkeypatch)
    with pytest.raises(gate.StudyNoGo,match="six-slot counterbalance"):
        run(sources)


def test_wrong_B_elf_identity_rejected_even_if_re_pinned(sources,monkeypatch):
    sources["b_auth_once_elf"].write_bytes(gate.B_BAD_MARKER)
    repin(sources,monkeypatch)
    # Update signed cross-references to match newly pinned (invalid) ELF.
    for key,field in (("matched_source","optimized_B_once_full1024_elf_sha256"),
                      ("b_prior_independent","genuine_new_mode_specific_A53_ELF_sha256")):
        doc=json.loads(sources[key].read_text())
        doc[field]=gate.PINS["b_auth_once_elf"]
        save(sources[key],doc)
    repin(sources,monkeypatch)
    with pytest.raises(gate.StudyNoGo,match="must be genuine V2 authenticate-once"):
        run(sources)


def test_no_evidence_overwrite_or_volatile_output(sources):
    report=run(sources)
    with pytest.raises(gate.StudyNoGo,match="durable study plan"):
        gate.write_plan(report,Path("/tmp/b46_synthetic_plan.json"),ROOT)
    # HOME temp is allowed ONLY for disposable synthetic test fixtures.
    with TemporaryDirectory(prefix="b46_fixture_",dir=Path.home()) as folder:
        out=Path(folder)/"study_plan.json"
        gate.write_plan(report,out,ROOT)
        assert json.loads(out.read_text()) == report
        with pytest.raises(gate.StudyNoGo,match="no-overwrite"):
            gate.write_plan(report,out,ROOT)


def test_never_launch_or_grant_a_destructive_jtag_operation():
    text=(ROOT/"scripts"/"p08_b46_4b_six_session_plan.py").read_text()
    for dangerous in ("import subprocess","subprocess.run(","os.system(","xsdb ","vivado -mode",
                      "P08_B46_CONFIRM_OVERWRITE_ORIGINAL_64M_DDR=YES"):
        assert dangerous not in text
    assert '"all_new_session_authorizations_granted": False' in text


def test_B_original_independent_verifier_schema_contract_not_guessed():
    # The B4.5 independent verifier creates the ACCEPTED real JSON.
    # It uses ordinary_frames (not the *preliminary* report's
    # ordinary_frame_count). Keep both B4.6 gates aligned to its output.
    original=(ROOT/"scripts"/"p08_b45_perf_full1024_independent_verify.py").read_text()
    plan_source=(ROOT/"scripts"/"p08_b46_4b_six_session_plan.py").read_text()
    receipt_source=(ROOT/"scripts"/"p08_b46_4b_session_receipt.py").read_text()
    assert 'return {"ordinary_frames":1023' in original
    assert '"whole_image_service_descriptive_1023":service_summary' in original
    assert '.get("ordinary_frames") == 1023' in plan_source
    assert 'service.get("ordinary_frames") == 1023' in receipt_source
    assert 'ordinary_frame_count' not in plan_source
