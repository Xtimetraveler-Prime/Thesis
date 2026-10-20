#!/usr/bin/env python3
"""P07-B.4b read-only PROBE ELF admission, not an inference authorization.

Checks actual AArch64 standalone ELF program headers, symbol table and
linker-map provenance with declared physical stack/heap ranges. Cannot prove
live DDR exclusivity, MMU attributes, PL provenance, context reset or board
execution. Requires an actually linked ELF: no synthetic placeholder accepted.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from p07_b3c3_elf_admission import Span, inspect, parse_load_segments, parse_named_span

REQUIRED = frozenset({
    "main", "p07_b4b_probe", "p07_b4b_xilinx_read_phys",
    "p03_hw_init", "p03_hw_identify", "p03_hw_quiescent",
    "p03_hw_xilinx_io",
})


def validate_elf_evidence(
    header: str, program_headers: str, symbols: str, linker_map: str,
    stack: Span, heap: Span,
) -> dict:
    if "Machine:" not in header or "AArch64" not in header:
        raise ValueError("not an AArch64 ELF")
    if "Data:" not in header or "little endian" not in header:
        raise ValueError("P03/P02 requires little-endian AArch64 ELF")
    if "Type:" not in header or "EXEC" not in header:
        raise ValueError("standalone probe must be linked as an EXEC ELF")
    loads = parse_load_segments(program_headers)
    layout = inspect(loads, stack, heap)
    names: set[str] = set()
    hw_bss: list[tuple[int, int]] = []
    for line in symbols.splitlines():
        words = line.split()
        if len(words) >= 3:
            names.add(words[-1])
        if len(words) >= 4 and words[-1] == "hw" and words[-2] in ("b", "B"):
            try:
                start, size = int(words[0], 16), int(words[1], 16)
            except ValueError as error:
                raise ValueError("invalid hw symbol extent") from error
            hw_bss.append((start, start + size))
    absent = sorted(REQUIRED.difference(names))
    if absent:
        raise ValueError("missing required read-only admission symbols: "
                         + ", ".join(absent))
    if not hw_bss or max(last-first for first,last in hw_bss) < 65000:
        raise ValueError("missing full-sized static P03 adapter context (hw)")
    if not any(load.first <= begin and end <= load.end
               for begin, end in hw_bss for load in loads):
        raise ValueError("P03 adapter context not contained in an ELF LOAD/BSS")
    if ".text" not in linker_map or ".bss" not in linker_map:
        raise ValueError("linker map missing text/BSS placement evidence")
    if "main" not in linker_map:
        raise ValueError("linker map does not identify the probe entry")
    return {
        **layout,
        "schema": "p07-b4b-readonly-elf-symbol-linker-admission-v1",
        "arch": "AArch64",
        "executable": "read-only shell probe",
        "required_symbols_checked": len(REQUIRED),
        "p03_adapter_static_bss_declared": True,
        "linker_map_supplied": True,
        "inference_authorized": False,
        "KV260_live_shell_verified": False,
        "DDR_ownership_verified": False,
        "physical_provenance_verified": False,
        "B2_official_MNIST_TEST": "SEALED",
    }


def _read(command: list[str]) -> str:
    return subprocess.run(command, check=True, text=True,
                          capture_output=True).stdout


def main() -> None:
    arg = argparse.ArgumentParser(description=__doc__)
    arg.add_argument("--elf", type=Path, required=True)
    arg.add_argument("--linker-map", type=Path, required=True)
    arg.add_argument("--stack", required=True, help="actual physical START:END")
    arg.add_argument("--heap", required=True, help="actual physical START:END")
    args = arg.parse_args()
    if not args.elf.is_file() or not args.linker_map.is_file():
        arg.error("real standalone ELF and corresponding linker map required")
    try:
        summary = validate_elf_evidence(
            _read(["readelf", "-W", "-h", str(args.elf)]),
            _read(["readelf", "-W", "-l", str(args.elf)]),
            _read(["nm", "-S", "--defined-only", str(args.elf)]),
            args.linker_map.read_text(encoding="utf8"),
            parse_named_span(args.stack, label="physical stack"),
            parse_named_span(args.heap, label="physical heap"),
        )
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        arg.error(str(exc))
    print(json.dumps(summary, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
