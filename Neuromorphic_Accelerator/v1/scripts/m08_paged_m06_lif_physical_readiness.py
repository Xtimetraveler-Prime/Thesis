#!/usr/bin/env python3
"""M08.4 owner-local READ-ONLY triage of the first real paged-neural K26 image.

This is a reporting tool, not a release gate. An SHA-correct original
Vivado build does NOT authorize JTAG. Never mutate owner native evidence,
reuse accepted M32Q DRC waivers, or write PS / PL DDR.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import m08_paged_m06_lif_native_review as native

OWNER_DIR = "m08_paged_m06_lif_QFKpXlPW"
OWNER_BIT_SHA = "6a4a71f255adcc79a4131401a3f75eb64f253d3431f5ad1babc0da48479f6494"
REPORTS = (
    "reports/20_route_drc.rpt",
    "reports/21_route_timing.rpt",
    "reports/22_route_utilization.rpt",
    "reports/23_route_clocks.rpt",
)

class Reject(ValueError):
    pass

def require(cond: bool, why: str) -> None:
    if not cond:
        raise Reject(why)

def selected_lines(text: str, max_lines: int = 70) -> list[str]:
    selected = []
    pattern = re.compile(
        r"Checks found:|^(?:[A-Z]+-\d+#\d+\s+)|"
        r"(?:ERROR|CRITICAL WARNING|Warning|WNS\(ns\)|WHS\(ns\)|"
        r"Fmax|100\.00|100\.000|clk_out|pl_clk|Design State|Device\s+:|"
        r"Fully Routed|Timing constraints|Slack|Failing Endpoints)",
        flags=re.IGNORECASE
    )
    for line in text.splitlines():
        if pattern.search(line):
            selected.append(line[:250])
    return selected[:max_lines]

def inspect(run: Path) -> dict:
    require(run.name == OWNER_DIR and
            run.parent == (Path.home() / "Thesis_Evidence/M08"),
            "only the owner-reported first original QFKpXlPW native folder is eligible")
    result = native.inspect(run)
    require(result["candidate_bitstream_sha256"] == OWNER_BIT_SHA,
            "owner original bit SHA differs from separately reported image")
    exit_txt = (run / "02_vivado_exit.txt").read_text(encoding="ascii")
    require(exit_txt.strip() == "vivado_build_exit=0",
            "offline Vivado was not successful")
    report_data = {}
    for rel in REPORTS:
        path = run / rel
        require(path.is_file() and not path.is_symlink() and
                path.stat().st_size < 30_000_000,
                "invalid original report " + rel)
        data = path.read_bytes()
        text = data.decode("utf-8", errors="replace")
        report_data[rel] = {
            "sha256": sha256(data).hexdigest(),
            "size_bytes": len(data),
            "selected_lines": selected_lines(text)
        }
    drc = (run / REPORTS[0]).read_text(encoding="utf-8", errors="replace")
    timing = (run / REPORTS[1]).read_text(encoding="utf-8", errors="replace")
    require("Fully Routed" in drc or "Fully Routed" in timing,
            "native DRC/timing provenance lacks Fully Routed label")
    return {
        "status": "M08_4_FIRST_NATIVE_READ_ONLY_REPORT_TRIAGE_NO_PROGRAM",
        "run": str(run),
        "original_15_sha_entries_verified": True,
        "candidate_bitstream_sha256": OWNER_BIT_SHA,
        "reports": report_data,
        "release_gate": "BLOCKED_PENDING_EXACT_NEW_IMAGE_DRC_TIMING_CLOCK_REVIEW",
        "physical_programming_authorized": False,
        "physical_execution_verified": False,
        "physical_ddr": False,
    }

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        print(json.dumps(inspect(args.run_dir), indent=2, sort_keys=True))
        return 0
    except (Reject, native.Reject, ValueError, OSError) as exc:
        print("M08_4_READINESS_REJECTED: " + str(exc), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
