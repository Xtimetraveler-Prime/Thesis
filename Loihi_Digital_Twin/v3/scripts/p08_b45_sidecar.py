#!/usr/bin/env python3
"""P08-B4.5 PC-only reset-sidecar binary structure verifier.

Validates a 256-byte experimental A53 reset record per image. This can
validate structural timing/CRC/receipt counters, NOT physical provenance,
correct neural outputs, runtime DDR protection, or permission to use JTAG.
It refuses an unprovisioned DDR guard in strict physical-candidate mode.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import struct
import sys
import zlib

MAGIC = {"once": 0x50384531, "unchecked": 0x50384532}
MODE = {"once": 1, "unchecked": 2}
ROW_BYTES = 256
ROW_FMT = "<64I"
WORDS = 64
COPY_BYTES = 14155776
PASS = 0x600D0823
DONE = 0xC0DEF00D
SCHEMA = "p08-b45-context-reset-sidecar-pc-structural-audit-v1"


class SidecarNoGo(ValueError):
    pass


def require(ok: bool, why: str) -> None:
    if not ok:
        raise SidecarNoGo("NO-GO: " + why)


def u64(lo: int, hi: int) -> int:
    return lo | (hi << 32)


def audit(blob: bytes, *, mode: str, expected_rows: int,
          observed_hz: int | None = None,
          require_protection: bool = True) -> dict:
    require(mode in MODE, "mode must be once or unchecked")
    require(expected_rows in (16, 1024), "only frozen 16-pilot or 1024-full rows")
    require(len(blob) == expected_rows * ROW_BYTES, "exact original 256-byte rows")
    assert_value = 27 if mode == "once" else 0
    ticks = []
    bind_ticks = None
    hz = None
    guard_values = set()

    for index in range(expected_rows):
        raw = blob[index * ROW_BYTES:(index + 1) * ROW_BYTES]
        w = struct.unpack(ROW_FMT, raw)
        prefix = "image " + str(index) + ": "
        require(w[0] == MAGIC[mode], prefix + "mode-specific magic")
        require(w[1] == 1, prefix + "version")
        require(w[2] == index and w[3] == PASS, prefix + "ordinal/status")
        require(w[4] == MODE[mode] and w[5] == index + 1,
                prefix + "mode/generation")
        require(w[6] == 27 and w[7] == COPY_BYTES, prefix + "copy geometry")
        require(all(w[i] == assert_value for i in (8, 9, 10, 11)),
                prefix + "mode-specific SHA/header counts")
        require(w[12] == 0, prefix + "unexpected per-image destination SHA")
        this_hz = u64(w[13], w[14])
        this_ticks = u64(w[15], w[16])
        this_bind = u64(w[17], w[18])
        require(this_hz > 0 and this_ticks > 0, prefix + "zero clock/ticks")
        if observed_hz is not None:
            require(this_hz == observed_hz, prefix + "A53 frequency changed")
        if hz is None:
            hz = this_hz
        require(hz == this_hz, prefix + "mixed CNTFRQ in one session")
        if bind_ticks is None:
            bind_ticks = this_bind
        require(bind_ticks == this_bind, prefix + "mixed one-time bind ticks")
        require(w[19] in (0, 1), prefix + "invalid backup guard flag")
        guard_values.add(w[19])
        require(w[20] == 26 and w[21] == 702,
                prefix + "frozen tick/dispatch counters drift")
        require(not any(w[22:61]) and w[62] == 0,
                prefix + "nonzero reserved words")
        require(w[61] == zlib.crc32(raw[:61 * 4]) and w[63] == DONE,
                prefix + "sidecar CRC/DONE mismatch")
        ticks.append(this_ticks)

    require(len(guard_values) == 1, "mixed guard provisioning status")
    if require_protection:
        require(guard_values == {1}, "DDR backup guard is NOT provisioned")
    ordinary = ticks[:-1] if expected_rows == 1024 else ticks
    durations_ms = [t * 1000.0 / hz for t in ordinary]
    rank = max(0, int(__import__("math").ceil(0.95 * len(ordinary))) - 1)
    ordered = sorted(durations_ms)
    return {
        "schema": SCHEMA,
        "mode": mode,
        "frames_structurally_verified": expected_rows,
        "ordinary_frames": len(ordinary),
        "isolated_trace_ordinal": 1023 if expected_rows == 1024 else None,
        "actual_a53_cntfrq_hz": hz,
        "one_time_bind_ticks": bind_ticks,
        "one_time_bind_ms": bind_ticks * 1000.0 / hz,
        "backing_backup_guard_provisioned_flag": next(iter(guard_values)),
        "strict_protection_required": require_protection,
        "reset_min_ms": min(durations_ms),
        "reset_median_ms": statistics.median(durations_ms),
        "reset_p95_nearest_rank_ms": ordered[rank],
        "reset_max_ms": max(durations_ms),
        "physical_memory_ownership_independently_proven": False,
        "actual_KV260_neural_FNV_oracle_parity_proven": False,
        "physical_JTAG_launch_authorized": False,
        "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capture", type=Path, required=True)
    p.add_argument("--mode", choices=MODE, required=True)
    p.add_argument("--rows", choices=(16, 1024), type=int, default=1024)
    p.add_argument("--hz", type=int, help="separately observed A53 CNTFRQ")
    p.add_argument("--out", type=Path, required=True)
    # Structural-only option is for synthetic/native tests; never permits
    # a real physical acceptance report.
    p.add_argument("--allow-unprovisioned-synthetic", action="store_true")
    a = p.parse_args(argv)
    try:
        require(a.capture.is_file() and not a.capture.is_symlink(),
                "existing regular capture required")
        require(a.out.is_absolute() and a.out.parent.is_dir() and
                not a.out.exists() and not a.out.is_symlink(),
                "new absolute no-overwrite report path required")
        result = audit(a.capture.read_bytes(), mode=a.mode,
                       expected_rows=a.rows, observed_hz=a.hz,
                       require_protection=not a.allow_unprovisioned_synthetic)
        with a.out.open("x", encoding="utf-8") as fd:
            json.dump(result, fd, indent=2, sort_keys=True)
            fd.write("\n")
        print("P08_B45_RESET_SIDECAR_PC_STRUCTURAL_PASS=1")
        print("P08_B45_NEURAL_PARITY_INDEPENDENTLY_PROVEN=0")
        print("P08_B45_NEW_HARDWARE_LAUNCH_AUTHORIZED=0")
        return 0
    except (SidecarNoGo, OSError, ValueError, TypeError) as exc:
        print("P08_B45_RESET_SIDECAR_NO_GO=" + str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
