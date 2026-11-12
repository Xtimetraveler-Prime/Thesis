#!/usr/bin/env python3
"""M08.2b Path A: fail-closed ORIGINAL K26 fan-route release preflight.

Read-only against original routed evidence. No release on a DRC change,
unconstrained timing, changed A12 I/O, unreviewed methodology or missing DCP.
A single SmartConnect RTSTAT-10 is documented, NOT silently waived.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sys

from m08_path_a_fan_post_route_audit import NATIVE, independent_audit

LEDGER_NAMES = (
    "00_source_sha256_before.txt", "00_run_input.txt",
    "01_vivado_fan_route.log", "03_route_status.txt",
    "04_source_sha256_after.txt", *NATIVE[1:],
    "49_independent_fan_route_audit.json",
    "50_audit_console.log", "51_audit_status.txt",
)
RTSTAT_NET = re.compile(
    r"m08_page_ps_i/ctrl_sc/inst/[A-Za-z0-9_./]*mi_handler_m_sc_areset_pipe"
)


def require(ok: bool, error: str) -> None:
    if not ok:
        raise ValueError(error)


def read(folder: Path, name: str) -> str:
    path = folder / name
    require(path.is_file() and not path.is_symlink(), "missing/symlinked ORIGINAL " + name)
    return path.read_text(encoding="utf-8", errors="replace")


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def check_ledger(folder: Path) -> dict[str, str]:
    lines = read(folder, "52_evidence_sha256.txt").splitlines()
    require(len(lines) == len(LEDGER_NAMES), "original receipt must cover every expected original")
    result = {}
    for row, expected in zip(lines, LEDGER_NAMES):
        match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9_.]+)", row)
        require(match is not None, "invalid original SHA receipt row")
        sha, name = match.groups()
        require(name == expected, "original receipt file order/name changed")
        target = folder / name
        require(target.is_file() and not target.is_symlink(), "missing original receipt file " + name)
        require(digest(target) == sha, "original SHA mismatch " + name)
        result[name] = sha
    return result


def check_timing(original: str, wns: float, whs: float) -> dict:
    for evidence in (
        "Design State      : Routed",
        "checking no_clock (0)",
        "checking unconstrained_internal_endpoints (0)",
        "checking no_input_delay (0)",
        "checking no_output_delay (0)",
        "There are 0 pins that are not constrained for maximum delay.",
        "All user specified timing constraints are met.",
        "0  Failing Endpoints",
        "| Unconstrained Path Table",
        "| Timing Details",
    ):
        require(evidence in original, "routed timing report missing: " + evidence)
    rows = re.findall(
        r"^\s*([-+]?\d+\.\d+)\s+([-+]?\d+\.\d+)\s+0\s+\d+\s+"
        r"([-+]?\d+\.\d+)\s+([-+]?\d+\.\d+)\s+0\s+\d+\s+",
        original, re.M
    )
    require(any(
        abs(float(row[0]) - wns) <= .001 and
        abs(float(row[2]) - whs) <= .001 and
        float(row[1]) == 0 and float(row[3]) == 0
        for row in rows
    ), "actual vendor timing summary disagrees with native metrics")
    section = original.split("| Unconstrained Path Table", 1)[1].split(
        "| Timing Details", 1)[0]
    require(re.search(r"From Clock\s+To Clock", section) is not None,
            "unconstrained table absent")
    require(re.search(r"clk_pl_\d+", section) is None,
            "unconstrained PL timing path present")
    require(math.isfinite(wns) and math.isfinite(whs) and wns >= 0 and whs >= 0,
            "nonfinite or negative original timing")
    return {"wns_ns": wns, "whs_ns": whs, "unconstrained_paths_reviewed": True}


def check_drc(original: str) -> dict:
    require("Design State : Fully Routed" in original,
            "DRC not based on original fully routed design")
    require("Checks found: 1" in original,
            "DRC differs from reviewed original single-warning status")
    require(re.search(
        r"\|\s*RTSTAT-10\s*\|\s*Warning\s*\|[^\n]*\|\s*1\s*\|", original
    ) is not None, "only documented SmartConnect RTSTAT-10 permitted")
    require(original.count("RTSTAT-10#1 Warning") == 1,
            "DRC warning detail missing or duplicated")
    require("15 net(s) have no routable loads." in original,
            "original SmartConnect reset warning net count changed")
    require(not re.search(r"\|\s*(Error|Critical Warning)\s*\|", original, re.I),
            "unexpected DRC severe rule")
    detail = original.split("15 net(s) have no routable loads.", 1)[1].split(
        "Related violations:", 1
    )[0]
    names = [n.rstrip(".") for n in RTSTAT_NET.findall(detail)]
    # Native Vivado text summarizes fifteen nets but prints fourteen names.
    require(len(names) in (14, 15) and len(names) == len(set(names)),
            "SmartConnect named net identities/count changed")
    return {
        "clean": False, "warning": "RTSTAT-10", "reported_nets": 15,
        "named_nets": len(names), "scope": "SmartConnect internal reset pipeline",
        "warning_waived": False,
    }


def check_methodology(original: str) -> dict:
    require("Design State : Fully Routed" in original,
            "methodology not from actual fully routed design")
    require(re.search(r"Checks found:\s+0\b", original) is not None,
            "methodology has issues or is not fully reported")
    return {"violations": 0}


def check_io(original: str) -> dict:
    rows = []
    for line in original.splitlines():
        if re.match(r"^\|\s*A12\s*\|", line):
            fields = [x.strip() for x in line.split("|")[1:-1]]
            rows.append(fields)
    require(len(rows) == 1 and len(rows[0]) >= 11,
            "original physical fan A12 report missing or duplicate")
    f = rows[0]
    require(f[0] == "A12" and f[1] == "M08_FAN_PWM[0]" and
            f[4] == "OUTPUT" and f[5] == "LVCMOS33" and
            f[7] == "4" and f[9] == "SLOW",
            "physical routed fan A12 I/O contract changed")
    return {"port": f[1], "pin": f[0], "direction": f[4],
            "standard": f[5], "drive_ma": 4, "slew": f[9]}


def check_route(original: str) -> dict:
    def number(description: str) -> int:
        m = re.search(re.escape(description) + r"\.{3,}\s*:\s*(\d+)", original)
        require(m is not None, "missing original route count " + description)
        return int(m.group(1))
    total = number("# of routable nets")
    routed = number("# of fully routed nets")
    faults = number("# of nets with routing errors")
    require(total > 0 and total == routed and faults == 0,
            "routing incomplete or route faults")
    return {"routable_nets": total, "fully_routed_nets": routed, "routing_errors": faults}


def release_preflight(folder: Path, root: Path) -> dict:
    base = independent_audit(folder, root)
    require(base["status"] ==
            "ORIGINAL_K26_FAN_AND_M08_DUAL_AXI_ROUTE_CONSISTENT_DRC_AND_UNCONSTRAINED_REVIEW_PENDING",
            "not the first-party original fan route source")
    receipt = check_ledger(folder)
    original_audit = json.loads(read(folder, "49_independent_fan_route_audit.json"))
    require(original_audit["original_native_sha256"] ==
            {name: receipt[name] for name in NATIVE},
            "original route auditor digests differ from independent receipt")
    require(original_audit["source_manifest_sha256"] ==
            receipt["00_source_sha256_before.txt"],
            "original route auditor source manifest differs")
    require(read(folder, "51_audit_status.txt").strip() ==
            "independent_audit_exit_status=0", "original route auditor failed")
    metric_rows = read(folder, "40_fan_route_metrics.txt").splitlines()
    metrics = dict((line.split("|", 2)[1], line.split("|", 2)[2])
                   for line in metric_rows)
    wns, whs = float(metrics["wns_ns"]), float(metrics["whs_ns"])
    timing = check_timing(read(folder, "41_fan_timing_post_route.rpt"), wns, whs)
    drc = check_drc(read(folder, "43_fan_drc_post_route.rpt"))
    methodology = check_methodology(read(folder, "44_fan_methodology_post_route.rpt"))
    io = check_io(read(folder, "46_fan_io_post_route.rpt"))
    route = check_route(read(folder, "47_fan_route_status_post_route.rpt"))
    return {
        "schema": "m08-path-a-fan-route-release-preflight-v1",
        "status": "K26_FAN_ROUTED_EVIDENCE_REVIEWED_RTSTAT10_DOCUMENTED_OFFLINE_ONLY",
        "original_route_dir": str(folder.resolve()),
        "original_route_dcp_sha256": receipt["48_fan_post_route.dcp"],
        "original_receipt_sha256": digest(folder / "52_evidence_sha256.txt"),
        "timing": timing, "drc": drc, "methodology": methodology,
        "io": io, "route": route,
        "id_window": "0xA0000000/0x1000",
        "page_window": "0xA0001000/0x1000",
        "physical_fan_continuity": "NOT_VERIFIED",
        "bitstream_generated": False, "board_programmed": False,
        "linux_overlay_installed": False, "linux_axi_accessor": "NOT_VALIDATED",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--route-dir", required=True, type=Path)
    ap.add_argument("--source-root", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    try:
        require(not args.output.exists() and not args.output.is_symlink(),
                "cannot overwrite an existing preflight receipt")
        result = release_preflight(args.route_dir, args.source_root)
        with args.output.open("x", encoding="utf-8") as out:
            json.dump(result, out, sort_keys=True, indent=2)
            out.write("\n")
    except (ValueError, OSError, KeyError, IndexError, json.JSONDecodeError) as exc:
        print("M08_PATH_A_FAN_RELEASE_PREFLIGHT_REJECTED:", exc, file=sys.stderr)
        return 2
    print("M08_PATH_A_FAN_ROUTE_DRC_TIMING_IO_METHODS_REVIEWED_NO_BOARD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
