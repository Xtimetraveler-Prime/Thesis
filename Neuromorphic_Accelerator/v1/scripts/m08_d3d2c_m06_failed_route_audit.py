#!/usr/bin/env python3
"""READ ONLY: inspect the FIRST D3.D.2C owner route which failed timing.

Does not invoke Vivado or touch the KV260. Extracts original worst timing
paths and report SHAs from the already existing routed checkpoint directory.
Never rewrites native evidence; never claims a successful route or bitstream.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

DESIGN = "m08_d3d2c_m06_lif_jtag"
TOP = DESIGN + "_wrapper"
IMPL_REL = Path("project") / (DESIGN + ".runs") / "impl_1"
REPORTS = {
    "routed_timing": TOP + "_timing_summary_routed.rpt",
    "routed_drc": TOP + "_drc_routed.rpt",
    "routed_bus_skew": TOP + "_bus_skew_routed.rpt",
    "route_status": TOP + "_route_status.rpt",
    "methodology": TOP + "_methodology_drc_routed.rpt",
}
ROUTED_DCP = TOP + "_routed.dcp"

class Reject(ValueError):
    pass


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise Reject(reason)


def read_existing(path: Path, max_bytes: int = 20_000_000) -> bytes:
    require(path.is_file() and not path.is_symlink(), "missing/symlinked original file: " + str(path))
    size = path.stat().st_size
    require(0 < size <= max_bytes, "empty/oversized original report: " + str(path))
    return path.read_bytes()


def timing_table(report: str) -> dict:
    lines = report.splitlines()
    found = [i for i, line in enumerate(lines)
             if line.strip().startswith("WNS(ns)") and "WHS(ns)" in line]
    require(len(found) == 1 and found[0] + 2 < len(lines),
            "original WNS/WHS summary table missing/ambiguous")
    raw = lines[found[0] + 2].split()
    require(len(raw) >= 8, "original timing numeric row incomplete")
    try:
        wns, tns, setup_failing = float(raw[0]), float(raw[1]), int(raw[2])
        whs, ths, hold_failing = float(raw[4]), float(raw[5]), int(raw[6])
    except (IndexError, ValueError) as e:
        raise Reject("original timing row invalid: " + str(raw)) from e
    return {
        "wns_ns": wns, "tns_ns": tns, "setup_failing_endpoints": setup_failing,
        "whs_ns": whs, "ths_ns": ths, "hold_failing_endpoints": hold_failing,
        "original_summary_row": lines[found[0] + 2].strip(),
    }


def path_blocks(report: str, max_paths: int = 3, max_lines: int = 75) -> list[dict]:
    lines = report.splitlines()
    violations = []
    for i, line in enumerate(lines):
        m = re.search(r"\bSlack\s*\(VIOLATED\)\s*:\s*([-+]?\d+(?:\.\d+)?)\s*ns", line)
        if m:
            violations.append((i, float(m.group(1))))
    chunks = []
    for start, slack in violations[:max_paths]:
        excerpt = []
        for line in lines[start:min(start + max_lines, len(lines))]:
            # Stop at the next timing-path entry, if the report has one.
            if excerpt and re.search(r"\bSlack\s*\((?:VIOLATED|MET)\)\s*:", line):
                break
            excerpt.append(line.rstrip())
        chunks.append({
            "slack_ns": slack, "original_report_line": start + 1,
            "original_path_excerpt": "\n".join(excerpt),
        })
    return chunks


def audit(original: Path) -> dict:
    require(original.is_absolute() and original.is_dir() and not original.is_symlink(),
            "require existing absolute, unsymlinked owner evidence folder")
    require(original.parent.name == "M08" and
            re.fullmatch(r"m08_d3d2c_m06_[A-Za-z0-9]+", original.name) is not None,
            "not original D3.D.2C M08 evidence folder")
    impl = original / IMPL_REL
    require(impl.is_dir() and not impl.is_symlink(),
            "first owner original impl_1 directory missing")
    dcp = impl / ROUTED_DCP
    require(dcp.is_file() and not dcp.is_symlink() and
            dcp.stat().st_size > 100000,
            "no valid original routed checkpoint -- do not recreate one")
    original_reports = {}
    hashes = {}
    for label, name in REPORTS.items():
        data = read_existing(impl / name)
        original_reports[label] = data.decode("utf-8", errors="replace")
        hashes[label] = sha256(data).hexdigest()
    row = timing_table(original_reports["routed_timing"])
    require(row["wns_ns"] < 0 or row["whs_ns"] < 0 or
            row["setup_failing_endpoints"] > 0 or row["hold_failing_endpoints"] > 0,
            "route does not show an actual negative/failing timing gate: inspect manually")
    # The first owner run failed before its source-owned bitstream/12-hash
    # ledger stage. Never retroactively claim they exist.
    bit = original / "bitstream_candidate" / (DESIGN + "_UNRELEASED.bit")
    require(not bit.exists() and not bit.is_symlink(),
            "unexpected bitstream in timing-failure folder: stop and inspect")
    return {
        "status": "M08_D3D2C_ORIGINAL_ROUTED_CHECKPOINT_TIMING_FAILED_NO_BITSTREAM",
        "owner_folder": str(original),
        "routed_checkpoint_path": str(dcp),
        "routed_checkpoint_bytes": dcp.stat().st_size,
        **row,
        "timing_violation_excerpts": path_blocks(original_reports["routed_timing"]),
        "original_reports": {k: str(impl / v) for k, v in REPORTS.items()},
        "original_report_sha256": hashes,
        "bus_skew_report_review_required": True,
        "new_bitstream_exists": False,
        "fpga_programmed": False,
        "physical_32_neuron_parity_verified": False,
        "no_board_actions": True,
        "no_evidence_written": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path,
                        help="Original FIRST native evidence folder, read only")
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.run_dir), indent=2, sort_keys=True))
        return 0
    except (Reject, OSError, ValueError) as exc:
        print("M08_D3D2C_ORIGINAL_ROUTE_DIAGNOSTIC_REJECTED: " + str(exc),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
