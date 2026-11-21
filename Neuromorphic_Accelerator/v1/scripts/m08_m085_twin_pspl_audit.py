#!/usr/bin/env python3
"""Read-only first-party v3 PS/PL DDR lineage and current M08 topology audit.

Only source files inside the checkout are read. No Vivado, XSA or hardware
manager, shell commands, memory-mapped IO, DMA, DDR or original owner evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
V1 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V1 / "src"))
from neuromorphic_accelerator_v1.m08_m085_pspl_lineage import (
    PRIOR, LineageError, audit_sources,
)


def collect() -> dict:
    paths = [ROOT / p for p in PRIOR]
    if any(not p.is_file() or p.is_symlink() for p in paths):
        raise LineageError("first-party source file absent or symlinked")
    return audit_sources({p: path.read_text(encoding="utf-8")
                          for p, path in zip(PRIOR, paths)})


def main() -> int:
    arg = argparse.ArgumentParser(description=__doc__)
    arg.add_argument("--source-only", action="store_true", required=True)
    arg.parse_args()
    try:
        print(json.dumps(collect(), indent=2, sort_keys=True))
        return 0
    except (ValueError, OSError) as exc:
        print("M08_5_TWIN_READONLY_LINEAGE_REJECTED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
