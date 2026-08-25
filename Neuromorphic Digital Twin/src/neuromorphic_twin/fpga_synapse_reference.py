"""M11.5.3 reference for FPGA-v1 Phase-B synaptic accumulation.

This module deliberately consumes the frozen M08.5 memory image rather than
high-level ``Synapse`` objects. It is the software oracle for the RTL that will
walk weight-format, synapse, and axon-row memories in M11.5.3.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from .fpga_core_capacity import FPGA_CORE_CAPACITY_V1, FpgaCoreCapacity
from .fpga_weight_storage import (
    FrozenWeightStorage,
    unpack_synapse_word,
    unpack_weight_format,
)
from .weights import encode_static_weight

SIGNED64_MIN = -(1 << 63)
SIGNED64_MAX = (1 << 63) - 1


@dataclass(frozen=True, slots=True)
class SynapseAccumulationStep:
    """One deterministic packed-memory contribution during Phase B."""

    source: Literal["external", "recurrent"]
    event_index: int
    axon_id: int
    synapse_index: int
    target_neuron: int
    format_index: int
    requested_mantissa: int
    effective_weight: int
    accumulator_after: int


@dataclass(frozen=True, slots=True)
class PhaseBAccumulationResult:
    """Exact signed-64 accumulator image plus deterministic traversal trace."""

    accumulators: tuple[int, ...]
    steps: tuple[SynapseAccumulationStep, ...]
    external_event_count: int
    recurrent_event_count: int

    @property
    def traversed_synapse_count(self) -> int:
        return len(self.steps)


def accumulate_frozen_weight_image_v1(
    storage: FrozenWeightStorage,
    *,
    neuron_count: int,
    external_axons: Iterable[int] = (),
    recurrent_axons: Iterable[int] = (),
    capacity: FpgaCoreCapacity = FPGA_CORE_CAPACITY_V1,
) -> PhaseBAccumulationResult:
    """Execute the frozen M11.5 Phase-B traversal exactly in software.

    External events are consumed first, then recurrent events. Event and row
    multiplicity are preserved. Axons inside the physical profile but beyond
    the configured M08 image are legal no-ops, matching the M10 unknown/no-row
    behavior. Every effective weight is reconstructed from the packed requested
    mantissa plus shared M08 weight format before being added to the target's
    mathematical signed-64 accumulator.
    """

    if not isinstance(storage, FrozenWeightStorage):
        raise TypeError("storage must be FrozenWeightStorage")
    _require_count("neuron_count", neuron_count, 1, capacity.max_neurons)

    if storage.format_count > capacity.max_weight_formats:
        raise ValueError("weight format count exceeds M11.5 physical capacity")
    if storage.synapse_count > capacity.max_synapses:
        raise ValueError("synapse count exceeds M11.5 physical capacity")
    if storage.axon_count > capacity.max_axons:
        raise ValueError("axon-row count exceeds M11.5 physical capacity")

    external = _materialize_events(
        "external_axons",
        external_axons,
        capacity.max_external_events_per_tick,
        capacity.max_axons,
    )
    recurrent = _materialize_events(
        "recurrent_axons",
        recurrent_axons,
        capacity.max_recurrent_events_per_tick,
        capacity.max_axons,
    )

    formats = tuple(unpack_weight_format(word) for word in storage.format_words)
    accumulators = [0] * neuron_count
    steps: list[SynapseAccumulationStep] = []

    def consume(source: Literal["external", "recurrent"], events: tuple[int, ...]) -> None:
        for event_index, axon_id in enumerate(events):
            # A physically valid axon with no configured CSR row is a no-op.
            if axon_id >= storage.axon_count:
                continue

            start = storage.axon_row_pointers[axon_id]
            stop = storage.axon_row_pointers[axon_id + 1]
            for synapse_index in range(start, stop):
                fields = unpack_synapse_word(storage.synapse_words[synapse_index])
                if fields.target_neuron >= neuron_count:
                    raise ValueError(
                        "synapse target is outside configured neuron_count: "
                        f"target={fields.target_neuron}, neuron_count={neuron_count}"
                    )
                if fields.format_index >= len(formats):
                    # FrozenWeightStorage normally rejects this at construction;
                    # keep the hardware-facing guard explicit at traversal time.
                    raise ValueError("synapse format index is outside format table")

                effective_weight = encode_static_weight(
                    fields.requested_mantissa,
                    formats[fields.format_index],
                ).effective_weight
                updated = accumulators[fields.target_neuron] + effective_weight
                if not SIGNED64_MIN <= updated <= SIGNED64_MAX:
                    raise OverflowError("signed-64 synaptic accumulator overflow")
                accumulators[fields.target_neuron] = updated
                steps.append(
                    SynapseAccumulationStep(
                        source=source,
                        event_index=event_index,
                        axon_id=axon_id,
                        synapse_index=synapse_index,
                        target_neuron=fields.target_neuron,
                        format_index=fields.format_index,
                        requested_mantissa=fields.requested_mantissa,
                        effective_weight=effective_weight,
                        accumulator_after=updated,
                    )
                )

    consume("external", external)
    consume("recurrent", recurrent)

    return PhaseBAccumulationResult(
        accumulators=tuple(accumulators),
        steps=tuple(steps),
        external_event_count=len(external),
        recurrent_event_count=len(recurrent),
    )


def _materialize_events(
    name: str,
    events: Iterable[int],
    maximum_count: int,
    max_axons: int,
) -> tuple[int, ...]:
    materialized = tuple(events)
    if len(materialized) > maximum_count:
        raise ValueError(f"{name} exceeds M11.5 per-tick capacity")
    for axon_id in materialized:
        if isinstance(axon_id, bool) or not isinstance(axon_id, int):
            raise TypeError(f"{name} entries must be ints")
        if not 0 <= axon_id < max_axons:
            raise ValueError(f"{name} axon is outside M11.5 physical capacity")
    return materialized


def _require_count(name: str, value: int, minimum: int, maximum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be in {minimum}..{maximum}")
