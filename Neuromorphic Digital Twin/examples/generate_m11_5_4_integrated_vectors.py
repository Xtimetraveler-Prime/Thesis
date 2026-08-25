from __future__ import annotations

import argparse
from pathlib import Path

from neuromorphic_twin.fpga_core_capacity import (
    pack_neuron_config_word,
    pack_neuron_state_word,
)
from neuromorphic_twin.fpga_recurrent_routing import (
    DoubleBufferedRecurrentQueue,
    freeze_spike_routes_v1,
    route_and_commit_recurrent_v1,
)
from neuromorphic_twin.fpga_synapse_reference import accumulate_frozen_weight_image_v1
from neuromorphic_twin.fpga_weight_storage import (
    FrozenWeightStorage,
    pack_synapse_word,
    pack_weight_format,
)
from neuromorphic_twin.model import NeuronConfig, NeuronState, SpikeRoute
from neuromorphic_twin.neuron_array_reference import step_packed_neuron_array_v1
from neuromorphic_twin.weights import WeightFormat, WeightSignMode

M11_5_4I_TAG = 0x4D353449  # "M54I"
M11_5_4I_NEURON_COUNT = 3
M11_5_4I_TICK_COUNT = 4


def _weight_storage() -> FrozenWeightStorage:
    fmt = WeightFormat(
        exponent=0,
        num_weight_bits=8,
        sign_mode=WeightSignMode.EXCITATORY,
    )
    rows = (
        ((0, 2, 0),),  # external axon 0 -> neuron 0, effective weight 128
        ((1, 2, 0),),  # recurrence axon 1 -> neuron 1
        ((2, 2, 0),),  # recurrence axon 2 -> neuron 2
    )
    synapses: list[int] = []
    pointers = [0]
    for row in rows:
        for target, mantissa, format_index in row:
            synapses.append(
                pack_synapse_word(
                    target_neuron=target,
                    requested_mantissa=mantissa,
                    format_index=format_index,
                )
            )
        pointers.append(len(synapses))
    return FrozenWeightStorage(
        format_words=(pack_weight_format(fmt),),
        synapse_words=tuple(synapses),
        axon_row_pointers=tuple(pointers),
    )


def integrated_vectors() -> dict[str, object]:
    storage = _weight_storage()
    routes = freeze_spike_routes_v1(
        (
            SpikeRoute(0, 1),
            SpikeRoute(1, 2),
        ),
        neuron_count=M11_5_4I_NEURON_COUNT,
    )

    config = NeuronConfig(
        current_decay=4096,
        voltage_decay=4096,
        threshold=64,
        bias=0,
        reset_voltage=0,
        refractory_ticks=0,
    )
    config_words = tuple(
        pack_neuron_config_word(config) for _ in range(M11_5_4I_NEURON_COUNT)
    )
    reset_word = pack_neuron_state_word(
        NeuronState(current=0, voltage=0, refractory_remaining=0)
    )
    state_words = tuple(reset_word for _ in range(M11_5_4I_NEURON_COUNT))
    initial_state_words = state_words

    external_by_tick = ((0,), (), (), ())
    queue = DoubleBufferedRecurrentQueue.empty()

    expected_states: list[tuple[int, ...]] = []
    expected_spikes: list[tuple[int, ...]] = []
    expected_accumulators: list[tuple[int, ...]] = []
    expected_consumed: list[tuple[int, ...]] = []
    expected_routed: list[tuple[int, ...]] = []
    expected_current_bank: list[int] = []
    expected_current_events: list[tuple[int, ...]] = []

    for external in external_by_tick:
        consumed = queue.current_events
        phase_b = accumulate_frozen_weight_image_v1(
            storage,
            neuron_count=M11_5_4I_NEURON_COUNT,
            external_axons=external,
            recurrent_axons=consumed,
        )
        stepped = step_packed_neuron_array_v1(
            state_words,
            config_words,
            phase_b.accumulators,
        )
        spikes_bool = tuple(bool(value) for value in stepped.spikes)
        routed = route_and_commit_recurrent_v1(queue, routes, spikes_bool)

        expected_accumulators.append(phase_b.accumulators)
        expected_states.append(stepped.state_words)
        expected_spikes.append(tuple(int(value) for value in stepped.spikes))
        expected_consumed.append(routed.consumed_recurrent_axons)
        expected_routed.append(routed.routed_output_axons)
        expected_current_bank.append(routed.queue_after_commit.current_bank)
        expected_current_events.append(routed.queue_after_commit.current_events)

        state_words = stepped.state_words
        queue = routed.queue_after_commit

    # Freeze the intended proof shape so generator changes cannot weaken the
    # strict next-tick chain without failing source tests.
    assert tuple(expected_spikes) == (
        (1, 0, 0),
        (0, 1, 0),
        (0, 0, 1),
        (0, 0, 0),
    )
    assert tuple(expected_consumed) == ((), (1,), (2,), ())
    assert tuple(expected_routed) == ((1,), (2,), (), ())

    return {
        "storage": storage,
        "routes": routes,
        "config_words": config_words,
        "initial_state_words": initial_state_words,
        "external_by_tick": external_by_tick,
        "expected_accumulators": tuple(expected_accumulators),
        "expected_states": tuple(expected_states),
        "expected_spikes": tuple(expected_spikes),
        "expected_consumed": tuple(expected_consumed),
        "expected_routed": tuple(expected_routed),
        "expected_current_bank": tuple(expected_current_bank),
        "expected_current_events": tuple(expected_current_events),
    }


