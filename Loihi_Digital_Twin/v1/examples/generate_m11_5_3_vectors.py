from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from neuromorphic_twin.fpga_synapse_reference import accumulate_frozen_weight_image_v1
from neuromorphic_twin.fpga_weight_storage import (
    FrozenWeightStorage,
    pack_synapse_word,
    pack_weight_format,
)
from neuromorphic_twin.weights import WeightFormat, WeightSignMode

M11_5_3_SEED = 0x4D313533
M11_5_3_CASE_COUNT = 12
M11_5_3_MAX_NEURONS = 16
M11_5_3_MAX_AXONS = 16
M11_5_3_MAX_SYNAPSES = 48
M11_5_3_MAX_FORMATS = 6
M11_5_3_MAX_EXTERNAL_EVENTS = 24
M11_5_3_MAX_RECURRENT_EVENTS = 24

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
class PhaseBVectorCase:
    name: str
    neuron_count: int
    storage: FrozenWeightStorage
    external_axons: tuple[int, ...]
    recurrent_axons: tuple[int, ...]
    expected_accumulators: tuple[int, ...]


def _directed_case() -> PhaseBVectorCase:
    formats = (
        WeightFormat(exponent=7, num_weight_bits=8, sign_mode=WeightSignMode.EXCITATORY),
        WeightFormat(exponent=7, num_weight_bits=8, sign_mode=WeightSignMode.INHIBITORY),
        WeightFormat(exponent=-3, num_weight_bits=8, sign_mode=WeightSignMode.MIXED),
        WeightFormat(exponent=0, num_weight_bits=0, sign_mode=WeightSignMode.EXCITATORY),
    )
    rows = (
        (
            (0, 255, 0),
            (1, -256, 1),
        ),
        (
            (2, -5, 2),
            (0, 255, 3),
        ),
        (),
        (
            (3, 17, 0),
        ),
    )
    synapse_words: list[int] = []
    pointers = [0]
    for row in rows:
        for target, mantissa, format_index in row:
            synapse_words.append(
                pack_synapse_word(
                    target_neuron=target,
                    requested_mantissa=mantissa,
                    format_index=format_index,
                )
            )
        pointers.append(len(synapse_words))
    storage = FrozenWeightStorage(
        format_words=tuple(pack_weight_format(fmt) for fmt in formats),
        synapse_words=tuple(synapse_words),
        axon_row_pointers=tuple(pointers),
    )
    external = (0, 1, 2, 0, 7)
    recurrent = (3, 1, 3)
    result = accumulate_frozen_weight_image_v1(
        storage,
        neuron_count=4,
        external_axons=external,
        recurrent_axons=recurrent,
    )
    return PhaseBVectorCase(
        name="directed_extremes",
        neuron_count=4,
        storage=storage,
        external_axons=external,
        recurrent_axons=recurrent,
        expected_accumulators=result.accumulators,
    )


def _random_format(rng: _SplitMix64, index: int) -> WeightFormat:
    sign_modes = (
        WeightSignMode.MIXED,
        WeightSignMode.EXCITATORY,
        WeightSignMode.INHIBITORY,
    )
    boundary_exponents = (-8, -3, -1, 0, 1, 4, 7)
    boundary_bits = (0, 1, 4, 7, 8)
    exponent = (
        boundary_exponents[index % len(boundary_exponents)]
        if index % 3 == 0
        else rng.randint(-8, 7)
    )
    num_weight_bits = (
        boundary_bits[index % len(boundary_bits)]
        if index % 4 == 0
        else rng.randint(0, 8)
    )
    return WeightFormat(
        exponent=exponent,
        num_weight_bits=num_weight_bits,
        sign_mode=sign_modes[rng.randint(0, len(sign_modes) - 1)],
    )


def _random_mantissa(rng: _SplitMix64, fmt: WeightFormat, index: int) -> int:
    low, high = fmt.mantissa_bounds
    edges = (low, min(low + 1, high), max(high - 1, low), high, 0)
    candidate = edges[index % len(edges)] if index % 5 == 0 else rng.randint(low, high)
    return min(max(candidate, low), high)


