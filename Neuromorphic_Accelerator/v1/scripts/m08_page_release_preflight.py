#!/usr/bin/env python3
"""M08.2b release gate: original post-route receipt, timing, DRC and source check.

Read-only against the owner ORIGINAL route folder. No bitstream is generated
here. Only the previously observed 15 SmartConnect reset-pipeline RTSTAT-10
nets can be considered an explicitly documented warning, NOT a clean DRC.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sys

from m08_page_post_route_audit import audit_evidence

RECEIPT_NAMES = (
    "01_vivado_impl.log",
    "02_vivado_page_bd_readback.txt",
    "03_page_bd_export.tcl",
    "04_implementation_metrics.txt",
    "05_timing_summary_post_route.rpt",
    "06_utilization_post_route.rpt",
    "07_drc_post_route.rpt",
    "08_methodology_post_route.rpt",
    "09_clock_utilization_post_route.rpt",
    "10_m08_page_post_route.dcp",
    "11_m08_route_independent_audit.json",
)
EXPECTED_WARNING = "RTSTAT-10"


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def read_original(folder: Path, name: str) -> str:
    p = folder / name
    if p.is_symlink() or not p.is_file():
        raise ValueError("missing/symlinked original: " + name)
    return p.read_text(encoding="utf-8", errors="replace")


def check_receipt(folder: Path) -> dict[str, str]:
    ledger = read_original(folder, "12_evidence_sha256.txt").splitlines()
    if len(ledger) != len(RECEIPT_NAMES):
        raise ValueError("original route SHA ledger must have precisely eleven rows")
    out = {}
    for row, name in zip(ledger, RECEIPT_NAMES):
        fields = row.split("  ", 1)
        if len(fields) != 2 or not re.fullmatch(r"[a-f0-9]{64}", fields[0]):
            raise ValueError("malformed original route SHA row")
        target = folder / name
        if target.is_symlink() or not target.is_file():
            raise ValueError("original artifact missing: " + name)
        if Path(fields[1]).resolve() != target.resolve():
            raise ValueError("ledger path does not identify original evidence: " + name)
        if sha(target) != fields[0]:
            raise ValueError("original artifact SHA mismatch: " + name)
        out[name] = fields[0]
    return out


def review_reports(folder: Path) -> dict:
    metrics = {}
    for line in read_original(folder, "04_implementation_metrics.txt").splitlines():
        fields = line.split("|")
        if len(fields) != 3 or fields[0] != "META" or fields[1] in metrics:
            raise ValueError("malformed implementation metrics")
        metrics[fields[1]] = fields[2]
    if metrics.get("no_bitstream") != "YES" or metrics.get("compute_enabled") != "NO":
        raise ValueError("incompatible routed checkpoint / compute gate")
    for key in ("wns_ns", "whs_ns"):
        try:
            val = float(metrics[key])
        except (KeyError, ValueError) as exc:
            raise ValueError("no numeric " + key) from exc
        if not math.isfinite(val) or val < 0:
            raise ValueError("negative/nonfinite routed " + key)

    timing = read_original(folder, "05_timing_summary_post_route.rpt")
    for expected in (
        "Design State      : Routed",
        "checking no_clock (0)",
        "checking unconstrained_internal_endpoints (0)",
        "There are 0 pins that are not constrained for maximum delay.",
        "checking no_input_delay (0)",
        "checking no_output_delay (0)",
        "All user specified timing constraints are met.",
        "0  Failing Endpoints",
    ):
        if expected not in timing:
            raise ValueError("timing report does not prove required closure: " + expected)
    # Extract the original summary row; compare to the two native metric fields.
    rows = re.findall(
        r"^\s*([-+]?\d+\.\d+)\s+([-+]?\d+\.\d+)\s+0\s+\d+\s+"
        r"([-+]?\d+\.\d+)\s+([-+]?\d+\.\d+)\s+0\s+\d+\s+",
        timing, flags=re.MULTILINE
    )
    if not any(
        abs(float(r[0])-float(metrics["wns_ns"])) < 0.001 and
        abs(float(r[2])-float(metrics["whs_ns"])) < 0.001 and
        abs(float(r[1])) < 0.001 and abs(float(r[3])) < 0.001
        for r in rows
    ):
        raise ValueError("actual timing summary does not match WNS/WHS metrics")

    unconst = timing.split("| Unconstrained Path Table", 1)
    if len(unconst) != 2 or "Timing Details" not in unconst[1]:
        raise ValueError("no standalone unconstrained path table")
    table = unconst[1].split("| Timing Details", 1)[0]
    if re.search(r"\S+\s+\S+\s+\S+", table.split("From Clock", 1)[-1].split(
        "----------", 1)[-1]
    ) and re.search(r"clk_pl_\d+", table):
        raise ValueError("reported unconstrained clock path")
    drc = read_original(folder, "07_drc_post_route.rpt")
    methodology = read_original(folder, "08_methodology_post_route.rpt")
    if "Design State : Fully Routed" not in drc:
        raise ValueError("original DRC is not post-route")
    if "Checks found: 1" not in drc or not re.search(
        r"\|\s*RTSTAT-10\s*\|\s*Warning\s*\|[^\n]*\|\s*1\s*\|", drc
    ):
        raise ValueError("DRC changed: only the original RTSTAT-10 warning is reviewed")
    if drc.count("RTSTAT-10#1 Warning") != 1 or (
        "15 net(s) have no routable loads." not in drc
    ):
        raise ValueError("SmartConnect RTSTAT-10 count not verified")
    detail = drc.split("15 net(s) have no routable loads.", 1)[1].split(
        "Related violations:", 1
    )[0]
    nets = re.findall(
        r"m08_page_ps_i/ctrl_sc/inst/[A-Za-z0-9_./]+", detail
    )
    # Vivado states "15 net(s)" but the human-readable summary lists
    # only fourteen full net names in this original report, ending with
    # a period. Keep both facts distinct; do NOT invent a fifteenth path.
    nets = [net.rstrip(".") for net in nets]
    if len(nets) not in (14, 15) or any(
        not net.endswith("mi_handler_m_sc_areset_pipe") for net in nets
    ) or len(set(nets)) != len(nets):
        raise ValueError("unexpected SmartConnect RTSTAT-10 net origin")
    if "Checks found: 0" not in methodology or (
        "Design State : Fully Routed" not in methodology
    ):
        raise ValueError("methodology report not violation-free and fully routed")
    util = read_original(folder, "06_utilization_post_route.rpt")
    for row in (
        "| CLB LUTs", "| CLB Registers", "| Block RAM Tile", "| DSPs",
        "10. Black Boxes",
    ):
        if row not in util:
            raise ValueError("incomplete original utilization report: " + row)
    black = util.split("10. Black Boxes", 1)[1].split(
        "11. Instantiated Netlists", 1
    )[0]
    if re.search(r"^\|\s*\S+\s*\|\s*[1-9]\d*\s*\|", black, re.M):
        raise ValueError("unexpected black-box in routed design")
    return {
        "timing_wns_ns": float(metrics["wns_ns"]),
        "timing_whs_ns": float(metrics["whs_ns"]),
        "unconstrained_internal_endpoints": 0,
        "drc_clean": False,
        "drc_warning": EXPECTED_WARNING,
        "drc_warning_nets": 15,
        "drc_named_nets_in_report": len(nets),
        "drc_warning_origin": "SmartConnect internal reset pipeline ONLY",
        "methodology_violations": 0,
        "contains_m08_compute_engine": False,
    }


def release_preflight(folder: Path, root: Path) -> dict:
    # Re-running original independent auditor verifies all original source
    # files STILL match their previously routed 10-source manifest.
    base = audit_evidence(folder, root)
    if base["status"] != "ORIGINAL_OWNER_M08_KV260_ROUTE_EVIDENCE_CONSISTENT_DRC_REVIEW_REQUIRED":
        raise ValueError("not an accepted original routed-K26 receipt")
    ledger = check_receipt(folder)
    json_original = json.loads(read_original(
        folder, "11_m08_route_independent_audit.json"
    ))
    if json_original.get("original_digests") != {
        k: ledger[k] for k in RECEIPT_NAMES[:-1]
    }:
        raise ValueError("original audit/report digests inconsistent")
    if json_original.get("source_sha256_manifest") != base["source_sha256_manifest"]:
        raise ValueError("wrong source SHA manifest in original audit")
    reports = review_reports(folder)
    return {
        "status": "M08_K26_POST_ROUTE_PREFLIGHT_REVIEWED_RTSTAT10_NOT_PHYSICAL",
        "original_route_evidence_dir": str(folder.resolve()),
        "source_sha256_manifest": base["source_sha256_manifest"],
        "route_checkpoint_sha256": ledger["10_m08_page_post_route.dcp"],
        "post_route_evidence_sha256": ledger,
        **reports,
        "bitstream_emitted": False,
        "board_programmed": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--route-dir", type=Path, required=True)
    p.add_argument("--source-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        if a.output.exists() or a.output.is_symlink():
            raise ValueError("preflight receipt already exists")
        receipt = release_preflight(a.route_dir, a.source_root)
        with a.output.open("x", encoding="utf-8") as out:
            json.dump(receipt, out, indent=2, sort_keys=True)
            out.write("\n")
    except (ValueError, OSError, KeyError, UnicodeError, json.JSONDecodeError) as exc:
        print("M08_BITSTREAM_PREFLIGHT_REJECTED:", exc, file=sys.stderr)
        return 2
    print("M08_ROUTE_REPORTS_REVIEWED_RTSTAT10_DOCUMENTED_NO_BITSTREAM_YET")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
