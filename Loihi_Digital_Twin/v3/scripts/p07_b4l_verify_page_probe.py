#!/usr/bin/env python3
"""Independently verify the 256-byte REAL B4l paging ELF mailbox.

Not a synthetic physical PASS generator: validates actual XSDB DDR bytes
captured after the A53 application finished. No hardware access here.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import struct
import sys

MAGIC=0x5042344C
DONE=0xC0DEF00D
PASS=0x600D600D
DIRTY=0x00000100
EXPECTED_PAGES=29
IDENTITY="P07_B4L_A53_27CORE_PAGING_PROBE_V1"


def verify(data:bytes)->dict:
    if len(data)!=256: raise ValueError("B4l requires exactly 256 REAL mailbox bytes")
    w=struct.unpack("<64I",data)
    checks={
        "magic":w[0]==MAGIC,
        "version":w[1]==1,
        "result":w[2]==PASS,
        "error":w[3]==0,
        "width_status":w[4]==0,
        "adapter_init":w[5]==0,
        "shell_identify":w[6]==0,
        "probe_exec":w[7]==0,
        "cores":w[8]==27,
        "page_ins":w[9]==28,
        "page_outs":w[10]==1,
        "dirty_xor":w[11]^w[12]==DIRTY,
        "saved_ddr":w[13]==w[12],
        "restored_slot":w[14]==w[12],
        "last_core":w[15]==0,
        "last_slot":w[16]==0,
        "page_cycles":(w[17]|w[18]<<32)>0,
        "hw_adapter":w[19]==0,
        "done_flag":w[20]==1,
        "fpd128":w[21]==0x00000A00,
        "pl_page_completions":w[22]>=EXPECTED_PAGES,
        "no_inference":w[23]==0,
        "record_count":w[24]==27,
        "resident_slots":w[25]==3,
        "ddr_base":w[26]==0x40000000,
        "record_stride":w[27]==0x80000,
        "dirty_mask":w[28]==DIRTY,
        "completion":w[63]==DONE,
        "reserved_zero":all(x==0 for x in w[29:63]),
    }
    invalid=[k for k,ok in checks.items() if not ok]
    if invalid: raise ValueError("NO-GO B4l real page proof: "+",".join(invalid))
    return {"original_state_word":f"0x{w[11]:08X}",
            "saved_dirty_word":f"0x{w[12]:08X}",
            "page_ins":w[9],"page_outs":w[10],"cores_visited":w[8],
            "physical_page_completions":w[22],
            "page_cycles":w[17]|w[18]<<32,
            "physical_inference_executed":False}


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--mailbox",required=True,type=Path)
    a=p.parse_args()
    try:
        result=verify(a.mailbox.read_bytes())
    except (ValueError,OSError) as e:
        print("P07_B4L_PAGING_MAILBOX_NO_GO="+str(e),file=sys.stderr)
        return 3
    import json
    print(json.dumps(result,indent=2,sort_keys=True))
    print("P07_B4L_PHYSICAL_27_CORE_3_SLOT_PAGE_DIRTY_SAVE_VERIFIED=1")
    print("P07_B4L_TRAINED_INFERENCE_EXECUTED=0")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
