from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from neuromorphic_twin.fpga_recurrent_routing import (
    DoubleBufferedRecurrentQueue,
    FrozenRouteStorage,
    RecurrentRoutingResult,
    freeze_spike_routes_v1,
    route_and_commit_recurrent_v1,
)
from neuromorphic_twin.model import SpikeRoute

M11_5_4_SEED = 0x4D313534
M11_5_4_CASE_COUNT = 16
M11_5_4_TICKS_PER_CASE = 4
M11_5_4_MAX_NEURONS = 12
M11_5_4_MAX_ROUTES = 32
M11_5_4_MAX_AXONS = 16
M11_5_4_MAX_EVENTS = 32

_MASK64 = (1 << 64) - 1


class _SplitMix64:
    def __init__(self, seed: int) -> None:
        self._state = seed & _MASK64

    def next_u64(self) -> int:
        self._state = (self._state + 0x9E3779B97F4A7C15) & _MASK64
        value = self._state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & _MASK64
        return (value ^ (value >> 31)) & _MASK64

    def randint(self, minimum: int, maximum: int) -> int:
        if maximum < minimum:
            raise ValueError("maximum must be >= minimum")
        return minimum + self.next_u64() % (maximum - minimum + 1)


@dataclass(frozen=True, slots=True)
class RecurrentVectorCase:
    name: str
    storage: FrozenRouteStorage
    spike_vectors: tuple[tuple[bool, ...], ...]
    results: tuple[RecurrentRoutingResult, ...]


def _evaluate(
    name: str,
    storage: FrozenRouteStorage,
    spike_vectors: tuple[tuple[bool, ...], ...],
) -> RecurrentVectorCase:
    queue = DoubleBufferedRecurrentQueue.empty()
    results: list[RecurrentRoutingResult] = []
    for spikes in spike_vectors:
        result = route_and_commit_recurrent_v1(queue, storage, spikes)
        results.append(result)
        queue = result.queue_after_commit
    return RecurrentVectorCase(
        name=name,
        storage=storage,
        spike_vectors=spike_vectors,
        results=tuple(results),
    )


def _directed_case() -> RecurrentVectorCase:
    storage = freeze_spike_routes_v1(
        (
            SpikeRoute(2, 9),
            SpikeRoute(1, 8),
            SpikeRoute(0, 6),
            SpikeRoute(1, 7),
            SpikeRoute(2, 6),
        ),
        neuron_count=3,
    )
    return _evaluate(
        "directed_order_and_empty_ticks",
        storage,
        (
            (True, True, True),
            (False, True, False),
            (False, False, False),
            (True, False, True),
        ),
    )


def _random_routes(rng: _SplitMix64, case_index: int) -> FrozenRouteStorage:
    neuron_count = rng.randint(2, M11_5_4_MAX_NEURONS)
    rows: list[list[int]] = [[] for _ in range(neuron_count)]
    route_total = 0

    for source in range(neuron_count):
        remaining = M11_5_4_MAX_ROUTES - route_total
        if remaining == 0:
            break
        row_length = min(rng.randint(0, 4), remaining, M11_5_4_MAX_AXONS)
        used: set[int] = set()
        for local_index in range(row_length):
            # Deliberately encourage cross-source target reuse while retaining
            # the M09 rule that one source cannot declare the same target twice.
            if source > 0 and local_index == 0 and rows[source - 1]:
                target = rows[source - 1][rng.randint(0, len(rows[source - 1]) - 1)]
            else:
                target = rng.randint(0, M11_5_4_MAX_AXONS - 1)
            while target in used:
                target = (target + 1) % M11_5_4_MAX_AXONS
            used.add(target)
            rows[source].append(target)
            route_total += 1

    if route_total == 0:
        rows[case_index % neuron_count].append(case_index % M11_5_4_MAX_AXONS)

    # Feed source groups to the freezer in a deterministic non-source order.
    # The freezer must canonicalize source order but retain each row's target order.
    source_order = list(range(neuron_count))
    if case_index & 1:
        source_order.reverse()
    elif neuron_count > 2:
        source_order = source_order[1:] + source_order[:1]

    routes: list[SpikeRoute] = []
    for source in source_order:
        for target in rows[source]:
            routes.append(SpikeRoute(source, target))
    return freeze_spike_routes_v1(routes, neuron_count=neuron_count)


