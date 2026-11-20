#!/usr/bin/env python3
"""D3.D.2D exact original 17 *individual* M06 signed input events.

630 x 8-hex-digit words:
  0..578  original D3.D.2C 579-word independently verified M02/M03 oracle
           incl expected coalesced currents for READBACK ONLY: never write
           those expected currents to fabric in D3.D.2D.
  579..629 17 distinct (neuron, tick, signed32 current) event tuples.
The hardware must perform coalescing via AXI mailbox PUSH itself.
NO DMA/DDR/streaming M05 HLS or physical execution is implied by vectors.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2c_m06_vectors as m06

EVENTS=17
WORDS=579+3*EVENTS

def words() -> tuple[str,...]:
    old=m06.words()  # M02 dense/event and M03 sparse agreement
    net,events,original_current,voltages,masks,syn=m06.golden()
    if len(old)!=579 or len(events)!=EVENTS:
        raise ValueError("original M06 workload drift")
    out=list(old)
    actual=[[0]*4 for _ in range(32)]
    for ev in events:
        if not (0<=ev.neuron<32 and 0<=ev.tick<4):
            raise ValueError("raw M06 event geometry drift")
        out.extend((m06.u32(ev.neuron),m06.u32(ev.tick),m06.u32(ev.current)))
        actual[ev.neuron][ev.tick]+=ev.current
    if actual!=original_current:
        raise ValueError("raw event independence and current coalescing mismatch")
    if len(out)!=WORDS or any(len(x)!=8 for x in out):
        raise ValueError("D3.D.2D raw event file length incorrect")
    return tuple(out)

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    if not a.out.parent.is_dir() or a.out.exists() or a.out.is_symlink():
        p.error("new exclusive hex output in existing directory only")
    try:
        with a.out.open("x",encoding="ascii") as handle:
            handle.write("\n".join(words())+"\n")
    except (ValueError,OSError) as exc:
        print("M08_D3D2D_RAW_EVENTS_PC_REJECTED: "+str(exc),file=sys.stderr)
        return 2
    print("M08_D3D2D_RAW_17_EVENTS_M02_M03_GOLDEN_PC_ONLY="+str(a.out))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
