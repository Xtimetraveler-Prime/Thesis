"""M02 structurally separate event-delivery LIF cross-check (not sparse neuron updates).

This simulator traverses only the outgoing synapses of neurons that fired and
schedules their contributions in time buckets. It updates EVERY neuron on EVERY
tick, including silent/bias-only neurons; correctness does not depend on an
unproved lazy LIF decay shortcut. Do not call this FPGA acceleration.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from .m02_types import InputCurrent, Network, ReferenceTrace, validate


def evaluate_events(
    network: Network, input_currents: Iterable[InputCurrent], *, ticks: int
) -> ReferenceTrace:
    external = validate(network, input_currents, ticks)
    outgoing: list[list[tuple[int, int, int]]] = [
        [] for _ in network.neurons
    ]
    for syn in network.synapses:
        outgoing[syn.pre].append((syn.post, syn.weight, syn.delay))

    # Future synaptic deliveries and external currents share this queue.
    scheduled: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for item in external:
        scheduled[item.tick].append((item.neuron, item.current))

    v = [cell.initial_v for cell in network.neurons]
    rows: list[tuple[int, ...]] = []
    spike_rows: list[tuple[int, ...]] = []
    bits = network.state_bits
    minv = -(1 << (bits - 1))
    maxv = (1 << (bits - 1)) - 1

    for clock in range(ticks):
        # Independently accumulate every current before applying any clamp.
        sums = [0] * len(v)
        for dst, signed_current in scheduled.pop(clock, ()):
            sums[dst] += signed_current

        spikes = []
        updated = []
        for neuron_id in range(len(v)):
            previous = v[neuron_id]
            numerator = previous * network.decay_num
            # Python's // floors negative numbers; perform sign-aware
            # division to implement truncation toward zero, independently
            # from the dense evaluator's leak implementation.
            if numerator >= 0:
                decay = numerator // network.decay_den
            else:
                decay = -((-numerator) // network.decay_den)
            new_value = sums[neuron_id] + network.neurons[neuron_id].bias + decay
            bounded = max(min(new_value, maxv), minv)
            cell = network.neurons[neuron_id]
            if bounded >= cell.threshold:
                spikes.append(neuron_id)
                updated.append(cell.reset_v)
            else:
                updated.append(bounded)

        v = updated
        spike_rows.append(tuple(spikes))
        rows.append(tuple(v))

        # Positive synaptic delays guarantee no propagation back into the
        # just-processed tick. Spike/edge enumeration is deterministic, but
        # integer accumulation is mathematically order independent.
        for pre in spikes:
            for post, weight, delay in outgoing[pre]:
                future = clock + delay
                if future < ticks:
                    scheduled[future].append((post, weight))

    return ReferenceTrace(tuple(rows), tuple(spike_rows))
