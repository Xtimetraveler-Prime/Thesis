#!/usr/bin/env python3
"""Generate ONLY M02-independent-reference golden results for real KV260 JTAG.

Four real ticks, one neuron, no synapses (D3.D.1 subset). Dense and event
reference evaluators MUST agree before producing host-consumed fixtures.
The FPGA receives only parameters and signed input currents, never voltages.
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
class Fixture:
    name: str
    nonce: int
    initial: int
    bias: int
    threshold: int
    reset: int
    mode: int             # ZERO=0, HALF=1, ONE=2
    currents: tuple[int, int, int, int]

FIXTURES = (
    Fixture("negative_trunc_spike", 0xD3D00001, -5, 1, 5, -2, 1, (3, 7, -4, 0)),
    Fixture("positive_negative_saturation", 0xD3D00002, 32760, 0, 32767, -5,
            2, (20, -32768, -2, -2)),
    Fixture("autonomous_bias_equality", 0xD3D00003, 0, 3, 6, 0, 2, (0, 0, -6, 0)),
    Fixture("negative_half_toward_zero", 0xD3D00004, -1, -1, 9, -2, 1,
            (0, 0, 0, 0)),
)
RATIOS = ((0, 1), (1, 2), (1, 1))

def expected(f: Fixture) -> tuple[tuple[int, ...], int]:
    num, den = RATIOS[f.mode]
    net = Network(
        neurons=(Neuron(initial_v=f.initial, bias=f.bias,
                        threshold=f.threshold, reset_v=f.reset),),
        synapses=(), decay_num=num, decay_den=den, state_bits=16
    )
    currents = tuple(InputCurrent(i, 0, v) for i, v in enumerate(f.currents))
    dense = evaluate_dense(net, currents, ticks=4)
    events = evaluate_events(net, currents, ticks=4)
    if dense != events:
        raise ValueError("M02 dense/event mismatch on " + f.name)
    volts = tuple(row[0] for row in dense.voltage_rows)
    spike_mask = sum((1 << t) for t, ids in enumerate(dense.spike_rows) if 0 in ids)
    return volts, spike_mask

def u32(value: int) -> str:
    if not -2**31 <= value < 2**32:
        raise ValueError("out of 32-bit range")
    return f"{value & 0xffffffff:08X}"

def format_fixture(f: Fixture) -> str:
    voltages, mask = expected(f)
    fields = [f.name, u32(f.nonce), u32(f.initial), u32(f.bias),
              u32(f.threshold), u32(f.reset), u32(f.mode),
              *(u32(c) for c in f.currents),
              *(u32(v) for v in voltages), u32(mask)]
    if len(fields) != 16:
        raise AssertionError("fixture wire format must have 16 fields")
    return "|".join(fields)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("refusing to overwrite original fixture evidence")
    if not args.out.parent.is_dir():
        parser.error("fixture output parent does not exist")
    result = ("# schema=m08-d3d-m02-golden-v1\n"
              "# independent_dense_vs_event=PASS\n"
              + "\n".join(format_fixture(f) for f in FIXTURES) + "\n")
    args.out.write_text(result, encoding="ascii")
    print(f"M08_D3D_M02_GOLDEN_CREATED_PC_ONLY={args.out} cases={len(FIXTURES)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
