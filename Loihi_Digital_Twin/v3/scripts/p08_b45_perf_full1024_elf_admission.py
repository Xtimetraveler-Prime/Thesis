#!/usr/bin/env python3
"""P08-B4.5: performance-only 1024-frame A53 ELF/map static admission, NO BOARD.

Unique 1024-frame unprotected pilot images do NOT pretend to implement a lock.
Admission is static only; genuine hardware staging, independent physical
source provenance and multiple explicit operator approvals are still needed.
Original secure-path artifacts and TEST remain unchanged.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import p08_b2_3_elf_admission as orig

MODES = ("once", "unchecked")
IDENTITIES = {
    "once": b"P08_B45_PERF_AUTH_ONCE_ORIGINAL_27CORE_1024_A53_V1",
    "unchecked": b"P08_B45_PERF_UNCHECKED_ORIGINAL_27CORE_1024_A53_V1",
}
TERMINAL = {
    "once": b"P08_B45_PERF_AUTH_ONCE_1024_TERMINAL_DONE=1",
    "unchecked": b"P08_B45_PERF_UNCHECKED_1024_TERMINAL_DONE=1",
}
ORIGINAL_ELF_SHA = (
    "0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1"
)
XSA_SHA = orig.EXPECTED_XSA_SHA
PINS_SHA = orig.EXPECTED_PINS_SHA
SCHEMA = "p08-b45-unprotected-performance-full1024-offline-elf-admission-v1"
PROFILE_BASE = 0x42400000
PROFILE_BYTES = 1024 * 256


class VariantElfNoGo(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise VariantElfNoGo("NO-GO: " + reason)


def existing(path: Path) -> bytes:
    require(path.is_absolute() and path.is_file() and not path.is_symlink(),
            "absolute existing regular non-symlink file required: " + str(path))
    return path.read_bytes()


def audit(mode: str, elf: Path, linker_map: Path, original_elf: Path,
          xsa: Path, pins_header: Path, out: Path) -> dict:
    require(mode in MODES, "mode must be once or unchecked")
    require(out.is_absolute() and out.parent.is_dir()
            and not out.is_symlink() and not out.exists()
            and not out.resolve().is_relative_to(orig.ROOT),
            "new external no-overwrite JSON report path required")
    original = existing(original_elf)
    require(orig.sha(original) == ORIGINAL_ELF_SHA and
            orig.IDENTITY in original and
            all(marker not in original for marker in IDENTITIES.values()),
            "accepted B2.3 original ELF fingerprint/identity drift")
    require(orig.sha(existing(xsa)) == XSA_SHA and
            orig.sha(existing(pins_header)) == PINS_SHA,
            "original routed XSA or frozen 27-core SHA pins changed")
    image = existing(elf)
    map_raw = existing(linker_map)
    require(orig.sha(image) != ORIGINAL_ELF_SHA and
            IDENTITIES[mode] in image and TERMINAL[mode] in image and
            orig.IDENTITY not in image and
            all(IDENTITIES[other] not in image for other in MODES if other != mode),
            "unique variant identity/terminal mismatch")
    require(all(x in map_raw for x in (
            b"Linker script and memory map", b".text", b".bss", b"main",
            b"p08_b45_perf_reset_bind", b"p08_b45_perf_reset_image",
            b"p07_b4m_full_run", b"p08_b2_meter_start")),
            "A53 linker map missing reset, guard, neural or timing symbols")
    try:
        original_segments = orig.load_segments(original)
        segments = orig.load_segments(image)
    except orig.ElfNoGo as exc:
        raise VariantElfNoGo("original/new AArch64 PT_LOAD invalid: " + str(exc)) from exc
    require(b"p08_b45_a53_backup_lock" not in map_raw and
            b"p08_b45_reset_bind" not in map_raw and
            b"p08_b45_reset_image" not in map_raw,
            "protected-mode guard or old reset symbols must not be linked")
    require(bool(segments) and all(
            int(seg["paddr_end_exclusive"], 16) <= orig.NEW_DDR_BASE
            for seg in segments),
            "new ELF PT_LOAD overlaps original P08 DDR envelope")
    require(PROFILE_BASE == 0x42400000 and
            PROFILE_BYTES == 262144 and
            PROFILE_BASE + PROFILE_BYTES <= 0x43000000,
            "proposed reset sidecar DDR envelope drift")

    report = {
        "schema": SCHEMA,
        "mode": mode,
        "new_distinct_A53_identity": IDENTITIES[mode].decode("ascii"),
        "new_elf_sha256": orig.sha(image),
        "new_linker_map_sha256": orig.sha(map_raw),
        "original_immutable_B2_3_elf_sha256": ORIGINAL_ELF_SHA,
        "original_p03_xsa_sha256": XSA_SHA,
        "original_27_core_sha_header_sha256": PINS_SHA,
        "new_elf_program_segments": segments,
        "original_elf_program_segments": original_segments,
        "proposed_reset_profile_base": hex(PROFILE_BASE),
        "proposed_reset_profile_bytes": PROFILE_BYTES,
        "source_build_mode_specific": True,
        "frames": 1024,
        "raw_source_population_sha_1024_images_checked_in_new_app": True,
        "unprotected_performance_only": True,
        "ELF64_AArch64_PT_LOAD_low_DDR_static_admission": True,
        "unprovisioned_backup_protection_adapter": False,
        "physical_DDR_immutability_not_claimed": True,
        "backup_guard_provisioned_flag_in_sidecar": 0,
        "independent_physical_DDR_owner_and_protection_proven": False,
        "new_KV260_neural_parity_verified": False,
        "new_KV260_physical_reset_timing_verified": False,
        "physical_JTAG_DDR_launch_authorized": False,
        "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
    }
    with out.open("x", encoding="utf-8") as fd:
        json.dump(report, fd, indent=2, sort_keys=True)
        fd.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=MODES, required=True)
    for n in ("elf", "map", "original-elf", "xsa", "pins-header", "out"):
        p.add_argument("--" + n, required=True, type=Path)
    a = p.parse_args(argv)
    try:
        result = audit(a.mode, a.elf, a.map, a.original_elf,
                       a.xsa, a.pins_header, a.out)
        print("P08_B45_PERF_1024_GENUINE_A53_ELF_STATIC_ADMISSION_PASS=1")
        print("P08_B45_MODE=" + a.mode)
        print("P08_B45_ELF_SHA=" + result["new_elf_sha256"])
        print("P08_B45_MAP_SHA=" + result["new_linker_map_sha256"])
        print("P08_B45_PERF_HARDWARE_BACKUP_PROTECTED=0")
        print("P08_B45_PERF_PHYSICAL_JTAG_AUTHORIZED_BY_ADMISSION=0")
        print("P08_B45_PERF_OFFLINE_REPORT=" + str(a.out))
        return 0
    except (orig.ElfNoGo, VariantElfNoGo, TypeError, OSError, KeyError, ValueError) as exc:
        print("P08_B45_PERF_A53_ELF_ADMISSION_NO_GO=" + str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
