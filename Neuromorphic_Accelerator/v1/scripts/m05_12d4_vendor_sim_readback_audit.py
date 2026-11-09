#!/usr/bin/env python3
"""Strict independent parser for original read-only Vivado simulation file discovery.

No generated/compiled/simulated IP accepted: this only states how to attempt
REAL offline vendor XSim safely after evidence review and owner decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from m05_12d4_protocol_risk import NEW_PREFIX, review

SCOPE = "META|scope|M05_D4_ORIGINAL_SIM_MODEL_FEASIBILITY_ONLY"
SUCCESS = "M05_D4_SIM_MODEL_DISCOVERY_COMPLETE|ORIGINAL_READ_ONLY|NO_XSIM_NO_BOARD"
TAIL = (
    "META|simulation|NOT_RUN",
    "META|generated_model_compile|NOT_RUN",
    "META|byte_scoreboard|NOT_RUN",
    "META|physical_board|NOT_AUTHORIZED",
    "SIM_MODEL_DISCOVERY|COMPLETE|SIMULATOR_FUNCTIONAL_PROOF_BLOCKED",
)


def inspect(report: str, original: Path) -> dict:
    lines = report.splitlines()
    root = original.resolve(strict=True)
    xpr = root / "13_file_backed_project/m05_d3_output_products.xpr"
    bdname = "m05_12d3_real_signed32_hls_six_control_address_candidate"
    bd = root / ("13_file_backed_project/m05_d3_output_products.srcs/"
                 "sources_1/bd/" + bdname + "/" + bdname + ".bd")
    if (not report.endswith("\n") or lines[:3] !=
            [SCOPE, "PROJECT|" + str(xpr), "BD|" + str(bd)]
            or tuple(lines[-5:]) != TAIL):
        raise ValueError("invalid original read-only saved project or altered simulation NOT_RUN footer")
    body = lines[3:-5]
    if not body or body[0] not in ("SIMFILESET|PRESENT", "SIMFILESET|MISSING"):
        raise ValueError("missing original simulation fileset status")
    simset = body.pop(0)
    simprops = {}
    if simset == "SIMFILESET|PRESENT":
        for prop in ("TOP", "TARGET_SIMULATOR"):
            if not body or not body[0].startswith(f"SIMPROP|{prop}|"):
                raise ValueError("unexpected simulation fileset property row")
            simprops[prop] = body.pop(0).split("|", 2)[2]
    if not body or body[0] not in (
            "SIMCOMPILE|QUERY_ERROR", "SIMCOMPILE|QUERY_OK", "SIMCOMPILE|UNAVAILABLE"):
        raise ValueError("simulation compile-order query status missing")
    simcompile = body.pop(0).split("|")[1]
    files = []
    project = []
    if simcompile == "QUERY_ERROR":
        if not body or not body[0].startswith("SIMERROR|"):
            raise ValueError("original simulator failure reason absent")
        simprops["compile_error"] = body.pop(0).split("|", 1)[1]
    elif simcompile == "QUERY_OK":
        while body and body[0].startswith("MEM_SIM_FILE|"):
            files.append(body.pop(0).split("|", 1)[1])
        if len(body) < 2 or not body[0].startswith("SIMCOMPILE_COUNT|") or not body[1].startswith("MEM_COMPILE_COUNT|"):
            raise ValueError("simulation model/file counts incomplete")
        total = int(body.pop(0).split("|")[1])
        mem = int(body.pop(0).split("|")[1])
        if total < len(files) or mem != len(files):
            raise ValueError("simulation model compile-order count inconsistent")
        simprops["total_compile_objects"] = total
        simprops["mem_compile_objects"] = mem
    elif simset != "SIMFILESET|MISSING":
        raise ValueError("unavailable simulation compile order while file set exists")
    while body and body[0].startswith("MEM_PROJECT_FILE|"):
        project.append(body.pop(0).split("|", 1)[1])
    if len(body) != 2 or not body[0].startswith("PROJECT_FILE_COUNT|") or not body[1].startswith("MEM_PROJECT_COUNT|"):
        raise ValueError("project file count missing or unexpected readback rows")
    project_total = int(body[0].split("|")[1])
    project_mem = int(body[1].split("|")[1])
    if project_total < len(project) or project_mem != len(project) or project_total <= 0:
        raise ValueError("project file counts inconsistent with original Vivado records")
    for path in files + project:
        if not path or "|" in path or "\n" in path or "mem_sc" not in path.lower():
            raise ValueError("unattributed/bad generated memory SmartConnect file")
        # Vivado may show logical IP paths; do not silently rewrite them.
    return {
        "scope": "ORIGINAL_D3_READ_ONLY_VENDOR_SIM_SOURCE_DISCOVERY",
        "simulation_fileset": simset.split("|")[1],
        "compile_order_status": simcompile,
        "compile_order_memory_file_paths": files,
        "project_memory_file_paths": project,
        "vivado_fileset": simprops,
        "project_file_count": project_total,
        "project_memory_file_count": project_mem,
        "simulation": "NOT_RUN",
        "compiled_vendor_simulation_model": "NOT_PROVEN",
        "vendor_downsize_axi_protocol": "NOT_PROVEN",
        "no_physical_board": True,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-d3", type=Path, required=True)
    p.add_argument("--d4-inventory", type=Path, required=True)
    p.add_argument("--d4-bd", type=Path, required=True)
    p.add_argument("--vivado-log", type=Path, required=True)
    p.add_argument("--model-report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        if (a.output.exists() or a.output.name != "06_model_discovery_audit.json"
                or not a.output.parent.resolve(strict=True).name.startswith(NEW_PREFIX)):
            raise ValueError("new immutable D4 protocol gate model report path required")
        risk = review(a.original_d3, a.d4_inventory, a.d4_bd)
        log = a.vivado_log.read_text()
        if sum(line.strip() == SUCCESS for line in log.splitlines()) != 1 or "ERROR:" in log:
            raise ValueError("original read-only Vivado simulation model discovery failed")
        result = inspect(a.model_report.read_text(), a.original_d3)
        result["original_d3"] = str(a.original_d3.resolve())
        result["original_d4_1b"] = str(a.d4_bd.resolve())
        result["original_model_report_sha256"] = hashlib.sha256(a.model_report.read_bytes()).hexdigest()
        result["original_vivado_discovery_log_sha256"] = hashlib.sha256(a.vivado_log.read_bytes()).hexdigest()
        result["risk_report_verified"] = (risk["decision"] ==
                                          "NO_MUTATION_JUSTIFIED_FROM_CONFIGURATION_READBACK_ALONE")
        with a.output.open("x", encoding="utf-8") as fp:
            json.dump(result, fp, indent=2, sort_keys=True)
            fp.write("\n")
    except (OSError, ValueError, KeyError, UnicodeError, json.JSONDecodeError) as err:
        print(f"FAIL: original D4 Vivado read-only simulation source model audit: {err}", file=sys.stderr)
        return 2
    print("D4.3 original Vivado simulation FILE DISCOVERY COMPLETE; "
          "vendor RTL compilation and AXI 256->128 scoreboard remain NOT RUN")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
