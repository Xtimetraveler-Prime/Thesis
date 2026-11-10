#!/usr/bin/env python3
"""Audit the *real* Vivado -compile_order -used_in simulation source listing.

The owner log proves this Vivado query succeeded before the separate
export_simulation command crashed. This checks both generated AMD IPs and
writes only new output files, not the read-only vendor project or source.
NO actual XSim compile/run, HLS binding or SmartConnect coupling is claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

IP_ROLES = {
    "m06_g3_read_dwc": "READ_ONLY",
    "m06_g3_write_dwc": "WRITE_ONLY",
}
ALLOWED_TYPES = {
    "Verilog": (".v",),
    "SystemVerilog": (".sv",),
    "VHDL": (".vhd", ".vhdl"),
    "Verilog Header": (".vh", ".svh"),
}
TAIL = {
    "original_amd_smartconnect_linked": "FALSE",
    "generated_hls_linked": "FALSE",
    "vendor_converter_xsim_run": "FALSE",
    "m06_complete": "FALSE",
}


def audit(compile_order: str, owner_root: Path) -> dict:
    root = owner_root.resolve(strict=True)
    if not root.is_dir() or not root.name.startswith("m06_g3_real_amd_dwc_"):
        raise ValueError("wrong genuine original AMD owner evidence directory")
    project = root / "new_scratch_project"
    if not project.is_dir():
        raise ValueError("real original AMD width-IP scratch project missing")
    rows = compile_order.splitlines()
    if not rows or rows[0] != (
        "original_vendor_simulation_files_only\tNOT_HLS_OR_SMARTCONNECT_CONNECTED"
    ):
        raise ValueError("missing explicit source-only original AMD scope")
    cursor = 1
    results = {}
    source_paths = []
    for ip, role in IP_ROLES.items():
        for key, value in (
            ("ip_name", ip), ("ip_mode", role)
        ):
            if cursor >= len(rows) or rows[cursor] != f"{key}\t{value}":
                raise ValueError(f"real Vivado IP order or role missing: {ip} {key}")
            cursor += 1
        if cursor >= len(rows):
            raise ValueError("missing original Vivado source count")
        count_row = rows[cursor].split("\t")
        if len(count_row) != 2 or count_row[0] != "ip_sim_file_count" or (
            not count_row[1].isdecimal()
        ):
            raise ValueError("invalid original Vivado compile-order file count")
        count = int(count_row[1])
        cursor += 1
        if count < 3 or count > 250:
            raise ValueError("incomplete or unreasonable original Vivado IP sources")
        sources = []
        seen = set()
        wrapper = False
        header = False
        for index in range(count):
            if cursor >= len(rows):
                raise ValueError("truncated original Vivado simulation source listing")
            fields = rows[cursor].split("\t")
            cursor += 1
            if len(fields) != 3 or fields[0] != ip:
                raise ValueError("corrupt original AMD source role, order or filename")
            _, kind, textpath = fields
            if kind not in ALLOWED_TYPES:
                raise ValueError("unrecognized Vivado simulation file type: " + kind)
            path = Path(textpath)
            if not path.is_absolute() or path.is_symlink() or (
                path.suffix.lower() not in ALLOWED_TYPES[kind]
            ):
                raise ValueError("original AMD simulation source path/type mismatch")
            resolved = path.resolve(strict=True)
            if not resolved.is_relative_to(project) or not resolved.is_file() or (
                resolved.stat().st_size == 0
            ):
                raise ValueError("original AMD simulation source outside original project or empty")
            if str(resolved) != textpath or str(resolved) in seen:
                raise ValueError("duplicate/noncanonical original AMD simulation file")
            seen.add(str(resolved))
            if path.name == ip + ".v" and "sim" in path.parts:
                wrapper = True
            if kind == "Verilog Header":
                header = True
            source_paths.append(str(resolved))
            sources.append({
                "path": str(resolved),
                "language": kind,
                "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
            })
        if not wrapper or not header:
            raise ValueError("missing real generated AMD simulation wrapper or header: " + ip)
        results[ip] = {
            "role": role,
            "ordered_simulation_files": sources,
            "sim_file_count": len(sources),
            "real_vendor_wrapper_found": wrapper,
            "real_vendor_include_found": header,
        }
    for key, value in TAIL.items():
        if cursor >= len(rows) or rows[cursor] != key + "\t" + value:
            raise ValueError("missing boundary marker: " + key)
        cursor += 1
    if cursor != len(rows):
        raise ValueError("unexpected extra Vivado source listings or false status")
    return {
        "schema": "m06-g3-real-amd-read-only-compile-order-audit-v1",
        "status": "REAL_AMD_XSIM_SOURCES_RECORDED_NOT_EXPORTED_NOT_COMPILED",
        "owner_original_ip_folder": str(root),
        "original_amd_smartconnect_linked": False,
        "generated_hls_linked": False,
        "vendor_converter_xsim_run": False,
        "physical_board": "NOT_ACCESSED",
        "m06_complete": False,
        "instances": results,
        "ordered_paths": source_paths,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compile-order", type=Path, required=True)
    parser.add_argument("--owner-dwc", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--paths-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        for out in (args.output, args.paths_output):
            if out.exists() or not out.parent.is_dir():
                raise ValueError("each report requires a new path in an existing folder")
        report = audit(args.compile_order.read_text(), args.owner_dwc)
        # Both paths have been checked for exclusivity before either write.
        with args.output.open("x", encoding="utf8") as stream:
            json.dump(report, stream, sort_keys=True, indent=2)
            stream.write("\n")
        with args.paths_output.open("x", encoding="utf8") as stream:
            stream.write("\n".join(report["ordered_paths"]) + "\n")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("M06 genuine AMD simulation compile order REJECTED: " + str(error),
              file=sys.stderr)
        return 2
    print("M06 genuine AMD XSim compile-order FILES ATTESTED; NO EXPORT SIMULATION / NO CONNECTED IP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
