"""P06-B1.4 independent MONOLITHIC 26-tick integer network oracle.

Crucial independence boundary: numerical evolution uses ONLY the previously
accepted standalone p06_integer_oracle (not LogicalChip, step_compartment,
compiled axon/synapse templates, P03 images or their decoded weights).
Connectivity and neuron order are derived directly from original NetworkSpec.
Production compiler/packed execution is a *test subject* in b14_differential.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

from .compiler import NetworkSpec
from .p06_integer_oracle import (
    LIFParameters, LIFState, accumulate_synapses, lif_step,
)

B14_ORACLE_SCHEMA = "p06-b1.4-independent-monolithic-integer-v1"
B14_TICKS = 26
_B14_INPUT_TICKS = 25
_B14_IMAGE_CHANNELS = 784
Neuron = tuple[str, int]
Source = tuple[str, int]
EventSchedule = Mapping[str, tuple[tuple[int, ...], ...]]


class B14OracleError(ValueError):
    """Reject an unsupported network, malformed input or lossy final epoch."""


def pixel_schedule_independent(pixels: bytes) -> tuple[tuple[int, ...], ...]:
    """Reimplement frozen pixel phase/quota equation independently of P06-A.

    The accepted production p06_input_contract.pixel_spikes is a differential
    test subject; importing/calling it here would hide encoder regressions.
    """
    if type(pixels) is not bytes or len(pixels) != _B14_IMAGE_CHANNELS:
        raise B14OracleError("independent pixel encoder requires 784 raw uint8 bytes")
    steps = []
    for tick in range(_B14_INPUT_TICKS):
        active = []
        for index, level in enumerate(pixels):
            phase = (tick + 17 * index) % 25
            if ((phase + 1) * level) // 255 > (phase * level) // 255:
                active.append(index)
        steps.append(tuple(active))
    steps.append(())
    return tuple(steps)


def _check_schedule(network: NetworkSpec, schedule: EventSchedule, ticks: int) -> None:
    if not isinstance(schedule, Mapping):
        raise B14OracleError("input schedule must be a mapping")
    sources = {pop.name: pop.size for pop in network.input_populations}
    if set(schedule) != set(sources):
        raise B14OracleError("input schedule populations must match original NetworkSpec")
    for population, size in sources.items():
        rows = schedule[population]
        if not isinstance(rows, tuple) or len(rows) != ticks:
            raise B14OracleError("input schedule must contain exactly 26 immutable tick tuples")
        for tick, indices in enumerate(rows):
            if (not isinstance(indices, tuple)
                    or any(type(index) is not int or not 0 <= index < size
                           for index in indices)
                    or tuple(sorted(set(indices))) != indices):
                raise B14OracleError(
                    f"input schedule {population} tick {tick}: invalid, repeated or unordered source indices")


def _parameters(network: NetworkSpec) -> dict[Neuron, LIFParameters]:
    parameters = {}
    for population in network.populations:
        cfg = population.compartment
        if cfg.parent_compartment is not None or cfg.root_compartment is not None:
            raise B14OracleError("B1.4 oracle does not support compartment tree links")
        try:
            par = LIFParameters(
                current_decay=cfg.current_decay,
                voltage_decay=cfg.voltage_decay,
                threshold=cfg.threshold,
                bias=cfg.bias,
                reset_voltage=cfg.reset_voltage,
                refractory_ticks=cfg.refractory_ticks,
            )
        except (TypeError, ValueError) as exc:
            raise B14OracleError(f"non-P03-representable parameters for {population.name}") from exc
        for index in range(population.size):
            parameters[(population.name, index)] = par
    return parameters


@dataclass(frozen=True, slots=True)
class MonolithicTick:
    tick: int
    before: tuple[tuple[Neuron, LIFState], ...]
    synaptic_inputs: tuple[tuple[Neuron, int], ...]
    after: tuple[tuple[Neuron, LIFState], ...]
    spikes: tuple[Neuron, ...]
    readout_counts: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class MonolithicRun:
    schema: str
    source_fingerprint: str
    readout_population: str
    ticks: tuple[MonolithicTick, ...]
    readout_spike_counts: tuple[int, ...]
    predicted_class: int
    trace_sha256: str

    @property
    def spike_count(self) -> int:
        return sum(len(tick.spikes) for tick in self.ticks)


def _trace_hash(steps: tuple[MonolithicTick, ...]) -> str:
    document = []
    for tick in steps:
        document.append({
            "tick": tick.tick,
            "before": [(p, i, s.current, s.voltage, s.refractory_remaining)
                       for (p, i), s in tick.before],
            "synaptic_input": [(p, i, weight) for (p, i), weight in tick.synaptic_inputs],
            "after": [(p, i, s.current, s.voltage, s.refractory_remaining)
                      for (p, i), s in tick.after],
            "spikes": list(tick.spikes),
            "readout_counts": list(tick.readout_counts),
        })
    return hashlib.sha256(json.dumps(
        document, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def simulate_monolithic(
    network: NetworkSpec, schedule: EventSchedule, *,
    readout_population: str, ticks: int = B14_TICKS,
) -> MonolithicRun:
    """Evaluate 26 ticks of independently accumulated, saturated integer LIF.

    Algorithmically synchronous, despite spike-driven sparse contributions.
    Neural edges from spike(t-1) only enter destination at timestep t.
    Raw input indices are explicit per-tick facts, NOT compiled ingress maps.
    """
    if not isinstance(network, NetworkSpec):
        raise TypeError("network must be original validated NetworkSpec")
    if type(ticks) is not int or ticks != B14_TICKS:
        raise B14OracleError("B1.4 requires exactly 25 input ticks plus one drain tick")
    populations = {pop.name: pop for pop in network.populations}
    if readout_population not in populations:
        raise B14OracleError("readout population missing from original network")
    _check_schedule(network, schedule, ticks)
    keys = tuple((pop.name, index) for pop in sorted(network.populations, key=lambda p: p.name)
                 for index in range(pop.size))
    params = _parameters(network)
    external_edges: dict[Source, list[tuple[Neuron, int]]] = {}
    neural_edges: dict[Source, list[tuple[Neuron, int]]] = {}
    for projection in network.input_projections:
        for e in projection.connections:
            external_edges.setdefault((projection.source_input, e.source_index), []).append(
                ((projection.destination_population, e.destination_index), e.weight))
    for projection in network.projections:
        for e in projection.connections:
            neural_edges.setdefault((projection.source_population, e.source_index), []).append(
                ((projection.destination_population, e.destination_index), e.weight))
    state = {neuron: LIFState() for neuron in keys}
    previously_spiked: tuple[Neuron, ...] = ()
    counts = [0] * populations[readout_population].size
    history: list[MonolithicTick] = []
    for tick in range(ticks):
        contributions: dict[Neuron, list[int]] = {key: [] for key in keys}
        # Direct source projection graph, NOT destination axons/templates.
        for population, rows in sorted(schedule.items()):
            for source_index in rows[tick]:
                for destination, weight in external_edges.get((population, source_index), ()):
                    contributions[destination].append(weight)
        for source in previously_spiked:
            for destination, weight in neural_edges.get(source, ()):
                contributions[destination].append(weight)
        old = tuple((neuron, state[neuron]) for neuron in keys)
        inputs = tuple((neuron, accumulate_synapses(contributions[neuron]))
                       for neuron in keys)
        next_state: dict[Neuron, LIFState] = {}
        emitted: list[Neuron] = []
        for neuron, received in inputs:
            step = lif_step(state[neuron], params[neuron], received)
            next_state[neuron] = step.state
            if step.spiked:
                emitted.append(neuron)
                if neuron[0] == readout_population:
                    counts[neuron[1]] += 1
        if tick == ticks - 1 and any(neural_edges.get(origin) for origin in emitted):
            raise B14OracleError("final drain tick emits neural packets targeting unserviced epoch 26")
        state = next_state
        previously_spiked = tuple(emitted)
        history.append(MonolithicTick(
            tick=tick,
            before=old,
            synaptic_inputs=inputs,
            after=tuple((key, state[key]) for key in keys),
            spikes=previously_spiked,
            readout_counts=tuple(counts),
        ))
    steps = tuple(history)
    winner = max(range(len(counts)), key=lambda neuron: counts[neuron])
    return MonolithicRun(
        schema=B14_ORACLE_SCHEMA,
        source_fingerprint=network.fingerprint,
        readout_population=readout_population,
        ticks=steps,
        readout_spike_counts=tuple(counts),
        predicted_class=winner,
        trace_sha256=_trace_hash(steps),
    )
