#!/usr/bin/env python3
"""Read-only original-evidence DRC inventory for blocked D3.D neural builds.

This is a DIAGNOSTIC, not a waiver or bitstream approval. It validates the
original DRC file against the original owner SHA ledger, prints the actual
RTSTAT-10 detail and its sample net names, then runs the strict existing gate.
Never changes build artifacts and never connects to a device.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
import re
import sys

import m08_d3d_neuron_gate as gate

RULE = "RTSTAT-10"
DRC_REL = "reports/20_route_drc.rpt"


def inspect(run_dir: Path) -> str:
    if not run_dir.is_dir() or run_dir.is_symlink():
        raise ValueError("run-dir must be a real evidence directory")
    if run_dir.parent.name != "M08" or not re.fullmatch(
        r"m08_d3d_neuron_[A-Za-z0-9]+", run_dir.name
    ):
        raise ValueError("expected original M08 D3.D native evidence directory")
    ledger = gate.read(run_dir / "99_evidence_sha256.txt", 20000)
    drc = gate.read(run_dir / DRC_REL, 3000000)
    matches = re.findall(
        rb"(?m)^([0-9a-f]{64})  reports/20_route_drc\.rpt$",
        ledger,
    )
    if len(matches) != 1 or sha256(drc).hexdigest().encode() != matches[0]:
        raise ValueError("original DRC file SHA does not match owner evidence ledger")
    text = drc.decode("utf-8", errors="replace")
    lines = text.splitlines()
    details = [i for i, line in enumerate(lines) if
               re.match(r"^[A-Z]+-\d+#\d+\s+(Warning|Critical Warning|Error)\s*$", line)]
    report = [
        "M08_D3D_DRC_EVIDENCE_SHA256=VERIFIED",
        f"M08_D3D_DRC_FILE={run_dir / DRC_REL}",
        "M08_D3D_DRC_DIAGNOSTIC_ONLY_NOT_A_RELEASE=YES",
    ]
    counts = re.findall(r"(?m)^\s*Checks found:\s*(\d+)\s*$", text)
    report.append("DRC_CHECKS_FOUND=" + (",".join(counts) if counts else "<missing>"))
    summary = re.findall(
        r"(?m)^\|\s*([A-Z]+-\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*(\d+)\s*\|\s*$",
        text,
    )
    report.append("DRC_SUMMARY_ROWS:")
    if summary:
        for code, severity, desc, qty in summary:
            report.append(f"  {code}: {severity.strip()} x{qty} -- {desc.strip()}")
    else:
        report.append("  <missing/none>")
    rtstat = [(j, i) for j, i in enumerate(details)
              if lines[i].startswith(RULE + "#")]
    report.append(f"RTSTAT_DETAIL_COUNT={len(rtstat)}")
    if not rtstat:
        report.append("RTSTAT_DETAILS_MISSING_OR_NOT_FORMATTED_AS_EXPECTED")
    for ordinal, start in rtstat:
        end = details[ordinal + 1] if ordinal + 1 < len(details) else len(lines)
        block = lines[start:end]
        report.append("RTSTAT_DETAIL_BEGIN")
        for n, line in enumerate(block[:140], start=start + 1):
            report.append(f"  L{n}: {line}")
        if len(block) > 140:
            report.append(f"  <truncated {len(block)-140} further lines; inspect original>")
        report.append("RTSTAT_DETAIL_END")
        body = "\n".join(block)
        claimed = re.search(r"(\d+)\s+net\(s\) have no routable loads", body)
        sample_count = re.search(r"\(the first\s+(\d+)\s+of\s+(\d+)\s+listed\)", body)
        report.append("RTSTAT_NETS_WITH_NO_LOADS="
                      + (claimed.group(1) if claimed else "<missing>"))
        report.append("RTSTAT_SAMPLE_DECLARED="
                      + (sample_count.group(0) if sample_count else "<missing>"))
        sample = re.search(
            r"problem bus\(es\) and/or net\(s\) are (.*?)\s*"
            r"\(the first\s+\d+\s+of\s+\d+\s+listed\)",
            body, flags=re.S,
        )
        if sample is not None:
            paths = [p.strip() for p in sample.group(1).split(",") if p.strip()]
            vendor_prefixes = (
                "dbg_hub/inst/",
                "m08_d3d_lif_jtag_i/jtag_axi/inst/",
            )
            report.append(f"RTSTAT_PARSED_SAMPLE_PATHS={len(paths)}")
            for p in paths:
                scope = "known_debug_prefix" if p.startswith(vendor_prefixes) else "UNREVIEWED"
                report.append(f"  {scope}: {p}")
    report.append("DRC_DIAGNOSTIC_END")
    return "\n".join(report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(inspect(args.run_dir))
    except (OSError, ValueError, UnicodeError, gate.Reject) as exc:
        print("M08_D3D_DRC_DIAGNOSTIC_REJECTED: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
