#!/usr/bin/env python3
"""Independent M02 dense/queued golden vectors for D3.D.2A FOUR real neurons.

NO hardware access. Host supplies parameters and externally aggregated currents,
NOT the computed voltage/spike outputs. No synapses: this is D3.D.2A, not B.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from neuromorphic_accelerator_v1.m02_types import InputCurrent, Network, Neuron
from neuromorphic_accelerator_v1.m02_dense_reference import evaluate_dense
from neuromorphic_accelerator_v1.m02_event_reference import evaluate_events


@dataclass(frozen=True)
class Unit:
    initial: int
    bias: int
    threshold: int
    reset: int
    currents: tuple[int, int, int, int]


@dataclass(frozen=True)
class Fixture:
    name: str
    nonce: int
    decay_mode: int
    units: tuple[Unit, Unit, Unit, Unit]


FIXTURES = (
    Fixture("independent_half_decay", 0xD2A00001, 1, (
        Unit(-5, 1, 5, -2, (3, 7, -4, 0)),
        Unit(32760, 0, 32767, -5, (20000, -32768, -2, -2)),
        Unit(0, 3, 6, 0, (0, 0, -6, 0)),
        Unit(-1, -1, 9, -2, (0, 0, 0, 0)),
    )),
    Fixture("independent_unit_decay", 0xD2A00002, 2, (
        Unit(0, 3, 6, 0, (0, 0, -6, 0)),
        Unit(32760, 0, 32767, -5, (20, -32768, -2, -2)),
        Unit(-5, 1, 5, -2, (3, 7, -4, 0)),
        Unit(-1, -1, 9, -2, (0, 0, 0, 0)),
    )),
)
RATIOS = ((0, 1), (1, 2), (1, 1))
# Independently hand-reviewed reference anchors, tied to the RTL testbench.
ANCHORS = {
    "independent_half_decay": (
        ((2, -2, -4, -1), (-5, -32768, -16386, -8195),
         (3, 4, -1, 3), (-1, -1, -1, -1)),
        (2, 1, 0, 0),
    ),
    "independent_unit_decay": (
        ((3, 0, -3, 0), (-5, -32768, -32768, -32768),
         (-1, -2, -5, -4), (-2, -3, -4, -5)),
        (2, 1, 2, 0),
    ),
}


def u32(value: int) -> str:
    if not -(1 << 31) <= value < (1 << 32):
        raise ValueError("value outside 32-bit wire representation")
    return f"{value & 0xFFFFFFFF:08X}"


def expected(f: Fixture) -> tuple[tuple[tuple[int, ...], ...], tuple[int, ...]]:
    if len(f.units) != 4 or f.decay_mode not in range(3):
        raise ValueError("wrong D3.D.2A fixture dimensions/decay mode")
    num, den = RATIOS[f.decay_mode]
    network = Network(
        neurons=tuple(Neuron(initial_v=u.initial, bias=u.bias,
                             threshold=u.threshold, reset_v=u.reset)
                      for u in f.units),
        synapses=(), decay_num=num, decay_den=den, state_bits=16,
    )
    currents = tuple(InputCurrent(t, n, c) for n, u in enumerate(f.units)
                     for t, c in enumerate(u.currents) if c != 0)
    dense = evaluate_dense(network, currents, ticks=4)
    queued = evaluate_events(network, currents, ticks=4)
    if dense != queued:
        raise ValueError("M02 dense/queued disagree: " + f.name)
    voltages = tuple(tuple(row[n] for row in dense.voltage_rows)
                     for n in range(4))
    masks = tuple(sum(1 << t for t, sp in enumerate(dense.spike_rows)
                      if n in sp) for n in range(4))
    result = voltages, masks
    if result != ANCHORS.get(f.name):
        raise ValueError("M02 oracle diverged from frozen numeric anchors: " + f.name)
    return result


def format_fixture(f: Fixture) -> str:
    voltages, masks = expected(f)
    fields = [f.name, u32(f.nonce), u32(f.decay_mode)]
    for u in f.units:
        fields += [u32(u.initial), u32(u.bias), u32(u.threshold),
                   u32(u.reset), *(u32(i) for i in u.currents)]
    for v, mask in zip(voltages, masks):
        fields += [*(u32(x) for x in v), u32(mask)]
    if len(fields) != 55:
        raise AssertionError(f"fixture schema expected 55 fields, got {len(fields)}")
    return "|".join(fields)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        p.error("refusing to replace original fixture evidence")
    if not args.out.parent.is_dir():
        p.error("output parent does not exist")
    text = ("# schema=m08-d3d2a-m02-four-neuron-v1\n"
            "# independent_dense_vs_queued=PASS\n" +
            "\n".join(format_fixture(f) for f in FIXTURES) + "\n")
    args.out.write_text(text, encoding="ascii")
    print(f"M08_D3D2A_M02_FOUR_NEURON_GOLDEN_PC_ONLY={args.out} fixtures={len(FIXTURES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
