"""P03 one-core FPGA memory-image boundary.

This module translates one validated :class:`LogicalCoreConfig` into the packed
words consumed by the first FPGA-v2 HLS core.  The logical resource contract is
still defined by ``resources.py`` and ``LOIHI1_TARGET_SPEC.md``; the packed word
widths here are a transparent K26 implementation choice.
"""

from __future__ import annotations

from dataclasses import dataclass

from .arithmetic import ArithmeticConfig, OverflowMode
from .compartment import CompartmentState
from .core import LogicalCoreConfig
from .packet import SpikePacket
from .resources import (
    MAX_COMPARTMENTS_PER_CORE,
    MAX_INPUT_AXONS_PER_CORE,
    MAX_OUTPUT_ROUTES_PER_CORE,
    MAX_SYNAPSE_MEMORY_BYTES_PER_CORE,
)

P03_PROFILE_NAME = "p03-k26-one-core-sat24-v1-compat"
P03_STATE_BITS = 24
P03_REFRACTORY_BITS = 16
P03_DECAY_BITS = 13
P03_MAX_SYNAPSE_ENTRIES = MAX_SYNAPSE_MEMORY_BYTES_PER_CORE // 4
P03_REQUIRED_ARITHMETIC = ArithmeticConfig(
    state_bits=P03_STATE_BITS,
    overflow=OverflowMode.SATURATE,
)


@dataclass(frozen=True, slots=True)
class SparseWord:
    index: int
    word: int


@dataclass(frozen=True, slots=True)
class OneCoreHardwareImage:
    profile: str
    core_id: int
    compartment_count: int
    synapse_count: int
    route_count: int
    config_words: tuple[int, ...]
    state_words: tuple[int, ...]
    axon_words: tuple[SparseWord, ...]
    synapse_words: tuple[int, ...]
    route_descriptor_words: tuple[SparseWord, ...]
    route_words: tuple[int, ...]


