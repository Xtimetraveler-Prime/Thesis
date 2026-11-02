#!/usr/bin/env python3
"""PC-only, READ-ONLY monitor for an ALREADY RUNNING P08-B4.2 JTAG session.

Reads ONLY the existing PC-side binary snapshots that the ORIGINAL XSDB
runner writes under <evidence>/full1024_capture/. NEVER connects to XSDB,
Vivado, hw_server, board, serial, or network, and NEVER writes/renames
any file. It is safe in a second VS Code terminal while the ORIGINAL
physical run owns JTAG. Not a substitute for independently verified
post-run physical evidence; terminal success is only a progress signal.

Usage:
 python scripts/p08_b4_2_monitor_mailbox_pc_only.py \
   --evidence "$P08_B4_PHYSICAL" --samples 2 --interval 20

IMPORTANT: Exact active evidence folder required. Do not auto-select an
old/other JTAG session. The XSDB poll loop deletes/recreates
mailbox_poll.tmp; short-lived absent/partial snapshots are normal.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import struct
import sys
import time

WORDS=64
SIZE=WORDS*4
MAGIC=0x50384232
DONE=0xC0DEF00D
PROGRESS=0xC0DE0000
SUCCESS=0x600D0823
FAILURE=0xDEAD0823
COUNT=1024
POLL="mailbox_poll.tmp"
TERMINAL="mailbox_terminal_physical.bin"

def decode(raw:bytes)->dict:
    """Strict progress/terminal interpretation; no JTAG required."""
    if len(raw)!=SIZE:
        return {"state":"PARTIAL","reason":f"{len(raw)} of {SIZE} bytes"}
    w=struct.unpack("<64I",raw)
    info={
        "completed":w[5],
        "last_frame":w[3],
        "fault":w[4],
        "status_word":f"0x{w[2]:08X}",
        "done_word":f"0x{w[63]:08X}",
    }
    if w[0]!=MAGIC or w[1]!=1:
        return {"state":"INVALID","reason":"wrong original P08 mailbox magic/version",**info}
    if w[63]!=DONE:
        return {"state":"INCOMPLETE","reason":"mailbox DONE not yet committed",**info}
    if w[2]==PROGRESS:
        ok=(w[4]==0 and w[5]<=COUNT and
            ((w[5]==0 and w[3]==0xFFFFFFFF) or
             (w[5]>0 and w[3]==w[5]-1)))
        return {"state":"PROGRESS" if ok else "INVALID",**info}
    if w[2]==SUCCESS:
        ok=(w[3]==COUNT-1 and w[4]==0 and w[5]==COUNT)
        return {"state":"SUCCESS" if ok else "INVALID",**info}
    if w[2]==FAILURE:
        return {"state":"FAILURE",**info}
    return {"state":"INVALID","reason":"unknown mailbox status",**info}

def snapshot(evidence:Path,capture_subdir:str="full1024_capture")->dict:
    """Read existing PC files only; tolerate XSDB temporary-file races."""
    if capture_subdir not in ("full1024_capture","profile1024_capture"):
        return {"state":"INVALID","reason":"unsupported PC-only capture directory"}
    directory=evidence/capture_subdir
    if not evidence.is_dir() or not directory.is_dir():
        return {"state":"MISSING","reason":"exact evidence/"+capture_subdir+" directory absent"}
    for filename in (TERMINAL,POLL):
        p=directory/filename
        try:
            # A read may race XSDB's unlink/recreate; retry on next sample.
            raw=p.read_bytes()
            status=decode(raw)
            status["source"]=filename
            status["snapshot_age_seconds"]=max(0.0,time.time()-p.stat().st_mtime)
            return status
        except (FileNotFoundError,PermissionError,OSError):
            continue
    return {"state":"MISSING","reason":"no terminal or current PC-side mailbox snapshot"}

def display(item:dict)->None:
    print("Mailbox:",item["state"])
    if "source" in item:
        print("PC evidence file:",item["source"])
        print("PC snapshot age (seconds):",
              round(item.get("snapshot_age_seconds",0),1))
    if "completed" in item:
        count=item["completed"]
        print("Completed images:",f"{count}/{COUNT}",
              f"({100*count/COUNT:.2f}%)" if count<=COUNT else "(INVALID count)")
        print("Last reported frame:",
              "-1 (startup)" if item["last_frame"]==0xFFFFFFFF
              else item["last_frame"])
        print("Fault code:",item["fault"])
        print("Status word:",item["status_word"])
        print("DONE marker:",item["done_word"])
    if item.get("reason"):
        print("Note:",item["reason"])
    if item["state"]=="SUCCESS":
        print("Observed terminal 1024/1024; independent post-run verifier STILL required.")
    elif item["state"]=="FAILURE":
        print("A53 reports a fault; preserve evidence and obey runner reboot notice.")
    elif item["state"] in ("MISSING","PARTIAL","INCOMPLETE"):
        print("Temporary snapshot may be unavailable while XSDB updates it; recheck.")
    elif item["state"]=="INVALID":
        print("Malformed snapshot; do NOT interpret as physical success.")

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",required=True,type=Path,
                   help="exact ACTIVE P08-B4 physical evidence directory")
    p.add_argument("--capture-subdir",
                   choices=("full1024_capture","profile1024_capture"),
                   default="full1024_capture",
                   help="PC-side saved ORIGINAL B4 or NEW B44 profile capture; no hardware")
    p.add_argument("--samples",type=int,default=2,
                   help="number of snapshots (default: 2)")
    p.add_argument("--interval",type=float,default=20.0,
                   help="seconds between samples (default: 20)")
    a=p.parse_args(argv)
    if not a.evidence.is_absolute() or a.samples<1 or a.samples>120 or not (
            0<=a.interval<=3600):
        p.error("absolute exact evidence directory, 1..120 samples and 0..3600s required")
    print("READ ONLY: reads PC-side cached files; no JTAG, board or hardware actions.")
    print("Evidence:",a.evidence)
    print("PC capture subdirectory:",a.capture_subdir)
    last=None
    for number in range(a.samples):
        if number:
            time.sleep(a.interval)
        print(f"\n--- Local mailbox snapshot {number+1}/{a.samples} ---")
        value=snapshot(a.evidence,a.capture_subdir)
        display(value)
        if last and all("completed" in item and item["state"]=="PROGRESS"
                        for item in (last,value)):
            delta=value["completed"]-last["completed"]
            print("Completed-image delta:",delta,
                  "(zero over this interval ALONE does NOT prove a hang)")
        last=value
    print("\nNo additional XSDB session, A53 halt, reset or reboot was performed.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
