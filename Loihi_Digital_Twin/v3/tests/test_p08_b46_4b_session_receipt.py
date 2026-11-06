"""B4.6 sequential evidence admission; synthetic PC-only negative tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
import p08_b46_4b_six_session_plan as plan
import p08_b46_4b_session_receipt as receipt


def save(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, dict):
        path.write_text(json.dumps(content,indent=2,sort_keys=True)+"\n")
    elif isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def sample():
    # Disposable synthetic fixtures only, NEVER real physical or accepted evidence.
    with TemporaryDirectory(prefix="b46_session_fixture_", dir=Path.home()) as name:
        root=Path(name)
        study=root/"study_plan.json"
        slots=[{
            "slot":i+1,"arm":plan.A_ARM if arm=="A" else plan.B_ARM,
            "new_independently_accepted_session_receipt":False}
            for i,arm in enumerate(plan.ORDER)]
        save(study,{
            "schema":plan.SCHEMA,
            "read_only_PC_inputs_sha256":dict(plan.PINS),
            "preregistered_exact_order":"A B / B A / A B",
            "accepted_old_standalone_sessions_count_toward_NEW_ABBAAB":0,
            "all_new_session_authorizations_granted":False,
            "all_six_new_sessions_accepted":False,
            "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
            "proposed_six_slots":slots,
        })
        run_a=root/"p08_b46_s01_A_synthetic_only"
        run_b=root/"p08_b46_s02_B_synthetic_only"
        run_a.mkdir()
        run_b.mkdir()
        save(run_a/"attempt_exit_status.txt","script_exit_status=0\n")
        raw_a={}
        for label, rel in (
            ("physical_identity","physical_identity.txt"),
            ("actual_real_A53_terminal_log","a53_run.log"),
            ("actual_real_A53_journal","p07_a4_journal_1m.bin"),
            ("actual_real_A53_selected_trace","p07_a4_trace_64k.bin"),
            ("actual_real_A53_timing","p08_a2_1_images_1m.bin"),
        ):
            path=run_a/rel
            save(path,("synthetic-"+label).encode())
            raw_a[label]=digest(path)
        independent_a=root/"new_A_independent.json"
        save(independent_a,{
            "schema":plan.A_SCHEMA,
            "new_rebuilt_A2_1_distinct_ELF_SHA256":plan.PINS["a_rebuilt_elf"],
            "original_P07_all_1024_independent_packed_neural_oracle":"PASS",
            "original_P07_selected_26x42_neural_trace":"EXACT",
            "new_A53_image_sidecar_crc_and_cntfrq":"PASS",
            "ordinary_frames":1023,
            "special_trace_ordinal_excluded":1023,
            "new_A_candidate_physically_revalidated_for_THIS_1024_session":True,
            "B46_six_repeated_A_B_auth_once_sessions_accepted":False,
            "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
            "source_sha256":raw_a,
            "original_A53_observed_CNTFRQ_EL0_hz":99999001,
            "original_A2_1_image_service_median_ms":35.7,
        })
        pre_a=root/"new_A_pc_preflight.log"
        save(pre_a, "\n".join((
            "P08_B46_REBUILT_A21_ORIGINAL_1024_OFFLINE_PREFLIGHT_PASS=1",
            "P08_B46_PREFLIGHT_AUTHORIZES_PHYSICAL_JTAG=0",
            "P08_B46_REBUILT_A21_KV260_PHYSICAL_STATUS=NOT_RUN",
        )))
        save(run_b/"stage.txt",
             "B45_PERF1024_NEURAL_AND_POSTBACKUP_PRESERVED_PRELIMINARY_PASS_REBOOT_REQUIRED\n")
        raw_b={}
        for label,rel in (
            ("journal_sha256","performance1024_capture/journal1024_physical.bin"),
            ("timing_sha256","performance1024_capture/timing1024_physical.bin"),
            ("reset_sidecar_sha256","performance1024_capture/reset_profile1024_physical.bin"),
            ("mailbox_sha256","performance1024_capture/mailbox_terminal_physical.bin"),
            ("same_session_original_immutable_source_JTAG_receipt_sha256",
             "same_session_six_source_receipt.json"),
        ):
            p=run_b/rel
            save(p,("synthetic-"+label).encode())
            raw_b[label]=digest(p)
        independent_b=root/"new_B_independent.json"
        save(independent_b,{
            "schema":plan.B_SCHEMA,
            "experiment":"once",
            "genuine_new_mode_specific_A53_ELF_sha256":plan.PINS["b_auth_once_elf"],
            "new_all_1024_original_classifier_spikes_26tick_FNV_equal_scalar":True,
            "new_all_1024_A53_timing_and_reset_profiles_valid":True,
            "new_all_27_post_run_backup_records_identical_to_original":True,
            "last_trace_ordinal_1023_excluded_from_ordinary_performance":True,
            "hardware_DDR_backup_protection_proven":False,
            "original_OFFICIAL_MNIST_TEST":"SEALED_NOT_ACCESSED",
            "actual_A53_CNTFRQ_hz":99999001,
            "whole_image_service_descriptive_1023":{
                "ordinary_frames":1023,"median_ms":7225.1},
            **raw_b,
        })
        pre_b=root/"new_B_pc_preflight.log"
        save(pre_b, "\n".join((
            "P08_B45_PERF_FULL1024_ORIGINAL_SOURCES_AND_REAL_ELF_OFFLINE_PASS=1",
            "P08_B45_PERF_BOARD_VISITED=0",
            "P08_B45_PERF_DESTRUCTIVE_JTAG_NOT_AUTHORIZED_BY_PREFLIGHT=1",
        )))
        yield {
            "root":root,"plan":study,"plan_sha256":digest(study),
            "A_run":run_a,"B_run":run_b,
            "A_independent":independent_a,"B_independent":independent_b,
            "A_preflight":pre_a,"B_preflight":pre_b,
            "ledger1":root/"slot1_accepted.json",
            "ledger2":root/"slot2_accepted.json",
        }


def add_one(s, slot, previous=None, before=None, after=None):
    role=plan.ORDER[slot-1]
    return receipt.review(
        s["plan"],s["plan_sha256"],slot,
        s[role+"_run"],s[role+"_independent"],s[role+"_preflight"],
        previous,
        "OPERATOR_CONFIRMED_NEW_INDEPENDENT_COLD_BOOT" if before is None else before,
        "OPERATOR_CONFIRMED_POWER_CYCLE_AFTER_ANY_JTAG" if after is None else after,
        s[f"ledger{slot}"],
    )


def test_first_then_second_two_distinct_real_session_slots_are_hash_linked(sample):
    a=add_one(sample,1)
    assert a["accepted_total_sessions"]==1
    assert a["remaining_scheduled_sessions"]==5
    assert a["paired_study_statistics_accepted"] is False
    assert a["accepted_sessions"][0]["arm"]==plan.A_ARM
    assert a["accepted_sessions"][0]["electrical_power_cycle_independently_proven_by_instrument"] is False
    b=add_one(sample,2,previous=sample["ledger1"])
    assert b["accepted_total_sessions"]==2
    assert b["remaining_scheduled_sessions"]==4
    assert [e["arm"] for e in b["accepted_sessions"]]==[plan.A_ARM,plan.B_ARM]
    assert b["previous_study_ledger_sha256"]==digest(sample["ledger1"])
    assert b["paired_study_statistics_accepted"] is False


def test_cannot_claim_second_slot_without_new_first_ledger(sample):
    with pytest.raises(receipt.SessionNoGo,match="prior independently reviewed"):
        add_one(sample,2)


def test_wrong_arm_or_recycled_run_directory_rejected(sample):
    wrong=sample["A_run"]
    sample["A_run"] = wrong.rename(sample["root"]/"old_runner_evidence")
    with pytest.raises(receipt.SessionNoGo,match="exact slot and arm"):
        add_one(sample,1)


@pytest.mark.parametrize("attest_arg,value",[
    ("before","YES"),("after","YES"),
    ("before","OPERATOR_CONFIRMED_POWER_CYCLE_AFTER_ANY_JTAG"),
])
def test_missing_specific_operator_coldboot_or_recovery_refused(sample,attest_arg,value):
    args={attest_arg:value}
    with pytest.raises(receipt.SessionNoGo,match="operator-attested"):
        add_one(sample,1,**args)


def test_fail_closed_on_original_raw_A_timing_tamper(sample):
    source=sample["A_run"]/"p08_a2_1_images_1m.bin"
    source.write_bytes(source.read_bytes()+b"tampered")
    with pytest.raises(receipt.SessionNoGo,match="actual physical bytes"):
        add_one(sample,1)


def test_fail_closed_on_new_B_backup_report_or_original_raw_timing(sample):
    add_one(sample,1)
    body=json.loads(sample["B_independent"].read_text())
    body["new_all_27_post_run_backup_records_identical_to_original"]=False
    save(sample["B_independent"],body)
    with pytest.raises(receipt.SessionNoGo,match="NEW B authentic-once"):
        add_one(sample,2,previous=sample["ledger1"])


def test_ordinal_and_timer_semantics_must_match_original_A(sample):
    body=json.loads(sample["A_independent"].read_text())
    body["ordinary_frames"]=1024
    save(sample["A_independent"],body)
    with pytest.raises(receipt.SessionNoGo,match="original NEW A2.1"):
        add_one(sample,1)


def test_original_previous_A_standalone_report_cannot_be_counted(sample,monkeypatch):
    monkeypatch.setattr(receipt,"A_OLD_PHYSICAL_SHA",digest(sample["A_independent"]))
    with pytest.raises(receipt.SessionNoGo,match="old standalone"):
        add_one(sample,1)


def test_read_only_preflight_log_must_be_original_pass(sample):
    sample["A_preflight"].write_text("FAKE preflight")
    with pytest.raises(receipt.SessionNoGo,match="new A offline original"):
        add_one(sample,1)


def test_exact_source_and_plan_sha_fail_closed(sample):
    with pytest.raises(receipt.SessionNoGo,match="strict external study plan SHA mismatch"):
        receipt.review(
            sample["plan"],"0"*64,1,sample["A_run"],
            sample["A_independent"],sample["A_preflight"],None,
            "OPERATOR_CONFIRMED_NEW_INDEPENDENT_COLD_BOOT",
            "OPERATOR_CONFIRMED_POWER_CYCLE_AFTER_ANY_JTAG",
            sample["ledger1"])


def test_append_only_no_overwrite(sample):
    add_one(sample,1)
    with pytest.raises(receipt.SessionNoGo,match="no-overwrite"):
        add_one(sample,1)
    assert sample["ledger1"].is_file()


def test_source_contains_no_board_launch_commands():
    text=(ROOT/"scripts"/"p08_b46_4b_session_receipt.py").read_text()
    for forbidden in ("import subprocess","subprocess.run(","os.system(",
                      "xsdb ", "vivado -mode", "hw_server -s"):
        assert forbidden not in text
