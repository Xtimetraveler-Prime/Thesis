#!/usr/bin/env python3
"""P08-B4.5.4.1: HOST-ONLY audit of DDR geometry and UNPROVEN owners.

No JTAG, XSDB, Vitis, MMIO, device register reads, DDR writes or board
contact. Nothing this script accepts enables the backup guard, attests
XMPU protection, or authorizes a physical ELF launch.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

import p08_b45_pair_elf_evidence as pair

V3 = Path(__file__).resolve().parents[1]
SCHEMA = "p08-b454-ddr-owner-gap-pc-only-preflight-v1"
ORIGINAL_PAIR_SHA = "03b433527901a9d51dfb8a8ca99c0321d81335859d1be14505eb6a7be9369ec1"
PINS_PATH = V3 / "docs/P08_B4_5_3_OPERATOR_REPORTED_A53_ARTIFACT_PINS_2026_11_05.json"
B4L_APERTURE = (0x40000000, 0x44000000)
MUTABLE = (0x40000000, 0x40D80000)
BACKUP = (0x43000000, 0x43D80000)
# AMD UG1085 DDR XMPU uses 1 MiB regional address granularity. This is
# only a possible *geometric* cover, not a hardware permission plan.
XMPU_UNIT = 0x100000
XMPU_COVER = (BACKUP[0], (BACKUP[1] + XMPU_UNIT - 1) & ~(XMPU_UNIT - 1))
BOOT_OBSERVATIONS = (
    "proc_iomem.txt", "reserved_memory.txt", "boot_log.txt",
    "boot_image_manifest.json", "xmpu_readback.json", "masters_snapshot.json",
)
MASTER_GAPS = (
    ("fsbl", "FSBL write/relocation ownership, original boot image, exact reset sequence"),
    ("tf_a", "TF-A/BL31 secure DDR mappings and current ownership"),
    ("uboot", "U-Boot DDR allocation, reserved regions, runtime absence"),
    ("linux", "Linux /proc/iomem, reserved-memory, allocator and drivers in relevant boot"),
    ("apu_other", "Other Cortex-A53 cores, MMU stage-1/2 and cache/coherency"),
    ("rpu", "R5/RPU boot state, DDR master ID and write ownership"),
    ("pmu_csu", "PMU/CSU/boot and secure configuration provenance"),
    ("pl_dma", "PL HP/HPx, accelerator and all DMA write masters"),
    ("ddr_xmpu_ports", "All six DDR XMPU ports, per-master permissions and locked boot configuration"),
    ("fpd_dma_cci", "FPD DMA, CCI/display/other PS AXI clients and default access policy"),
    ("debug", "JTAG/XSDB and other debug masters, staging/lock sequence"),
    ("low_ddr", "A53 image PT_LOAD, heap/stack, boot state and exclusive DDR owner"),
    ("backup_staging", "Exact 27 immutable P02 records loaded BEFORE protection and read-only afterward"),
    ("profile_sidecar", "Separate exclusive ownership of profiling, raw input, journals and mailbox"),
)
# Entire geometry derived from existing immutable application entrypoints,
# not newly proposed temporary allocations.
REGIONS = (
    ("27_mutable_P02_records", *MUTABLE, "A53 copy target, PL/AXI DDR paging"),
    ("P07_B4M_route_input", 0x41000000, 0x410E0000, "frozen input routing"),
    ("P07_B4M_frame_staging", 0x41100000, 0x411E0000, "input frame staging"),
    ("1024_raw_MNIST_TRAIN_pool", 0x42100000, 0x421C4000, "raw input"),
    ("1024_result_journal", 0x42200000, 0x42240000, "result"),
    ("1024_whole_image_timing", 0x42300000, 0x42340000, "meter"),
    ("1024_B45_reset_sidecar", 0x42400000, 0x42440000, "meter"),
    ("27_immutable_P02_backup", *BACKUP, "requested read-only"),
    ("P07_B4L_bindings", 0x43FC0000, 0x43FC4000, "frozen source bindings"),
    ("P07_B4M_route_output", 0x43FC4000, 0x43FD8000, "route writeout"),
    ("B45_terminal_mailbox", 0x43FF0200, 0x43FF0300, "mailbox"),
)


class DdrGapNoGo(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise DdrGapNoGo("NO-GO: " + reason)


def no_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[1] <= b[0] or b[1] <= a[0]


def source_contract() -> None:
    """Reject accidental DDR constant/guard edits; no memory is accessed."""
    p03 = (V3 / "software/p03/include/p03_hw_adapter.h").read_text()
    need("#define P03_HW_BACKING_BASE UINT64_C(0x40000000)" in p03
         and "#define P03_HW_BACKING_BYTES UINT64_C(0x04000000)" in p03
         and "#define P03_HW_RECORD_BYTES UINT64_C(0x00080000)" in p03,
         "original routed P03 address/record geometry drifted")
    route = (V3 / "software/p07/include/p07_b4m_frozen_routes.h").read_text()
    binding = (V3 / "software/p07/include/p07_b4l_b3_bindings.h").read_text()
    need(all(x in route for x in (
        "#define P07_B4M_ROUTE_IN_BASE UINT32_C(0x41000000)",
        "#define P07_B4M_ROUTE_IN_BYTES UINT32_C(0x000E0000)",
        "#define P07_B4M_FRAME_BASE UINT32_C(0x41100000)",
        "#define P07_B4M_FRAME_MAX_BYTES UINT32_C(0x000E0000)",
        "#define P07_B4M_ROUTE_OUT_BASE UINT32_C(0x43FC4000)",
        "#define P07_B4M_ROUTE_OUT_BYTES UINT32_C(0x00014000)",
    )), "frozen B4M routing memory envelope drifted")
    need("#define B4L_BIND_BASE UINT32_C(0x43FC0000)" in binding
         and "#define B4L_BIND_SIZE 0x4000u" in binding,
         "frozen B4L binding memory envelope drifted")
    for mode, main in (
        ("once", "p08_b45_auth_once_full1024_a53.c"),
        ("unchecked", "p08_b45_unchecked_full1024_a53.c"),
    ):
        data = (V3 / "software/p08" / main).read_text()
        checks = (
            "#define B23_FRAMES 1024u",
            "#define B23_RAW_POOL 0x42100000u",
            "#define B23_RAW_POOL_BYTES (B23_FRAMES*784u)",
            "#define B23_BACKUP 0x43000000u",
            "#define B23_JOURNAL 0x42200000u",
            "#define B23_TIMING 0x42300000u",
            "#define B45_PROFILE_BASE UINT32_C(0x42400000)",
            "#define B23_MAILBOX 0x43FF0200u",
            "#define B23_ROW_BYTES (B23_WORDS*4u)",
            "#define B23_WORDS 64u",
            "reset_config.lock_backup=p08_b45_a53_backup_lock;",
            "reset_config.backup_lock_valid=p08_b45_a53_backup_lock_valid;",
        )
        need(all(x in data for x in checks), mode + " memory/guard source changed")
    guard = (V3 / "software/p08/p08_b45_a53_backup_guard.c").read_text()
    guard_h = (V3 / "software/p08/p08_b45_a53_backup_guard.h").read_text()
    need(guard.count("return -1;") == 2 and
         "#define P08_B45_A53_GUARD_PROVISIONED 0u" in guard_h,
         "current B4.5 backup guard must remain fail-closed")
    need(BACKUP[1] - BACKUP[0] == 27 * 0x80000 and
         XMPU_COVER == (0x43000000, 0x43E00000),
         "backup or proposed 1MiB granularity calculation drifted")
    for label, lo, hi, _owner in REGIONS:
        need(B4L_APERTURE[0] <= lo < hi <= B4L_APERTURE[1],
             label + " falls outside P03 reserved aperture")
    for i, a in enumerate(REGIONS):
        for b in REGIONS[i+1:]:
            need(no_overlap((a[1], a[2]), (b[1], b[2])),
                 "original firmware DDR allocations overlap: " + a[0] + " " + b[0])
    for label, lo, hi, _owner in REGIONS:
        if label != "27_immutable_P02_backup":
            need(no_overlap(XMPU_COVER, (lo, hi)),
                 "1MiB-aligned protective envelope intersects original allocation: " + label)


def optional_boot_inventory(directory: Path | None) -> list[dict]:
    """Provenance of operator-supplied snapshots ONLY, never owner proof."""
    if directory is None:
        return []
    need(directory.is_absolute() and directory.is_dir() and not directory.is_symlink(),
         "optional observation directory must exist and be absolute, nonsymlink")
    items = []
    for name in BOOT_OBSERVATIONS:
        file = directory / name
        if file.exists() or file.is_symlink():
            need(file.is_file() and not file.is_symlink(),
                 "snapshot is not a regular original file: " + name)
            need(0 < file.stat().st_size <= 16 * 1024 * 1024,
                 "snapshot size outside read-only 16 MiB bound: " + name)
            items.append({"name": name, "sha256": pair.hex_sha(file.read_bytes()),
                          "bytes": file.stat().st_size,
                          "authority": "UNVERIFIED_OPERATOR_SUPPLIED_SNAPSHOT"})
    return items


def review(*, paired: Path, once_build: Path, unchecked_build: Path,
           out: Path, inventory: Path | None = None) -> dict:
    need(out.is_absolute() and out.parent.is_dir() and
         not out.exists() and not out.is_symlink() and
         not out.resolve().is_relative_to(V3),
         "fresh, external, non-overwriting absolute report required")
    need(paired.is_absolute() and paired.is_file() and not paired.is_symlink(),
         "operator's independently verified paired JSON required")
    need(pair.hex_sha(paired.read_bytes()) == ORIGINAL_PAIR_SHA,
         "operator-accepted genuine two-A53 paired report fingerprint drift")
    accepted = pair.load_json(paired)
    need(accepted.get("schema") == pair.SCHEMA and
         accepted.get("each_elf_and_map_cryptographically_reverified") is True
         and accepted.get("both_admission_reports_exactly_recomputed_against_original_inputs") is True
         and accepted.get("both_staged_sources_match_reviewed_offline_branch") is True
         and accepted.get("A53_ELF_artifact_generation_both_modes") == "PC_ONLY_VERIFIED"
         and accepted.get("physical_memory_ownership_proven") is False
         and accepted.get("physical_JTAG_authorized") is False
         and accepted.get("backup_protection_adapter_provisioned") is False
         and accepted.get("KV260_neural_parity_verified") is False,
         "paired report does not match frozen B4.5.3 PC admission")
    pins = pair.load_json(PINS_PATH)
    need(pins.get("schema") == pair.PIN_SCHEMA,
         "original operator SHA-256 manifest schema changed")
    source_contract()

    segments_by_mode = {}
    for mode, root in (("once", once_build), ("unchecked", unchecked_build)):
        need(root.is_absolute() and root.is_dir() and not root.is_symlink() and
             root.resolve() == Path(pins["variants"][mode]["build_root"]).resolve(),
             mode + " build root differs from independently accepted operator path")
        app = "p08_b45_auth_once_1024" if mode == "once" else "p08_b45_unchecked_1024"
        elf = root / "vitis_workspace" / (app + ".elf")
        need(elf.is_file() and not elf.is_symlink(), mode + " genuine ELF absent")
        raw = elf.read_bytes()
        need(pair.hex_sha(raw) == pins["variants"][mode]["elf_sha256"] ==
             accepted["independent_report_files"][mode]["elf"],
             mode + " genuine ELF hash no longer matches accepted B4.5.3 evidence")
        # Parses actual ELF64/AArch64 PT_LOAD from disk, not a static
        # approximation or unproven statement about low-DDR ownership.
        parsed = pair.gate.orig.load_segments(raw)
        need(all(int(s["paddr_end_exclusive"], 16) <= B4L_APERTURE[0]
                 for s in parsed), mode + " ELF PT_LOAD overlaps P03 DDR")
        segments_by_mode[mode] = parsed

    observations = optional_boot_inventory(inventory)
    result = {
        "schema": SCHEMA,
        "accepted_B45_3_independent_paired_SHA256": ORIGINAL_PAIR_SHA,
        "actual_A53_load_segments_by_mode": segments_by_mode,
        "original_P03_backing_aperture": [hex(x) for x in B4L_APERTURE],
        "firmware_declared_regions": [
            {"name": name, "start": hex(lo), "end_exclusive": hex(hi),
             "bytes": hi-lo, "purpose": purpose,
             "physical_owner_independently_proven": False}
            for name, lo, hi, purpose in REGIONS
        ],
        "backup_original_27_core_range": [hex(x) for x in BACKUP],
        "ddr_xmpu_1MiB_alignment_candidate_only": [hex(x) for x in XMPU_COVER],
        "xmpu_candidate_overprotects_bytes": XMPU_COVER[1] - BACKUP[1],
        "xmpu_region_programmed_or_readback": False,
        "xmpu_granularity_is_not_hardware_permission_proof": True,
        "backup_stage_must_precede_protection": True,
        "source_geometry_nonoverlap_only": True,
        "owner_proof_requirements": [
            {"master_class": who, "required_evidence": what,
             "status": "NOT_ESTABLISHED"}
            for who, what in MASTER_GAPS
        ],
        "supplied_boot_observations_not_physical_proof": observations,
        "physical_backup_immutable_after_one_time_sha_proven": False,
        "all_DDR_port_and_master_permissions_proven": False,
        "all_processor_DDR_owners_excluded": False,
        "low_DDR_exclusive_A53_ownership_proven": False,
        "persistent_backup_lock_available_to_both_modes": False,
        "new_guard_enabled_ELF_built": False,
        "operator_authorized_KV260_board_action": False,
        "board_contact": False,
        "16_image_pilot_or_1024_session_performed": False,
        "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
        "decision": "PC_STATIC_GEOMETRY_PASS_PHYSICAL_OWNER_NO_GO",
    }
    with out.open("x", encoding="utf-8") as fd:
        json.dump(result, fd, indent=2, sort_keys=True)
        fd.write("\n")
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--paired-report", required=True, type=Path)
    p.add_argument("--once-build", required=True, type=Path)
    p.add_argument("--unchecked-build", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--inventory-dir", type=Path)
    a = p.parse_args(argv)
    try:
        r = review(paired=a.paired_report, once_build=a.once_build,
                   unchecked_build=a.unchecked_build, out=a.out,
                   inventory=a.inventory_dir)
        print("P08_B454_HOST_ONLY_GENUINE_A53_MEMORY_GEOMETRY_PASS=1")
        print("P08_B454_XMPU_BACKUP_1M_COVER=" +
              str(r["ddr_xmpu_1MiB_alignment_candidate_only"]))
        print("P08_B454_DDR_MASTER_OWNER_PROOF=0")
        print("P08_B454_PERSISTENT_BACKUP_PROTECTION_PROVEN=0")
        print("P08_B454_BOARD_JTAG_AND_DDR_ACTION_AUTHORIZED=0")
        print("P08_B454_PC_ONLY_GAP_REPORT=" + str(a.out))
        return 0
    except (DdrGapNoGo, pair.PairElfNoGo, pair.gate.orig.ElfNoGo,
            TypeError, OSError, KeyError, ValueError) as exc:
        print("P08_B454_HOST_ONLY_GAP_PREFLIGHT_NO_GO=" + str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
