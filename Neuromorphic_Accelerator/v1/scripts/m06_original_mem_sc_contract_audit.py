#!/usr/bin/env python3
"""Independently audit exact-original Vivado memory-IP BFM port data.

Never turns Vivado SOURCE discovery into functional AXI PASS. Also locate
candidate generated HDL module declarations to design one honest functional
vendor XSim testbench after owner returns the original result.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ORIGINAL = "neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
BD = "m05_12d3_real_signed32_hls_six_control_address_candidate"
ENDPOINTS = {
    **{f"mem_sc/S{i:02d}_AXI": 256 for i in range(4)},
    "mem_sc/M00_AXI": 128,
    "ps/S_AXI_HP0_FPD": 128,
}
SOURCE_LIMIT = 500_000


def inspect(original: Path, report: Path, vivado_log: Path) -> dict:
    if original.name != ORIGINAL or not original.is_dir():
        raise ValueError("exact original accepted D3 path required")
    if not report.is_file() or not vivado_log.is_file():
        raise ValueError("real original Vivado port report and log required")
    lines = report.read_text(encoding="utf-8").splitlines()
    log = vivado_log.read_text(encoding="utf-8", errors="replace")
    if len(lines) < 20 or any("\x00" in row for row in lines):
        raise ValueError("missing or malformed real Vivado port report")
    if lines.count("RESULT|ORIGINAL_PORTS_CAPTURED_FOR_ONE_VENDOR_FUNCTIONAL_XSIM_TRIAL") != 1:
        raise ValueError("original Vivado query did not finish cleanly")
    # Vivado 2025.2 echoes Tcl source lines as commented '# puts ...',
    # so a raw substring count double-counts the SUCCESS token. Authenticate
    # the *actual standalone stdout line*, NOT the echo of a Tcl instruction.
    marker = "M06_EXACT_ORIGINAL_MEM_SC_PORTS_CAPTURED|READ_ONLY_NO_XSIM_NO_BOARD"
    if sum(line.strip() == marker for line in log.splitlines()) != 1:
        raise ValueError("real tool stdout missing unique executed Vivado completion marker")
    expected_xpr = original / "13_file_backed_project/m05_d3_output_products.xpr"
    expected_bd = (original / "13_file_backed_project/m05_d3_output_products.srcs"
                   / "sources_1/bd" / BD / f"{BD}.bd")
    for marker, expected in (("SOURCE_XPR", expected_xpr),
                             ("SOURCE_BD", expected_bd)):
        if lines.count(f"{marker}|{expected.resolve()}") != 1:
            raise ValueError(f"original path provenance not confirmed: {marker}")
    seen: dict[str, dict[str, str]] = {key: {} for key in ENDPOINTS}
    end_order: list[str] = []
    for row in lines:
        fields = row.split("|")
        if len(fields) == 2 and fields[0] == "ENDPOINT":
            end_order.append(fields[1])
        elif len(fields) == 4 and fields[0] == "ENDPOINT_PROPERTY":
            endpoint, prop, val = fields[1:]
            if endpoint not in seen or prop in seen[endpoint] or not val:
                raise ValueError("unexpected or duplicate endpoint property")
            seen[endpoint][prop] = val
    if set(end_order) != set(ENDPOINTS) or len(end_order) != len(ENDPOINTS):
        raise ValueError("missing, extra, or duplicate original AXI endpoints")
    for endpoint, expected in ENDPOINTS.items():
        props = seen[endpoint]
        if props.get("CONFIG.DATA_WIDTH") != str(expected):
            raise ValueError(f"original AXI width contradicts expected {endpoint}")
    # Observed ORIGINAL D3 properties, not four generic full-duplex SI.
    for index in range(4):
        name = f"mem_sc/S{index:02d}_AXI"
        props = seen[name]
        expected_mode = "WRITE_ONLY" if index == 3 else "READ_ONLY"
        expected_values = {
            "CONFIG.PROTOCOL": "AXI4",
            "CONFIG.READ_WRITE_MODE": expected_mode,
            "CONFIG.ADDR_WIDTH": "32",
            "CONFIG.ID_WIDTH": "0",
            "CONFIG.MAX_BURST_LENGTH": "16",
            "CONFIG.HAS_BURST": "0",
        }
        for key, value in expected_values.items():
            if props.get(key) != value:
                raise ValueError(
                    f"original {name} {key} contradicts actual owner readback: {value}")
    mem_out = seen["mem_sc/M00_AXI"]
    for key, value in {
        "CONFIG.READ_WRITE_MODE": "READ_WRITE",
        "CONFIG.ADDR_WIDTH": "49",
        "CONFIG.ID_WIDTH": "0",
        "CONFIG.MAX_BURST_LENGTH": "32",
        "CONFIG.HAS_BURST": "1",
    }.items():
        if mem_out.get(key) != value:
            raise ValueError(f"original mem_sc/M00 {key} unexpected: {value}")
    ps = seen["ps/S_AXI_HP0_FPD"]
    for key, value in {
        "CONFIG.READ_WRITE_MODE": "READ_WRITE",
        "CONFIG.ADDR_WIDTH": "49",
        "CONFIG.ID_WIDTH": "6",
        "CONFIG.AWUSER_WIDTH": "1",
        "CONFIG.ARUSER_WIDTH": "1",
    }.items():
        if ps.get(key) != value:
            raise ValueError(f"original PS HP0 {key} unexpected: {value}")
    for required in ("MEM_IP_PROPERTY|CONFIG.NUM_SI|4",
                     "MEM_IP_PROPERTY|CONFIG.NUM_MI|1",
                     "CLOCK_RESET_PORT|mem_sc/aclk|PRESENT",
                     "CLOCK_RESET_PORT|mem_sc/aresetn|PRESENT",
                     "SIMULATOR_FUNCTIONAL_TRIAL|NOT_EXECUTED",
                     "GENERATE_TARGET|NOT_EXECUTED",
                     "PHYSICAL_BOARD|NOT_AUTHORIZED"):
        if lines.count(required) != 1:
            raise ValueError(f"original simulator safety marker missing: {required}")
    sim_meta = [row for row in lines if row.startswith("SIM_QUERY|")]
    if len(sim_meta) != 1:
        raise ValueError("must record exactly one simulator compile-order query")
    sim_files = [row[11:] for row in lines if row.startswith("SIM_SOURCE|")]
    query = sim_meta[0].split("|", 2)
    if query[1] == "OK":
        if int(query[2]) != len(sim_files):
            raise ValueError("simulation compile order file count corrupted")
    elif query[1] != "ERROR":
        raise ValueError("unknown simulation source query status")
    mem_sources = [row[len("MEM_PROJECT_SOURCE|"):] for row in lines
                   if row.startswith("MEM_PROJECT_SOURCE|")]

    # Scan only project-reported original memory-IP paths, not a full
    # recursive filesystem walk. This makes retrospective re-audit of an
    # existing owner capture cheap and avoids unrelated original files.
    # This is optional module-header discovery, NOT RTL elaboration/proof.
    candidates = []
    root = original / "13_file_backed_project"
    candidate_paths = list(dict.fromkeys(sim_files + mem_sources))
    for source_name in candidate_paths:
        filename = Path(source_name)
        if not filename.is_absolute() or not filename.is_relative_to(root):
            continue
        if "mem_sc" not in filename.as_posix().lower():
            continue
        if not filename.is_file() or filename.suffix.lower() not in (".v", ".sv"):
            continue
        if filename.stat().st_size > SOURCE_LIMIT:
            continue
        content = filename.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"(?m)^[ \t]*module[ \t]+([A-Za-z_]\w*)", content):
            name = m.group(1)
            if "mem_sc" in name.lower():
                candidates.append({
                    "relative_path": str(filename.relative_to(original)),
                    "module": name,
                    "declared_signal_hints": sorted(set(
                        re.findall(r"\b(?:S0[0-3]|M00)_AXI_[A-Za-z0-9_]+", content)
                    ))[:40],
                    "is_only_a_candidate_not_a_compiled_vendor_sim": True,
                })
    result = {
        "scope": "M06_ORIGINAL_2025_2_VENDOR_BFM_PORT_CONTRACT_ONLY",
        "original_d3": str(original.resolve()),
        "original_bd": str(expected_bd.resolve()),
        "endpoint_count": len(end_order),
        "endpoints": seen,
        "memory_si": 4,
        "memory_mi": 1,
        "memory_si_width_bits": 256,
        "memory_mi_width_bits": 128,
        "observed_si_modes": {f"S{i:02d}": ("WRITE_ONLY" if i == 3 else "READ_ONLY")
                              for i in range(4)},
        "original_si_max_burst_property": 16,
        "original_si_has_burst_property": 0,
        "original_mi_max_burst_property": 32,
        "has_burst_zero_needs_real_rtl_port_interpretation": True,
        "read_ports": ["S00", "S01", "S02"],
        "write_ports": ["S03"],
        "source_compile_query": sim_meta[0],
        "source_compile_count": len(sim_files),
        "sim_mem_source_count": sum("mem_sc" in x.lower() for x in sim_files),
        "original_project_mem_source_count": len(mem_sources),
        "scan_policy": "BOUNDED_LISTED_ORIGINAL_SOURCES_ONLY_NO_RECURSIVE_WALK",
        "candidate_module_declarations": candidates[:30],
        "total_candidate_module_declarations": len(candidates),
        "functional_vendor_axi_result": "NOT_EXECUTED",
        "axi_transfer_correctness": "NOT_PROVEN",
        "physical_board": "NOT_AUTHORIZED",
        "goal": "one genuine original-IP functional XSim transaction test after real module/port data",
    }
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original", required=True, type=Path)
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--vivado-log", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    try:
        if a.output.exists():
            raise ValueError("refuse to overwrite an existing owner evidence report")
        value = inspect(a.original.resolve(strict=True), a.report, a.vivado_log)
        with a.output.open("x", encoding="utf-8") as f:
            json.dump(value, f, sort_keys=True, indent=2)
            f.write("\n")
    except (ValueError, OSError, KeyError) as e:
        print(f"M06 ORIGINAL VENDOR SOURCE PORT AUDIT FAILED: {e}", file=sys.stderr)
        return 2
    print("M06 ORIGINAL 2025.2 AXI PORT CONTRACT VERIFIED: "
          "4x256-bit SI, 1x128-bit MI; "
          f"sim-files={value['source_compile_count']}; "
          f"candidate-modules={value['total_candidate_module_declarations']}; "
          "GENUINE FUNCTIONAL XSIM NOT RUN; NO BOARD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
