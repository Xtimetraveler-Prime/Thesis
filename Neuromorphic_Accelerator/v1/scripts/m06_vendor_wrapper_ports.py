#!/usr/bin/env python3
"""Find ORIGINAL saved vendor mem_sc HDL wrapper/ANSI ports without Vivado.

This consumes the PREVIOUS owner's 02_original_mem_sc_ports.txt (SIM_SOURCE,
MEM_PROJECT_SOURCE paths) and reads only original D3 generated Verilog files.
It NEVER writes original sources, compiles RTL, fabricates a port list or
claims a functional vendor XSim PASS. If no readable public wrapper exists,
it returns a bounded "MODEL_HEADER_UNAVAILABLE" result rather than guessing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from m06_verilog_port_decls import module_port_contracts

D3_NAME = "neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
SOURCE_MAX_BYTES = 2_000_000
MODULE_LIMIT = 200
MODULE_RE = re.compile(
    r"\bmodule\s+([a-zA-Z_][a-zA-Z0-9_$]*)\s*(?:#\s*\(.*?\)\s*)?\("
    r"(.{0,150000}?)\)\s*;", re.S)
PORT_RE = re.compile(
    r"\b(input|output|inout)\b\s*"
    r"(?:(?:wire|logic|reg|signed|unsigned)\s+)*"
    r"(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?"
    r"([a-zA-Z_][a-zA-Z0-9_$]*)", re.I)


def inspect(original: Path, captured_report: Path) -> dict:
    if original.name != D3_NAME or not original.is_dir():
        raise ValueError("exact accepted original D3 directory required")
    if not captured_report.is_file():
        raise ValueError("previous original Vivado port report missing")
    report = captured_report.read_text(encoding="utf-8")
    lines = report.splitlines()
    if lines.count(
        "RESULT|ORIGINAL_PORTS_CAPTURED_FOR_ONE_VENDOR_FUNCTIONAL_XSIM_TRIAL") != 1:
        raise ValueError("previous original Vivado port capture incomplete")
    if lines.count("SOURCE_XPR|" + str(
        (original/"13_file_backed_project/m05_d3_output_products.xpr").resolve())) != 1:
        raise ValueError("report does not attest this exact original XPR")
    root = (original/"13_file_backed_project").resolve()
    listed = [line.split("|", 1)[1] for line in lines
              if line.startswith(("SIM_SOURCE|", "MEM_PROJECT_SOURCE|"))]
    # Do not accept user-provided arbitrary file paths, even with a report:
    # only generated HDL within accepted original project is inspected.
    candidates: list[Path] = []
    for raw in dict.fromkeys(listed):
        path = Path(raw)
        if not path.is_absolute() or not path.is_relative_to(root):
            continue
        if "mem_sc" not in path.as_posix().lower():
            continue
        if path.suffix.lower() not in (".v", ".sv"):
            continue
        if path.is_file() and path.stat().st_size <= SOURCE_MAX_BYTES:
            candidates.append(path)

    wrappers = []
    skipped = 0
    for path in candidates:
        body = path.read_text(encoding="utf-8", errors="replace")
        found = module_port_contracts(body)
        for parsed in found[:MODULE_LIMIT]:
            name = parsed["module"]
            axi_ports = parsed["axi_ports"]
            if "mem_sc" not in name.lower() and not axi_ports:
                continue
            wrappers.append({
                "module": name,
                "source_relative_to_original": str(path.relative_to(original)),
                "source_sha256": hashlib.sha256(body.encode()).hexdigest(),
                "declaration_style": parsed["declaration_style"],
                "ansi_port_count": len(axi_ports) + len(parsed["other_ports"]),
                "axi_port_count": len(axi_ports),
                "ansi_axi_ports": axi_ports[:260],
                "other_ports": parsed["other_ports"][:40],
                "port_header_only_not_elaborated": True,
                "source_file_is_original_read_only": True,
            })
        skipped += max(0, len(found)-MODULE_LIMIT)
    wrappers.sort(key=lambda x: (-x["axi_port_count"], x["module"]))
    usable = sum(x["axi_port_count"] > 0 for x in wrappers)
    return {
        "scope": "M06_ORIGINAL_VENDOR_HEADER_ONLY_NO_VIVADO_NO_XSIM",
        "original_d3": str(original.resolve()),
        "original_report_sha256": hashlib.sha256(report.encode()).hexdigest(),
        "source_candidates_from_previous_vivado_report": len(candidates),
        "wrapper_candidates": wrappers[:30],
        "wrapper_candidate_count": len(wrappers),
        "wrappers_with_ansi_axi_ports": usable,
        "non_ansi_compatible_parser": True,
        "ports_are_unelaborated_declarations_only": True,
        "module_scan_limit_truncated_modules": skipped,
        "status": ("MODULE_HEADERS_FOUND_NOT_COMPILED" if usable
                   else "MODEL_HEADER_UNAVAILABLE_NO_GUESSED_WRAPPER"),
        "physical_board": "NOT_ACCESSED",
        "vendor_functional_axi": "NOT_EXECUTED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError("new exclusive output path required")
        result = inspect(args.original.resolve(strict=True), args.report)
        with args.output.open("x", encoding="utf-8") as out:
            json.dump(result, out, indent=2, sort_keys=True)
            out.write("\n")
    except (OSError, ValueError) as exc:
        print(f"M06 vendor module header extraction FAILED: {exc}", file=sys.stderr)
        return 2
    print(f"M06 ORIGINAL HDL HEADER READ ONLY: {result['status']}; "
          f"candidate modules={result['wrapper_candidate_count']}; "
          f"AXI wrappers={result['wrappers_with_ansi_axi_ports']}; "
          "REAL VENDOR XSIM NOT RUN")
    return 0 if result["wrappers_with_ansi_axi_ports"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
