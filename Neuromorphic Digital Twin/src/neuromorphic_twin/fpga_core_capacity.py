"""Frozen finite-capacity profile for M11.5 FPGA core integration.

M10 freezes architectural widths and behavior but intentionally leaves physical
array depths open. M11.5 needs finite memories, queues, and route tables, so
this module names the first K26 implementation-capacity profile and the packed
neuron state/configuration words consumed by RTL.

These capacities are project implementation choices. They do not claim to
reproduce undocumented Intel Loihi physical memory capacities or layouts.
"""

from __future__ import annotations

from dataclasses import dataclass

from .fpga_weight_storage import (
    AXON_ROW_POINTER_BITS,
    FORMAT_WORD_BITS,
    MAX_WEIGHT_FORMATS,
    SYNAPSE_WORD_BITS,
)
from .model import NeuronConfig, NeuronState
from .specification import (
    ID_MAX,
    REFRACTORY_BITS,
    STATE_BITS,
    validate_neuron_config_v1,
    validate_neuron_state_v1,
)

FPGA_CORE_CAPACITY_SCHEMA = "neuromorphic-twin-fpga-core-capacity-v1"

# First finite physical profile for the K26 implementation. Architectural IDs
# remain 16 bits per M10; these constants limit the arrays instantiated by M11.5.
MAX_NEURONS = 256
MAX_AXONS = 1024
MAX_SYNAPSES = 4096
MAX_ROUTES = 4096
MAX_EXTERNAL_EVENTS_PER_TICK = 4096
MAX_RECURRENT_EVENTS_PER_TICK = 4096

# M10 requires exact mathematical synaptic accumulation until state arithmetic
# is applied. M11.1/M11.3 already use signed 64-bit synaptic_input at the HLS
# boundary, so M11.5 freezes the tick-local accumulator memory to the same width.
SYNAPTIC_ACCUMULATOR_BITS = 64
EVENT_WORD_BITS = 16
ROUTE_TARGET_WORD_BITS = 16
ROUTE_ROW_POINTER_BITS = 32

# Per-neuron dynamic-state word. There are no reserved bits.
NEURON_STATE_WORD_BITS = 64
NEURON_STATE_CURRENT_SHIFT = 0
NEURON_STATE_CURRENT_BITS = STATE_BITS
NEURON_STATE_VOLTAGE_SHIFT = 24
NEURON_STATE_VOLTAGE_BITS = STATE_BITS
NEURON_STATE_REFRACTORY_SHIFT = 48
NEURON_STATE_REFRACTORY_BITS = REFRACTORY_BITS

# Per-neuron configuration word. M10 fields require 114 bits; the first hardware
# image rounds that to 128 bits and requires the upper 14 reserved bits to zero.
NEURON_CONFIG_WORD_BITS = 128
NEURON_CONFIG_CURRENT_DECAY_SHIFT = 0
NEURON_CONFIG_CURRENT_DECAY_BITS = 13
NEURON_CONFIG_VOLTAGE_DECAY_SHIFT = 13
NEURON_CONFIG_VOLTAGE_DECAY_BITS = 13
NEURON_CONFIG_THRESHOLD_SHIFT = 26
NEURON_CONFIG_THRESHOLD_BITS = STATE_BITS
NEURON_CONFIG_BIAS_SHIFT = 50
NEURON_CONFIG_BIAS_BITS = STATE_BITS
NEURON_CONFIG_RESET_VOLTAGE_SHIFT = 74
NEURON_CONFIG_RESET_VOLTAGE_BITS = STATE_BITS
NEURON_CONFIG_REFRACTORY_TICKS_SHIFT = 98
NEURON_CONFIG_REFRACTORY_TICKS_BITS = REFRACTORY_BITS
NEURON_CONFIG_USED_BITS = 114
NEURON_CONFIG_RESERVED_MASK = (
    ((1 << NEURON_CONFIG_WORD_BITS) - 1)
    ^ ((1 << NEURON_CONFIG_USED_BITS) - 1)
)

BRAM36_CAPACITY_BITS = 36 * 1024


