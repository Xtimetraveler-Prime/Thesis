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
import re
from pathlib import Path
import subprocess

from p07_b3c3_elf_admission import (
    Span, inspect, parse_load_segments, parse_named_span,
    P02_RESERVED, P03_MMIO,
)

# In genuine standalone Vitis ELF files, allocated .heap/.stack sections
# are intentionally INSIDE PT_LOAD alongside .bss (not separate DMA buffers).
# B3c's generic external-allocation guard must remain unchanged.
_SECTION = re.compile(
    r"^\s*\[\s*\d+\]\s+(\S+)\s+(\S+)\s+"
    r"([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+"
    r"([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+(\S+)",
    re.MULTILINE,
)

def inspect_embedded_sections(
    loads: tuple[Span, ...], stack: Span, heap: Span, raw: str
) -> dict:
    sections: dict[str, Span] = {}
    for entry in _SECTION.finditer(raw):
        name, _kind, address, _offset, size, _es, flags = entry.groups()
        if "A" not in flags:
            continue
        start, length = int(address, 16), int(size, 16)
        if length == 0:
            continue
        if name in sections:
            raise ValueError("duplicate allocated ELF section: " + name)
        sections[name] = Span("ELF section " + name, start, start + length)

    for name, declared in ((".heap", heap), (".stack", stack), (".bss", None)):
        if name not in sections:
            raise ValueError("real ELF allocated section missing: " + name)
        actual = sections[name]
        if declared is not None and (actual.first, actual.end) != (
            declared.first, declared.end
        ):
            raise ValueError(name + " differs from actual ELF section extent")
        if not any(segment.first <= actual.first and actual.end <= segment.end
                   for segment in loads):
            raise ValueError(name + " not contained in ELF LOAD segment")

    for item in (*loads, heap, stack):
        for protected, (lower, upper) in (
            ("P02 64MiB backing/staging/descriptor/result", P02_RESERVED),
            ("P03 4KiB AXI-Lite register window", P03_MMIO),
        ):
            if item.first < upper and lower < item.end:
                raise ValueError(item.label + " overlaps " + protected)

    if heap.first < stack.end and stack.first < heap.end:
        raise ValueError("ELF heap overlaps stack")
    for name, section in sections.items():
        if name in (".heap", ".stack"):
            continue
        for region in (heap, stack):
            if region.first < section.end and section.first < region.end:
                raise ValueError(region.label + " overlaps allocated " + name)
    return {
        "schema": "p07-b4b-real-vitis-embedded-stack-heap-v1",
        "load_segments": len(loads),
        "actual_allocated_sections_checked": len(sections),
        "heap_section_verified": True,
        "stack_section_verified": True,
        "embedded_stack_heap_within_elf_load": True,
        "protected_P02_start": f"0x{P02_RESERVED[0]:08x}",
        "protected_P02_end_exclusive": f"0x{P02_RESERVED[1]:08x}",
        "physical_ddr_exclusivity": "UNVERIFIED",
        "fpd128_live_shell": "UNVERIFIED",
        "real_ELF_bytes_parsed": True,
    }


REQUIRED = frozenset({
    "main", "p07_b4b_probe", "p07_b4b_xilinx_read_phys",
    "p03_hw_init", "p03_hw_identify", "p03_hw_quiescent",
    "p03_hw_xilinx_io",
})


def validate_elf_evidence(
    header: str, program_headers: str, symbols: str, linker_map: str,
    stack: Span, heap: Span, section_headers: str | None = None,
) -> dict:
    if "Machine:" not in header or "AArch64" not in header:
        raise ValueError("not an AArch64 ELF")
    if "Data:" not in header or "little endian" not in header:
        raise ValueError("P03/P02 requires little-endian AArch64 ELF")
    if "Type:" not in header or "EXEC" not in header:
        raise ValueError("standalone probe must be linked as an EXEC ELF")
    loads = parse_load_segments(program_headers)
    layout = (
        inspect_embedded_sections(loads, stack, heap, section_headers)
        if section_headers is not None else inspect(loads, stack, heap)
    )
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
            _read(["readelf", "-W", "-S", str(args.elf)]),
        )
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        arg.error(str(exc))
    print(json.dumps(summary, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
