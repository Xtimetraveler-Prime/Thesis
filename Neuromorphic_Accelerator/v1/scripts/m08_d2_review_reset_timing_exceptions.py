#!/usr/bin/env python3
"""M08 D2: PC-only review of owner-original K26 fan-DCP timing exceptions.

This analyzer reads FOUR existing vendor text reports. No Vivado, hardware,
JTAG, PL manager, AXI/MMIO, DCP mutation, or written outputs. Static routes
are NOT physical proof of a running PL clock or protected PS-to-PL bus.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ORIGINAL_DCP_SHA = "aea9bb224006907cf7e62c2a135ec36eda4582b15e8cf6575805f7b807b94b0e"
NAMES = (
    "10_dcp_identity.txt",
    "13_dcp_methodology.rpt",
    "18_dcp_exception_coverage.rpt",
    "19_dcp_ignored_paths_inventory.txt",
)
EXCEPTION = re.compile(
    r"^\s*(\d+)\s+False Path\s+false\s+false\s+1\s+(pins|cells)\s+"
    r"(\d+)\s+(\d+\.\d+)\s*$"
)
STAGE = re.compile(
    r"^(m08_page_ps_i/ctrl_sc/inst/.+/"
    r"(?:s_sc_)?xpm_cdc_async_rst_inst)/arststages_ff_reg\[([012])\]/CLR$"
)
START = (
    "m08_page_ps_i/ctrl_sc/inst/clk_map/psr_aclk/U0/"
    "ACTIVE_LOW_BSR_OUT_DFF[0].FDRE_BSR_N/C"
)


class ReviewRejected(ValueError):
    pass


def must(valid: bool, why: str) -> None:
    if not valid:
        raise ReviewRejected(why)


def read_input(folder: Path, name: str) -> tuple[str, str]:
    p = folder / name
    must(p.is_file() and not p.is_symlink(),
         "missing/symlinked original Vivado file: " + name)
    b = p.read_bytes()
    must(len(b) > 150, "implausibly short original Vivado file: " + name)
    return b.decode("utf-8"), sha256(b).hexdigest()


def inspect(folder: Path) -> dict:
    must(folder.is_dir() and not folder.is_symlink(), "invalid report folder")
    original = {}
    receipts = {}
    for name in NAMES:
        original[name], receipts[name] = read_input(folder, name)

    identity: dict[str, str] = {}
    for line in original[NAMES[0]].splitlines():
        pair = line.split("=", 1)
        must(len(pair) == 2 and pair[0] not in identity,
             "invalid/duplicate identity line")
        identity[pair[0]] = pair[1]
    accepted = {
        "schema": "m08-d2-native-fan-dcp-readonly-v1",
        "vivado": "2025.2",
        "dcp_sha256": ORIGINAL_DCP_SHA,
        "part": "xck26-sfvc784-2LV-c",
        "top": "m08_page_ps_wrapper",
        "fan_pin": "A12",
        "fan_iostandard": "LVCMOS33",
        "fan_direction": "OUT",
        "original_routed_dcp": "YES",
        "exception_coverage_report": "GENERATED_REQUIRES_OWNER_REVIEW",
        "ignored_paths_diagnostic": "SAMPLED_NOT_EXHAUSTIVE",
        "ignored_paths_sample_count": "30",
        "timing_exceptions_signed_off": "NO",
        "live_clock_reset_or_atb_verified": "NO",
        "root_cause_proven": "NO",
        "physical_mmio_performed": "NO",
        "new_bitstream_created": "NO",
        "board_programmed": "NO",
    }
    for key, value in accepted.items():
        must(identity.get(key) == value, "identity mismatch " + key)

    methodology = original["13_dcp_methodology.rpt"]
    must("Vivado v.2025.2" in methodology and
         "Design State : Fully Routed" in methodology and
         "Design       : m08_page_ps_wrapper" in methodology,
         "methodology wrong source/tool/routed design")
    m = re.findall(r"^\s*Checks found:\s*(\d+)\s*$",
                   methodology, flags=re.MULTILINE)
    must(m == ["0"], "methodology violations or missing original count")

    coverage = original["18_dcp_exception_coverage.rpt"]
    must("Vivado v.2025.2" in coverage and
         "Design State      : Routed" in coverage and
         "Exceptions Report" in coverage and
         "report_exceptions -coverage" in coverage,
         "exception coverage wrong command/tool/routed source")
    entries = []
    for line in coverage.splitlines():
        if re.match(r"^\s*\d+\s+False Path", line):
            match = EXCEPTION.fullmatch(line)
            must(match is not None, "unexpected timing exception format")
            position, kind, endpoints, percentage = match.groups()
            entries.append({
                "position": int(position), "object_kind": kind,
                "endpoints": int(endpoints), "coverage_percent": float(percentage),
            })
    must(len(entries) == 29, "original exception row count changed")
    must(len({row["position"] for row in entries}) == 29,
         "duplicate exception position")
    pins = [r for r in entries if r["object_kind"] == "pins"]
    cells = [r for r in entries if r["object_kind"] == "cells"]
    must(len(pins) == 25 and all(r["endpoints"] == 3 and
             r["coverage_percent"] == 100.0 for r in pins),
         "original pin exception coverage drift")
    must(len(cells) == 4 and
         [(r["position"], r["endpoints"], r["coverage_percent"])
          for r in cells] == [
              (48, 1, 33.33), (49, 0, 0.0),
              (50, 0, 0.0), (51, 1, 0.0)],
         "original zero/partial cell exception coverage drift")

    inv = original["19_dcp_ignored_paths_inventory.txt"]
    must(inv.startswith("schema=m08-d2-routed-ignored-timing-paths-sample-v1\n"),
         "wrong ignored-path schema")
    for expected in ("sample_max_paths=30", "status=SAMPLED_NOT_EXHAUSTIVE",
                     "sample_returned=30", "all_false_paths_reviewed=NO",
                     "runtime_clock_reset_proven=NO"):
        must(inv.splitlines().count(expected) == 1,
             "missing/duplicate ignored-path marker: " + expected)
    samples = [x.split("|", 2) for x in inv.splitlines()
               if x.startswith("IGNORED_PATH|")]
    must(len(samples) == 30 and all(len(row) == 3 for row in samples),
         "missing original 30 ignored-path samples")
    groups: dict[str, set[int]] = defaultdict(set)
    for _, src, dest in samples:
        must(src == START, "ignored path not from known SmartConnect reset clock")
        stage = STAGE.fullmatch(dest)
        must(stage is not None, "ignored path not at XPM async reset clear pin")
        must(int(stage.group(2)) not in groups[stage.group(1)],
             "duplicate reset synchronizer stage")
        groups[stage.group(1)].add(int(stage.group(2)))
    must(len(groups) == 10 and all(stages == {0, 1, 2} for stages in groups.values()),
         "ignored paths not ten separate three-stage reset synchronizers")

    return {
        "schema": "m08-d2-native-reset-timing-exception-review-v1",
        "status": "ORIGINAL_ROUTED_RESET_EXCEPTIONS_CHARACTERIZED_RUNTIME_UNPROVEN",
        "original_dcp_sha256": ORIGINAL_DCP_SHA,
        "input_sha256": receipts,
        "methodology": {
            "checks_found": 0, "native_report": True,
            "physical_clock_reset_or_axi_proven": False,
        },
        "exception_coverage": {
            "false_path_rows": len(entries),
            "pin_exceptions_100_percent_three_endpoints": len(pins),
            "cell_entries": cells,
            "cell_entries_zero_percent": 3,
            "fully_ignored_or_nonexistent_positions_not_yet_classified": [49, 50, 51],
            "coverage_not_timing_slack": True,
            "timing_exception_signoff": False,
        },
        "ignored_timing_sample": {
            "sample_size": len(samples),
            "unique_startpoints": 1,
            "unique_reset_synchronizers": len(groups),
            "stage_indices_each": [0, 1, 2],
            "all_endpoints_async_clear": True,
            "all_paths_checked": False,
            "reset_synchronizer_groups": sorted(groups),
        },
        "next_offline_evidence": [
            "report_exceptions -ignored from same original DCP",
            "report_exceptions -summary from same original DCP",
            "source/stock Linux PS PL0 clock and AFI ownership audit",
        ],
        "physical_hardware": {
            "m08_quarantine_active": True,
            "runtime_pl0_verified": False,
            "runtime_hpm0_axi_response_verified": False,
            "ps_atb4_enabled_at_failed_boot_verified": False,
            "rcu_stall_cause_proven": False,
            "new_image_approved_for_board": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reports-dir", type=Path, required=True)
    args = ap.parse_args()
    try:
        summary = inspect(args.reports_dir)
    except (ReviewRejected, OSError, UnicodeError) as exc:
        print("M08_D2_RESET_EXCEPTION_REVIEW_REJECTED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
