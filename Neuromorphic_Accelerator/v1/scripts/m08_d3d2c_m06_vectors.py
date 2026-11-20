#!/usr/bin/env python3
"""D3.D.2C source-only exact M06 G3.3 32-neuron × 4-tick golden image.

Reuses the *accepted original* M06 5 recurrent synapses / 17 input events.
M02 dense, M02 queue and M03 sparse must match, then this generator
derives hardware-readback synaptic-current words from prior spike events.
External events are coalesced in Python to signed32 neuron/tick currents,
NOT delivered separately or accumulated in the FPGA in this stage.
This is not evidence of physical M06 HLS, paging, DDR or board execution.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
sys.path.insert(0, str(ROOT/"scripts"))

from m06_g3_3_m02_m03_owner_vectors import fixture_oracles

NEURONS=32
TICKS=4
MAX_EDGES=8
WORDS=3 + NEURONS*8 + MAX_EDGES*4 + NEURONS*9
NONCE=0xD2C00001
DECAY_MODE=3 # exact M06 3/4 signed truncate-to-zero

def u32(x: int) -> str:
    if not -(1<<31) <= x < (1<<32):
        raise ValueError("32-bit signed wire value overflow")
    return f"{x & 0xffffffff:08X}"

def golden():
    network,events,dense,sparse=fixture_oracles()
    if (len(network.neurons)!=NEURONS or len(network.synapses)!=5 or
            len(events)!=17 or network.decay_num!=3 or
            network.decay_den!=4 or network.state_bits!=16):
        raise ValueError("original M06 32x4 neural fixture drift")
    external=[[0]*TICKS for _ in range(NEURONS)]
    for ev in events:
        if not (0<=ev.neuron<NEURONS and 0<=ev.tick<TICKS):
            raise ValueError("M06 external event outside 32x4 geometry")
        external[ev.neuron][ev.tick]+=ev.current
    synaptic=[[0]*TICKS for _ in range(NEURONS)]
    for e in network.synapses:
        if not (0<=e.pre<NEURONS and 0<=e.post<NEURONS and
                1<=e.delay<TICKS and -(1<<15)<=e.weight<(1<<15)):
            raise ValueError("M06 recurrent edge outside physical ABI")
        for t in range(e.delay,TICKS):
            if e.pre in dense.spike_rows[t-e.delay]:
                synaptic[e.post][t]+=e.weight
    masks=tuple(sum(1<<t for t in range(TICKS)
                    if n in dense.spike_rows[t]) for n in range(NEURONS))
    voltages=tuple(tuple(dense.voltage_rows[t][n] for t in range(TICKS))
                   for n in range(NEURONS))
    return network,events,external,voltages,masks,synaptic

def words() -> tuple[str,...]:
    net,events,ext,voltages,masks,syn=golden()
    out=[u32(NONCE),u32(DECAY_MODE),u32(len(net.synapses))]
    for n,unit in enumerate(net.neurons):
        out.extend(u32(x) for x in (
            unit.initial_v,unit.bias,unit.threshold,unit.reset_v,*ext[n]))
    for edge in net.synapses:
        out.extend(u32(x) for x in (
            edge.pre,edge.post,edge.weight,edge.delay))
    for _ in range(MAX_EDGES-len(net.synapses)):
        out.extend(["00000000"]*4)
    for n in range(NEURONS):
        out.extend(u32(x) for x in voltages[n])
        out.append(u32(masks[n]))
        out.extend(u32(x) for x in syn[n])
    if len(out)!=WORDS or any(len(x)!=8 for x in out):
        raise AssertionError("wrong original 32x4 wire data geometry")
    return tuple(out)

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists() or not args.out.parent.is_dir() or args.out.is_symlink():
        parser.error("exclusive NEW hex file in existing directory required")
    try:
        with args.out.open("x",encoding="ascii") as f:
            f.write("\n".join(words())+"\n")
    except (OSError,ValueError) as exc:
        print("M08_D3D2C_M06_VECTORS_REJECTED: "+str(exc),file=sys.stderr)
        return 2
    print("M08_D3D2C_M06_32X4_DENSE_EVENT_SPARSE_GOLDEN_PC_ONLY="+
          str(args.out)+" words="+str(WORDS)+" neurons=32 ticks=4 edges=5 events=17")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
