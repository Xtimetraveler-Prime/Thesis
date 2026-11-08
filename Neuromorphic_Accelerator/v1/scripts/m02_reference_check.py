#!/usr/bin/env python3
"""M02 independent dense vs queued-event LIF reference comparison, PC-only.

Reproducible fixtures with original SHA256 of inputs and per-tick expected
states/spikes; exclusive-create JSON output, never hardware interaction.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from neuromorphic_accelerator_v1.m02_types import (
    SCHEMA, InputCurrent, Network, Neuron, Synapse,
)
from neuromorphic_accelerator_v1.m02_dense_reference import evaluate_dense
from neuromorphic_accelerator_v1.m02_event_reference import evaluate_events


def _bytes(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_bytes(value)).hexdigest()


def _fixtures() -> tuple[tuple[str, Network, tuple[InputCurrent, ...], int], ...]:
    return (
        (
            "threshold_equality",
            Network((Neuron(threshold=5),), decay_num=1, decay_den=2,
                    state_bits=8),
            (InputCurrent(0, 0, 3), InputCurrent(1, 0, 4),
             InputCurrent(2, 0, 2)), 4,
        ),
        (
            "autonomous_bias_no_input",
            Network((Neuron(bias=3, threshold=5),),
                    decay_num=1, decay_den=1, state_bits=8),
            (), 4,
        ),
        (
            "positive_delay_recurrent_loop",
            Network(
                (Neuron(threshold=5), Neuron(threshold=4)),
                (Synapse(0, 1, 4, 2), Synapse(1, 0, 5, 1)),
                decay_num=1, decay_den=1, state_bits=8,
            ),
            (InputCurrent(0, 0, 5),), 4,
        ),
        (
            "negative_current_and_parallel_edges",
            Network((Neuron(threshold=3), Neuron(initial_v=1, threshold=30)),
                    (Synapse(0, 1, 20, 1), Synapse(0, 1, -7, 1)),
                    state_bits=8),
            (InputCurrent(0, 0, 3),), 4,
        ),
    )


def run_original_reference_check(*, seed: int = 20261107, random_cases: int = 50) -> dict:
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    if type(random_cases) is not int or not 0 <= random_cases <= 1000:
        raise ValueError("random_cases must be an integer in [0,1000]")
    reports = []

    def check_case(label: str, net: Network, items: tuple[InputCurrent, ...],
                   ticks: int) -> None:
        dense = evaluate_dense(net, items, ticks=ticks)
        sparse = evaluate_events(net, items, ticks=ticks)
        if dense != sparse:
            raise AssertionError(f"dense/queued disagreement at {label}")
        original = {
            "network": asdict(net), "input_currents": [asdict(i) for i in items],
            "ticks": ticks,
        }
        expected = asdict(dense)
        reports.append({
            "case": label,
            "network_and_input_sha256": _sha(original),
            "voltage_spike_trace_sha256": _sha(expected),
            "neuron_count": len(net.neurons),
            "synapse_count": len(net.synapses),
            "input_count": len(items),
            "ticks": ticks,
            "emitted_spikes": [list(x) for x in dense.emitted_spikes],
            "voltage_rows": [list(x) for x in dense.voltage_rows],
            "spike_rows": [list(x) for x in dense.spike_rows],
            "equal_dense_vs_event_queue": True,
        })

    for args in _fixtures():
        check_case(*args)

    rng = random.Random(seed)
    for index in range(random_cases):
        n = rng.randint(1, 6)
        neurons = tuple(
            Neuron(initial_v=rng.randint(-5, 5),
                   bias=rng.randint(-2, 3),
                   threshold=rng.randint(3, 22),
                   reset_v=0)
            for _ in range(n)
        )
        syn = tuple(
            Synapse(rng.randrange(n), rng.randrange(n),
                    rng.randint(-8, 8), rng.randint(1, 3))
            for _ in range(rng.randint(0, 14))
        )
        inputs = tuple(
            InputCurrent(rng.randrange(12), rng.randrange(n),
                         rng.randint(-10, 10))
            for _ in range(rng.randint(0, 30))
        )
        net = Network(neurons, syn,
                      decay_num=rng.randrange(5), decay_den=4, state_bits=8)
        check_case(f"seeded_random_{index:03d}", net, inputs, 12)

    # This is a pinned handwritten absolute fixture, not just a comparison
    # of two programs that might share the same bug.
    first = reports[0]
    assert first["voltage_rows"] == [[3], [0], [2], [1]]
    assert first["emitted_spikes"] == [[1, 0]]

    return {
        "schema": "neuromorphic-accelerator-v1-m02-independent-ref-report-draft-1",
        "status": "PC_ONLY_PROVISIONAL_M02_REFERENCE_NO_HARDWARE",
        "functional_contract": SCHEMA,
        "numerics": "signed integer, leak trunc_zero, input sum then saturate, inclusive threshold, reset",
        "limits": [
            "No Loihi silicon numerical equivalence",
            "No refractory or separate synaptic-current state",
            "No hardware event scheduling or virtual DDR access",
            "Every neuron updated every timestep despite queued synapses",
            "No trained model or physical latency, power, energy",
        ],
        "seed": seed,
        "random_cases": random_cases,
        "total_cases": len(reports),
        "cases": reports,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261107)
    parser.add_argument("--random-cases", type=int, default=50)
    parser.add_argument("--out", type=Path,
                        help="exclusive-create report path; omit for stdout")
    args = parser.parse_args(argv)
    try:
        result = run_original_reference_check(
            seed=args.seed, random_cases=args.random_cases
        )
        output = json.dumps(result, sort_keys=True, indent=2) + "\n"
        if args.out is None:
            sys.stdout.write(output)
        else:
            with args.out.open("x", encoding="utf-8") as out:
                out.write(output)
            print(f"M02_PC_ONLY_ORIGINAL_REFERENCE_PATH={args.out}")
        print("M02_INDEPENDENT_DENSE_QUEUED_LIF_PARITY_PASS=1",
              file=sys.stderr)
        return 0
    except (OSError, ValueError, AssertionError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
