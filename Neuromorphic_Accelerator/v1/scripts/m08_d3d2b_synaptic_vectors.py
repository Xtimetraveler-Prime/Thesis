#!/usr/bin/env python3
"""D3.D.2B: M02 dense + event independent routed-synapse golden (PC only).

Four neurons, four ticks, up to 8 signed16 weighted delayed synapses.
Actual FPGA must calculate synaptic current, voltages and spikes itself.
No hardware access here.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from neuromorphic_accelerator_v1.m02_types import (
    InputCurrent, Network, Neuron, Synapse,
)
from neuromorphic_accelerator_v1.m02_dense_reference import evaluate_dense
from neuromorphic_accelerator_v1.m02_event_reference import evaluate_events


@dataclass(frozen=True)
class Unit:
    initial: int
    bias: int
    threshold: int
    reset: int
    external: tuple[int, int, int, int]


@dataclass(frozen=True)
class Edge:
    pre: int
    post: int
    weight: int
    delay: int


@dataclass(frozen=True)
class Fixture:
    name: str
    nonce: int
    decay_mode: int
    units: tuple[Unit, Unit, Unit, Unit]
    edges: tuple[Edge, ...]


FIXTURES = (
    Fixture("chain_recurrent", 0xD2B00001, 2, (
        Unit(0, 0, 4, 0, (4, 0, 0, 0)),
        Unit(0, 0, 3, 0, (0, 0, 0, 0)),
        Unit(0, 0, 3, 0, (0, 0, 0, 0)),
        Unit(0, 0, 4, 0, (0, 0, 0, 0)),
    ), (
        Edge(0, 1, 4, 1), Edge(1, 2, 5, 1),
        Edge(2, 3, 4, 1), Edge(3, 0, 1, 1),
        Edge(0, 2, 2, 2), Edge(0, 2, -2, 2),
        Edge(1, 1, 2, 2), Edge(2, 0, -3, 1),
    )),
    Fixture("inhibition_half_decay", 0xD2B00002, 1, (
        Unit(-3, 0, 5, -2, (8, 0, 0, 0)),
        Unit(0, 3, 6, 0, (0, 0, 0, 0)),
        Unit(0, 0, 5, 0, (0, 0, 0, 0)),
        Unit(-1, -1, 8, -2, (0, 0, 0, 0)),
    ), (
        Edge(0, 1, 3, 1), Edge(0, 2, 6, 1),
        Edge(0, 2, -6, 1), Edge(1, 2, 6, 1),
        Edge(1, 1, 4, 2), Edge(1, 0, -4, 1),
        Edge(2, 3, 10, 1), Edge(3, 0, -2, 1),
    )),
)

# Fixed, independently hand-calculated trace anchors; cannot accept oracle
# agreement alone if both implementations drift from the known mathematics.
ANCHORS = {
    "chain_recurrent": (
        ((0, 0, 0, -3), (0, 0, 0, 2),
         (0, 0, 0, 0), (0, 0, 0, 0)),
        (1, 2, 4, 8),
        ((0, 0, 0, -3), (0, 4, 0, 2),
         (0, 0, 5, 0), (0, 0, 0, 4)),
    ),
    "inhibition_half_decay": (
        ((-2, -1, -4, -2), (3, 0, 3, 0),
         (0, 0, 0, 0), (-1, -1, -1, -2)),
        (1, 10, 4, 8),
        ((0, 0, -4, 0), (0, 3, 0, 4),
         (0, 0, 6, 0), (0, 0, 0, 10)),
    ),
}

# 1 workload name + 103 fixed-length 32-bit words:
# 3 header + 4x8 neurons + 8x4 synapses + 4x9 outputs.
FIELD_COUNT = 104
RATIOS = ((0, 1), (1, 2), (1, 1))


def u32(value: int) -> str:
    if not -(1 << 31) <= value < (1 << 32):
        raise ValueError("32-bit wire integer required")
    return f"{value & 0xFFFFFFFF:08X}"


def expected(f: Fixture):
    if len(f.units) != 4 or len(f.edges) > 8 or f.decay_mode not in range(3):
        raise ValueError("wrong physical fixture geometry")
    for edge in f.edges:
        if not (0 <= edge.pre < 4 and 0 <= edge.post < 4
                and 1 <= edge.delay <= 3 and -32768 <= edge.weight <= 32767):
            raise ValueError("edge violates new D3.D.2B supported ABI")
    num, den = RATIOS[f.decay_mode]
    net = Network(
        neurons=tuple(Neuron(initial_v=u.initial, bias=u.bias,
                             threshold=u.threshold, reset_v=u.reset)
                      for u in f.units),
        synapses=tuple(Synapse(e.pre, e.post, e.weight, e.delay)
                       for e in f.edges),
        decay_num=num, decay_den=den, state_bits=16,
    )
    inputs = tuple(InputCurrent(t, n, c)
                   for n, u in enumerate(f.units)
                   for t, c in enumerate(u.external) if c != 0)
    dense = evaluate_dense(net, inputs, ticks=4)
    queued = evaluate_events(net, inputs, ticks=4)
    if dense != queued:
        raise ValueError("M02 independent dense and event queue disagree")
    voltages = tuple(tuple(row[n] for row in dense.voltage_rows)
                     for n in range(4))
    masks = tuple(sum((1 << t) for t, row in enumerate(dense.spike_rows)
                      if n in row) for n in range(4))
    # Independent explicit synaptic-current trace from the oracle spike rows,
    # NOT from the RTL. The FPGA must expose its computed synapse sums.
    delivered = tuple(tuple(
        sum(e.weight for e in f.edges if e.post == n and
            t >= e.delay and e.pre in dense.spike_rows[t - e.delay])
        for t in range(4)) for n in range(4))
    result = voltages, masks, delivered
    if result != ANCHORS[f.name]:
        raise ValueError("M02 reference diverged from hand-checked routed anchors: " + f.name)
    return result


def format_fixture(f: Fixture) -> str:
    voltages, masks, syn = expected(f)
    fields = [f.name, u32(f.nonce), u32(f.decay_mode), u32(len(f.edges))]
    for unit in f.units:
        fields += [u32(x) for x in (unit.initial, unit.bias, unit.threshold,
                                   unit.reset, *unit.external)]
    for edge in f.edges:
        fields += [u32(x) for x in (edge.pre, edge.post, edge.weight, edge.delay)]
    for _ in range(8 - len(f.edges)):
        fields += [u32(0)]*4
    for n in range(4):
        fields += [u32(v) for v in voltages[n]]
        fields += [u32(masks[n])]
        fields += [u32(x) for x in syn[n]]
    if len(fields) != FIELD_COUNT:
        raise AssertionError("malformed complete routed reference frame")
    return "|".join(fields)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists() or not a.out.parent.is_dir():
        ap.error("fresh regular-file output parent required, no overwrite")
    text = ("# schema=m08-d3d2b-m02-routed-four-neuron-v1\n"
            "# independent_dense_vs_queued=PASS\n" +
            "\n".join(format_fixture(f) for f in FIXTURES) + "\n")
    a.out.write_text(text, encoding="ascii")
    print("M08_D3D2B_M02_ROUTED_GOLDENS_PC_ONLY=" + str(a.out)
          + " fixtures=" + str(len(FIXTURES)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
