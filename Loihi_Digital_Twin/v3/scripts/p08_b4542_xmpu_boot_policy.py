#!/usr/bin/env python3
"""P08-B4.5.4.2 OFFLINE ONLY: symbolic six-DDR-XMPU boot-time policy.

This validates a *candidate mathematical permission model*, never emits
register programming, a BOOT.BIN, or a hardware approval. AMD UG1085's
XMPU regions are 1MiB aligned, use AXI Master-ID/mask matching and higher-
numbered priority. The actual six ports, source image, secure FSBL and
trusted reader IDs are NOT established by this host simulation.

No socket, XSDB, JTAG, MMIO, platform API, or board access whatsoever.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import p08_b454_ddr_owner_preflight as prior
import p08_b45_pair_elf_evidence as pair

V3 = Path(__file__).resolve().parents[1]
CANDIDATE = V3 / "config/p08_b4542_xmpu_boot_candidate.json"
SCHEMA = "p08-b4542-zynqmp-ddr-xmpu-boot-candidate-UNIMPLEMENTED-v1"
REPORT_SCHEMA = "p08-b4542-host-only-symbolic-xmpu-boot-policy-audit-v1"
ACCEPTED_GAP_SHA = "7a1d87cf3278245a4a5ed612773ac228097e506f464861c3e1b69856f6ba56f2"
MIN_REG = 0
MAX_REG = 15
MAX_AXI_MID = 0x3FF
ONE_MIB = 0x100000
ADDRS = (0x43000000, 0x430FFFFF, 0x43100000,
         0x43D7FFFF, 0x43D80000, 0x43DFFFFF)
EVENTS = (
    "verify_boot_image_and_exact_partition",
    "stage_27_original_p02_records_into_backup",
    "verify_all_original_27_context_SHA256",
    "quiesce_all_PSU_and_PL_write_masters",
    "program_all_six_ddr_xmpu_priority14_deny_all_and_priority15_reader_whitelist",
    "secure_readback_all_six_ddr_xmpu_region_configs",
    "lock_all_six_ddr_xmpu_configs",
    "secure_readback_lock_and_coverage",
    "first_apu_handoff",
)
REQUIRED_DOC_SOURCES = (
    "amd_ug1085_instances", "amd_ug1085_xmpu_regions",
    "amd_ug1085_mid_validation", "amd_ug1085_configuration",
    "amd_ug1085_permissions", "amd_ug1137_fsbl_hooks",
    "amd_ug1137_partition_loading", "amd_ug1283_bootgen_load",
    "amd_public_fsbl_hook_source",
)

class BootPolicyNoGo(ValueError):
    pass


def need(ok: bool, message: str) -> None:
    if not ok:
        raise BootPolicyNoGo("NO-GO: " + message)


def region_matches(region: dict, addr: int, mid: int) -> bool:
    if region["enabled"] is not True:
        return False
    first = int(region["start"], 16)
    last = int(region["end_exclusive"], 16)
    mask = region["master_mask"]
    rid = region["master_id"]
    return (first <= addr < last and
            (mid & mask) == (rid & mask))


def effective_allow(regions: list[dict], addr: int, mid: int,
                    secure: bool, *, write: bool) -> tuple[bool | None, int | None]:
    """Symbolic priority/MID rule. None = no matched region; not an allow."""
    matching = [r for r in regions if region_matches(r, addr, mid)]
    if not matching:
        return None, None
    winner = max(matching, key=lambda r: r["region_index"])
    if winner["secure_only"] is True and not secure:
        return False, winner["region_index"]
    return ((winner["write_allowed"] if write else
             winner["read_allowed"]) is True, winner["region_index"])


def validate_boot_plan(candidate: dict) -> None:
    boot = candidate.get("boot_plan")
    need(type(boot) is dict, "missing trusted boot architecture plan")
    fixed = {
        "boot_media": "SEPARATE_RECOVERABLE_DEV_MEDIA_CANDIDATE_ONLY",
        "existing_qspi_or_accepted_boot_image_to_modify": False,
        "proposed_fsbl_integration_point": "XFsbl_HookBeforeHandoff",
        "no_early_handoff_required": True,
        "verified_hook_occurs_after_all_partitions": False,
        "partition_source_kind": "ORIGINAL_27_SIGNED_P02_RECORDS_ON_BOOT_MEDIA",
        "partition_load_address": "0x43000000",
        "partition_exact_bytes": 27 * 524288,
        "partition_original_SHA256_27_PROVEN": False,
        "boot_chain_authenticated": False,
        "prevent_any_post_lock_backup_partition_write": True,
        "trust_domain_for_xmpu_programming": "SECURE_FSBL_OR_TRUSTED_EL3_SERVICE",
        "no_runtime_a53_xmpu_writes": True,
        "stage_before_lock": True,
    }
    for key, value in fixed.items():
        need(boot.get(key) == value and type(boot.get(key)) is type(value),
             "incorrect/unsupported boot design contract: " + key)
    need(boot.get("candidate_event_order") == list(EVENTS),
         "trusted partition load / SHA / quiesce / secure lock / A53 handoff order drift")
    need("first_apu_handoff" == EVENTS[-1] and
         EVENTS.index("stage_27_original_p02_records_into_backup") <
         EVENTS.index("lock_all_six_ddr_xmpu_configs"),
         "backup cannot be staged after XMPU lock")


def audit(candidate_path: Path, gap_report: Path, output: Path) -> dict:
    need(output.is_absolute() and output.parent.is_dir() and
         not output.exists() and not output.is_symlink() and
         not output.resolve().is_relative_to(V3),
         "fresh external no-overwrite PC-only report file required")
    need(gap_report.is_absolute() and gap_report.is_file() and
         not gap_report.is_symlink() and
         pair.hex_sha(gap_report.read_bytes()) == ACCEPTED_GAP_SHA,
         "accepted operator B4.5.4.1 DDR gap report missing or SHA drift")
    prior_gap = pair.load_json(gap_report)
    need(prior_gap.get("schema") == prior.SCHEMA and
         prior_gap.get("decision") == "PC_STATIC_GEOMETRY_PASS_PHYSICAL_OWNER_NO_GO" and
         prior_gap.get("source_geometry_nonoverlap_only") is True and
         prior_gap.get("physical_backup_immutable_after_one_time_sha_proven") is False and
         prior_gap.get("all_DDR_port_and_master_permissions_proven") is False and
         prior_gap.get("board_contact") is False and
         prior_gap.get("operator_authorized_KV260_board_action") is False and
         prior_gap.get("accepted_B45_3_independent_paired_SHA256") ==
         prior.ORIGINAL_PAIR_SHA,
         "previous genuine PC DDR risk report incorrectly claims hardware ownership")
    prior.source_contract()
    candidate = pair.load_json(candidate_path)
    need(candidate.get("schema") == SCHEMA and
         candidate.get("disposition") ==
         "DENY_ALL_BACKUP_COVER_PLUS_UNRESOLVED_READ_WHITELIST_STATIC_ONLY",
         "candidate is not exact unresolved, nonphysical model")
    need(candidate.get("hardware") == "AMD_KV260_K26_Zynq_UltraScale_Plus",
         "candidate hardware identity drift")
    refs = candidate.get("documentation_sources", {})
    need(type(refs) is dict and set(refs) == set(REQUIRED_DOC_SOURCES) and
         all(type(v) is str and v.startswith(
             "https://docs.amd.com/") or
             k == "amd_public_fsbl_hook_source" and
             v == "https://github.com/Xilinx/embeddedsw/blob/master/lib/sw_apps/zynqmp_fsbl/src/xfsbl_hooks.c"
             for k, v in refs.items()),
         "vendor documentation/source provenance incomplete")
    backup = candidate.get("proposed_backup", {})
    need(backup.get("start") == "0x43000000" and
         backup.get("end_exclusive") == "0x43d80000" and
         backup.get("bytes") == 14155776 and
         backup.get("full_1MiB_cover") == ["0x43000000", "0x43e00000"] and
         backup.get("additional_write_protected_bytes") == 524288 and
         backup.get("additional_region_owner_independently_proven") is False,
         "backup and 1MiB overcoverage contract mismatch")
    need(prior.XMPU_COVER == (0x43000000, 0x43E00000) and
         prior.BACKUP == (0x43000000, 0x43D80000),
         "accepted prior source geometry changed")
    validate_boot_plan(candidate)
    need(candidate.get("all_master_IDs_swept") is True and
         candidate.get("both_secure_and_nonsecure_access_modes_modeled") is True,
         "all 1024 AXI IDs and both security modes must be modeled")
    fixed_hard_no_go = (
        "no_jtag", "no_xmpu_register_writes", "no_boot_bin_build",
    )
    need(all(candidate.get(k) is True for k in fixed_hard_no_go) and
         candidate.get("approved_for_physical_execution") is False and
         candidate.get("official_mnist_test") == "SEALED_NOT_ACCESSED",
         "candidate illegally claims physical approval or output firmware")
    gaps = candidate.get("hardware_evidence_gaps", {})
    need(type(gaps) is dict and len(gaps) >= 13 and
         all(value is False for value in gaps.values()),
         "unverified physical XMPU/master ownership evidence must remain unproven")
    prior_pins = candidate.get("firmware_drift_constraints", {})
    need(prior_pins.get("accepted_b4541_gap_SHA256") == ACCEPTED_GAP_SHA and
         prior_pins.get("accepted_b453_pair_SHA256") ==
         prior.ORIGINAL_PAIR_SHA and
         prior_pins.get("original_guard_provisioned") is False,
         "original accepted offline evidence or fail-closed guard changed")

    ports = candidate.get("ddr_xmpu_ports")
    need(type(ports) is list and len(ports) == 6 and
         [p.get("ddr_xmpu_port") for p in ports] == list(range(6)),
         "must model each of the six distinct DDR XMPU ports, 0..5")
    total_simulated = 0
    for port in ports:
        num = port["ddr_xmpu_port"]
        need(all(port.get(f) is False for f in (
            "registers_programmed", "registers_readback",
            "lock_readback_proven",
            "existing_regions_and_defaults_audited",
            "region_slot_14_and_15_independently_available_proven",
            "known_readers_with_real_physical_AXIMIDs_proven",
        )), "must not fabricate observed XMPU or master ownership port " +
             str(num))
        regions = port.get("proposed_regions")
        need(type(regions) is list and len(regions) == 2 and
             [r.get("region_index") for r in regions] == [14, 15],
             "region 14 deny all then higher priority 15 whitelist required")
        deny, reader = regions
        for region in regions:
            need(type(region) is dict and
                 region.get("region_index") in range(MIN_REG, MAX_REG + 1) and
                 region.get("start") == "0x43000000" and
                 region.get("end_exclusive") == "0x43e00000" and
                 region.get("secure_only") is False and
                 region.get("write_allowed") is False,
                 "region aligned bounds, security or write permissions invalid")
        need(deny.get("purpose") == "CATCH_ALL_BLOCK_BOTH" and
             deny.get("enabled") is True and
             deny.get("master_id") == 0 and
             type(deny.get("master_id")) is int and
             deny.get("master_mask") == 0 and
             type(deny.get("master_mask")) is int and
             deny.get("read_allowed") is False,
             "priority14 must deny read/write to all 1024 IDs")
        need(reader.get("purpose") == "WHITELIST_VERIFIED_READER_READONLY" and
             reader.get("enabled") is False and
             reader.get("master_id") is None and
             reader.get("master_mask") is None and
             reader.get("read_allowed") is True,
             "priority15 reader remains DISABLED until physical AXI master IDs are proven")
        for mid in range(MAX_AXI_MID + 1):
            for secure in (False, True):
                for address in ADDRS:
                    allowed_write, region_write = effective_allow(
                        regions, address, mid, secure, write=True)
                    allowed_read, region_read = effective_allow(
                        regions, address, mid, secure, write=False)
                    need(allowed_write is False and allowed_read is False and
                         region_write == 14 and region_read == 14,
                         "model leaves a protected backup byte reachable at port "+
                         str(num) + " by AXI MID " + str(mid))
                    total_simulated += 2
        for edge in (0x42FFFFFF, 0x43E00000):
            value, no_region = effective_allow(regions, edge, 0, False, write=True)
            need(value is None and no_region is None,
                 "candidate protection unlawfully covers adjoining firmware allocations")

    need(total_simulated == 6 * 1024 * 2 * len(ADDRS) * 2,
         "symbolic full six-port sweep unexpectedly incomplete")
    response = {
        "schema": REPORT_SCHEMA,
        "accepted_b4541_original_gap_report_sha256": ACCEPTED_GAP_SHA,
        "candidate_file_sha256": pair.hex_sha(candidate_path.read_bytes()),
        "original_firmware_guard_unprovisioned": True,
        "candidate_port_count": len(ports),
        "AXI_master_ID_width": 10,
        "symbolic_transactions_tested": total_simulated,
        "candidate_aligned_backup_cover": ["0x43000000", "0x43e00000"],
        "additional_512KiB_unproven_owner": True,
        "candidate_all_ports_deny_all_writes": True,
        "candidate_all_ports_deny_all_reads_UNTIL_REAL_MASTER_WHITELIST": True,
        "candidate_real_readers_authorized": False,
        "existing_XMPU_region_slot_14_15_free_proven": False,
        "real_register_values_and_priority_readback_proven": False,
        "all_six_real_DDR_ports_confirmed_and_locked": False,
        "verified_FSBL_hook_after_staging": False,
        "trusted_boot_image_partition_validated": False,
        "new_guard_enabled_A53_ELF_available": False,
        "any_physical_DDR_master_exclusivity_proven": False,
        "physical_KV260_contact": False,
        "physical_execution_authorized": False,
        "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
        "decision": "SYMBOLIC_WRITE_DENY_CONTRACT_PASS_READERS_AND_REAL_BOOT_NOT_READY_NO_GO",
        "upstream_references": refs,
    }
    with output.open("x", encoding="utf-8") as fd:
        json.dump(response, fd, indent=2, sort_keys=True)
        fd.write("\n")
    return response


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gap-report", type=Path, required=True)
    p.add_argument("--candidate", type=Path, default=CANDIDATE)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        r = audit(a.candidate, a.gap_report, a.out)
        print("P08_B4542_SIX_PORT_SYMBOLIC_WRITE_DENIAL_PC_ONLY_PASS=1")
        print("P08_B4542_MODELED_TRANSACTIONS=" + str(r["symbolic_transactions_tested"]))
        print("P08_B4542_REAL_READER_ALLOWLIST_READY=0")
        print("P08_B4542_FSBL_BOOT_PROTECTION_PROVEN=0")
        print("P08_B4542_XMPU_REGISTERS_PROGRAMMED=0")
        print("P08_B4542_NEW_A53_FIRMWARE_PROVISIONED=0")
        print("P08_B4542_BOARD_JTAG_DDR_ACTION_AUTHORIZED=0")
        print("P08_B4542_POLICY_REPORT=" + str(a.out))
        return 0
    except (BootPolicyNoGo, prior.DdrGapNoGo,
            pair.PairElfNoGo, TypeError, OSError, KeyError, ValueError) as exc:
        print("P08_B4542_HOST_ONLY_XMPU_POLICY_NO_GO=" + str(exc),
              file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