def _require_unsigned(name: str, value: int, bits: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if not 0 <= value < (1 << bits):
        raise ValueError(f"{name} must fit unsigned {bits} bits")
    return value


def _require_signed(name: str, value: int, bits: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    low = -(1 << (bits - 1))
    high = (1 << (bits - 1)) - 1
    if not low <= value <= high:
        raise ValueError(f"{name} must fit signed {bits} bits")
    return value & ((1 << bits) - 1)


def _signed_from_bits(value: int, bits: int) -> int:
    value &= (1 << bits) - 1
    sign = 1 << (bits - 1)
    return value - (1 << bits) if value & sign else value


def pack_compartment_config(config) -> int:
    """Pack the frozen v1-compatible P03 compartment configuration word."""

    current_decay = _require_unsigned("current_decay", config.current_decay, 13)
    voltage_decay = _require_unsigned("voltage_decay", config.voltage_decay, 13)
    threshold = _require_signed("threshold", config.threshold, 24)
    bias = _require_signed("bias", config.bias, 24)
    reset = _require_signed("reset_voltage", config.reset_voltage, 24)
    refractory = _require_unsigned("refractory_ticks", config.refractory_ticks, 16)

    return (
        current_decay
        | (voltage_decay << 13)
        | (threshold << 26)
        | (bias << 50)
        | (reset << 74)
        | (refractory << 98)
    )


def unpack_compartment_config(word: int) -> dict[str, int]:
    if word >> 114:
        raise ValueError("P03 compartment-config reserved bits must be zero")
    return {
        "current_decay": word & 0x1FFF,
        "voltage_decay": (word >> 13) & 0x1FFF,
        "threshold": _signed_from_bits(word >> 26, 24),
        "bias": _signed_from_bits(word >> 50, 24),
        "reset_voltage": _signed_from_bits(word >> 74, 24),
        "refractory_ticks": (word >> 98) & 0xFFFF,
    }


def pack_compartment_state(state: CompartmentState) -> int:
    current = _require_signed("current", state.current, 24)
    voltage = _require_signed("voltage", state.voltage, 24)
    refractory = _require_unsigned(
        "refractory_remaining", state.refractory_remaining, 16
    )
    return current | (voltage << 24) | (refractory << 48)


def unpack_compartment_state(word: int) -> CompartmentState:
    if word >> 64:
        raise ValueError("P03 state word must fit 64 bits")
    return CompartmentState(
        current=_signed_from_bits(word, 24),
        voltage=_signed_from_bits(word >> 24, 24),
        refractory_remaining=(word >> 48) & 0xFFFF,
    )


def pack_axon_word(*, synapse_start: int, synapse_count: int, target_offset: int) -> int:
    start = _require_unsigned("synapse_start", synapse_start, 15)
    count = _require_unsigned("synapse_count", synapse_count, 16)
    offset = _require_unsigned("target_offset", target_offset, 10)
    return start | (count << 15) | (offset << 31) | (1 << 41)


def unpack_axon_word(word: int) -> dict[str, int | bool]:
    return {
        "synapse_start": word & 0x7FFF,
        "synapse_count": (word >> 15) & 0xFFFF,
        "target_offset": (word >> 31) & 0x3FF,
        "valid": bool((word >> 41) & 1),
    }


def pack_synapse_word(*, target_compartment: int, weight: int, delay: int = 0, tag: int | None = None) -> int:
    target = _require_unsigned("target_compartment", target_compartment, 10)
    weight_bits = _require_signed("weight", weight, 24)
    delay_bits = _require_unsigned("delay", delay, 6)
    tag_bits = _require_unsigned("tag", 0 if tag is None else tag, 8)
    return target | (weight_bits << 10) | (delay_bits << 34) | (tag_bits << 40)


def unpack_synapse_word(word: int) -> dict[str, int]:
    return {
        "target_compartment": word & 0x3FF,
        "weight": _signed_from_bits(word >> 10, 24),
        "delay": (word >> 34) & 0x3F,
        "tag": (word >> 40) & 0xFF,
    }


def pack_route_descriptor(*, route_start: int, route_count: int) -> int:
    start = _require_unsigned("route_start", route_start, 12)
    count = _require_unsigned("route_count", route_count, 13)
    return start | (count << 12) | (1 << 25)


def unpack_route_descriptor(word: int) -> dict[str, int | bool]:
    return {
        "route_start": word & 0xFFF,
        "route_count": (word >> 12) & 0x1FFF,
        "valid": bool((word >> 25) & 1),
    }


def pack_route_word(*, destination_core: int, destination_axon: int) -> int:
    core = _require_unsigned("destination_core", destination_core, 7)
    axon = _require_unsigned("destination_axon", destination_axon, 12)
    return core | (axon << 7)


def unpack_route_word(word: int) -> dict[str, int]:
    return {
        "destination_core": word & 0x7F,
        "destination_axon": (word >> 7) & 0xFFF,
    }


def pack_output_packet(packet: SpikePacket) -> int:
    """Pack the P03 normalized egress record.

    Source core is implicit because P03 contains one logical core.  Source
    compartment and target timestep remain explicit so the record normalizes
    directly back to the P02 packet boundary.
    """

    if packet.source_compartment is None:
        raise ValueError("P03 egress packets require source_compartment metadata")
    core = _require_unsigned("destination_core", packet.destination_core, 7)
    axon = _require_unsigned("destination_axon", packet.destination_axon, 12)
    source = _require_unsigned("source_compartment", packet.source_compartment, 10)
    timestep = _require_unsigned("target_timestep", packet.target_timestep, 32)
    return core | (axon << 7) | (source << 19) | (timestep << 29) | (1 << 61)


def unpack_output_packet(word: int) -> dict[str, int | bool]:
    return {
        "destination_core": word & 0x7F,
        "destination_axon": (word >> 7) & 0xFFF,
        "source_compartment": (word >> 19) & 0x3FF,
        "target_timestep": (word >> 29) & 0xFFFFFFFF,
        "valid": bool((word >> 61) & 1),
    }


def export_one_core_image(
    config: LogicalCoreConfig,
    initial_states: tuple[CompartmentState, ...] | None = None,
) -> OneCoreHardwareImage:
    """Translate one P02 logical core into the P03 packed-memory profile."""

    if config.arithmetic != P03_REQUIRED_ARITHMETIC:
        raise ValueError(
            "P03 hardware requires signed 24-bit saturating arithmetic; "
            "configure ArithmeticConfig(state_bits=24, overflow=SATURATE)"
        )
    if len(config.compartments) > MAX_COMPARTMENTS_PER_CORE:
        raise ValueError("compartment count exceeds P03 logical capacity")
    if initial_states is None:
        initial_states = tuple(CompartmentState() for _ in config.compartments)
    if len(initial_states) != len(config.compartments):
        raise ValueError("initial_states must match compartment count")

    template_offsets: dict[int, tuple[int, int]] = {}
    synapse_words: list[int] = []
    for template in sorted(config.synapse_templates, key=lambda item: item.template_id):
        start = len(synapse_words)
        for entry in template.entries:
            synapse_words.append(
                pack_synapse_word(
                    target_compartment=entry.target_compartment,
                    weight=entry.weight,
                    delay=entry.delay,
                    tag=entry.tag,
                )
            )
        template_offsets[template.template_id] = (start, len(template.entries))

    if len(synapse_words) > P03_MAX_SYNAPSE_ENTRIES:
        raise ValueError("unique P03 synapse entries exceed physical table capacity")

    axon_words: list[SparseWord] = []
    for binding in sorted(config.input_axons, key=lambda item: item.axon_id):
        if binding.axon_id >= MAX_INPUT_AXONS_PER_CORE:
            raise ValueError("axon ID exceeds P03 logical capacity")
        start, count = template_offsets[binding.template_id]
        axon_words.append(
            SparseWord(
                binding.axon_id,
                pack_axon_word(
                    synapse_start=start,
                    synapse_count=count,
                    target_offset=binding.target_offset,
                ),
            )
        )

    route_words: list[int] = []
    route_descriptors: list[SparseWord] = []
    for entry in sorted(config.output_routes, key=lambda item: item.source_compartment):
        start = len(route_words)
        for route in entry.routes:
            route_words.append(
                pack_route_word(
                    destination_core=route.destination_core,
                    destination_axon=route.destination_axon,
                )
            )
        route_descriptors.append(
            SparseWord(
                entry.source_compartment,
                pack_route_descriptor(route_start=start, route_count=len(entry.routes)),
            )
        )

    if len(route_words) > MAX_OUTPUT_ROUTES_PER_CORE:
        raise ValueError("P03 output routes exceed logical capacity")

    return OneCoreHardwareImage(
        profile=P03_PROFILE_NAME,
        core_id=config.core_id,
        compartment_count=len(config.compartments),
        synapse_count=len(synapse_words),
        route_count=len(route_words),
        config_words=tuple(pack_compartment_config(item) for item in config.compartments),
        state_words=tuple(pack_compartment_state(item) for item in initial_states),
        axon_words=tuple(axon_words),
        synapse_words=tuple(synapse_words),
        route_descriptor_words=tuple(route_descriptors),
        route_words=tuple(route_words),
    )
