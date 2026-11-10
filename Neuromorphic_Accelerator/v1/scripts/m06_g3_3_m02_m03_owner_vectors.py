#!/usr/bin/env python3
"""Original-HLS G3.3: independent M02/M03 neural/eviction owner XSim vectors.

The source of neural truth is the ALREADY accepted independent M02 dense
oracle, cross-checked against M03 exact sparse and M02 event references.
The generated SystemVerilog vectors are source-only until owner ORIGINAL
Vivado 2025.2 XSim with generated HLS + AMD IP. No fake-IP functional run.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from neuromorphic_accelerator_v1.m02_event_reference import evaluate_events
from neuromorphic_accelerator_v1.m03_sparse_reference import evaluate_exact_sparse
from m06_generate_paged_lif16_vectors import fixture,NEURONS,TICKS

# Last two 256B pages in 64KiB, 16 bytes/row, one 256B cache slot.
CANONICAL_FIRST=4096-NEURONS
SLOTS=1

def twos(value: int,width: int) -> int:
    if not -(1<<(width-1))<=value<(1<<(width-1)):
        raise ValueError("fixture signed width exceeded")
    return value & ((1<<width)-1)

def pack_neuron(p) -> int:
    return (twos(p.initial_v,32) | (twos(p.bias,32)<<32) |
            (twos(p.threshold,32)<<64) | (twos(p.reset_v,32)<<96))

def pack_synapse(p) -> int:
    # 192-bit Vitis struct ABI: pre[31:0],post[63:32],weight[95:64],
    # 32b C alignment pad [127:96], delay64[191:128].
    return (p.pre | (p.post<<32) | (twos(p.weight,32)<<64) |
            (p.delay<<128))

def pack_external(p) -> int:
    return p.tick | (p.neuron<<64) | (twos(p.current,32)<<96)

def pack_trace(t: int, i: int, voltage: int, spike: bool, evaluate: bool,
               deliveries: int) -> int:
    # 192b C struct layout, including alignment pad [159:144]:
    # tick64,id32,voltage32,spike8,evaluated8,pad16,delivered_count32.
    return (t | (i<<64) | (twos(voltage,32)<<96) |
            (int(spike)<<128) | (int(evaluate)<<136) |
            (deliveries<<160))

def metrics_reference(sparse) -> dict[str,int]:
    """Deterministic ONE-slot page access oracle (not the HLS implementation).

    Independent expected page touches from M03 evaluated IDs + the public
    32-row full trace ABI. Every evaluate dirties its whole resident block.
    """
    values={k:0 for k in (
        "page_accesses","page_hits","page_misses","page_evictions",
        "dirty_writebacks","page_fills","m05_evaluations","emitted_spikes")}
    page=None
    dirty=False
    def touch(idx:int,write:bool) -> None:
        nonlocal page,dirty
        block=(CANONICAL_FIRST+idx)//16
        values["page_accesses"]+=1
        if page==block:
            values["page_hits"]+=1
        else:
            values["page_misses"]+=1
            if page is not None:
                values["page_evictions"]+=1
                if dirty:
                    values["dirty_writebacks"]+=1
            page=block
            dirty=False
            values["page_fills"]+=1
        if write:
            dirty=True
    for t in range(TICKS):
        for i in sparse.evaluated_ids_by_tick[t]:
            touch(i,True)
            values["m05_evaluations"]+=1
        for i in range(NEURONS):
            touch(i,False)
        values["emitted_spikes"]+=len(sparse.trace.spike_rows[t])
    if dirty:
        values["dirty_writebacks"]+=1
    return values

def fixture_oracles():
    from neuromorphic_accelerator_v1.m02_types import InputCurrent
    # Event stream is explicitly the original 17-event independent fixture,
    # NOT the already aggregated 32x4 currents.
    events=(
        InputCurrent(0,0,18),InputCurrent(0,3,14),
        InputCurrent(0,16,-8),InputCurrent(0,7,32767),
        InputCurrent(0,8,-32768),InputCurrent(1,16,24),
        InputCurrent(1,9,32767),InputCurrent(1,9,-32768),
        InputCurrent(1,5,14),InputCurrent(1,31,8),
        InputCurrent(2,0,-20),InputCurrent(2,31,25),
        InputCurrent(2,3,7),InputCurrent(2,8,32767),
        InputCurrent(3,0,30),InputCurrent(3,16,21),
        InputCurrent(3,5,-22),
    )
    net,dense,_=fixture()
    event=evaluate_events(net,events,ticks=TICKS)
    sparse=evaluate_exact_sparse(net,events,ticks=TICKS)
    if dense!=event or dense!=sparse.trace:
        raise ValueError("independent M02 dense/event and M03 sparse oracle disagree")
    if len(net.neurons)!=32 or len(net.synapses)!=5 or len(events)!=17 or TICKS!=4:
        raise ValueError("independent paging fixture contract drift")
    return net,events,dense,sparse

def vectors() -> str:
    net,events,dense,sparse=fixture_oracles()
    metrics=metrics_reference(sparse)
    if metrics["page_evictions"]<4 or metrics["dirty_writebacks"]<2:
        raise ValueError("test no longer forces canonical dirty eviction")
    lines=[
        "// Source-only GENERATION: independent M02 dense + M02 event + M03 sparse oracles",
        "// 32 neurons, 4 ticks, 5 recurrent edges, 17 external deliveries,",
        "// LAST two 256B pages in 64KiB, 1 cache slot, real owner XSim PENDING.",
        "reg [127:0] oracle_neurons [0:31];",
        "reg [191:0] oracle_synapses [0:4];",
        "reg [127:0] oracle_external [0:16];",
        "reg [191:0] oracle_trace [0:127];",
        "reg [127:0] oracle_final_row [0:31];",
        "reg [255:0] oracle_metrics;",
        "initial begin"
    ]
    for i,cell in enumerate(net.neurons):
        lines.append(f"  oracle_neurons[{i}] = 128'h{pack_neuron(cell):032x};")
    for j,syn in enumerate(net.synapses):
        lines.append(f"  oracle_synapses[{j}] = 192'h{pack_synapse(syn):048x};")
    for j,event in enumerate(events):
        lines.append(f"  oracle_external[{j}] = 128'h{pack_external(event):032x};")
    last_evaluated=[0]*NEURONS
    for t in range(TICKS):
        evaluations=set(sparse.evaluated_ids_by_tick[t])
        fires=set(dense.spike_rows[t])
        for i in range(NEURONS):
            idx=t*NEURONS+i
            trace_word=pack_trace(t,i,dense.voltage_rows[t][i],
                                  i in fires,i in evaluations,
                                  sparse.deliveries_by_tick[t])
            lines.append(f"  oracle_trace[{idx}] = 192'h{trace_word:048x};")
            if i in evaluations:
                last_evaluated[i]=t+1
    for i,v in enumerate(dense.voltage_rows[-1]):
        # Four LE words per 16B canonical row: sign16 v, tick+1 watermark,0,0.
        row=twos(v,16) | (last_evaluated[i]<<32)
        lines.append(f"  oracle_final_row[{i}] = 128'h{row:032x};")
    order=(
        "page_accesses","page_hits","page_misses","page_evictions",
        "dirty_writebacks","page_fills","m05_evaluations","emitted_spikes")
    packed=sum(metrics[k]<<(32*i) for i,k in enumerate(order))
    lines.append(f"  oracle_metrics = 256'h{packed:064x};")
    lines.append("end")
    lines.append("")
    return "\n".join(lines)

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output",required=True,type=Path)
    a=ap.parse_args()
    try:
        if a.output.exists() or not a.output.parent.is_dir():
            raise ValueError("original oracle vector output must be NEW file")
        text=vectors()
        a.output.write_text(text)
    except (OSError,ValueError) as err:
        print("M06_G3_3_INDEPENDENT_ORACLE_REJECTED:",err,file=sys.stderr)
        return 2
    print("M06_G3_3_INDEPENDENT_M02_M03_VECTORS_GENERATED "
          "32_NEURONS 4_TICKS 5_EDGES 17_EVENTS 1_CACHE_SLOT "
          "CANONICAL_LAST_TWO_PAGES SOURCE_ONLY_NO_VENDOR_XSIM")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
