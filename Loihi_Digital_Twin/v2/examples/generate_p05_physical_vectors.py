#!/usr/bin/env python3
"""Generate Tcl data for P05 one-engine/three-context physical conformance."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from loihi_twin_v2 import (
    CompartmentConfig,
    InputAxonBinding,
    LogicalChip,
    LogicalCoreConfig,
    OutputRoute,
    OutputRouteEntry,
    SpikePacket,
    SynapseEntry,
    SynapseTemplate,
)
from loihi_twin_v2.hardware_p03 import (
    P03_REQUIRED_ARITHMETIC,
    pack_compartment_state,
    pack_output_packet,
)
from loihi_twin_v2.hardware_p05 import export_virtualized_hardware_image


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    cores: tuple[LogicalCoreConfig, LogicalCoreConfig, LogicalCoreConfig]
    initial_packets: tuple[SpikePacket, ...]
    ticks: int


def lif() -> CompartmentConfig:
    return CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=5)


def ring_core(core_id: int, input_axon: int, next_core: int, next_axon: int) -> LogicalCoreConfig:
    return LogicalCoreConfig(
        core_id=core_id,
        compartments=(lif(),),
        input_axons=(InputAxonBinding(input_axon, 0),),
        synapse_templates=(SynapseTemplate(0, (SynapseEntry(0, 6),)),),
        output_routes=(OutputRouteEntry(0, (OutputRoute(next_core, next_axon),)),),
        arithmetic=P03_REQUIRED_ARITHMETIC,
    )


def logical_id_ring() -> Scenario:
    cores = (
        ring_core(7, 100, 42, 200),
        ring_core(42, 200, 99, 300),
        ring_core(99, 300, 7, 100),
    )
    return Scenario(
        name="logical_id_ring",
        cores=cores,
        initial_packets=(SpikePacket(0, 7, 100),),
        ticks=4,
    )


def local_remote_fanin() -> Scenario:
    core7 = LogicalCoreConfig(
        core_id=7,
        compartments=(lif(),),
        input_axons=(InputAxonBinding(100, 0), InputAxonBinding(101, 1)),
        synapse_templates=(
            SynapseTemplate(0, (SynapseEntry(0, 6),)),
            SynapseTemplate(1, (SynapseEntry(0, 6),)),
        ),
        output_routes=(
            OutputRouteEntry(0, (OutputRoute(7, 101), OutputRoute(99, 300))),
        ),
        arithmetic=P03_REQUIRED_ARITHMETIC,
    )
    core42 = LogicalCoreConfig(
        core_id=42,
        compartments=(lif(),),
        input_axons=(InputAxonBinding(200, 0), InputAxonBinding(201, 1)),
        synapse_templates=(
            SynapseTemplate(0, (SynapseEntry(0, 6),)),
            SynapseTemplate(1, (SynapseEntry(0, 6),)),
        ),
        output_routes=(
            OutputRouteEntry(0, (OutputRoute(42, 201), OutputRoute(99, 301))),
        ),
        arithmetic=P03_REQUIRED_ARITHMETIC,
    )
    core99 = LogicalCoreConfig(
        core_id=99,
        compartments=(lif(),),
        input_axons=(
            InputAxonBinding(300, 0),
            InputAxonBinding(301, 1),
            InputAxonBinding(302, 2),
        ),
        synapse_templates=(
            SynapseTemplate(0, (SynapseEntry(0, 3),)),
            SynapseTemplate(1, (SynapseEntry(0, 4),)),
            SynapseTemplate(2, (SynapseEntry(0, 6),)),
        ),
        output_routes=(
            OutputRouteEntry(0, (OutputRoute(99, 302), OutputRoute(7, 101))),
        ),
        arithmetic=P03_REQUIRED_ARITHMETIC,
    )
    return Scenario(
        name="local_remote_fanin",
        cores=(core7, core42, core99),
        initial_packets=(SpikePacket(0, 7, 100), SpikePacket(0, 42, 200)),
        ticks=3,
    )


def _hex(value: int, bits: int) -> str:
    digits = (bits + 3) // 4
    return f"0x{value & ((1 << bits) - 1):0{digits}X}"


def _pair_list(entries: list[tuple[int, int]], bits: int) -> str:
    return "{" + " ".join(
        "{" + f"{index} {_hex(word, bits)}" + "}" for index, word in entries
    ) + "}"


def _word_list(words: list[int], bits: int) -> str:
    return "{" + " ".join(_hex(word, bits) for word in words) + "}"


def _int_list(values: list[int] | tuple[int, ...]) -> str:
    return "{" + " ".join(str(value) for value in values) + "}"


def _trace_word(before: int, synaptic_input: int, after: int, spike: bool) -> int:
    return (
        (before & ((1 << 64) - 1))
        | ((synaptic_input & ((1 << 64) - 1)) << 64)
        | ((after & ((1 << 64) - 1)) << 128)
        | ((1 if spike else 0) << 192)
    )


def _context_image_dict(context) -> str:
    image = context.image
    config = list(enumerate(image.config_words))
    state = list(enumerate(image.state_words))
    axons = [(seed.index, seed.word) for seed in image.axon_words]
    synapses = list(enumerate(image.synapse_words))
    route_desc = [(seed.index, seed.word) for seed in image.route_descriptor_words]
    routes = list(enumerate(image.route_words))
    return (
        "{"
        f"slot {context.context_slot} "
        f"logical_core_id {context.logical_core_id} "
        f"compartment_count {image.compartment_count} "
        f"synapse_count {image.synapse_count} "
        f"route_count {image.route_count} "
        f"config_seeds {_pair_list(config, 128)} "
        f"state_seeds {_pair_list(state, 64)} "
        f"axon_seeds {_pair_list(axons, 64)} "
        f"synapse_seeds {_pair_list(synapses, 64)} "
        f"route_desc_seeds {_pair_list(route_desc, 32)} "
        f"route_seeds {_pair_list(routes, 32)}"
        "}"
    )


def build_text() -> str:
    scenarios = (logical_id_ring(), local_remote_fanin())
    lines = [
        "# Generated by examples/generate_p05_physical_vectors.py. Do not edit.",
        "set P05_CONTEXTS 3",
        "set P05_PHYSICAL_ENGINES 1",
        "set P05_SCENARIOS {",
    ]

    for scenario in scenarios:
        image = export_virtualized_hardware_image(scenario.cores)
        id_to_slot = image.logical_to_context_slot
        initial_events: list[list[int]] = [[], [], []]
        for packet in scenario.initial_packets:
            initial_events[id_to_slot[packet.destination_core]].append(packet.destination_axon)

        metadata_words = [
            context.metadata_word(initial_event_count=len(initial_events[context.context_slot]))
            for context in image.contexts
        ]
        combined_metadata = (
            metadata_words[0]
            | (metadata_words[1] << 64)
            | (metadata_words[2] << 128)
        )

        chip = LogicalChip(scenario.cores)
        tick_lines: list[str] = []
        for timestep in range(scenario.ticks):
            trace = chip.step(scenario.initial_packets if timestep == 0 else ())
            context_dicts: list[str] = []
            next_events: list[list[int]] = [[], [], []]
            local_packets = 0
            remote_packets = 0

            for context in image.contexts:
                core_id = context.logical_core_id
                core_trace = next(c for c in trace.cores if c.logical_core_id == core_id)
                synaptic_input = [0] * len(core_trace.compartment_state_after)
                for contribution in core_trace.synaptic_contributions:
                    synaptic_input[contribution.target_compartment] += contribution.weight
                spike_set = set(core_trace.spikes_out)

                states: list[int] = []
                traces: list[int] = []
                for compartment_id in range(len(core_trace.compartment_state_after)):
                    before = pack_compartment_state(core_trace.compartment_state_before[compartment_id].state)
                    after = pack_compartment_state(core_trace.compartment_state_after[compartment_id].state)
                    states.append(after)
                    traces.append(
                        _trace_word(
                            before,
                            synaptic_input[compartment_id],
                            after,
                            compartment_id in spike_set,
                        )
                    )

                packets = [pack_output_packet(packet) for packet in core_trace.packets_out]
                for packet in core_trace.packets_out:
                    next_events[id_to_slot[packet.destination_core]].append(packet.destination_axon)
                    if packet.destination_core == core_id:
                        local_packets += 1
                    else:
                        remote_packets += 1

                context_dicts.append(
                    "{"
                    f"slot {context.context_slot} "
                    f"logical_core_id {core_id} "
                    f"spike_count {len(spike_set)} "
                    f"packet_count {len(packets)} "
                    f"states {_word_list(states, 64)} "
                    f"traces {_word_list(traces, 256)} "
                    f"packets {_word_list(packets, 64)}"
                    "}"
                )

            tick_lines.append(
                "{"
                f"timestep {timestep} "
                f"contexts {{{' '.join(context_dicts)}}} "
                f"next_events0 {_int_list(next_events[0])} "
                f"next_events1 {_int_list(next_events[1])} "
                f"next_events2 {_int_list(next_events[2])} "
                f"local_packets {local_packets} "
                f"remote_packets {remote_packets}"
                "}"
            )

        lines.append(
            "    {"
            f"name {scenario.name} "
            f"context_metadata {_hex(combined_metadata, 192)} "
            f"contexts {{{' '.join(_context_image_dict(context) for context in image.contexts)}}} "
            f"initial_events0 {_int_list(initial_events[0])} "
            f"initial_events1 {_int_list(initial_events[1])} "
            f"initial_events2 {_int_list(initial_events[2])} "
            "ticks {"
            + " ".join(tick_lines)
            + "}"
            "}"
        )

    lines.extend(["}", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_text(), encoding="utf-8")
    print(f"P05 generated physical corpus: output={args.output} scenarios=2")


if __name__ == "__main__":
    main()
