"""M02 v1 neural interface and strict input validation; no hardware semantics.

The two implementation modules share only immutable types/validation, not the
LIF step arithmetic or spike propagation implementation. CONTRACT:
docs/M02_PROVISIONAL_LIF_CONTRACT.md; not Loihi numerical fidelity.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


SCHEMA = "neuromorphic-accelerator-v1-m02-lif-contract-draft-1"


def _integer(name: str, value: object) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} requires integer (not boolean/float): {value!r}")
    return value


@dataclass(frozen=True)
class Neuron:
    initial_v: int = 0
    bias: int = 0
    threshold: int = 10
    reset_v: int = 0


@dataclass(frozen=True)
class Synapse:
    pre: int
    post: int
    weight: int
    delay: int = 1


@dataclass(frozen=True)
class InputCurrent:
    tick: int
    neuron: int
    current: int


@dataclass(frozen=True)
class Network:
    neurons: tuple[Neuron, ...]
    synapses: tuple[Synapse, ...] = ()
    decay_num: int = 1
    decay_den: int = 1
    state_bits: int = 16


@dataclass(frozen=True)
class ReferenceTrace:
    voltage_rows: tuple[tuple[int, ...], ...]
    spike_rows: tuple[tuple[int, ...], ...]

    @property
    def emitted_spikes(self) -> tuple[tuple[int, int], ...]:
        """Sorted (tick, logical-neuron-id) emitted spikes."""
        return tuple((tick, neuron)
                     for tick, neurons in enumerate(self.spike_rows)
                     for neuron in neurons)


def validate(
    network: Network,
    input_currents: Iterable[InputCurrent],
    ticks: int,
) -> tuple[InputCurrent, ...]:
    """Validate all provenance-critical parameters before any state update.

    Input sequence may be unsorted; current deliveries at the same destination
    and tick are algebraically summed, so no dependence on iteration ordering.
    """
    if not isinstance(network, Network):
        raise ValueError("network must be a Network instance")
    n = len(network.neurons)
    if n == 0:
        raise ValueError("at least one neuron is required")
    _integer("ticks", ticks)
    if ticks < 1:
        raise ValueError("ticks must be >=1")
    bits = _integer("state_bits", network.state_bits)
    if not 4 <= bits <= 32:
        raise ValueError("state_bits must be in [4,32]")
    lo, hi = -(1 << (bits-1)), (1 << (bits-1)) - 1
    dnum = _integer("decay_num", network.decay_num)
    dden = _integer("decay_den", network.decay_den)
    if dden < 1 or dnum < 0 or dnum > dden:
        raise ValueError("expected 0 <= decay_num <= decay_den, decay_den>0")

    for i, p in enumerate(network.neurons):
        if not isinstance(p, Neuron):
            raise ValueError(f"neurons[{i}] must be Neuron")
        for name in ("initial_v", "bias", "threshold", "reset_v"):
            v = _integer(f"neurons[{i}].{name}", getattr(p, name))
            if not lo <= v <= hi:
                raise ValueError(f"neurons[{i}].{name} outside signed state width")
        if p.threshold <= 0:
            raise ValueError("threshold must be positive")
        if p.reset_v >= p.threshold:
            raise ValueError("reset_v must be below threshold")

    for i, e in enumerate(network.synapses):
        if not isinstance(e, Synapse):
            raise ValueError(f"synapses[{i}] must be Synapse")
        pre = _integer("synapse.pre", e.pre)
        post = _integer("synapse.post", e.post)
        weight = _integer("synapse.weight", e.weight)
        delay = _integer("synapse.delay", e.delay)
        if pre not in range(n) or post not in range(n):
            raise ValueError("synapse endpoint outside network")
        if not lo <= weight <= hi:
            raise ValueError("synapse weight outside signed state width")
        if delay < 1:
            raise ValueError("zero/negative delay unsupported; no same-tick loops")

    try:
        events = tuple(input_currents)
    except (TypeError, ValueError) as exc:
        raise ValueError("input_currents must be iterable") from exc
    for i, e in enumerate(events):
        if not isinstance(e, InputCurrent):
            raise ValueError(f"input_currents[{i}] must be InputCurrent")
        t = _integer("input.tick", e.tick)
        neuron = _integer("input.neuron", e.neuron)
        current = _integer("input.current", e.current)
        if not 0 <= t < ticks or neuron not in range(n):
            raise ValueError("external event outside tick horizon or neuron range")
        if not lo <= current <= hi:
            raise ValueError("external current outside signed state width")
    return events
