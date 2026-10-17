"""P06-A2.4: independent P03 one-core packed-image event and state replay.

Decode and execute published P03 bitfields without invoking hardware_p03
unpackers, LogicalChip, or the HLS implementation. Reuses only the separately
implemented P06 scalar LIF oracle and fixed label-free input encoder. Intended
as a reference for full-frame differential tests, not a physical FPGA run.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .p06_input_contract import (
    INPUT_CHANNELS, HIDDEN_NEURONS, OUTPUT_CLASSES, EVENT_BANK_DEPTH,
    classify_spike_counts, image_event_schedule,
)
from .p06_integer_oracle import LIFParameters, LIFState, lif_step, wrap64


def _signed24(word: int) -> int:
    raw = word & ((1 << 24) - 1)
    return raw - (1 << 24) if raw & (1 << 23) else raw


def _decode_config(word: int) -> LIFParameters:
    if word >> 114:
        raise ValueError("config word reserved bits nonzero")
    return LIFParameters(
        current_decay=word & 0x1FFF,
        voltage_decay=(word >> 13) & 0x1FFF,
        threshold=_signed24(word >> 26),
        bias=_signed24(word >> 50),
        reset_voltage=_signed24(word >> 74),
        refractory_ticks=(word >> 98) & 0xFFFF,
    )


def _decode_state(word: int) -> LIFState:
    if not 0 <= word < (1 << 64):
        raise ValueError("state word exceeds 64 bits")
    return LIFState(_signed24(word), _signed24(word >> 24), (word >> 48) & 0xFFFF)


@dataclass(frozen=True, slots=True)
class PackedTick:
    timestep: int
    axons_current: tuple[int, ...]
    accumulators: tuple[int, ...]
    states_after: tuple[LIFState, ...]
    fired_compartments: tuple[int, ...]
    next_packet_sources: tuple[int, ...]
    next_packet_axons: tuple[int, ...]
    output_counts: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class PackedInference:
    ticks: tuple[PackedTick, ...]
    output_counts: tuple[int, ...]
    predicted_class: int
    dropped_boundary_packets: tuple[int, ...]


def replay_p03_image(image: Any, pixel_to_axon: Sequence[int], pixels: Sequence[int] | bytes) -> PackedInference:
    """Replay the exact P03 image arrays for a compact, single-core graph.

    The source input-to-axon map is supplied separately; it must be derived
    from the independent network/compiler ingress record, not guessed to be
    identical to pixel indices. The physical word layouts are decoded here.
    """
    n = image.compartment_count
    if n != HIDDEN_NEURONS + OUTPUT_CLASSES:
        raise ValueError("compact image must have exactly 42 compartments")
    if not 0 <= image.core_id < 128:
        raise ValueError("invalid logical core ID")
    if not (len(image.config_words) == len(image.state_words) == n):
        raise ValueError("packed image config/state length mismatch")
    if image.synapse_count != len(image.synapse_words) or image.synapse_count > 32768:
        raise ValueError("invalid packed synapse count")
    if image.route_count != len(image.route_words) or image.route_count > 4096:
        raise ValueError("invalid route count")
    if len(pixel_to_axon) != INPUT_CHANNELS or any(type(i) is not int or not 0 <= i < 4096 for i in pixel_to_axon):
        raise ValueError("784 input channels require a complete axon map")
    if len(set(pixel_to_axon)) != INPUT_CHANNELS:
        raise ValueError("input pixels require distinct destination axons")

    params = tuple(_decode_config(w) for w in image.config_words)
    initial_state = tuple(_decode_state(w) for w in image.state_words)
    axon_table: dict[int, tuple[int, int, int]] = {}
    for item in image.axon_words:
        if not 0 <= item.index < 4096 or item.index in axon_table:
            raise ValueError("invalid or duplicate packed axon index")
        word = item.word
        if word >> 42 or (word >> 41) & 1 != 1:
            raise ValueError("invalid axon valid/reserved bits")
        first, length, offset = word & 0x7FFF, (word >> 15) & 0xFFFF, (word >> 31) & 0x3FF
        if first + length > image.synapse_count:
            raise ValueError("axon points outside packed synapse table")
        axon_table[item.index] = (first, length, offset)
    if any(index not in axon_table for index in pixel_to_axon):
        raise ValueError("pixel ingress map references unavailable axon")

    rows: list[tuple[int, int]] = []
    for word in image.synapse_words:
        if word >> 48 or ((word >> 34) & 0x3F):
            raise ValueError("unsupported packed synapse reserved bits or delay")
        rows.append((word & 0x3FF, _signed24(word >> 10)))

    route_desc: dict[int, tuple[int, int]] = {}
    for item in image.route_descriptor_words:
        if item.index in route_desc or not 0 <= item.index < n:
            raise ValueError("invalid or duplicate route descriptor")
        word = item.word
        if word >> 26 or (word >> 25) & 1 != 1:
            raise ValueError("invalid route descriptor valid/reserved bits")
        first, length = word & 0xFFF, (word >> 12) & 0x1FFF
        if first + length > image.route_count:
            raise ValueError("route descriptor outside route table")
        route_desc[item.index] = (first, length)
    routes: list[int] = []
    for word in image.route_words:
        if word >> 19:
            raise ValueError("route word reserved bits nonzero")
        dst_core, dst_axon = word & 0x7F, (word >> 7) & 0xFFF
        if dst_core != image.core_id or dst_axon not in axon_table:
            raise ValueError("compact self-route has invalid destination")
        routes.append(dst_axon)

    states = list(initial_state)
    counts = [0] * OUTPUT_CLASSES
    next_bank: tuple[tuple[int, int], ...] = ()  # (source compartment, destination axon)
    ticks: list[PackedTick] = []
    for timestep, active in enumerate(image_event_schedule(pixels)):
        external_axons = tuple(pixel_to_axon[pixel_index] for pixel_index in active)
        current_bank = external_axons + tuple(axon for _source, axon in next_bank)
        if len(current_bank) > EVENT_BANK_DEPTH:
            raise ValueError("P03 current event bank overflow")
        accum = [0] * n
        for axon in current_bank:
            if axon not in axon_table:
                raise ValueError("event references unregistered axon")
            first, length, offset = axon_table[axon]
            for relative, weight in rows[first : first + length]:
                destination = offset + relative
                if destination >= n:
                    raise ValueError("synapse target outside compartment bank")
                accum[destination] = wrap64(accum[destination] + weight)

        fired: list[int] = []
        routed: list[tuple[int, int]] = []
        for compartment in range(n):
            stepped = lif_step(states[compartment], params[compartment], accum[compartment])
            states[compartment] = stepped.state
            if stepped.spiked:
                fired.append(compartment)
                if compartment >= HIDDEN_NEURONS:
                    counts[compartment - HIDDEN_NEURONS] += 1
                if compartment in route_desc:
                    first, length = route_desc[compartment]
                    routed.extend((compartment, axon) for axon in routes[first : first + length])
        if len(routed) > 4096:
            raise ValueError("P03 emitted packet capacity exceeded")
        ticks.append(PackedTick(
            timestep=timestep, axons_current=current_bank,
            accumulators=tuple(accum), states_after=tuple(states),
            fired_compartments=tuple(fired),
            next_packet_sources=tuple(src for src, _axon in routed),
            next_packet_axons=tuple(axon for _src, axon in routed),
            output_counts=tuple(counts),
        ))
        next_bank = tuple(routed)

    return PackedInference(
        ticks=tuple(ticks), output_counts=tuple(counts),
        predicted_class=classify_spike_counts(counts),
        dropped_boundary_packets=tuple(axon for _, axon in next_bank),
    )
