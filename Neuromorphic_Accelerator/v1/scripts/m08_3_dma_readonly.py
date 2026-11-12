#!/usr/bin/env python3
"""M08.3.1 board-local READ-ONLY Linux/DMA readiness inventory.

Run on a booted KV260 Linux shell, not on the development PC.
No sudo, /dev/mem, DMA buffer allocation, MMIO, driver attach, FPGA
programming or DDR writes. Reports NEVER authorize DMA.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from neuromorphic_accelerator_v1.m08_dma_readiness import collect,write_fresh,audit


def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir",required=True,type=Path,
                   help="NEW exclusive immutable folder (parent must exist)")
    p.add_argument("--audit-only",action="store_true",
                   help="Only independently audit an existing capture folder")
    a=p.parse_args()
    try:
        if a.audit_only:
            result=audit(a.output_dir)
            print(json.dumps(result,sort_keys=True))
            return 0
        # No --root override: the actual board-local /proc and /sys only.
        out=write_fresh(a.output_dir,collect(Path("/")))
        result=audit(a.output_dir)
    except (OSError,ValueError,KeyError,json.JSONDecodeError) as exc:
        print("M08_3_READONLY_REJECTED:",exc,file=sys.stderr)
        return 2
    print("M08_3_READONLY_RECEIPT_OK_NOT_DMA_READY",out)
    print(json.dumps(result,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