def _random_spikes(
    rng: _SplitMix64,
    neuron_count: int,
    case_index: int,
) -> tuple[tuple[bool, ...], ...]:
    vectors: list[tuple[bool, ...]] = []
    for tick in range(M11_5_4_TICKS_PER_CASE):
        if tick == 2 and case_index % 3 == 0:
            values = [False] * neuron_count
        elif tick == 0 and case_index % 4 == 0:
            values = [True] * neuron_count
        else:
            values = [bool(rng.next_u64() & 1) for _ in range(neuron_count)]
        vectors.append(tuple(values))
    return tuple(vectors)


def _random_case(rng: _SplitMix64, case_index: int) -> RecurrentVectorCase:
    storage = _random_routes(rng, case_index)
    spikes = _random_spikes(rng, storage.neuron_count, case_index)
    return _evaluate(f"random_{case_index:02d}", storage, spikes)


def m11_5_4_cases() -> tuple[RecurrentVectorCase, ...]:
    rng = _SplitMix64(M11_5_4_SEED)
    return (_directed_case(),) + tuple(
        _random_case(rng, index) for index in range(M11_5_4_CASE_COUNT - 1)
    )


def _hex(value: int, width: int) -> str:
    return f"{value & ((1 << width) - 1):0{(width + 3) // 4}x}"