def _random_case(rng: _SplitMix64, case_index: int) -> PhaseBVectorCase:
    neuron_count = rng.randint(2, M11_5_3_MAX_NEURONS)
    axon_count = rng.randint(1, M11_5_3_MAX_AXONS)
    format_count = rng.randint(1, M11_5_3_MAX_FORMATS)
    formats = tuple(_random_format(rng, case_index * M11_5_3_MAX_FORMATS + i) for i in range(format_count))

    rows: list[list[tuple[int, int, int]]] = []
    synapse_total = 0
    for axon_id in range(axon_count):
        remaining = M11_5_3_MAX_SYNAPSES - synapse_total
        if remaining == 0:
            row_length = 0
        else:
            row_length = min(rng.randint(0, 5), remaining)
        row: list[tuple[int, int, int]] = []
        for local_index in range(row_length):
            format_index = rng.randint(0, format_count - 1)
            fmt = formats[format_index]
            row.append(
                (
                    rng.randint(0, neuron_count - 1),
                    _random_mantissa(rng, fmt, case_index * 97 + axon_id * 7 + local_index),
                    format_index,
                )
            )
        rows.append(row)
        synapse_total += row_length

    if synapse_total == 0:
        fmt = formats[0]
        rows[0].append((0, _random_mantissa(rng, fmt, case_index), 0))

    synapse_words: list[int] = []
    pointers = [0]
    for row in rows:
        for target, mantissa, format_index in row:
            synapse_words.append(
                pack_synapse_word(
                    target_neuron=target,
                    requested_mantissa=mantissa,
                    format_index=format_index,
                )
            )
        pointers.append(len(synapse_words))

    storage = FrozenWeightStorage(
        format_words=tuple(pack_weight_format(fmt) for fmt in formats),
        synapse_words=tuple(synapse_words),
        axon_row_pointers=tuple(pointers),
    )

    def events(maximum: int, salt: int) -> tuple[int, ...]:
        count = rng.randint(0, maximum)
        values: list[int] = []
        for index in range(count):
            if index % 7 == salt and axon_count < M11_5_3_MAX_AXONS:
                values.append(rng.randint(axon_count, M11_5_3_MAX_AXONS - 1))
            elif values and index % 5 == 0:
                values.append(values[-1])
            else:
                values.append(rng.randint(0, axon_count - 1))
        return tuple(values)

    external = events(M11_5_3_MAX_EXTERNAL_EVENTS, case_index % 7)
    recurrent = events(M11_5_3_MAX_RECURRENT_EVENTS, (case_index + 3) % 7)
    if not external and not recurrent:
        external = (0,)

    result = accumulate_frozen_weight_image_v1(
        storage,
        neuron_count=neuron_count,
        external_axons=external,
        recurrent_axons=recurrent,
    )
    return PhaseBVectorCase(
        name=f"random_{case_index:02d}",
        neuron_count=neuron_count,
        storage=storage,
        external_axons=external,
        recurrent_axons=recurrent,
        expected_accumulators=result.accumulators,
    )


def m11_5_3_cases() -> tuple[PhaseBVectorCase, ...]:
    rng = _SplitMix64(M11_5_3_SEED)
    return (_directed_case(),) + tuple(
        _random_case(rng, index) for index in range(M11_5_3_CASE_COUNT - 1)
    )


def _hex(value: int, width: int) -> str:
    mask = (1 << width) - 1
    return f"{value & mask:0{(width + 3) // 4}x}"


