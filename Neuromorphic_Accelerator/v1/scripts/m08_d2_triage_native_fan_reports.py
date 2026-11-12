#!/usr/bin/env python3
"""D2 PC-only triage of original K26 fan-routed Vivado reports.

Reads independent native report TEXT as evidence. It neither invokes Vivado
nor opens a DCP, changes a file, touches the KV260 or claims runtime safety.
Expect an unverified status even when the original routed design is consistent.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

SHA = "aea9bb224006907cf7e62c2a135ec36eda4582b15e8cf6575805f7b807b94b0e"
FILES = (
    "10_dcp_identity.txt",
    "11_dcp_timing.rpt",
    "12_dcp_drc.rpt",
    "14_dcp_clock_utilization.rpt",
    "15_dcp_clock_interaction.rpt",
    "16_dcp_reset_net_inventory.txt",
    "17_dcp_cdc.rpt",
)
NET = re.compile(
    r"m08_page_ps_i/ctrl_sc/inst/[A-Za-z0-9_/]+/mi_handler_m_sc_areset_pipe"
)


class TriageError(ValueError):
    pass


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise TriageError(reason)


def unique_int(text: str, pattern: str, label: str) -> int:
    found = re.findall(pattern, text, flags=re.MULTILINE)
    require(len(found) == 1, "missing/ambiguous original report value " + label)
    return int(found[0])


def report_contents(folder: Path) -> tuple[dict[str, str], dict[str, str]]:
    require(folder.is_dir() and not folder.is_symlink(),
            "reports directory absent or symlinked")
    original = {}
    digests = {}
    for name in FILES:
        path = folder / name
        require(path.is_file() and not path.is_symlink(), "missing/unsafe report " + name)
        data = path.read_bytes()
        require(len(data) > 90, "empty/implausibly short report " + name)
        original[name] = data.decode("utf-8")
        digests[name] = sha256(data).hexdigest()
    return original, digests


def assess(folder: Path) -> dict:
    reports, digests = report_contents(folder)
    ident = {}
    for line in reports[FILES[0]].splitlines():
        parts = line.split("=", 1)
        require(len(parts) == 2 and parts[0] not in ident,
                "malformed/duplicate identity metadata line")
        ident[parts[0]] = parts[1]
    expected = {
        "schema": "m08-d2-native-fan-dcp-readonly-v1",
        "dcp_sha256": SHA,
        "vivado": "2025.2",
        "part": "xck26-sfvc784-2LV-c",
        "top": "m08_page_ps_wrapper",
        "fan_pin": "A12",
        "fan_iostandard": "LVCMOS33",
        "fan_direction": "OUT",
        "original_routed_dcp": "YES",
        "root_cause_proven": "NO",
        "physical_mmio_performed": "NO",
        "new_bitstream_created": "NO",
        "board_programmed": "NO",
    }
    for key, value in expected.items():
        require(ident.get(key) == value, "wrong original identity " + key)
    clock_count = int(ident.get("clock_count", "0"))
    require(clock_count >= 1, "no declared routed clocks")
    wns = float(ident.get("wns_ns", "nan"))
    whs = float(ident.get("whs_ns", "nan"))
    require(wns == 5.355 and whs == 0.029,
            "routed timing metrics do not match accepted original fan DCP")

    timing = reports["11_dcp_timing.rpt"]
    require("Design State      : Routed" in timing,
            "timing report is not from routed design")
    require("All user specified timing constraints are met." in timing,
            "native timing report did not meet constraints")
    for x in ("checking no_clock (0)", "checking unconstrained_internal_endpoints (0)"):
        require(x in timing, "native timing failed coverage item: " + x)
    require(re.search(r"clk_pl_0\s+\{0\.000 5\.000\}\s+10\.000\s+100\.000", timing),
            "missing native 100MHz clk_pl_0 summary")
    require(re.search(r"clk_pl_1\s+\{0\.000 5\.000\}\s+10\.000\s+100\.000", timing),
            "missing declared but unused clk_pl_1 entry")
    for metric in ("5.355", "0.029"):
        require(metric in timing, "missing genuine timing slack " + metric)

    drc = reports["12_dcp_drc.rpt"]
    require("Design State : Fully Routed" in drc and "Checks found: 1" in drc,
            "DRC no longer original fully routed single warning")
    require(re.search(r"\|\s*RTSTAT-10\s*\|\s*Warning\s*\|[^\n]*\|\s*1\s*\|", drc),
            "RTSTAT-10 warning changed")
    require("15 net(s) have no routable loads." in drc,
            "reset-pipeline no-routable-load warning changed")
    drc_names = set(NET.findall(drc))
    require(len(drc_names) == 14, "original DRC reset-pipeline readable name count changed")

    inventory = reports["16_dcp_reset_net_inventory.txt"]
    lines = inventory.splitlines()
    matches = {line.split("|", 1)[1] for line in lines if line.startswith("RESET_NET|")}
    count = unique_int(inventory, r"^matching_net_count=(\d+)$", "reset inventory")
    require(count == len(matches) == 20, "reset inventory original 20-net match changed")
    require(drc_names <= matches, "DRC named nets not present in routed inventory")
    require("reset_warning_proven_root_cause=NO" in inventory,
            "reset inventory incorrectly claims proven hardware root cause")

    clock = reports["14_dcp_clock_utilization.rpt"]
    require("PS8/PLCLK[0]" in clock and "BUFG_PS/O" in clock,
            "native PS PL0->BUFG_PS routing not in clock utilization report")
    require(re.search(r"\|\s*1678\s*\|\s*0\s*\|\s*10\.000\s*\|\s*clk_pl_0", clock),
            "fan-route original 1678 clock-load path missing")

    interaction = reports["15_dcp_clock_interaction.rpt"]
    require(re.search(
        r"clk_pl_0\s+clk_pl_0\s+rise - rise\s+5\.35\s+0\.00\s+0\s+4591\s+10\.00\s+Clean\s+Partial False Path",
        interaction),
        "original same-domain partial false path classification changed")

    cdc = reports["17_dcp_cdc.rpt"]
    require("CDC Report" in cdc and "Design State : Routed" in cdc,
            "CDC report not a genuine routed report")
    cdc_body = cdc.split("CDC Report", 1)[1].strip()
    cdc_status = ("EMPTY_REPORT_NO_CDC_SIGNOFF"
                  if cdc_body == "" else "NONEMPTY_REPORT_REQUIRES_REVIEW")

    opt = folder / "13_dcp_methodology.rpt"
    methodology_state = ("PRESENT_REQUIRES_REVIEW" if opt.is_file() and not opt.is_symlink()
                         else "NOT_PROVIDED_NO_SIGNOFF")
    optional_exceptions = folder / "18_dcp_exception_coverage.rpt"
    ignored_path_sample = folder / "19_dcp_ignored_paths_inventory.txt"
    return {
        "schema": "m08-d2-original-native-fan-report-triage-v1",
        "status": "ORIGINAL_ROUTED_STATIC_REPORTS_CONSISTENT_RUNTIME_ROOT_CAUSE_OPEN",
        "original_routed_dcp_sha256": SHA,
        "actual_native_report_sha256": digests,
        "identity": {
            "part": ident["part"], "top": ident["top"],
            "fan_pin": ident["fan_pin"], "fan_iostandard": ident["fan_iostandard"],
            "declared_clock_count": clock_count,
        },
        "routed_timing": {
            "setup_wns_ns": wns,
            "hold_whs_ns": whs,
            "pl0_assumed_mhz": 100,
            "pl0_route_loads": 1678,
            "pl1_declared_but_no_timed_endpoints_shown": True,
            "zero_unconstrained_internal_endpoints": True,
        },
        "smartconnect_reset": {
            "drc_rule": "RTSTAT-10",
            "drc_counted_nets": 15,
            "drc_explicit_named_nets": len(drc_names),
            "net_inventory_pattern_matches": count,
            "unresolved": True,
        },
        "timing_exceptions": {
            "same_clock_partial_false_path": True,
            "coverage": ("PRESENT_REVIEW_REQUIRED" if optional_exceptions.is_file()
                         else "NOT_PROVIDED_REVIEW_REQUIRED"),
            "ignored_path_sample": ("PRESENT_NOT_EXHAUSTIVE"
                                    if ignored_path_sample.is_file()
                                    else "NOT_PROVIDED"),
            "signed_off": False,
        },
        "cdc": cdc_status,
        "methodology": methodology_state,
        "physical_runtime": {
            "failed_boot_clock_liveness_verified": False,
            "failed_boot_reset_release_verified": False,
            "ps_afi_and_hpm0_state_verified": False,
            "ps_atb4_timeout_armed_verified": False,
            "axi_response_verified": False,
            "rcu_stall_root_cause_proven": False,
            "hardware_retry_authorized": False,
        },
        "missing_or_open_evidence": [
            "original failure-state PS clock/reset/AFI/ATB settings unavailable",
            "methodology report not reviewed here",
            "same-domain false-path exception coverage requires review",
            "SmartConnect RTSTAT-10 requires source/vendor review",
            "CDC empty report is not a certification",
            "original live AXI response and fault-address trace unavailable",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reports-dir", required=True, type=Path)
    args = ap.parse_args()
    try:
        finding = assess(args.reports_dir)
    except (TriageError, OSError, UnicodeError, KeyError, TypeError) as exc:
        print("M08_D2_NATIVE_REPORT_TRIAGE_REJECTED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(finding, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