def write_systemverilog_include(output: Path) -> Path:
    cases = m11_5_4_cases()
    lines = [
        "// Generated by examples/generate_m11_5_4_vectors.py; do not edit.",
        f"localparam int M11_5_4_CASE_COUNT = {M11_5_4_CASE_COUNT};",
        f"localparam int M11_5_4_TICKS_PER_CASE = {M11_5_4_TICKS_PER_CASE};",
        f"localparam logic [31:0] M11_5_4_SEED = 32'h{M11_5_4_SEED:08x};",
        f"localparam int M11_5_4_MAX_NEURONS = {M11_5_4_MAX_NEURONS};",
        f"localparam int M11_5_4_MAX_ROUTES = {M11_5_4_MAX_ROUTES};",
        f"localparam int M11_5_4_MAX_EVENTS = {M11_5_4_MAX_EVENTS};",
        "",
    ]

    def emit_case_counts(name: str, width: int, values: list[int]) -> None:
        lines.append(
            f"localparam logic [{width - 1}:0] {name} [0:M11_5_4_CASE_COUNT-1] = '{{"
        )
        for index, value in enumerate(values):
            comma = "," if index + 1 != len(values) else ""
            lines.append(f"    {width}'d{value}{comma} // {cases[index].name}")
        lines.append("};")
        lines.append("")

    emit_case_counts(
        "M11_5_4_NEURON_COUNTS", 9, [case.storage.neuron_count for case in cases]
    )
    emit_case_counts(
        "M11_5_4_ROUTE_COUNTS", 13, [case.storage.route_count for case in cases]
    )

    def emit_flat(
        name: str,
        width: int,
        per_case: int,
        rows: list[tuple[int, ...]],
    ) -> None:
        total = len(rows) * per_case
        lines.append(f"localparam logic [{width - 1}:0] {name} [0:{total - 1}] = '{{")
        emitted = 0
        for case_index, row in enumerate(rows):
            padded = tuple(row) + (0,) * (per_case - len(row))
            if len(padded) != per_case:
                raise ValueError(f"{name} row exceeds generated capacity")
            for local_index, value in enumerate(padded):
                emitted += 1
                comma = "," if emitted != total else ""
                comment = f" // {cases[case_index].name}" if local_index == 0 else ""
                lines.append(f"    {width}'h{_hex(value, width)}{comma}{comment}")
        lines.append("};")
        lines.append("")

    emit_flat(
        "M11_5_4_ROUTE_ROWS",
        32,
        M11_5_4_MAX_NEURONS + 1,
        [case.storage.row_pointers for case in cases],
    )
    emit_flat(
        "M11_5_4_ROUTE_TARGETS",
        16,
        M11_5_4_MAX_ROUTES,
        [case.storage.target_axons for case in cases],
    )

    tick_count = M11_5_4_CASE_COUNT * M11_5_4_TICKS_PER_CASE
    spike_rows: list[tuple[int, ...]] = []
    consumed_rows: list[tuple[int, ...]] = []
    routed_rows: list[tuple[int, ...]] = []
    consumed_counts: list[int] = []
    routed_counts: list[int] = []
    current_banks: list[int] = []
    current_counts: list[int] = []
    bank0_counts: list[int] = []
    bank1_counts: list[int] = []

    for case in cases:
        for spikes, result in zip(case.spike_vectors, case.results, strict=True):
            spike_rows.append(tuple(int(value) for value in spikes))
            consumed_rows.append(result.consumed_recurrent_axons)
            routed_rows.append(result.routed_output_axons)
            consumed_counts.append(len(result.consumed_recurrent_axons))
            routed_counts.append(len(result.routed_output_axons))
            queue = result.queue_after_commit
            current_banks.append(queue.current_bank)
            current_counts.append(len(queue.current_events))
            bank0_counts.append(len(queue.bank0))
            bank1_counts.append(len(queue.bank1))

    def emit_tick_values(name: str, width: int, values: list[int]) -> None:
        if len(values) != tick_count:
            raise ValueError(f"{name} has wrong tick count")
        lines.append(f"localparam logic [{width - 1}:0] {name} [0:{tick_count - 1}] = '{{")
        for index, value in enumerate(values):
            comma = "," if index + 1 != len(values) else ""
            lines.append(f"    {width}'d{value}{comma}")
        lines.append("};")
        lines.append("")

    emit_flat("M11_5_4_SPIKES", 1, M11_5_4_MAX_NEURONS, spike_rows)
    emit_flat("M11_5_4_EXPECTED_CONSUMED", 16, M11_5_4_MAX_EVENTS, consumed_rows)
    emit_flat("M11_5_4_EXPECTED_ROUTED", 16, M11_5_4_MAX_EVENTS, routed_rows)
    emit_tick_values("M11_5_4_EXPECTED_CONSUMED_COUNTS", 13, consumed_counts)
    emit_tick_values("M11_5_4_EXPECTED_ROUTED_COUNTS", 13, routed_counts)
    emit_tick_values("M11_5_4_EXPECTED_CURRENT_BANKS", 1, current_banks)
    emit_tick_values("M11_5_4_EXPECTED_CURRENT_COUNTS", 13, current_counts)
    emit_tick_values("M11_5_4_EXPECTED_BANK0_COUNTS", 13, bank0_counts)
    emit_tick_values("M11_5_4_EXPECTED_BANK1_COUNTS", 13, bank1_counts)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = write_systemverilog_include(args.output)
    cases = m11_5_4_cases()
    transitions = sum(len(case.results) for case in cases)
    total_routes = sum(case.storage.route_count for case in cases)
    total_routed = sum(
        len(result.routed_output_axons)
        for case in cases
        for result in case.results
    )
    print(
        "M11.5.4 differential vectors generated: "
        f"cases={len(cases)}, ticks={transitions}, seed=0x{M11_5_4_SEED:08X}, "
        f"stored_routes={total_routes}, routed_events={total_routed}"
    )
    print(f"output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