def _hex(value: int, width: int) -> str:
    return f"{value & ((1 << width) - 1):0{(width + 3) // 4}x}"


def write_systemverilog_include(output: Path) -> Path:
    values = integrated_vectors()
    storage = values["storage"]
    routes = values["routes"]
    assert isinstance(storage, FrozenWeightStorage)

    lines = [
        "// Generated by examples/generate_m11_5_4_integrated_vectors.py; do not edit.",
        f"localparam int M11_5_4I_NEURON_COUNT = {M11_5_4I_NEURON_COUNT};",
        f"localparam int M11_5_4I_TICK_COUNT = {M11_5_4I_TICK_COUNT};",
        f"localparam int M11_5_4I_AXON_COUNT = {storage.axon_count};",
        f"localparam int M11_5_4I_SYNAPSE_COUNT = {storage.synapse_count};",
        f"localparam int M11_5_4I_FORMAT_COUNT = {storage.format_count};",
        f"localparam int M11_5_4I_ROUTE_COUNT = {routes.route_count};",
        f"localparam logic [31:0] M11_5_4I_TAG = 32'h{M11_5_4I_TAG:08x};",
        "",
    ]

    def emit(name: str, width: int, words: tuple[int, ...]) -> None:
        lines.append(f"localparam logic [{width - 1}:0] {name} [0:{len(words) - 1}] = '{{")
        for index, word in enumerate(words):
            comma = "," if index + 1 != len(words) else ""
            lines.append(f"    {width}'h{_hex(word, width)}{comma}")
        lines.append("};")
        lines.append("")

    emit("M11_5_4I_FORMAT_WORDS", 16, storage.format_words)
    emit("M11_5_4I_SYNAPSE_WORDS", 32, storage.synapse_words)
    emit("M11_5_4I_WEIGHT_ROWS", 32, storage.axon_row_pointers)
    emit("M11_5_4I_ROUTE_ROWS", 32, routes.row_pointers)
    emit("M11_5_4I_ROUTE_TARGETS", 16, routes.target_axons)
    emit("M11_5_4I_CONFIG_WORDS", 128, values["config_words"])
    emit("M11_5_4I_INITIAL_STATE_WORDS", 64, values["initial_state_words"])

    external_by_tick = values["external_by_tick"]
    states = values["expected_states"]
    spikes = values["expected_spikes"]
    accumulators = values["expected_accumulators"]
    consumed = values["expected_consumed"]
    routed = values["expected_routed"]
    current_bank = values["expected_current_bank"]
    current_events = values["expected_current_events"]

    external_counts = tuple(len(row) for row in external_by_tick)
    consumed_counts = tuple(len(row) for row in consumed)
    routed_counts = tuple(len(row) for row in routed)
    current_counts = tuple(len(row) for row in current_events)

    emit("M11_5_4I_EXTERNAL_COUNTS", 13, external_counts)
    emit("M11_5_4I_EXPECTED_CONSUMED_COUNTS", 13, consumed_counts)
    emit("M11_5_4I_EXPECTED_ROUTED_COUNTS", 13, routed_counts)
    emit("M11_5_4I_EXPECTED_CURRENT_BANK", 1, current_bank)
    emit("M11_5_4I_EXPECTED_CURRENT_COUNTS", 13, current_counts)

    # One external-event slot per tick is enough for this directed proof.
    emit(
        "M11_5_4I_EXTERNAL_EVENT0",
        16,
        tuple(row[0] if row else 0 for row in external_by_tick),
    )
    emit(
        "M11_5_4I_EXPECTED_CONSUMED_EVENT0",
        16,
        tuple(row[0] if row else 0 for row in consumed),
    )
    emit(
        "M11_5_4I_EXPECTED_ROUTED_EVENT0",
        16,
        tuple(row[0] if row else 0 for row in routed),
    )
    emit(
        "M11_5_4I_EXPECTED_CURRENT_EVENT0",
        16,
        tuple(row[0] if row else 0 for row in current_events),
    )

    emit(
        "M11_5_4I_EXPECTED_STATES",
        64,
        tuple(word for tick_words in states for word in tick_words),
    )
    emit(
        "M11_5_4I_EXPECTED_SPIKES",
        1,
        tuple(word for tick_words in spikes for word in tick_words),
    )
    emit(
        "M11_5_4I_EXPECTED_ACCUMULATORS",
        64,
        tuple(word for tick_words in accumulators for word in tick_words),
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = write_systemverilog_include(args.output)
    values = integrated_vectors()
    storage = values["storage"]
    routes = values["routes"]
    assert isinstance(storage, FrozenWeightStorage)
    print(
        "M11.5.4 integrated recurrence vectors generated: "
        f"ticks={M11_5_4I_TICK_COUNT}, neurons={M11_5_4I_NEURON_COUNT}, "
        f"axons={storage.axon_count}, synapses={storage.synapse_count}, "
        f"routes={routes.route_count}, tag=0x{M11_5_4I_TAG:08X}"
    )
    print(f"output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
