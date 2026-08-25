"""Post-tick FPGA trace reconstruction contract for M11.5.5.

The M10 software trace uses a zero-based ``TickTrace.tick`` value, while the
integrated M11 hardware exposes a committed tick counter that increments only
after Phase F.  ``FpgaTickTraceSnapshot`` therefore stores the hardware-visible
``committed_tick`` and losslessly reconstructs the software trace tick as the
preceding unsigned-32 value.

The snapshot is intentionally transport-neutral.  M11.5.5 RTL may expose the
fields through debug memories/ports, while M12 can turn the captured words into
the existing backend-neutral ``TickTrace`` without changing semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .fpga_core_capacity import (
    FPGA_CORE_CAPACITY_V1,
    MAX_EXTERNAL_EVENTS_PER_TICK,
    MAX_NEURONS,
    MAX_RECURRENT_EVENTS_PER_TICK,
    SYNAPTIC_ACCUMULATOR_BITS,
    unpack_neuron_state_word,
)
from .model import Spike, TickTrace
from .specification import TICK_BITS


FPGA_TRACE_SNAPSHOT_SCHEMA = "neuromorphic-twin-fpga-trace-snapshot-v1"
_TICK_MASK = (1 << TICK_BITS) - 1
_ACCUM_MIN = -(1 << (SYNAPTIC_ACCUMULATOR_BITS - 1))
_ACCUM_MAX = (1 << (SYNAPTIC_ACCUMULATOR_BITS - 1)) - 1
_STATE_WORD_MAX = (1 << 64) - 1


@dataclass(frozen=True, slots=True)
class FpgaTickTraceSnapshot:
    """One complete post-Phase-F FPGA observation window.

    ``state_before_words`` are snapshots captured before Phase C overwrites the
    neuron state memory. ``state_after_words`` and ``spikes`` are the committed
    architectural results. ``synaptic_input`` is the exact signed-64 Phase-B
    accumulator image before the neuron controller applies state-width rules.
    Event tuples preserve hardware order and multiplicity.
    """

    committed_tick: int
    external_input_axons: tuple[int, ...]
    recurrent_input_axons: tuple[int, ...]
    synaptic_input: tuple[int, ...]
    state_before_words: tuple[int, ...]
    state_after_words: tuple[int, ...]
    spikes: tuple[bool, ...]
    routed_output_axons: tuple[int, ...]

    def __post_init__(self) -> None:
        if isinstance(self.committed_tick, bool) or not isinstance(self.committed_tick, int):
            raise TypeError("committed_tick must be an int")
        if not 0 <= self.committed_tick <= _TICK_MASK:
            raise ValueError(f"committed_tick must fit unsigned {TICK_BITS} bits")

        neuron_count = len(self.state_after_words)
        if not 1 <= neuron_count <= MAX_NEURONS:
            raise ValueError("snapshot neuron count is outside M11.5 physical capacity")
        if len(self.state_before_words) != neuron_count:
            raise ValueError("state_before_words length must equal state_after_words length")
        if len(self.synaptic_input) != neuron_count:
            raise ValueError("synaptic_input length must equal neuron count")
        if len(self.spikes) != neuron_count:
            raise ValueError("spikes length must equal neuron count")

        _validate_state_words("state_before_words", self.state_before_words)
        _validate_state_words("state_after_words", self.state_after_words)

        for value in self.synaptic_input:
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError("synaptic_input entries must be ints")
            if not _ACCUM_MIN <= value <= _ACCUM_MAX:
                raise ValueError("synaptic_input entry does not fit signed-64 accumulator")
        if any(not isinstance(value, bool) for value in self.spikes):
            raise TypeError("spikes entries must be bools")

        _validate_events(
            "external_input_axons",
            self.external_input_axons,
            MAX_EXTERNAL_EVENTS_PER_TICK,
        )
        _validate_events(
            "recurrent_input_axons",
            self.recurrent_input_axons,
            MAX_RECURRENT_EVENTS_PER_TICK,
        )
        _validate_events(
            "routed_output_axons",
            self.routed_output_axons,
            MAX_RECURRENT_EVENTS_PER_TICK,
        )

    @property
    def neuron_count(self) -> int:
        return len(self.state_after_words)

    @property
    def trace_tick(self) -> int:
        """Zero-based M10/M12 tick represented by this committed snapshot."""

        return (self.committed_tick - 1) & _TICK_MASK

    @property
    def input_axons(self) -> tuple[int, ...]:
        return self.external_input_axons + self.recurrent_input_axons

    @property
    def current_before(self) -> tuple[int, ...]:
        return tuple(unpack_neuron_state_word(word).current for word in self.state_before_words)

    @property
    def voltage_before(self) -> tuple[int, ...]:
        return tuple(unpack_neuron_state_word(word).voltage for word in self.state_before_words)

    @property
    def current_after(self) -> tuple[int, ...]:
        return tuple(unpack_neuron_state_word(word).current for word in self.state_after_words)

    @property
    def voltage_after(self) -> tuple[int, ...]:
        return tuple(unpack_neuron_state_word(word).voltage for word in self.state_after_words)

    @property
    def refractory_after(self) -> tuple[int, ...]:
        return tuple(
            unpack_neuron_state_word(word).refractory_remaining
            for word in self.state_after_words
        )

    def to_tick_trace(self) -> TickTrace:
        """Convert the hardware snapshot into the existing M10 trace schema."""

        tick = self.trace_tick
        spike_records = tuple(
            Spike(tick=tick, neuron_id=neuron_id)
            for neuron_id, spiked in enumerate(self.spikes)
            if spiked
        )
        return TickTrace(
            tick=tick,
            input_axons=self.input_axons,
            synaptic_input=self.synaptic_input,
            current_before=self.current_before,
            voltage_before=self.voltage_before,
            current_after=self.current_after,
            voltage_after=self.voltage_after,
            refractory_after=self.refractory_after,
            spikes=spike_records,
            external_input_axons=self.external_input_axons,
            recurrent_input_axons=self.recurrent_input_axons,
            routed_output_axons=self.routed_output_axons,
        )


def _validate_state_words(name: str, words: Iterable[int]) -> None:
    for word in words:
        if isinstance(word, bool) or not isinstance(word, int):
            raise TypeError(f"{name} entries must be ints")
        if not 0 <= word <= _STATE_WORD_MAX:
            raise ValueError(f"{name} entry does not fit 64 bits")
        # This also applies the frozen state-field interpretation.
        unpack_neuron_state_word(word)


def _validate_events(name: str, events: tuple[int, ...], maximum_count: int) -> None:
    if len(events) > maximum_count:
        raise ValueError(f"{name} count exceeds M11.5 physical capacity")
    for axon_id in events:
        if isinstance(axon_id, bool) or not isinstance(axon_id, int):
            raise TypeError(f"{name} entries must be ints")
        if not 0 <= axon_id < FPGA_CORE_CAPACITY_V1.max_axons:
            raise ValueError(f"{name} axon is outside M11.5 physical capacity")
