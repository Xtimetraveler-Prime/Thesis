#!/usr/bin/env python3
"""Verify an actual 64-byte P07-B.4i JTAG DDR mailbox (no hardware access).
This is read-only shell admission, NEVER trained B2 inference.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import struct

MAGIC=0x50374249
DONE=0xC0DEF00D
PASS=0x600D600D
FPD128=0x00000A00
EXPECTED=(0x4C543302,0x00010000,0x0001031F)

def verify(raw:bytes)->dict:
    if len(raw)!=64:
        raise ValueError("physical mailbox must contain exactly 64 bytes")
    v=struct.unpack("<16I",raw)
    labels=("magic","version","result","init_rc","probe_rc","fpd",
            "id","shell_version","capabilities","global_status",
            "page_pending","read_only_shell_pass","inference_authorized",
            "mailbox_base","reserved","complete")
    result=dict(zip(labels,v))
    expected={0:MAGIC,1:1,2:PASS,3:0,4:0,5:FPD128,
              6:EXPECTED[0],7:EXPECTED[1],8:EXPECTED[2],9:0,
              10:0,11:1,12:0,13:0x43FF0000,14:0,15:DONE}
    bad=[f"{labels[i]} got=0x{v[i]:08x} expected=0x{want:08x}"
         for i,want in expected.items() if v[i]!=want]
    if bad:
        raise ValueError("read-only admission NOT PASS: "+"; ".join(bad))
    return result

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--mailbox",required=True,type=Path)
    args=p.parse_args()
    try:
        actual=args.mailbox.read_bytes()
        verify(actual)
    except (OSError,ValueError) as exc:
        print(f"P07_B4I_PHYSICAL_ADMISSION_FAIL={exc}")
        return 3
    print("P07_B4I_PHYSICAL_READONLY_ADMISSION_PASS=1")
    print("P07_B4I_TRAINED_B2_INFERENCE_VERIFIED=0")
    print("P07_B4I_PHYSICAL_INFERENCE_AUTHORIZED=0")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
