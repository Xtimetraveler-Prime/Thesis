#!/usr/bin/env python3
"""Independently verify an M08 read-only receipt (NOT physical attestation)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from neuromorphic_accelerator_v1.m08_receipt_audit import audit_receipt


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capture-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        # Never overwrite a previously recorded positive or failure receipt.
        if a.output.exists() or a.output.is_symlink():
            raise ValueError("audit output already exists")
        data=audit_receipt(a.capture_dir)
        if not a.output.parent.is_dir():
            raise ValueError("audit output parent must exist")
        with a.output.open("x",encoding="utf-8") as f:
            json.dump(data,f,indent=2,sort_keys=True)
            f.write("\n")
    except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:
        print("M08_READONLY_AUDIT_FAILED:",e,file=sys.stderr)
        return 2
    print("M08_READONLY_RECEIPT_INTEGRITY_OK_NOT_HARDWARE_ACCEPTANCE",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
