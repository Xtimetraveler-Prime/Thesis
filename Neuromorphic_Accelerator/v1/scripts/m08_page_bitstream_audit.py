#!/usr/bin/env python3
"""Independently check ORIGINAL offline M08 K26 bitstream and source receipt.

Not a deployment authorization. It never programs FPGA, checks Linux MMIO,
allocates DMA, or claims signed16 inference. DRC warning is NOT waived.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

from m08_page_release_preflight import release_preflight

SOURCES = (
    "rtl/m08/m08_axil_readonly_identity.v",
    "rtl/m08/m08_host_staged_page_bank.sv",
    "rtl/m08/m08_axil_page_control.sv",
    "rtl/m08/m08_ps_page_safe_shell.v",
    "scripts/m08_page_ps_bd_candidate.tcl",
    "scripts/m08_page_bd_audit.py",
    "scripts/run_m08_page_bd.sh",
    "scripts/m08_page_post_route_candidate.tcl",
    "scripts/m08_page_post_route_audit.py",
    "scripts/run_m08_page_post_route.sh",
    "scripts/m08_page_release_preflight.py",
    "scripts/m08_page_bitstream_candidate.tcl",
    "scripts/m08_page_bitstream_audit.py",
    "scripts/run_m08_page_bitstream.sh",
)
MARKERS = (
    "M08_PAGE_RELEASE_CHECKPOINT_TOP_VALIDATED=m08_page_ps_wrapper",
    "M08_PAGE_RELEASE_CHECKPOINT_TIMING_AND_DRC_RECHECKED=1",
    "M08_PAGE_GENUINE_OFFLINE_BITSTREAM_EMITTED_NOT_PROGRAMMED",
)


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def get(folder: Path, filename: str) -> Path:
    f = folder / filename
    if not f.is_file() or f.is_symlink():
        raise ValueError("original bitstream release evidence missing/symlinked: " + filename)
    return f


def audit_release(release: Path, route: Path, root: Path) -> dict:
    if not release.is_dir() or release.is_symlink():
        raise ValueError("not an original release evidence directory")
    before = get(release, "source_sha256_before.txt").read_bytes()
    after = get(release, "source_sha256_after.txt").read_bytes()
    expected = "".join(
        f"{sha(root/name)}  {name}\n" for name in SOURCES
    ).encode("ascii")
    if before != after or before != expected:
        raise ValueError("bitstream release source SHA is mismatched/changed")
    preflight = release_preflight(route, root)
    actual_preflight = json.loads(
        get(release, "01_release_preflight.json").read_text()
    )
    if actual_preflight != preflight or preflight["drc_clean"] is not False:
        raise ValueError("original route SHA and explicit DRC review no longer match")
    if get(release, "result.txt").read_bytes() != b"exit_status=0\n":
        raise ValueError("original Vivado bitstream generation did not exit successfully")
    log = get(release, "02_vivado_bitstream.log").read_text(errors="replace")
    if "ERROR:" in log or "CRITICAL WARNING:" in log:
        raise ValueError("new bitstream vendor log contains severe error or warning")
    for marker in MARKERS:
        if sum(line.strip() == marker for line in log.splitlines()) != 1:
            raise ValueError("missing/duplicated original bitstream vendor marker: " + marker)
    drc = get(release, "03_rechecked_drc.rpt").read_text(errors="replace")
    if ("Checks found: 1" not in drc or
            not re.search(r"\|\s*RTSTAT-10\s*\|\s*Warning\s*\|[^\n]*\|\s*1\s*\|", drc) or
            "15 net(s) have no routable loads." not in drc or
            "m08_page_ps_i/ctrl_sc/inst/" not in drc):
        raise ValueError("original checkpoint DRC recheck diverged from documented RTSTAT-10")
    timing = get(release, "04_rechecked_timing.rpt").read_text(errors="replace")
    if ("All user specified timing constraints are met." not in timing or
            "checking unconstrained_internal_endpoints (0)" not in timing):
        raise ValueError("released checkpoint timing constraint recheck failed")
    metrics = {}
    for line in get(release, "06_bitstream_native_metrics.txt").read_text().splitlines():
        parts = line.split("|")
        if len(parts) != 3 or parts[0] != "META" or parts[1] in metrics:
            raise ValueError("malformed original bitstream metrics")
        metrics[parts[1]] = parts[2]
    if (metrics.get("scope") != "M08_GENUINE_LOCAL_KV260_PS_SAFE_PAGE_BITSTREAM_NO_BOARD"
        or not metrics.get("vivado_version", "").startswith("2025.2")
        or metrics.get("part") != "xck26-sfvc784-2LV-c"
        or metrics.get("top") != "m08_page_ps_wrapper"
        or "design_display_name" not in metrics
        or metrics.get("drc_warning") != "RTSTAT-10"
        or metrics.get("compute_enabled") != "NO"
        or metrics.get("board_programmed") != "NO"
        or metrics.get("linux_mmio") != "NOT_ACCESSED"
        or metrics.get("physical_ddr") != "NOT_ACCESSED"):
        raise ValueError("new Vivado bitstream metadata/physical scope invalid")
    try:
        wns = float(metrics["wns_ns"])
        whs = float(metrics["whs_ns"])
        clocks = int(metrics["clock_count"])
    except (ValueError, KeyError) as exc:
        raise ValueError("invalid Vivado bitstream metrics") from exc
    if wns < 0 or whs < 0 or clocks < 1 or (
        abs(wns-preflight["timing_wns_ns"]) > 0.1 or
        abs(whs-preflight["timing_whs_ns"]) > 0.1
    ):
        raise ValueError("bitstream reloaded checkpoint timing differs from original route")
    bit = get(release, "05_m08_safe_page.bit")
    if bit.stat().st_size < 1024:
        raise ValueError("original K26 bitstream missing or implausibly short")
    return {
        "status": "M08_ORIGINAL_K26_SAFE_PAGE_BITSTREAM_GENERATED_NOT_PROGRAMMED",
        "original_route_evidence_dir": str(route.resolve()),
        "original_route_dcp_sha256": preflight["route_checkpoint_sha256"],
        "bitstream_sha256": sha(bit),
        "bitstream_bytes": bit.stat().st_size,
        "source_sha256_manifest": sha(release/"source_sha256_before.txt"),
        "original_preflight_sha256": sha(release/"01_release_preflight.json"),
        "original_vivado_log_sha256": sha(release/"02_vivado_bitstream.log"),
        "original_drc_sha256": sha(release/"03_rechecked_drc.rpt"),
        "original_timing_sha256": sha(release/"04_rechecked_timing.rpt"),
        "native_wns_ns": wns,
        "native_whs_ns": whs,
        "verified_routed_hdl_top": metrics["top"],
        "vivado_design_display_name": metrics["design_display_name"],
        "drc_warning_retained": "RTSTAT-10 SmartConnect internal reset pipeline",
        "compute_engine_connected": False,
        "physical_board_programmed": False,
        "linux_mmio_accessed": False,
        "physical_ddr_accessed": False,
        "signed16_neural_inference_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", required=True, type=Path)
    parser.add_argument("--route-dir", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if (args.output.is_symlink() or args.output.exists() or
                args.output.parent.resolve() != args.release_dir.resolve()):
            raise ValueError("audit output must be a NEW file inside its release evidence directory")
        output = audit_release(args.release_dir, args.route_dir, args.source_root)
        with args.output.open("x", encoding="utf-8") as f:
            json.dump(output, f, sort_keys=True, indent=2)
            f.write("\n")
    except (ValueError, OSError, KeyError, UnicodeError, json.JSONDecodeError) as exc:
        print("M08_OFFLINE_BITSTREAM_AUDIT_REJECTED:", exc, file=sys.stderr)
        return 2
    print("M08_OFFLINE_BITSTREAM_SHA_AND_NATIVE_VENDOR_RECEIPT_AUDITED_NO_BOARD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
