#!/usr/bin/env python3
"""Build XSim compile/include plan from original saved Vivado source report.

A Vivado compile-order report lists .vh include HEADERS separately from
compilable .sv/.v/.vhd. All original header directories must be passed to
xvlog even when their header basename doesn't begin 'sc_' or 'axi_...'.
This is not a warning investigation, vendor RTL copy, or hardware action.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

EXPECTED_D3 = "neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
MEM_SC = "m05_12d3_real_signed32_hls_six_control_address_candidate_mem_sc_0"
REQUIRED_INCLUDE = "axi_infrastructure_v1_1_0.vh"
RTL_SUFFIX = {".v", ".sv", ".vhd"}
HEADER_SUFFIX = {".vh", ".svh"}
SUPPORTED = RTL_SUFFIX | HEADER_SUFFIX


def plan(original: Path, report_text: str) -> dict:
    if original.name != EXPECTED_D3:
        raise ValueError("exact previously accepted D3 path required")
    original = original.resolve(strict=True)
    if not original.is_dir():
        raise ValueError("original D3 missing")
    lines = report_text.splitlines()
    source_rows = [row.split("|", 1)[1] for row in lines
                   if row.startswith("SIM_SOURCE|")]
    if len(source_rows) != 186 or len(set(source_rows)) != 186:
        raise ValueError("expected 186 unique original Vivado source declarations")
    paths = []
    for name in source_rows:
        file = Path(name)
        # All report entries, including irrelevant project paths, are
        # parsed. Only paths under this EXACT D3 can enter the plan.
        if not file.is_absolute() or not file.is_relative_to(original):
            continue
        suffix = file.suffix.lower()
        if suffix not in SUPPORTED:
            continue
        # Some of the 186 whole-project entries refer to unrelated HLS,
        # PS or testbench files. Only selected original memory RTL and ALL
        # original header paths affect this isolated vendor-IP compile.
        # Do not block M06 because an UNUSED whole-project file is absent.
        if suffix in RTL_SUFFIX:
            mem = f"/{MEM_SC}/" in file.as_posix()
            shared = "/ipshared/" in file.as_posix() and file.name.startswith(
                ("sc_", "axi_register_slice_v2_1",
                 "axi_infrastructure_v1_1", "util_vector_logic_v2_0",
                 "xlconstant_v1_1", "proc_sys_reset_v5_0"))
            if not mem and not shared:
                continue
        # Authentication includes actual existence. Never follow an
        # escaped symlink into another source tree.
        if not file.is_file() or not file.resolve().is_relative_to(original):
            raise ValueError("missing or escaped original simulation source: "+name)
        paths.append(file)
    includes = [p for p in paths if p.suffix.lower() in HEADER_SUFFIX]
    matches = [p for p in includes if p.name == REQUIRED_INCLUDE]
    if len(matches) != 1:
        raise ValueError("original AXI infrastructure header must appear exactly once")
    chosen = []
    for p in paths:
        if p.suffix.lower() not in RTL_SUFFIX:
            continue
        name = p.name
        mem = f"/{MEM_SC}/" in p.as_posix()
        shared = "/ipshared/" in p.as_posix() and name.startswith(
            ("sc_", "axi_register_slice_v2_1", "axi_infrastructure_v1_1",
             "util_vector_logic_v2_0", "xlconstant_v1_1", "proc_sys_reset_v5_0"))
        if mem or shared:
            chosen.append(p)
    if len(chosen) < 40 or len(chosen) != len(set(chosen)):
        raise ValueError("original memory subgraph compilation selection incomplete")
    if not any(p.name == MEM_SC+".sv" for p in chosen):
        raise ValueError("original memory IP simulator wrapper missing")
    if not any(p.name == "bd_13bd.v" for p in chosen):
        raise ValueError("original nested memory BD missing")
    # Retain ORIGINAL compile order from Vivado rather than sorting.
    include_dirs = list(dict.fromkeys(
        [p.parent for p in includes] + [p.parent for p in chosen]
    ))
    if matches[0].parent not in include_dirs:
        raise ValueError("necessary original AXI header include dir missing")
    manifest = {
        "schema": "m06-original-vivado-compile-plan-v2",
        "original_D3": str(original),
        "vivado_original_source_count": 186,
        "selected_vendor_compilation_source_count": len(chosen),
        "verilog_files": [str(p) for p in chosen
                          if p.suffix.lower() in (".v", ".sv")],
        "vhdl_files": [str(p) for p in chosen if p.suffix.lower() == ".vhd"],
        "original_include_files": [str(p) for p in includes],
        "include_directories": [str(p) for p in include_dirs],
        "axi_infrastructure_header": str(matches[0]),
        "axi_infrastructure_header_sha256": hashlib.sha256(
            matches[0].read_bytes()).hexdigest(),
        "all_original_headers_sha256": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in includes
        },
        "non_original_vendor_source_writes": "FORBIDDEN",
        "vendor_XSim_executed": False,
        "physical_board": "NOT_AUTHORIZED",
    }
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    try:
        if a.output.exists() or not a.output.parent.is_dir():
            raise ValueError("compile plan output must be a new file in an existing directory")
        result = plan(a.original, a.report.read_text(encoding="utf-8"))
        with a.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, sort_keys=True, indent=2)
            stream.write("\n")
    except (OSError, ValueError) as exc:
        print(f"M06 original vendor compile plan ERROR: {exc}", file=sys.stderr)
        return 2
    print("M06 original vendor compile plan READY: "
          f"{result['selected_vendor_compilation_source_count']} original RTL files, "
          f"{len(result['original_include_files'])} authentic header files, "
          "AXI infrastructure header mapped; REAL VENDOR XSIM NOT RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
