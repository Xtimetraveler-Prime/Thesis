#!/usr/bin/env python3
"""Read ONLY PC-side B4.5 full1024 host progress; no JTAG/serial access.

The active XSDB process reads the existing A53 mailbox and writes an
atomically renamed progress_state.txt inside the new capture directory.
This monitor only reads those host text files from a second VS Code
terminal; it neither polls the physical device nor implies parity PASS.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
import time

SCHEMA="p08-b45-perf-full1024-xsdb-progress-v1"
TERMINAL={"FAILED_REBOOT_REQUIRED","CAPTURE_DONE_PENDING_INDEPENDENT"}
STATES={"POLLING","TERMINAL_CAPTURE","BACKUP_READBACK"} | TERMINAL
VALID=re.compile(r"^[A-Za-z0-9_.-]+$")
class ProgressNoGo(ValueError): pass

def parse_snapshot(text: str, *, expected_mode: str) -> dict:
    entries={}
    for line in text.splitlines():
        if line.count("=")!=1:raise ProgressNoGo("invalid host progress line")
        key,value=line.split("=",1)
        if key in entries or not VALID.fullmatch(key) or not VALID.fullmatch(value):
            raise ProgressNoGo("invalid or duplicate progress field")
        entries[key]=value
    required={"schema","mode","completed","total","state",
              "started_epoch","updated_epoch","elapsed_seconds"}
    if set(entries)!=required or entries["schema"]!=SCHEMA:
        raise ProgressNoGo("unexpected host progress schema")
    if entries["mode"]!=expected_mode or entries["state"] not in STATES:
        raise ProgressNoGo("wrong experiment or invalid progress status")
    for k in ("completed","total","started_epoch","updated_epoch","elapsed_seconds"):
        if not entries[k].isdigit():raise ProgressNoGo("noninteger "+k)
        entries[k]=int(entries[k])
    if not (entries["total"]==1024 and
            0<=entries["completed"]<=1024 and
            entries["started_epoch"]>0 and
            entries["updated_epoch"]>=entries["started_epoch"] and
            entries["elapsed_seconds"]==
               entries["updated_epoch"]-entries["started_epoch"]):
        raise ProgressNoGo("impossible progress geometry/timestamps")
    if entries["state"] in {"TERMINAL_CAPTURE","BACKUP_READBACK",
                            "CAPTURE_DONE_PENDING_INDEPENDENT"} and \
       entries["completed"]!=1024:
        raise ProgressNoGo("capture state without complete terminal 1024")
    return entries

def snapshot(evidence: Path, mode: str, now: int|None=None)->tuple[str,bool,bool]:
    if now is None:now=int(time.time())
    if not evidence.is_absolute() or evidence.is_symlink():
        raise ProgressNoGo("absolute non-symlink evidence path required")
    if not evidence.is_dir():
        return ("No evidence directory yet. Run the PC execution command "
                "in the first terminal.",False,False)
    stage_file=evidence/"stage.txt"
    stage="RUNNER_STARTING"
    if stage_file.is_file() and not stage_file.is_symlink():
        rows=stage_file.read_text().splitlines()
        if rows: stage=rows[-1][:128]
    progress=evidence/"performance1024_capture"/"progress_state.txt"
    if not progress.is_file():
        return ("Host stage: "+stage+" | no A53 mailbox progress snapshot yet",
                False,False)
    if progress.is_symlink():raise ProgressNoGo("symlink progress disallowed")
    data=parse_snapshot(progress.read_text(),expected_mode=mode)
    completed=data["completed"]
    percent=100*completed/1024
    age=max(0,now-data["updated_epoch"])
    speed=completed/max(1,data["elapsed_seconds"])
    width=int(percent/5)
    bar="#"*width+"-"*(20-width)
    status=(f"{mode}: [{bar}] {completed}/1024 ({percent:5.1f}%) | "
            f"observed {speed:.3f} frames/s | elapsed {data['elapsed_seconds']}s | "
            f"snapshot age {age}s | state={data['state']}")
    if age>180:status+=" | STALE HOST SNAPSHOT: check execution terminal"
    if data["state"]=="CAPTURE_DONE_PENDING_INDEPENDENT":
        status+="\nRaw capture complete; only independent neural/FNV/postbackup review can certify PASS."
    elif data["state"]=="FAILED_REBOOT_REQUIRED":
        status+="\nJTAG runner FAILED: do not resume halted Linux. Reboot KV260."
    return status,data["state"] in TERMINAL,data["state"]=="FAILED_REBOOT_REQUIRED"

def main(argv: list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",type=Path,required=True)
    p.add_argument("--experiment",choices=("once","unchecked"),required=True)
    p.add_argument("--interval",type=int,default=15)
    p.add_argument("--once",action="store_true",
                   help="print current host file state then exit (no loop)")
    a=p.parse_args(argv)
    if not (2<=a.interval<=120):
        p.error("--interval must be 2..120 seconds")
    last=None
    try:
        while True:
            status,done,failed=snapshot(a.evidence,a.experiment)
            if status!=last or a.once:
                print(status,flush=True)
                last=status
            if done or a.once:return 3 if failed else 0
            time.sleep(a.interval)
    except (ProgressNoGo,OSError,UnicodeError) as e:
        print("P08_B45_PERF1024_HOST_MONITOR_NO_GO="+str(e),file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print("Monitor stopped; main hardware run unaffected.",flush=True)
        return 0

if __name__=="__main__":
    raise SystemExit(main())
