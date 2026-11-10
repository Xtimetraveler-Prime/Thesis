#!/usr/bin/env python3
"""Generate independent M02 dense-reference inputs for a paged RTL LIF gate.

32 logical neurons, 16B record each, 16 neurons/page, ONE 256B RTL slot.
Four ticks force dirty evictions between blocks and preserve previous
signed16 voltage and four-byte last-update tick metadata. The RTL computes
LIF arithmetic, while this Python generator supplies external+recurrent
current deliveries and M02 oracle reference outputs. Synaptic routing and
the accepted M05 HLS neural accelerator are NOT tested by this fixture.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from neuromorphic_accelerator_v1.m02_dense_reference import evaluate_dense
from neuromorphic_accelerator_v1.m02_types import Network, Neuron, Synapse, InputCurrent

NEURONS=32
TICKS=4
DECAY_NUM=3
DECAY_DEN=4


def fixture():
    cells=tuple(Neuron(
        initial_v=((n*7)%17)-8,
        bias=(n%5)-2,
        threshold=9+(n%4),
        reset_v=-2+(n%3),
    ) for n in range(NEURONS))
    edges=(
        Synapse(pre=0,post=16,weight=4,delay=1),
        Synapse(pre=16,post=0,weight=-3,delay=1),
        Synapse(pre=3,post=31,weight=7,delay=1),
        Synapse(pre=31,post=3,weight=-5,delay=1),
        Synapse(pre=5,post=5,weight=2,delay=2),
    )
    currents=(
        InputCurrent(tick=0,neuron=0,current=18),
        InputCurrent(tick=0,neuron=3,current=14),
        InputCurrent(tick=0,neuron=16,current=-8),
        # Force signed16 positive/negative saturation before threshold:
        InputCurrent(tick=0,neuron=7,current=32767),
        InputCurrent(tick=0,neuron=8,current=-32768),
        InputCurrent(tick=1,neuron=16,current=24),
        # Two independently admitted events must cancel BEFORE clamping:
        InputCurrent(tick=1,neuron=9,current=32767),
        InputCurrent(tick=1,neuron=9,current=-32768),
        InputCurrent(tick=1,neuron=5,current=14),
        InputCurrent(tick=1,neuron=31,current=8),
        InputCurrent(tick=2,neuron=0,current=-20),
        InputCurrent(tick=2,neuron=31,current=25),
        InputCurrent(tick=2,neuron=3,current=7),
        InputCurrent(tick=2,neuron=8,current=32767),
        InputCurrent(tick=3,neuron=0,current=30),
        InputCurrent(tick=3,neuron=16,current=21),
        InputCurrent(tick=3,neuron=5,current=-22),
    )
    network=Network(neurons=cells,synapses=edges,
                    decay_num=DECAY_NUM,decay_den=DECAY_DEN,
                    state_bits=16)
    golden=evaluate_dense(network,currents,ticks=TICKS)
    deliveries=[[0]*NEURONS for _ in range(TICKS)]
    for event in currents:
        deliveries[event.tick][event.neuron]+=event.current
    for t in range(TICKS):
        for edge in edges:
            if t>=edge.delay and edge.pre in golden.spike_rows[t-edge.delay]:
                deliveries[t][edge.post]+=edge.weight
    return network,golden,deliveries


def generate() -> str:
    net,trace,deliveries=fixture()
    lines=[
        "// GENERATED FROM INDEPENDENT M02 DENSE PYTHON ORACLE",
        "// NOT an M05 HLS hardware result; recurrent inputs precomputed.",
        "// 32 neurons x 16B state / 16 neurons per 256B block / 1 slot.",
        "task automatic load_m06_lif_vectors;",
        "begin",
    ]
    for i,p in enumerate(net.neurons):
        for arr,val in (
            ("initial_v",p.initial_v),("neuron_bias",p.bias),
            ("neuron_threshold",p.threshold),("neuron_reset",p.reset_v),
        ):
            lines.append(f"  {arr}[{i}]=16'sd{val};" if val>=0
                         else f"  {arr}[{i}]=-16'sd{-val};")
    for t in range(TICKS):
        for i in range(NEURONS):
            idx=t*NEURONS+i
            current=deliveries[t][i]
            v=trace.voltage_rows[t][i]
            spike=int(i in trace.spike_rows[t])
            lines.append(f"  routed_current[{idx}]=32'sd{current};" if current>=0
                         else f"  routed_current[{idx}]=-32'sd{-current};")
            lines.append(f"  oracle_v[{idx}]=16'sd{v};" if v>=0
                         else f"  oracle_v[{idx}]=-16'sd{-v};")
            lines.append(f"  oracle_spike[{idx}]=1'b{spike};")
    lines.extend(["end","endtask",""])
    return "\n".join(lines)


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    try:
        if a.output.exists() or not a.output.parent.is_dir():
            raise ValueError("exclusive new vector output in existing directory required")
        with a.output.open("x",encoding="utf-8") as f:
            f.write(generate())
    except (ValueError,OSError) as err:
        print("M06 LIF fixture generation FAILED: "+str(err),file=sys.stderr)
        return 2
    net,trace,deliveries=fixture()
    spikes=sum(map(len,trace.spike_rows))
    print(f"M06 independent dense M02 neural fixture generated: "
          f"{len(net.neurons)} neurons, {TICKS} ticks, {spikes} spikes; "
          "routed currents PRECOMPUTED; hardware RTL NOT RUN")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
