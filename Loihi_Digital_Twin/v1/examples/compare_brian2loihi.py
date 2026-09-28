"""Compare deterministic smoke and decay-order scenarios with Brian2Loihi.

Both scenarios are expected to pass. The decay-order case is retained as a
regression test for the corrected rule that delivered synaptic input is visible
before current decay while voltage sees the pre-decay working current.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from neuromorphic_twin import NeuronConfig, Synapse
from neuromorphic_twin.comparison import (
    BackendUnavailableError,
    ComparisonScenario,
    compare_traces,
    format_report,
    run_brian2loihi_backend,
    run_python_backend,
    write_report_json,
    write_trace_json,
)


def build_smoke_scenario() -> ComparisonScenario:
    config = NeuronConfig(
        current_decay=0,
        voltage_decay=0,
        threshold=256,
        reset_voltage=0,
        refractory_ticks=1,
    )
    return ComparisonScenario.build(
        name="brian2loihi-smoke",
        neuron_configs=[config],
        synapses=[Synapse(axon_id=0, target_neuron=0, weight=128)],
        input_schedule=[(0,), (0,)],
    )


def build_decay_order_scenario() -> ComparisonScenario:
    config = NeuronConfig(
        current_decay=2048,
        voltage_decay=0,
        threshold=4096,
        reset_voltage=0,
        refractory_ticks=1,
    )
    return ComparisonScenario.build(
        name="brian2loihi-decay-order",
        neuron_configs=[config],
        synapses=[Synapse(axon_id=0, target_neuron=0, weight=128)],
        input_schedule=[(0,), (), ()],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        choices=("smoke", "decay-order"),
        default="smoke",
    )
    parser.add_argument(
        "--output",
        default="comparison_output",
        help="directory for trace and report JSON files",
    )
    args = parser.parse_args()

    scenario = (
        build_smoke_scenario()
        if args.scenario == "smoke"
        else build_decay_order_scenario()
    )
    candidate = run_python_backend(scenario)
    output = Path(args.output)
    write_trace_json(candidate, output / "python_trace.json")

    try:
        reference = run_brian2loihi_backend(scenario)
    except BackendUnavailableError as exc:
        print(exc)
        print("The Python trace was still written successfully.")
        return 2

    report = compare_traces(reference, candidate)
    print(format_report(report))

    write_trace_json(reference, output / "brian2loihi_trace.json")
    write_report_json(report, output / "comparison_report.json")
    print(f"Wrote trace artifacts to {output.resolve()}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
