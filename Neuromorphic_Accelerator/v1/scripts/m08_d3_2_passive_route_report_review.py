#!/usr/bin/env python3
"""M08 D3.2 owner-PC PASSIVE route semantic and receipt review (read-only).

A zero-findings DRC on a PS8+OBUF fan scaffold is useful but does not certify
a fan, its running firmware, or a future clocked neuromorphic accelerator.
WNS/TNS=NA with zero fabric FFs is NO TIMING MARGIN MEASUREMENT, not pass.
No Vivado, device access, hardware release, bitstream, or file writes.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
RECEIPTS = {
    "99_evidence_sha256.txt": {
        "01_passive_bd_vivado.log", "02_passive_bd_vivado.jou",
        "03_passive_synth_vivado.log", "04_passive_synth_vivado.jou",
        "output/10_d3a_passive_bd_readback.txt",
        "output/11_d3a_passive_bd_export.tcl",
        "output/12_d3a_fan_a12.xdc",
        "output/20_passive_synth_readback.txt",
        "output/21_passive_synth_utilization.rpt",
        "output/22_passive_synth_timing.rpt",
        "30_pc_source_and_native_review.json",
    },
    "98_route_evidence_sha256.txt": {
        "05_passive_route_vivado.log", "06_passive_route_vivado.jou",
        "output/40_passive_route_readback.txt",
        "output/41_passive_route_timing.rpt",
        "output/42_passive_route_drc.rpt",
        "output/43_passive_route_utilization.rpt",
        "output/44_passive_route_clocks.rpt",
        "50_pc_route_evidence_review.json",
    },
}
REPORTS = {
    "timing": "output/41_passive_route_timing.rpt",
    "drc": "output/42_passive_route_drc.rpt",
    "utilization": "output/43_passive_route_utilization.rpt",
    "clocks": "output/44_passive_route_clocks.rpt",
}
REQUIRED_PRIMITIVES = {"PS8": 1, "OBUF": 1}
REQUIRED_ZERO_FABRIC = ("CLB LUTs", "CLB Registers")


class ReviewRejected(ValueError):
    pass


def demand(value: bool, explanation: str) -> None:
    if not value:
        raise ReviewRejected(explanation)


def regular_bytes(file: Path, base: Path, cap: int = 8_000_000) -> bytes:
    demand(file.is_file() and not file.is_symlink(),
           "receipt candidate missing/not regular/symlink: " + file.name)
    # Refuse any symlink ancestor below the run root as well.
    for folder in file.relative_to(base).parents:
        if str(folder) != ".":
            demand(not (base / folder).is_symlink(),
                   "linked evidence ancestor: " + str(folder))
    size = file.stat().st_size
    demand(0 < size <= cap, "evidence empty/oversize: " + file.name)
    return file.read_bytes()


def verify_ledger(run: Path, ledger: str, exact: set[str]) -> dict[str, str]:
    blob = regular_bytes(run / ledger, run, 10_000)
    lines = blob.decode("ascii").splitlines()
    demand(len(lines) == len(exact), "receipt entry count changed: " + ledger)
    seen: dict[str, str] = {}
    for line in lines:
        m = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_./-]+)", line)
        demand(m is not None, "unexpected SHA ledger format: " + ledger)
        digest, relative = m.groups()
        path = PurePosixPath(relative)
        demand(not path.is_absolute() and ".." not in path.parts
               and relative not in seen and relative in exact,
               "unknown/duplicate/path-traversal ledger file: " + relative)
        seen[relative] = digest
        observed = sha256(regular_bytes(run / relative, run)).hexdigest()
        demand(observed == digest, "changed receipt content: " + relative)
    demand(set(seen) == exact, "missing expected SHA evidence: " + ledger)
    return seen


def row_count(report: str, key: str) -> int:
    # Only use the exact table-row first count, not text elsewhere in reports.
    pattern = r"(?m)^\|\s*" + re.escape(key) + r"\s*\|\s*(\d+)\s*\|"
    matches = re.findall(pattern, report)
    demand(len(matches) == 1, "missing/duplicate resource row: " + key)
    return int(matches[0])


def parse_timing(report: str) -> dict:
    demand("| Design State      : Routed" in report,
           "timing is not from a routed netlist")
    section = report.split("| Design Timing Summary", 1)
    demand(len(section) == 2, "timing summary absent")
    match = re.search(r"(?m)^\s*WNS\(ns\)\s+TNS\(ns\).*?\n"
                      r"\s*-[-\s]+\n\s*([^\n]+)", section[1])
    demand(match is not None, "missing actual WNS/TNS summary row")
    fields = match.group(1).split()
    demand(len(fields) >= 4, "incomplete timing summary")
    demand(fields[:4] == ["NA", "NA", "NA", "NA"],
           "unexpected nonempty/clocked timing endpoints; new review required")
    for phrase in (
        "There are 0 register/latch pins with no clock.",
        "There are 0 pins that are not constrained for maximum delay.",
        "There are 0 combinational loops in the design.",
    ):
        demand(phrase in report, "timing diagnostics changed: " + phrase)
    demand("All user specified timing constraints are met." in report,
           "Vivado timing-summary message not observed")
    return {
        "WNS_ns": "NA",
        "TNS_ns": "NA",
        "timed_fabric_endpoints": "NONE_REPORTED",
        "meaning": "NO_TIMING_CLOSURE_CLAIM_NO_FABRIC_REGISTERS",
        "future_neuromorphic_timing_proven": False,
        "ps_pl0_runtime_clock_proven": False,
    }


def parse_drc(report: str) -> dict:
    demand("| Design State : Fully Routed" in report,
           "DRC not from the fully routed netlist")
    demand("Ruledeck: default" in report,
           "DRC ruledeck unknown")
    counts = re.findall(r"(?m)^\s*Checks found:\s*(\d+)\s*$", report)
    demand(len(counts) == 1, "ambiguous/missing DRC findings count")
    found = int(counts[0])
    demand(found == 0, "nonzero reported DRC findings require review")
    return {
        "default_ruledeck_reported_findings": 0,
        "reported_drc_findings": "ZERO_IN_CAPTURED_DEFAULT_RULEDECK_ONLY",
        "full_board_or_cooling_verification": False,
    }


def parse_utilization(report: str) -> dict:
    demand("| Design State : Routed" in report,
           "utilization not from a routed netlist")
    fabric = {name: row_count(report, name) for name in REQUIRED_ZERO_FABRIC}
    demand(all(n == 0 for n in fabric.values()),
           "passive design unexpectedly contains timing-relevant fabric")
    primitives = {name: row_count(report, name) for name in REQUIRED_PRIMITIVES}
    demand(primitives == REQUIRED_PRIMITIVES,
           "expected PS8+fan OBUF primitive footprint changed")
    demand(row_count(report, "Bonded IOB") == 1,
           "expected one fan output IOB")
    demand(row_count(report, "DSPs") == 0,
           "passive design unexpectedly used DSP")
    demand(row_count(report, "Block RAM Tile") == 0,
           "passive design unexpectedly used Block RAM")
    demand("Black Boxes" in report, "missing black-box section")
    return {
        "fabric_luts": 0,
        "fabric_registers": 0,
        "PS8": 1,
        "OBUF": 1,
        "bonded_iob": 1,
        "timing_scope": "PASSIVE_FAN_ONLY_NO_CLOCKED_FABRIC",
        "neural_inference_present": False,
    }


def parse_clocks(report: str) -> dict:
    demand("| Design State      : Routed" in report,
           "clock report not from routed netlist")
    clocks = re.findall(
        r"(?m)^(clk_pl_[01])\s+10\.000\s+\{0\.000 5\.000\}\s+P\s+"
        r"\{[^\n]*PS8_i/PLCLK\[([01])\]\}",
        report)
    demand(sorted(clocks) == [("clk_pl_0", "0"), ("clk_pl_1", "1")],
           "reported Vivado clock definitions unexpected")
    return {
        "nominal_vivado_ps_pl_clocks": ["clk_pl_0", "clk_pl_1"],
        "nominal_clock_period_ns": 10.0,
        "boot_clock_owners_or_actual_runtime_enable": "UNKNOWN",
    }


def load_route_gate():
    path = ROOT / "scripts/m08_d3_2_passive_route_gate.py"
    spec = importlib.util.spec_from_file_location("m08_d3_2_route_gate_review", path)
    demand(spec is not None and spec.loader is not None, "missing original route gate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def review_run(run: Path, *, dependency=None) -> dict:
    demand(run.is_dir() and not run.is_symlink(),
           "owner run missing or symlinked")
    demand(re.fullmatch(r"m08_d3_2_passive_synth_[A-Za-z0-9]+", run.name)
           and run.parent.name == "M08",
           "run directory does not match isolated D3.2 evidence")
    route = dependency if dependency is not None else load_route_gate()
    # Existing independent report gate verifies native D3.1, synthesis, route
    # summary and all declarative hardware-ban fields.
    try:
        earlier = route.audit_native(run)
    except route.RouteRejected as exc:
        raise ReviewRejected("original source/native gate refused: " + str(exc)) from exc
    receipts = {
        name: verify_ledger(run, name, expected)
        for name, expected in RECEIPTS.items()
    }
    for name in ("30_pc_source_and_native_review.json",
                 "50_pc_route_evidence_review.json"):
        ledger_obj = json.loads(regular_bytes(run / name, run))
        demand(ledger_obj.get("physical_programming_authorized") is False
               or ledger_obj.get("hardware_mmio_authorized") is False,
               "earlier PC report missing hardware prohibition")
        if name.startswith("50_"):
            native = ledger_obj.get("native", {})
            demand(native.get("bitstream_generated") is False
                   and native.get("hardware_mmio_authorized") is False,
                   "original route PC reviewer cannot grant bitstream/MMIO")
    contents = {
        key: regular_bytes(run / rel, run).decode("utf-8")
        for key, rel in REPORTS.items()
    }
    log = regular_bytes(run / "05_passive_route_vivado.log", run).decode("utf-8")
    demand(not re.search(r"(?m)^(?:ERROR:|CRITICAL WARNING:)", log),
           "Vivado route log contains an error/critical warning")
    warnings = re.findall(r"(?m)^WARNING:\s*(.+)$", log)
    unknown = [w for w in warnings
               if not ("[Board 49-26]" in w
                       or "[Place 30-2953]" in w)]
    # Do NOT silently declare unknown warnings benign.
    demand(not unknown, "unreviewed route warning classes: " +
           ", ".join(w[:90] for w in unknown[:3]))
    return {
        "schema": "m08-d3-2-passive-route-semantic-review-v1",
        "status": "PASSIVE_ROUTE_DRC_ZERO_NO_TIMED_FABRIC_PATHS_HARDWARE_BLOCKED",
        "verified_ledgers": {name: len(contents) for name, contents in receipts.items()},
        "parent_native": earlier["status"],
        "drc": parse_drc(contents["drc"]),
        "timing": parse_timing(contents["timing"]),
        "resources": parse_utilization(contents["utilization"]),
        "clocks": parse_clocks(contents["clocks"]),
        "route_log_warning_count": len(warnings),
        "route_log_warning_classes": {
            "unrelated_board_catalog": sum("[Board 49-26]" in w for w in warnings),
            "no_critical_timing_terminals": sum("[Place 30-2953]" in w for w in warnings),
            "other": len(unknown),
        },
        "fan_port_routed_A12_reported": True,
        "physical_fan_and_boot_rollback_proven": False,
        "physical_programming_authorized": False,
        "protected_hpm0_hardware_ready": False,
        "bitstream_generated_by_this_tool": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = review_run(args.run_dir)
    except (ReviewRejected, OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        print("M08_D3_2_PASSIVE_ROUTE_REVIEW_REJECTED_NO_BOARD: " + str(exc),
              file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