def write_systemverilog_include(output: Path) -> Path:
    cases = m11_5_3_cases()
    lines = [
        "// Generated by examples/generate_m11_5_3_vectors.py; do not edit.",
        f"localparam int M11_5_3_CASE_COUNT = {len(cases)};",
        f"localparam logic [31:0] M11_5_3_SEED = 32'h{M11_5_3_SEED:08x};",
        f"localparam int M11_5_3_MAX_NEURONS = {M11_5_3_MAX_NEURONS};",
        f"localparam int M11_5_3_MAX_AXONS = {M11_5_3_MAX_AXONS};",
        f"localparam int M11_5_3_MAX_SYNAPSES = {M11_5_3_MAX_SYNAPSES};",
        f"localparam int M11_5_3_MAX_FORMATS = {M11_5_3_MAX_FORMATS};",
        f"localparam int M11_5_3_MAX_EXTERNAL_EVENTS = {M11_5_3_MAX_EXTERNAL_EVENTS};",
        f"localparam int M11_5_3_MAX_RECURRENT_EVENTS = {M11_5_3_MAX_RECURRENT_EVENTS};",
        "",
    ]

    def emit_counts(name: str, width: int, values: list[int]) -> None:
        lines.append(f"localparam logic [{width - 1}:0] {name} [0:M11_5_3_CASE_COUNT-1] = '{{")
        for index, value in enumerate(values):
            comma = "," if index + 1 != len(values) else ""
            lines.append(f"    {width}'d{value}{comma} // {cases[index].name}")
        lines.append("};")
        lines.append("")

    emit_counts("M11_5_3_NEURON_COUNTS", 9, [case.neuron_count for case in cases])
    emit_counts("M11_5_3_AXON_COUNTS", 11, [case.storage.axon_count for case in cases])
    emit_counts("M11_5_3_SYNAPSE_COUNTS", 13, [case.storage.synapse_count for case in cases])
    emit_counts("M11_5_3_FORMAT_COUNTS", 5, [case.storage.format_count for case in cases])
    emit_counts("M11_5_3_EXTERNAL_COUNTS", 13, [len(case.external_axons) for case in cases])
    emit_counts("M11_5_3_RECURRENT_COUNTS", 13, [len(case.recurrent_axons) for case in cases])

    def emit_flat(name: str, width: int, per_case: int, rows: list[tuple[int, ...]], signed: bool = False) -> None:
        sign = " signed" if signed else ""
        total = len(rows) * per_case
        lines.append(f"localparam logic{sign} [{width - 1}:0] {name} [0:{total - 1}] = '{{")
        emitted = 0
        for case_index, row in enumerate(rows):
            padded = tuple(row) + (0,) * (per_case - len(row))
            if len(padded) != per_case:
                raise ValueError(f"{name} row exceeds fixed generated capacity")
            for local_index, value in enumerate(padded):
                emitted += 1
                comma = "," if emitted != total else ""
                comment = f" // {cases[case_index].name}[{local_index}]" if local_index == 0 else ""
                lines.append(f"    {width}'h{_hex(value, width)}{comma}{comment}")
        lines.append("};")
        lines.append("")

    emit_flat(
        "M11_5_3_FORMAT_WORDS",
        16,
        M11_5_3_MAX_FORMATS,
        [case.storage.format_words for case in cases],
    )
    emit_flat(
        "M11_5_3_SYNAPSE_WORDS",
        32,
        M11_5_3_MAX_SYNAPSES,
        [case.storage.synapse_words for case in cases],
    )
    emit_flat(
        "M11_5_3_ROW_POINTERS",
        32,
        M11_5_3_MAX_AXONS + 1,
        [case.storage.axon_row_pointers for case in cases],
    )
    emit_flat(
        "M11_5_3_EXTERNAL_EVENTS",
        16,
        M11_5_3_MAX_EXTERNAL_EVENTS,
        [case.external_axons for case in cases],
    )
    emit_flat(
        "M11_5_3_RECURRENT_EVENTS",
        16,
        M11_5_3_MAX_RECURRENT_EVENTS,
        [case.recurrent_axons for case in cases],
    )
    emit_flat(
        "M11_5_3_EXPECTED_ACCUMULATORS",
        64,
        M11_5_3_MAX_NEURONS,
        [case.expected_accumulators for case in cases],
        signed=True,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = write_systemverilog_include(args.output)
    cases = m11_5_3_cases()
    total_synapses = sum(case.storage.synapse_count for case in cases)
    total_events = sum(len(case.external_axons) + len(case.recurrent_axons) for case in cases)
    print(
        "M11.5.3 differential vectors generated: "
        f"cases={len(cases)}, seed=0x{M11_5_3_SEED:08X}, "
        f"stored_synapses={total_synapses}, events={total_events}"
    )
    print(f"output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
