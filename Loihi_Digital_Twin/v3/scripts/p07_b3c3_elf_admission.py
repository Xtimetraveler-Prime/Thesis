#!/usr/bin/env python3
"""P07-B.3c3 read-only ELF LOAD/stack/heap/buffer DDR owner guard.

Checks DECLARED memory extents; cannot prove exclusive DDR ownership,
boot-state isolation, physical cache coherence, PL identity, or final XSA.
Usage: python scripts/p07_b3c3_elf_admission.py --elf /path/to/p07.elf
       --stack START:END --heap START:END --buffer LABEL=START:END
No ELF exists yet: do not treat synthetic tests as an actual ELF PASS.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess

P02_RESERVED = (0x40000000, 0x44000000)
P03_MMIO = (0xA4000000, 0xA4001000)
U64_END = 1 << 64


@dataclass(frozen=True)
class Span:
    label: str
    first: int
    end: int

    def __post_init__(self):
        if not (0 <= self.first < self.end <= U64_END):
            raise ValueError(f"{self.label}: invalid nonempty 64-bit memory span")


def parse_load_segments(readelf_text: str) -> tuple[Span, ...]:
    """GNU/LLVM readelf -W -l: type, offset, vaddr, paddr, filesz, memsz."""
    result = []
    for line in readelf_text.splitlines():
        fields = line.split()
        if not fields or fields[0] != "LOAD":
            continue
        if len(fields) < 7:
            raise ValueError("truncated LOAD entry in ELF program headers")
        try:
            paddr = int(fields[3], 0)
            memsize = int(fields[5], 0)
        except ValueError as e:
            raise ValueError("malformed ELF program LOAD extent") from e
        if memsize == 0:
            continue
        result.append(Span(f"ELF LOAD #{len(result)}", paddr, paddr + memsize))
    if not result:
        raise ValueError("ELF has no nonempty LOAD program headers")
    return tuple(result)


def parse_named_span(raw: str, *, label: str) -> Span:
    try:
        first, end = raw.split(":")
        return Span(label, int(first, 0), int(end, 0))
    except (ValueError, TypeError) as e:
        raise ValueError(f"{label}: expected START:END (half-open)") from e


def inspect(
    segments: tuple[Span, ...],
    stack: Span | None,
    heap: Span | None,
    buffers: tuple[Span, ...] = (),
) -> dict:
    """Fail-closed: declared stack/heap required; guards occupied ranges.

    User-supplied stack/heap extents are ASSERTIONS, not derived from linker;
    physical verification must additionally inspect actual BSP/linker map.
    """
    if stack is None or heap is None:
        raise ValueError("explicit stack and heap extents are mandatory")
    all_regions = (*segments, stack, heap, *buffers)
    for i, item in enumerate(all_regions):
        for protected_name, (first, end) in (
            ("P02 64MiB backing/staging/descriptor/result", P02_RESERVED),
            ("P03 4KiB AXI-Lite register window", P03_MMIO),
        ):
            if item.first < end and first < item.end:
                raise ValueError(f"{item.label} overlaps {protected_name}")
        for prior in all_regions[:i]:
            # ELF LOAD segments can legitimately have overlapping mappings
            # on some linkers; however the *declared* standalone memory
            # owner must not silently alias stack/heap or custom DMA buffers.
            if ((item.label.startswith("ELF LOAD") and
                 prior.label.startswith("ELF LOAD"))):
                continue
            if item.first < prior.end and prior.first < item.end:
                raise ValueError(
                    f"{item.label} overlaps independently owned {prior.label}"
                )
    return {
        "schema": "p07-b3c3-host-elf-declared-owner-guard-v1",
        "load_segments": len(segments),
        "protected_P02_start": f"0x{P02_RESERVED[0]:08x}",
        "protected_P02_end_exclusive": f"0x{P02_RESERVED[1]:08x}",
        "declared_memory_spans": len(all_regions),
        "only_declared_address_overlap_checked": True,
        "physical_ddr_exclusivity": "UNVERIFIED",
        "fpd128_live_shell": "UNVERIFIED",
        "real_ELF_bytes_parsed": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--stack", required=True, help="START:END hex physical")
    parser.add_argument("--heap", required=True, help="START:END hex physical")
    parser.add_argument("--buffer", action="append", default=[],
                        help="NAME=START:END, repeatable")
    args = parser.parse_args()
    if not args.elf.is_file():
        parser.error("real existing standalone ELF is required")
    try:
        raw = subprocess.run(
            ["readelf", "-W", "-l", str(args.elf)],
            check=True, text=True, capture_output=True,
        ).stdout
        extras = []
        for entry in args.buffer:
            name, span = entry.split("=", 1)
            if not name:
                raise ValueError("buffer must have a nonempty name")
            extras.append(parse_named_span(span, label=f"buffer:{name}"))
        result = inspect(
            parse_load_segments(raw),
            parse_named_span(args.stack, label="stack"),
            parse_named_span(args.heap, label="heap"),
            tuple(extras),
        )
    except (ValueError, OSError, subprocess.CalledProcessError) as e:
        parser.error(str(e))
    import json
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
