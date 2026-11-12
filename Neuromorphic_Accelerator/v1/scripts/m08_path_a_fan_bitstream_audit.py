#!/usr/bin/env python3
"""Independent M08.2b Path A OFFLINE .bit audit, never physical acceptance."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sys

from m08_path_a_fan_release_preflight import release_preflight

RELEASE_SOURCE = (
    "scripts/m08_path_a_fan_release_preflight.py",
    "scripts/m08_path_a_fan_bitstream.tcl",
    "scripts/m08_path_a_fan_bitstream_audit.py",
    "scripts/run_m08_path_a_fan_bitstream.sh",
)
EXPECTED_METRICS = (
    "scope", "vivado", "part", "top", "checkpoint_sha256",
    "wns_ns", "whs_ns", "fan_pin", "fan_iostandard", "fan_direction",
    "drc_warning", "bit_bytes", "board_programmed",
    "linux_overlay_installed", "physical_fan_continuity",
    "ps_axi", "compute_enabled",
)


def hash_file(p: Path) -> str:
    h = sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def require(value: bool, what: str) -> None:
    if not value:
        raise ValueError(what)


def original(folder: Path, name: str) -> bytes:
    path = folder / name
    require(not path.is_symlink() and path.is_file(), "missing/symlinked " + name)
    return path.read_bytes()


def audit_bitstream(folder: Path, route: Path, root: Path) -> dict:
    require(folder.is_dir() and not folder.is_symlink(), "bad original release folder")
    require(original(folder, "02_vivado_fan_bitstream_exit.txt") ==
            b"vivado_exit_status=0\n", "native bitstream Vivado not successful")
    require(original(folder, "00_source_sha256_before.txt") ==
            original(folder, "03_source_sha256_after.txt"), "release sources mutated")
    expected_manifest = "".join(
        f"{hash_file(root / name)}  {name}\n"
        for name in RELEASE_SOURCE
    ).encode()
    require(original(folder, "00_source_sha256_before.txt") == expected_manifest,
            "release code not SHA-pinned to current first-party source")
    preflight = json.loads(original(folder, "01_original_route_preflight.json"))
    genuine = release_preflight(route, root)
    require(preflight == genuine, "original route changed since preflight")
    original_sha = genuine["original_route_dcp_sha256"]
    require(hash_file(folder / "48_fan_post_route.dcp") == original_sha,
            "bitstream source snapshot not same original owner DCP")
    require(original(folder, "04_copied_dcp_sha256.txt").decode().strip() ==
            f"copied_dcp_sha256={original_sha}", "copied original DCP SHA receipt changed")
    log = original(folder, "02_vivado_fan_bitstream.log").decode(
        "utf-8", errors="replace"
    )
    require("ERROR:" not in log and "CRITICAL WARNING:" not in log,
            "Vivado bitstream vendor log reports severe error/critical warning")
    for token in (
        "M08_PATH_A_FAN_CHECKPOINT_TOP_A12_TIMING_DRC_RECHECKED=1",
        "M08_PATH_A_NEW_OFFLINE_FAN_BITSTREAM_EMITTED_NOT_PROGRAMMED",
    ):
        require(sum(row.strip() == token for row in log.splitlines()) == 1,
                "Vivado native release marker missing or duplicated: " + token)
    metrics = {}
    for row in original(folder, "06_fan_bitstream_metrics.txt").decode().splitlines():
        f = row.split("|")
        require(len(f) == 3 and f[0] == "META" and f[1] not in metrics,
                "bad or duplicate bitstream metrics")
        metrics[f[1]] = f[2]
    require(set(metrics) == set(EXPECTED_METRICS), "missing/extra native bitstream metric")
    for key, value in (
        ("scope", "M08_PATH_A_K26_FAN_SAFE_PAGE_OFFLINE_BITSTREAM"),
        ("part", "xck26-sfvc784-2LV-c"), ("top", "m08_page_ps_wrapper"),
        ("checkpoint_sha256", original_sha), ("fan_pin", "A12"),
        ("fan_iostandard", "LVCMOS33"), ("fan_direction", "OUT"),
        ("drc_warning", "RTSTAT-10"), ("board_programmed", "NO"),
        ("linux_overlay_installed", "NO"),
        ("physical_fan_continuity", "NOT_VERIFIED"),
        ("ps_axi", "NOT_ACCESSED"), ("compute_enabled", "NO"),
    ):
        require(metrics[key] == value, "unexpected bitstream metric: " + key)
    require(metrics["vivado"].startswith("2025.2"), "wrong native Vivado version")
    for name in ("wns_ns", "whs_ns"):
        value = float(metrics[name])
        require(math.isfinite(value) and value >= 0 and value < 1000,
                "native bitstream timing negative/nonfinite")
        require(abs(value - genuine["timing"][name]) < 0.05,
                "native release timing drifted from original routed DCP")
    bitfile = folder / "05_m08_path_a_fan_page.bit"
    require(not bitfile.is_symlink() and bitfile.is_file(), "original bitstream missing")
    size = bitfile.stat().st_size
    require(1048576 <= size < 50000000 and metrics["bit_bytes"] == str(size),
            "original .bit unexpected size")
    # The real old M08 bitstream is intentionally NOT the input of Path A.
    require(hash_file(bitfile) !=
            "170da137f315a6f53c345c416808c5203e866b8772acb6b7e69265fe38d31bbf",
            "old unfanned M08 bitstream must not be treated as Path A release")
    from m08_path_a_fan_release_preflight import check_drc, check_timing
    check_drc(original(folder, "03_fan_release_drc.rpt").decode())
    check_timing(
        original(folder, "04_fan_release_timing.rpt").decode(),
        float(metrics["wns_ns"]), float(metrics["whs_ns"])
    )
    return {
        "schema": "m08-path-a-fan-bitstream-offline-audit-v1",
        "status": "M08_K26_NEW_FAN_BITSTREAM_OFFLINE_ONLY_NO_LINUX_NO_BOARD",
        "bitstream_sha256": hash_file(bitfile),
        "bitstream_bytes": size,
        "source_route_checkpoint_sha256": original_sha,
        "original_route_ledger_sha256": genuine["original_receipt_sha256"],
        "new_bitstream_is_not_original_unfanned_m08": True,
        "fan_pin": "A12", "fan_iostandard": "LVCMOS33",
        "drc_warning": "RTSTAT-10_NOT_WAIVED",
        "original_post_route_timing": genuine["timing"],
        "native_bitstream_timing": {
            "wns_ns": float(metrics["wns_ns"]),
            "whs_ns": float(metrics["whs_ns"]),
        },
        "linux_overlay_installed": False, "physical_fan_continuity": "NOT_VERIFIED",
        "fpga_programmed": False, "ps_axi_readback_verified": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--release-dir", type=Path, required=True)
    ap.add_argument("--route-dir", type=Path, required=True)
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    try:
        require(not args.output.exists() and not args.output.is_symlink(),
                "do not overwrite original audit")
        require(args.output.parent.resolve() == args.release_dir.resolve(),
                "bitstream audit must be written to original release evidence dir")
        data = audit_bitstream(args.release_dir, args.route_dir, args.source_root)
        with args.output.open("x", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
        print("M08_PATH_A_FAN_BITSTREAM_AUDIT_REJECTED:", e, file=sys.stderr)
        return 2
    print("M08_PATH_A_FAN_NEW_OFFLINE_BITSTREAM_SOURCE_AND_SHA_AUDITED_NO_BOARD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
