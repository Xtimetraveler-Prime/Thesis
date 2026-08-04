"""Adapter for the transparent Python neuromorphic-core model."""

from __future__ import annotations

from .model import (
    BackendTick,
    BackendTrace,
    ComparisonScenario,
    describe_synapses,
)
from ..core import NeuromorphicCore


def run_python_backend(scenario: ComparisonScenario) -> BackendTrace:
    """Run a scenario using :class:`NeuromorphicCore`."""

    core = NeuromorphicCore(
        scenario.neuron_configs,
        scenario.synapses,
        arithmetic=scenario.arithmetic,
    )
    ticks: list[BackendTick] = []

    for input_axons in scenario.input_schedule:
        trace = core.step(input_axons)
        ticks.append(
            BackendTick(
                tick=trace.tick,
                current_before=trace.current_before,
                voltage_before=trace.voltage_before,
                current_after=trace.current_after,
                voltage_after=trace.voltage_after,
                spikes=tuple(spike.neuron_id for spike in trace.spikes),
            )
        )

    return BackendTrace(
        backend="python-golden-model",
        scenario=scenario.name,
        ticks=tuple(ticks),
        metadata=(("model", "NeuromorphicCore"),),
        synapses=describe_synapses(scenario.synapses),
    )