@dataclass(frozen=True, slots=True)
class FpgaCoreCapacity:
    """Finite array/queue capacities for one physical FPGA core instance."""

    max_neurons: int = MAX_NEURONS
    max_axons: int = MAX_AXONS
    max_synapses: int = MAX_SYNAPSES
    max_weight_formats: int = MAX_WEIGHT_FORMATS
    max_routes: int = MAX_ROUTES
    max_external_events_per_tick: int = MAX_EXTERNAL_EVENTS_PER_TICK
    max_recurrent_events_per_tick: int = MAX_RECURRENT_EVENTS_PER_TICK

    def __post_init__(self) -> None:
        for name, value in (
            ("max_neurons", self.max_neurons),
            ("max_axons", self.max_axons),
            ("max_synapses", self.max_synapses),
            ("max_weight_formats", self.max_weight_formats),
            ("max_routes", self.max_routes),
            ("max_external_events_per_tick", self.max_external_events_per_tick),
            ("max_recurrent_events_per_tick", self.max_recurrent_events_per_tick),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an int")
            if value <= 0:
                raise ValueError(f"{name} must be positive")

        if self.max_neurons > ID_MAX + 1:
            raise ValueError("max_neurons exceeds the M10 16-bit ID space")
        if self.max_axons > ID_MAX + 1:
            raise ValueError("max_axons exceeds the M10 16-bit ID space")
        if self.max_weight_formats > MAX_WEIGHT_FORMATS:
            raise ValueError(
                "max_weight_formats exceeds the M08 four-bit format-index capacity"
            )

    def validate_image_counts(
        self,
        *,
        neuron_count: int,
        axon_count: int,
        synapse_count: int,
        weight_format_count: int,
        route_count: int,
    ) -> None:
        """Reject a static image that exceeds the frozen physical profile."""

        for name, value, limit in (
            ("neuron_count", neuron_count, self.max_neurons),
            ("axon_count", axon_count, self.max_axons),
            ("synapse_count", synapse_count, self.max_synapses),
            ("weight_format_count", weight_format_count, self.max_weight_formats),
            ("route_count", route_count, self.max_routes),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an int")
            if value < 0:
                raise ValueError(f"{name} cannot be negative")
            if value > limit:
                raise ValueError(f"{name}={value} exceeds M11.5 capacity {limit}")

        if neuron_count == 0:
            raise ValueError("at least one neuron is required")


FPGA_CORE_CAPACITY_V1 = FpgaCoreCapacity()


@dataclass(frozen=True, slots=True)
class FpgaCoreStorageEstimate:
    """Logical-bit estimate for the complete frozen M11.5 physical capacity.

    BRAM36 is a capacity-only lower bound; legal width/depth configurations,
    banking, replication, placement, and timing can require more blocks.
    """

    neuron_state_bits: int
    neuron_config_bits: int
    synaptic_accumulator_bits: int
    weight_format_bits: int
    synapse_bits: int
    axon_row_pointer_bits: int
    route_target_bits: int
    route_row_pointer_bits: int
    external_event_bits: int
    recurrent_event_bits: int
    spike_flag_bits: int
    total_bits: int
    bram36_lower_bound: int


def estimate_fpga_core_storage_v1(
    capacity: FpgaCoreCapacity = FPGA_CORE_CAPACITY_V1,
) -> FpgaCoreStorageEstimate:
    """Estimate raw logical storage at the configured physical maxima."""

    neuron_state_bits = capacity.max_neurons * NEURON_STATE_WORD_BITS
    neuron_config_bits = capacity.max_neurons * NEURON_CONFIG_WORD_BITS
    synaptic_accumulator_bits = capacity.max_neurons * SYNAPTIC_ACCUMULATOR_BITS
    weight_format_bits = capacity.max_weight_formats * FORMAT_WORD_BITS
    synapse_bits = capacity.max_synapses * SYNAPSE_WORD_BITS
    axon_row_pointer_bits = (capacity.max_axons + 1) * AXON_ROW_POINTER_BITS
    route_target_bits = capacity.max_routes * ROUTE_TARGET_WORD_BITS
    route_row_pointer_bits = (capacity.max_neurons + 1) * ROUTE_ROW_POINTER_BITS
    external_event_bits = capacity.max_external_events_per_tick * EVENT_WORD_BITS

    # Phase A consumes the prior recurrent queue while Phase E constructs the
    # next queue. Two banks avoid read/write aliasing and make Phase F a bank swap.
    recurrent_event_bits = (
        2 * capacity.max_recurrent_events_per_tick * EVENT_WORD_BITS
    )
    spike_flag_bits = capacity.max_neurons

    total_bits = sum(
        (
            neuron_state_bits,
            neuron_config_bits,
            synaptic_accumulator_bits,
            weight_format_bits,
            synapse_bits,
            axon_row_pointer_bits,
            route_target_bits,
            route_row_pointer_bits,
            external_event_bits,
            recurrent_event_bits,
            spike_flag_bits,
        )
    )
    bram36_lower_bound = (
        total_bits + BRAM36_CAPACITY_BITS - 1
    ) // BRAM36_CAPACITY_BITS

    return FpgaCoreStorageEstimate(
        neuron_state_bits=neuron_state_bits,
        neuron_config_bits=neuron_config_bits,
        synaptic_accumulator_bits=synaptic_accumulator_bits,
        weight_format_bits=weight_format_bits,
        synapse_bits=synapse_bits,
        axon_row_pointer_bits=axon_row_pointer_bits,
        route_target_bits=route_target_bits,
        route_row_pointer_bits=route_row_pointer_bits,
        external_event_bits=external_event_bits,
        recurrent_event_bits=recurrent_event_bits,
        spike_flag_bits=spike_flag_bits,
        total_bits=total_bits,
        bram36_lower_bound=bram36_lower_bound,
    )


def _pack_signed(value: int, bits: int) -> int:
    minimum = -(1 << (bits - 1))
    maximum = (1 << (bits - 1)) - 1
    if not minimum <= value <= maximum:
        raise ValueError(f"signed value {value} does not fit {bits} bits")
    return value & ((1 << bits) - 1)


def _unpack_signed(value: int, bits: int) -> int:
    mask = (1 << bits) - 1
    value &= mask
    sign_bit = 1 << (bits - 1)
    return value - (1 << bits) if value & sign_bit else value


def _require_word(word: int, bits: int, *, name: str) -> int:
    if isinstance(word, bool) or not isinstance(word, int):
        raise TypeError(f"{name} must be an int")
    if not 0 <= word < (1 << bits):
        raise ValueError(f"{name} must fit unsigned {bits} bits")
    return word


def pack_neuron_state_word(state: NeuronState) -> int:
    """Pack one validated M10 neuron state into the frozen 64-bit word."""

    validate_neuron_state_v1(state)
    return (
        (_pack_signed(state.current, NEURON_STATE_CURRENT_BITS)
         << NEURON_STATE_CURRENT_SHIFT)
        | (_pack_signed(state.voltage, NEURON_STATE_VOLTAGE_BITS)
           << NEURON_STATE_VOLTAGE_SHIFT)
        | (state.refractory_remaining << NEURON_STATE_REFRACTORY_SHIFT)
    )


def unpack_neuron_state_word(word: int) -> NeuronState:
    """Decode one 64-bit state word back into the Python model type."""

    word = _require_word(word, NEURON_STATE_WORD_BITS, name="state word")
    current = _unpack_signed(
        word >> NEURON_STATE_CURRENT_SHIFT,
        NEURON_STATE_CURRENT_BITS,
    )
    voltage = _unpack_signed(
        word >> NEURON_STATE_VOLTAGE_SHIFT,
        NEURON_STATE_VOLTAGE_BITS,
    )
    refractory = (
        word >> NEURON_STATE_REFRACTORY_SHIFT
    ) & ((1 << NEURON_STATE_REFRACTORY_BITS) - 1)
    state = NeuronState(
        current=current,
        voltage=voltage,
        refractory_remaining=refractory,
    )
    validate_neuron_state_v1(state)
    return state


def pack_neuron_config_word(config: NeuronConfig) -> int:
    """Pack one validated M10 neuron configuration into a 128-bit word."""

    validate_neuron_config_v1(config)
    return (
        (config.current_decay << NEURON_CONFIG_CURRENT_DECAY_SHIFT)
        | (config.voltage_decay << NEURON_CONFIG_VOLTAGE_DECAY_SHIFT)
        | (_pack_signed(config.threshold, NEURON_CONFIG_THRESHOLD_BITS)
           << NEURON_CONFIG_THRESHOLD_SHIFT)
        | (_pack_signed(config.bias, NEURON_CONFIG_BIAS_BITS)
           << NEURON_CONFIG_BIAS_SHIFT)
        | (_pack_signed(config.reset_voltage, NEURON_CONFIG_RESET_VOLTAGE_BITS)
           << NEURON_CONFIG_RESET_VOLTAGE_SHIFT)
        | (config.refractory_ticks << NEURON_CONFIG_REFRACTORY_TICKS_SHIFT)
    )


def unpack_neuron_config_word(word: int) -> NeuronConfig:
    """Decode a 128-bit config word, rejecting nonzero reserved bits."""

    word = _require_word(word, NEURON_CONFIG_WORD_BITS, name="config word")
    if word & NEURON_CONFIG_RESERVED_MASK:
        raise ValueError("config word reserved bits must be zero")

    current_decay = (
        word >> NEURON_CONFIG_CURRENT_DECAY_SHIFT
    ) & ((1 << NEURON_CONFIG_CURRENT_DECAY_BITS) - 1)
    voltage_decay = (
        word >> NEURON_CONFIG_VOLTAGE_DECAY_SHIFT
    ) & ((1 << NEURON_CONFIG_VOLTAGE_DECAY_BITS) - 1)
    threshold = _unpack_signed(
        word >> NEURON_CONFIG_THRESHOLD_SHIFT,
        NEURON_CONFIG_THRESHOLD_BITS,
    )
    bias = _unpack_signed(
        word >> NEURON_CONFIG_BIAS_SHIFT,
        NEURON_CONFIG_BIAS_BITS,
    )
    reset_voltage = _unpack_signed(
        word >> NEURON_CONFIG_RESET_VOLTAGE_SHIFT,
        NEURON_CONFIG_RESET_VOLTAGE_BITS,
    )
    refractory_ticks = (
        word >> NEURON_CONFIG_REFRACTORY_TICKS_SHIFT
    ) & ((1 << NEURON_CONFIG_REFRACTORY_TICKS_BITS) - 1)

    config = NeuronConfig(
        current_decay=current_decay,
        voltage_decay=voltage_decay,
        threshold=threshold,
        bias=bias,
        reset_voltage=reset_voltage,
        refractory_ticks=refractory_ticks,
    )
    validate_neuron_config_v1(config)
    return config
