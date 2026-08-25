"""Packed-memory golden reference for the M11.5.2 neuron-array boundary.

This module does not introduce new neuron behavior. It adapts the frozen M10
Python transition to the exact 64-bit state / 128-bit configuration memory words
frozen by M11.5.1 so RTL integration tests can compare memory images directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .fpga_core_capacity import (
    FPGA_CORE_CAPACITY_V1,
    pack_neuron_state_word,
    unpack_neuron_config_word,
    unpack_neuron_state_word,
)
from .neuron import step_neuron
from .specification import FPGA_CORE_ARITHMETIC_V1


@dataclass(frozen=True, slots=True)
class PackedNeuronArrayTick:
    """Golden result for one already-accumulated multi-neuron Phase-C pass."""

    state_words: tuple[int, ...]
    spikes: tuple[bool, ...]


def step_packed_neuron_array_v1(
    state_words: Sequence[int],
    config_words: Sequence[int],
    synaptic_inputs: Sequence[int],
) -> PackedNeuronArrayTick:
    """Step packed neuron memories exactly once using the frozen Python model.

    The synaptic inputs are already-accumulated signed integers. M11.5.3 will
    produce these values by walking the M08 CSR synapse image; M11.5.2 consumes
    them only as the signed-64 per-neuron accumulator boundary already verified
    by the HLS neuron step.
    """

    neuron_count = len(state_words)
    if neuron_count == 0:
        raise ValueError("at least one neuron is required")
    if neuron_count > FPGA_CORE_CAPACITY_V1.max_neurons:
        raise ValueError(
            "neuron count exceeds M11.5 physical capacity "
            f"{FPGA_CORE_CAPACITY_V1.max_neurons}"
        )
    if len(config_words) != neuron_count:
        raise ValueError("config_words length must equal state_words length")
    if len(synaptic_inputs) != neuron_count:
        raise ValueError("synaptic_inputs length must equal state_words length")

    next_words: list[int] = []
    spikes: list[bool] = []

    for state_word, config_word, synaptic_input in zip(
        state_words,
        config_words,
        synaptic_inputs,
        strict=True,
    ):
        if isinstance(synaptic_input, bool) or not isinstance(synaptic_input, int):
            raise TypeError("synaptic inputs must be ints")
        if not -(1 << 63) <= synaptic_input <= (1 << 63) - 1:
            raise ValueError("synaptic input must fit signed 64 bits")

        state = unpack_neuron_state_word(state_word)
        config = unpack_neuron_config_word(config_word)
        result = step_neuron(
            state,
            config,
            synaptic_input,
            arithmetic=FPGA_CORE_ARITHMETIC_V1,
        )
        next_words.append(pack_neuron_state_word(result.state))
        spikes.append(result.spiked)

    return PackedNeuronArrayTick(
        state_words=tuple(next_words),
        spikes=tuple(spikes),
    )
