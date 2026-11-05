"""B4.5.4.2 symbolic DDR-XMPU admission tests; NO HARDWARE.

The report fixture is SYNTHETIC, and the DDR-XMPU policy is never
programmed or interpreted as a real KV260 master inventory.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import p08_b4542_xmpu_boot_policy as policy


def sh(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def synthetic(tmp_path: Path, monkeypatch):
    accepted = {
        "schema": policy.prior.SCHEMA,
        "decision": "PC_STATIC_GEOMETRY_PASS_PHYSICAL_OWNER_NO_GO",
        "source_geometry_nonoverlap_only": True,
        "physical_backup_immutable_after_one_time_sha_proven": False,
        "all_DDR_port_and_master_permissions_proven": False,
        "board_contact": False,
        "operator_authorized_KV260_board_action": False,
        "accepted_B45_3_independent_paired_SHA256":
            policy.prior.ORIGINAL_PAIR_SHA,
    }
    gap = tmp_path / "synthetic_host_gap.json"
    gap.write_text(json.dumps(accepted))
    monkeypatch.setattr(policy, "ACCEPTED_GAP_SHA", sh(gap.read_bytes()))
    cfg = json.loads(policy.CANDIDATE.read_text())
    cfg["firmware_drift_constraints"]["accepted_b4541_gap_SHA256"] = (
        policy.ACCEPTED_GAP_SHA
    )
    candidate = tmp_path / "synthetic_proposed_xmpu_policy.json"
    candidate.write_text(json.dumps(cfg))
    return gap, candidate, cfg


def check(fixture, path: Path):
    return policy.audit(fixture[1], fixture[0], path)


def test_six_ports_all_1024_mids_and_both_security_modes_are_denied(
        synthetic, tmp_path):
    out = tmp_path / "model.json"
    result = check(synthetic, out)
    assert result["schema"] == policy.REPORT_SCHEMA
    assert result["candidate_port_count"] == 6
    assert result["AXI_master_ID_width"] == 10
    assert result["symbolic_transactions_tested"] == 6 * 1024 * 2 * 6 * 2
    assert result["candidate_all_ports_deny_all_writes"] is True
    assert result["candidate_all_ports_deny_all_reads_UNTIL_REAL_MASTER_WHITELIST"] is True
    assert result["candidate_real_readers_authorized"] is False
    assert result["physical_KV260_contact"] is False
    assert result["physical_execution_authorized"] is False
    assert result["new_guard_enabled_A53_ELF_available"] is False
    assert result["decision"].endswith("NO_GO")
    assert out.is_file()
    with pytest.raises(policy.BootPolicyNoGo, match="no-overwrite"):
        check(synthetic, out)


def test_symbolic_mid_mask_and_priority_are_not_flat_read_only_all_master():
    deny = {
        "region_index": 14, "enabled": True,
        "start": "0x43000000", "end_exclusive": "0x43e00000",
        "master_id": 0, "master_mask": 0,
        "secure_only": False, "read_allowed": False,
        "write_allowed": False,
    }
    allow_one_known_id = copy.deepcopy(deny)
    allow_one_known_id.update(
        region_index=15, master_id=0x80, master_mask=0x3FF,
        read_allowed=True,
    )
    # HYPOTHETICAL per-master policy; not the shipped candidate.
    for mid in range(1024):
        for sec in (False, True):
            permitted_read, winning = policy.effective_allow(
                [deny, allow_one_known_id], 0x43000000, mid, sec,
                write=False,
            )
            permitted_write, winning_write = policy.effective_allow(
                [deny, allow_one_known_id], 0x43000000, mid, sec,
                write=True,
            )
            assert permitted_read is (mid == 0x80)
            assert permitted_write is False
            assert winning == (15 if mid == 0x80 else 14)
            assert winning_write == winning
    # Wrong: granting read to EVERY master silently widens privilege.
    blanket_ro = copy.deepcopy(deny)
    blanket_ro["read_allowed"] = True
    assert policy.effective_allow(
        [blanket_ro], 0x43000000, 0x3FF, False,
        write=False,
    )[0] is True


@pytest.mark.parametrize("damage", [
    "missing_port", "duplicate_port", "extra_port",
    "denier_disabled", "denier_read_all", "denier_write_all",
    "denier_master_mask", "denier_15", "bad_cover", "extra_cover",
    "nonsecure_rejected", "reader_enabled_no_mid", "reader_grants_write",
    "reader_id_fabricated", "reader_wrong_priority",
    "region_slot_availability_claimed",
    "claimed_secure_readback", "claimed_master_inventory",
    "fake_hardware_authorization", "fake_xmpu_programming",
    "fake_signed_boot", "allow_backup_post_lock_writes",
    "fsbl_stage_after_handoff", "early_handoff_allowed",
    "boot_stage_wrong_address", "falsely_claims_real_hook_order",
    "tamper_gap_hash", "gap_claims_physical",
    "wrong_original_guard", "missing_AMD_reference",
    "unexpected_boot_event", "readiness_claimed",
])
def test_policy_and_boot_evidence_fail_closed(
        synthetic, tmp_path, damage):
    gap, candidate, cfg = synthetic
    cfg = copy.deepcopy(cfg)
    port = cfg["ddr_xmpu_ports"][0]
    deny, reader = port["proposed_regions"]
    if damage == "missing_port":
        cfg["ddr_xmpu_ports"].pop()
    elif damage == "duplicate_port":
        cfg["ddr_xmpu_ports"][1]["ddr_xmpu_port"] = 0
    elif damage == "extra_port":
        cfg["ddr_xmpu_ports"].append(copy.deepcopy(port))
    elif damage == "denier_disabled":
        deny["enabled"] = False
    elif damage == "denier_read_all":
        deny["read_allowed"] = True
    elif damage == "denier_write_all":
        deny["write_allowed"] = True
    elif damage == "denier_master_mask":
        deny["master_mask"] = 1
    elif damage == "denier_15":
        deny["region_index"] = 15
    elif damage == "bad_cover":
        deny["end_exclusive"] = "0x43d80000"
    elif damage == "extra_cover":
        reader["end_exclusive"] = "0x43f00000"
    elif damage == "nonsecure_rejected":
        deny["secure_only"] = True
    elif damage == "reader_enabled_no_mid":
        reader["enabled"] = True
    elif damage == "reader_grants_write":
        reader["write_allowed"] = True
    elif damage == "reader_id_fabricated":
        reader["master_id"] = 0x80
        reader["master_mask"] = 0x3FF
    elif damage == "reader_wrong_priority":
        reader["region_index"] = 13
    elif damage == "region_slot_availability_claimed":
        port["region_slot_14_and_15_independently_available_proven"] = True
    elif damage == "claimed_secure_readback":
        port["registers_readback"] = True
    elif damage == "claimed_master_inventory":
        port["known_readers_with_real_physical_AXIMIDs_proven"] = True
    elif damage == "fake_hardware_authorization":
        cfg["approved_for_physical_execution"] = True
    elif damage == "fake_xmpu_programming":
        cfg["no_xmpu_register_writes"] = False
    elif damage == "fake_signed_boot":
        cfg["boot_plan"]["boot_chain_authenticated"] = True
    elif damage == "allow_backup_post_lock_writes":
        cfg["boot_plan"]["prevent_any_post_lock_backup_partition_write"] = False
    elif damage == "fsbl_stage_after_handoff":
        cfg["boot_plan"]["candidate_event_order"][-2:] = list(reversed(
            cfg["boot_plan"]["candidate_event_order"][-2:]))
    elif damage == "early_handoff_allowed":
        cfg["boot_plan"]["no_early_handoff_required"] = False
    elif damage == "boot_stage_wrong_address":
        cfg["boot_plan"]["partition_load_address"] = "0x42000000"
    elif damage == "falsely_claims_real_hook_order":
        cfg["boot_plan"]["verified_hook_occurs_after_all_partitions"] = True
    elif damage == "tamper_gap_hash":
        gap.write_bytes(gap.read_bytes() + b"tampered")
    elif damage == "gap_claims_physical":
        d = json.loads(gap.read_text())
        d["all_DDR_port_and_master_permissions_proven"] = True
        gap.write_text(json.dumps(d))
    elif damage == "wrong_original_guard":
        cfg["firmware_drift_constraints"]["original_guard_provisioned"] = True
    elif damage == "missing_AMD_reference":
        cfg["documentation_sources"].pop("amd_ug1137_fsbl_hooks")
    elif damage == "unexpected_boot_event":
        cfg["boot_plan"]["candidate_event_order"][2] = "skip_27_context_sha"
    elif damage == "readiness_claimed":
        cfg["hardware_evidence_gaps"]["secure_xmpu_readback_collected"] = True
    candidate.write_text(json.dumps(cfg))
    with pytest.raises(policy.BootPolicyNoGo):
        check(synthetic, tmp_path / "must_not_create.json")
    assert not (tmp_path / "must_not_create.json").exists()


def test_prev_report_has_actual_original_operator_sha_pin():
    assert policy.ACCEPTED_GAP_SHA == (
        "7a1d87cf3278245a4a5ed612773ac228097e506f464861c3e1b69856f6ba56f2"
    )
    assert policy.prior.ORIGINAL_PAIR_SHA == (
        "03b433527901a9d51dfb8a8ca99c0321d81335859d1be14505eb6a7be9369ec1"
    )
    cfg = json.loads(policy.CANDIDATE.read_text())
    assert cfg["schema"] == policy.SCHEMA
    assert cfg["disposition"].startswith("DENY_ALL")
    assert cfg["approved_for_physical_execution"] is False
    assert cfg["boot_plan"]["verified_hook_occurs_after_all_partitions"] is False
    assert [r["region_index"] for r in cfg["ddr_xmpu_ports"][0]["proposed_regions"]] == [14, 15]
