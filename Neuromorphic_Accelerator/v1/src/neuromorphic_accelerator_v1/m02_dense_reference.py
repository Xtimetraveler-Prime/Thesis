"""M02 independent dense timestep scalar LIF oracle.

Intentionally O(ticks * neurons * (external events + synapses)), for
transparency rather than acceleration; it does not call the event-queued
implementation's neuron update or routing code.
"""
from __future__ import annotations

from collections.abc import Iterable

from .m02_types import InputCurrent, Network, ReferenceTrace, validate


def evaluate_dense(
    network: Network, input_currents: Iterable[InputCurrent], *, ticks: int
) -> ReferenceTrace:
    events = validate(network, input_currents, ticks)
    lo = -(2 ** (network.state_bits - 1))
    hi = (2 ** (network.state_bits - 1)) - 1
    previous = [p.initial_v for p in network.neurons]
    voltages: list[tuple[int, ...]] = []
    spikes_at_tick: list[tuple[int, ...]] = []

    for t in range(ticks):
        next_voltages = []
        fires = []
        for neuron_id, p in enumerate(network.neurons):
            # Intentionally rescan *all* external currents and edges for each
            # logical neuron, rather than consuming scheduled event buckets.
            current = sum(
                e.current for e in events
                if e.tick == t and e.neuron == neuron_id
            )
            for edge in network.synapses:
                if (edge.post == neuron_id and t >= edge.delay
                        and edge.pre in spikes_at_tick[t - edge.delay]):
                    current += edge.weight

            product = previous[neuron_id] * network.decay_num
            if product < 0:
                leaked = -(abs(product) // network.decay_den)
            else:
                leaked = product // network.decay_den

            candidate = leaked + p.bias + current
            if candidate < lo:
                candidate = lo
            elif candidate > hi:
                candidate = hi
            if candidate >= p.threshold:
                fires.append(neuron_id)
                next_voltages.append(p.reset_v)
            else:
                next_voltages.append(candidate)
        previous = next_voltages
        voltages.append(tuple(previous))
        spikes_at_tick.append(tuple(fires))

    return ReferenceTrace(tuple(voltages), tuple(spikes_at_tick))
