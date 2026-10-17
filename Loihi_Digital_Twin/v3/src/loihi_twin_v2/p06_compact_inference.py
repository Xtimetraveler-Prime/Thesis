"""P06-A2.3: independent, uncompiled 784->32->10 integer SNN inference.

This module deliberately avoids LogicalCore, LogicalChip, compiler mapping,
P03 hardware images, and existing compartment arithmetic. Its dense model
is a separately built reference against which packed and compiled executions
can be differentially compared in A2.4.

Within each of 26 timesteps: source pixel events reach hidden neurons now;
hidden spikes from the PRIOR tick reach readout neurons now. New hidden spikes
route only to the next tick, including self-routed packets in one logical core.
Pending spikes generated at tick 25 are discarded at the image boundary, and
all states, counters and event banks are newly created for every image.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from .p06_input_contract import (
    EVENT_BANK_DEPTH, HIDDEN_NEURONS, INPUT_CHANNELS, OUTPUT_CLASSES,
    TOTAL_TICKS, classify_spike_counts, image_event_schedule,
)
from .p06_integer_oracle import (
    STATE_MAX, STATE_MIN, LIFParameters, LIFState, accumulate_synapses, lif_step,
)


def _validate_integer_matrix(name: str, matrix: tuple[tuple[int, ...], ...], rows: int, cols: int) -> None:
    if len(matrix) != rows:
        raise ValueError(f"{name} must contain {rows} rows")
    for row in matrix:
        if len(row) != cols or any(type(weight) is not int or not STATE_MIN <= weight <= STATE_MAX for weight in row):
            raise ValueError(f"{name} must have {rows}x{cols} signed-24-bit integer weights")


@dataclass(frozen=True, slots=True)
class CompactNetwork:
    """Weights are in destination-major order, never a packed-axon layout."""
    input_to_hidden: tuple[tuple[int, ...], ...]  # [32][784]
    hidden_to_output: tuple[tuple[int, ...], ...]  # [10][32]
    hidden_params: tuple[LIFParameters, ...]
    output_params: tuple[LIFParameters, ...]

    def __post_init__(self) -> None:
        _validate_integer_matrix("input_to_hidden", self.input_to_hidden, HIDDEN_NEURONS, INPUT_CHANNELS)
        _validate_integer_matrix("hidden_to_output", self.hidden_to_output, OUTPUT_CLASSES, HIDDEN_NEURONS)
        if len(self.hidden_params) != HIDDEN_NEURONS or len(self.output_params) != OUTPUT_CLASSES:
            raise ValueError("network requires 32 hidden and 10 output parameter records")
        if any(not isinstance(p, LIFParameters) for p in self.hidden_params + self.output_params):
            raise TypeError("neuron parameters must be LIFParameters")

    @classmethod
    def from_uniform_parameters(
        cls,
        input_to_hidden: Sequence[Sequence[int]],
        hidden_to_output: Sequence[Sequence[int]],
        hidden: LIFParameters,
        output: LIFParameters,
    ) -> "CompactNetwork":
        return cls(tuple(tuple(row) for row in input_to_hidden),
                   tuple(tuple(row) for row in hidden_to_output),
                   (hidden,) * HIDDEN_NEURONS, (output,) * OUTPUT_CLASSES)


@dataclass(frozen=True, slots=True)
class TickTrace:
    tick: int
    external_pixel_indices: tuple[int, ...]
    received_hidden_spikes: tuple[int, ...]
    hidden_synaptic_inputs: tuple[int, ...]
    output_synaptic_inputs: tuple[int, ...]
    hidden_before: tuple[LIFState, ...]
    output_before: tuple[LIFState, ...]
    hidden_after: tuple[LIFState, ...]
    output_after: tuple[LIFState, ...]
    hidden_spikes: tuple[int, ...]
    output_spikes: tuple[int, ...]
    output_spike_counts: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class InferenceResult:
    traces: tuple[TickTrace, ...]
    output_counts: tuple[int, ...]
    predicted_class: int
    dropped_boundary_hidden_spikes: tuple[int, ...]


def infer_event_schedule(
    network: CompactNetwork, schedule: Sequence[Sequence[int]],
) -> InferenceResult:
    """Execute a complete frame from fresh state, never reuse previous frame state.

    No precomputed "analog" pixel values enter the model. A route emitted
    at tick t cannot affect readout until tick t+1. Repeated packet deliveries
    from the same hidden source are impossible within one tick, but any number
    of distinct sources may contribute to an output via signed accumulation.
    """
    if not isinstance(network, CompactNetwork):
        raise TypeError("expected a CompactNetwork")
    if len(schedule) != TOTAL_TICKS:
        raise ValueError("inference requires exactly 26 event ticks")
    hidden = [LIFState() for _ in range(HIDDEN_NEURONS)]
    outputs = [LIFState() for _ in range(OUTPUT_CLASSES)]
    count = [0] * OUTPUT_CLASSES
    prior_spikes: tuple[int, ...] = ()
    traces: list[TickTrace] = []

    for tick, raw_events in enumerate(schedule):
        active = tuple(raw_events)
        if any(type(index) is not int or not 0 <= index < INPUT_CHANNELS for index in active):
            raise ValueError(f"invalid external pixel index at tick {tick}")
        if tuple(sorted(set(active))) != active:
            raise ValueError(f"external pixel events must be unique ascending indices at tick {tick}")
        if tick == TOTAL_TICKS - 1 and active:
            raise ValueError("tick 25 is a drain tick with no external pixel events")
        if len(active) + len(prior_spikes) > EVENT_BANK_DEPTH:
            raise ValueError(f"event bank overflow at tick {tick}")

        hidden_inputs = tuple(accumulate_synapses(weights[index] for index in active)
                              for weights in network.input_to_hidden)
        output_inputs = tuple(accumulate_synapses(weights[index] for index in prior_spikes)
                              for weights in network.hidden_to_output)
        before_hidden, before_outputs = tuple(hidden), tuple(outputs)
        hidden_spikes: list[int] = []
        output_spikes: list[int] = []
        for neuron in range(HIDDEN_NEURONS):
            result = lif_step(hidden[neuron], network.hidden_params[neuron], hidden_inputs[neuron])
            hidden[neuron] = result.state
            if result.spiked:
                hidden_spikes.append(neuron)
        for neuron in range(OUTPUT_CLASSES):
            result = lif_step(outputs[neuron], network.output_params[neuron], output_inputs[neuron])
            outputs[neuron] = result.state
            if result.spiked:
                output_spikes.append(neuron)
                count[neuron] += 1
        traces.append(TickTrace(
            tick=tick, external_pixel_indices=active,
            received_hidden_spikes=prior_spikes,
            hidden_synaptic_inputs=hidden_inputs, output_synaptic_inputs=output_inputs,
            hidden_before=before_hidden, output_before=before_outputs,
            hidden_after=tuple(hidden), output_after=tuple(outputs),
            hidden_spikes=tuple(hidden_spikes), output_spikes=tuple(output_spikes),
            output_spike_counts=tuple(count),
        ))
        prior_spikes = tuple(hidden_spikes)

    final_counts = tuple(count)
    return InferenceResult(
        traces=tuple(traces), output_counts=final_counts,
        predicted_class=classify_spike_counts(final_counts),
        dropped_boundary_hidden_spikes=prior_spikes,
    )


def infer_image(network: CompactNetwork, image: Sequence[int] | bytes) -> InferenceResult:
    return infer_event_schedule(network, image_event_schedule(image))
