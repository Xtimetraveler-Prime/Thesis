#!/usr/bin/env python3
"""Generate the deterministic P04 two-core integration corpus.

The generated include is consumed by the C simulation harness that invokes the
accepted P03 HLS core twice, routes the *actual* emitted packet words into the
next-timestep event lists, and compares both cores against the Python golden
model. Only timestep-0 external events are seeded by the harness; subsequent
input-event lists must arise from routed HLS packets.
"""

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
from loihi_twin_v2.hardware_p04 import export_two_core_validation_image

MAX_SEED_COMPARTMENTS = 4
MAX_SEED_EVENTS = 8
MAX_SEED_PACKETS = 8


@dataclass(frozen=True)
class Scenario:
    name: str
    cores: tuple[LogicalCoreConfig, LogicalCoreConfig]
    initial_packets: tuple[SpikePacket, ...]
    ticks: int


def lif(threshold: int = 5) -> CompartmentConfig:
    return CompartmentConfig(
        current_decay=4096,
        voltage_decay=4096,
        threshold=threshold,
    )


def feed_forward() -> Scenario:
    core0 = LogicalCoreConfig(
        core_id=0,
        compartments=(lif(),),
        input_axons=(InputAxonBinding(0, 0),),
        synapse_templates=(SynapseTemplate(0, (SynapseEntry(0, 6),)),),
        output_routes=(OutputRouteEntry(0, (OutputRoute(1, 1),)),),
        arithmetic=P03_REQUIRED_ARITHMETIC,
    )
    core1 = LogicalCoreConfig(
        core_id=1,
        compartments=(lif(),),
        input_axons=(InputAxonBinding(1, 0),),
        synapse_templates=(SynapseTemplate(0, (SynapseEntry(0, 6),)),),
        arithmetic=P03_REQUIRED_ARITHMETIC,
    )
    return Scenario(
        "feed_forward",
        (core0, core1),
        (SpikePacket(0, 0, 0),),
        2,
    )


def recurrent_multicast() -> Scenario:
    def config(core_id: int, remote_core: int) -> LogicalCoreConfig:
        return LogicalCoreConfig(
            core_id=core_id,
            compartments=(lif(),),
            input_axons=(
                InputAxonBinding(0, 0),
                InputAxonBinding(1, 1),
                InputAxonBinding(2, 1),
            ),
            synapse_templates=(
                SynapseTemplate(0, (SynapseEntry(0, 6),)),
                SynapseTemplate(1, (SynapseEntry(0, 3),)),
            ),
            output_routes=(
                OutputRouteEntry(
                    0,
                    (
                        OutputRoute(core_id, 1),
                        OutputRoute(remote_core, 2),
                    ),
                ),
            ),
            arithmetic=P03_REQUIRED_ARITHMETIC,
        )

    return Scenario(
        "recurrent_multicast",
        (config(0, 1), config(1, 0)),
        (SpikePacket(0, 0, 0), SpikePacket(0, 1, 0)),
        3,
    )


def _hex64(value: int) -> str:
    return f"0x{value & ((1 << 64) - 1):016X}ULL"


def _emit_u32(values: list[int], length: int) -> str:
    padded = values + [0] * (length - len(values))
    return "{" + ", ".join(str(v) for v in padded) + "}"


def _emit_u64(values: list[int], length: int) -> str:
    padded = values + [0] * (length - len(values))
    return "{" + ", ".join(_hex64(v) for v in padded) + "}"


def _emit_seed_array(
    lines: list[str],
    declaration: str,
    entries: list[str],
    dummy: str,
) -> None:
    lines.append(declaration + " = {")
    if entries:
        lines.extend(f"    {entry}," for entry in entries)
    else:
        # Standard C++ does not allow a zero-length inferred array. The seed
        # count stored in CoreSeed remains zero, so this sentinel is never read.
        lines.append(f"    {dummy},")
    lines.append("};")


def _emit_core_seed(lines: list[str], scenario_index: int, core_index: int, image) -> str:
    prefix = f"P04_S{scenario_index}_C{core_index}"

    config_entries = [
        f"{{{index}, {_hex64(word)}, {_hex64(word >> 64)}}}"
        for index, word in enumerate(image.config_words)
    ]
    state_entries = [
        f"{{{index}, {_hex64(word)}}}" for index, word in enumerate(image.state_words)
    ]
    axon_entries = [
        f"{{{seed.index}, {_hex64(seed.word)}}}" for seed in image.axon_words
    ]
    synapse_entries = [
        f"{{{index}, {_hex64(word)}}}" for index, word in enumerate(image.synapse_words)
    ]
    route_desc_entries = [
        f"{{{seed.index}, 0x{seed.word & 0xFFFFFFFF:08X}u}}"
        for seed in image.route_descriptor_words
    ]
    route_entries = [
        f"{{{index}, 0x{word & 0xFFFFFFFF:08X}u}}"
        for index, word in enumerate(image.route_words)
    ]

    _emit_seed_array(
        lines,
        f"const Word128Seed {prefix}_CONFIG[]",
        config_entries,
        "{0, 0ULL, 0ULL}",
    )
    _emit_seed_array(
        lines,
        f"const Word64Seed {prefix}_STATE[]",
        state_entries,
        "{0, 0ULL}",
    )
    _emit_seed_array(
        lines,
        f"const Word64Seed {prefix}_AXON[]",
        axon_entries,
        "{0, 0ULL}",
    )
    _emit_seed_array(
        lines,
        f"const Word64Seed {prefix}_SYNAPSE[]",
        synapse_entries,
        "{0, 0ULL}",
    )
    _emit_seed_array(
        lines,
        f"const Word32Seed {prefix}_ROUTE_DESC[]",
        route_desc_entries,
        "{0, 0u}",
    )
    _emit_seed_array(
        lines,
        f"const Word32Seed {prefix}_ROUTE[]",
        route_entries,
        "{0, 0u}",
    )
    lines.append("")

    return (
        "{" + ", ".join(
            (
                str(image.core_id),
                str(image.compartment_count),
                str(image.synapse_count),
                str(image.route_count),
                f"{prefix}_CONFIG, {len(config_entries)}",
                f"{prefix}_STATE, {len(state_entries)}",
                f"{prefix}_AXON, {len(axon_entries)}",
                f"{prefix}_SYNAPSE, {len(synapse_entries)}",
                f"{prefix}_ROUTE_DESC, {len(route_desc_entries)}",
                f"{prefix}_ROUTE, {len(route_entries)}",
            )
        ) + "}"
    )


def build_text() -> str:
    scenarios = (feed_forward(), recurrent_multicast())
    lines: list[str] = [
        "// Generated by examples/generate_p04_hls_vectors.py. Do not edit.",
        "",
    ]

    scenario_core_seed_exprs: list[tuple[str, str]] = []
    scenario_tick_names: list[str] = []

    for scenario_index, scenario in enumerate(scenarios):
        image = export_two_core_validation_image(scenario.cores)
        core_seed_exprs = (
            _emit_core_seed(lines, scenario_index, 0, image.core0),
            _emit_core_seed(lines, scenario_index, 1, image.core1),
        )
        scenario_core_seed_exprs.append(core_seed_exprs)

        chip = LogicalChip(scenario.cores)
        tick_name = f"P04_S{scenario_index}_TICKS"
        scenario_tick_names.append(tick_name)
        lines.append(f"const TwoCoreTickSeed {tick_name}[] = {{")
        for timestep in range(scenario.ticks):
            external = scenario.initial_packets if timestep == 0 else ()
            trace = chip.step(external)
            core_entries: list[str] = []
            local_packets = 0
            remote_packets = 0
            for core_id in (0, 1):
                core_trace = next(c for c in trace.cores if c.logical_core_id == core_id)
                events = [packet.destination_axon for packet in core_trace.packet_in]
                if len(events) > MAX_SEED_EVENTS:
                    raise ValueError("P04 seed event capacity exceeded")

                contributions = [0] * len(core_trace.compartment_state_after)
                for contribution in core_trace.synaptic_contributions:
                    contributions[contribution.target_compartment] += contribution.weight
                spikes = set(core_trace.spikes_out)
                expected: list[str] = []
                for compartment_id in range(MAX_SEED_COMPARTMENTS):
                    if compartment_id < len(core_trace.compartment_state_after):
                        before = pack_compartment_state(
                            core_trace.compartment_state_before[compartment_id].state
                        )
                        after = pack_compartment_state(
                            core_trace.compartment_state_after[compartment_id].state
                        )
                        expected.append(
                            "{" + ", ".join(
                                (
                                    _hex64(before),
                                    str(contributions[compartment_id]),
                                    _hex64(after),
                                    "1" if compartment_id in spikes else "0",
                                )
                            ) + "}"
                        )
                    else:
                        expected.append("{0ULL, 0, 0ULL, 0}")

                packets = [pack_output_packet(packet) for packet in core_trace.packets_out]
                for packet in core_trace.packets_out:
                    if packet.destination_core == core_id:
                        local_packets += 1
                    else:
                        remote_packets += 1
                if len(packets) > MAX_SEED_PACKETS:
                    raise ValueError("P04 seed packet capacity exceeded")
                core_entries.append(
                    "{" + ", ".join(
                        (
                            str(len(events)),
                            _emit_u32(events, MAX_SEED_EVENTS),
                            "{" + ", ".join(expected) + "}",
                            str(len(packets)),
                            _emit_u64(packets, MAX_SEED_PACKETS),
                        )
                    ) + "}"
                )
            lines.append(
                "    {"
                + str(timestep)
                + ", {"
                + ", ".join(core_entries)
                + f"}}, {local_packets}, {remote_packets}}},"
            )
        lines.append("};")
        lines.append("")

    lines.append("const P04ScenarioSeed P04_SCENARIOS[] = {")
    for index, scenario in enumerate(scenarios):
        c0, c1 = scenario_core_seed_exprs[index]
        ticks = scenario_tick_names[index]
        lines.append(
            "    {"
            + f'"{scenario.name}", '
            + "{" + c0 + ", " + c1 + "}, "
            + f"{ticks}, sizeof({ticks})/sizeof({ticks}[0])"
            + "},"
        )
    lines.append("};")
    lines.append(
        "constexpr unsigned P04_SCENARIO_COUNT = sizeof(P04_SCENARIOS)/sizeof(P04_SCENARIOS[0]);"
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    text = build_text()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(
        f"P04 generated two-core HLS corpus: output={args.output} "
        "scenarios=2"
    )


if __name__ == "__main__":
    main()
