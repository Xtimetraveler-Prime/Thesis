"""Frozen FPGA-oriented storage for validated Loihi-style static weights.

Storage profile v1 separates shared weight formats from per-synapse records.
All bit positions are constants so software, testbenches, RTL, and host tools use
one contract. Reserved bits must be zero and are available only to a future
schema version.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .model import Synapse
from .weights import WeightFormat, WeightSignMode

FPGA_WEIGHT_STORAGE_SCHEMA = "neuromorphic-twin-fpga-weight-storage-v1"

FORMAT_WORD_BITS = 16
FORMAT_EXPONENT_SHIFT = 0
FORMAT_EXPONENT_BITS = 4
FORMAT_NUM_WEIGHT_BITS_SHIFT = 4
FORMAT_NUM_WEIGHT_BITS_BITS = 4
FORMAT_SIGN_MODE_SHIFT = 8
FORMAT_SIGN_MODE_BITS = 2
FORMAT_USED_BITS = 10
FORMAT_RESERVED_MASK = (
    ((1 << FORMAT_WORD_BITS) - 1) ^ ((1 << FORMAT_USED_BITS) - 1)
)

SYNAPSE_WORD_BITS = 32
SYNAPSE_MANTISSA_SHIFT = 0
SYNAPSE_MANTISSA_BITS = 9
SYNAPSE_FORMAT_INDEX_SHIFT = 9
SYNAPSE_FORMAT_INDEX_BITS = 4
SYNAPSE_TARGET_SHIFT = 13
SYNAPSE_TARGET_BITS = 16
SYNAPSE_USED_BITS = 29
SYNAPSE_RESERVED_MASK = (
    ((1 << SYNAPSE_WORD_BITS) - 1) ^ ((1 << SYNAPSE_USED_BITS) - 1)
)

AXON_ID_BITS = 16
AXON_ROW_POINTER_BITS = 32
MAX_WEIGHT_FORMATS = 1 << SYNAPSE_FORMAT_INDEX_BITS
MAX_AXON_ID = (1 << AXON_ID_BITS) - 1
MAX_TARGET_NEURON = (1 << SYNAPSE_TARGET_BITS) - 1
MAX_SYNAPSES = (1 << AXON_ROW_POINTER_BITS) - 1

INLINE_SYNAPSE_WORD_BITS = 36
BRAM36_CAPACITY_BITS = 36 * 1024

_SIGN_MODE_TO_CODE = {
    WeightSignMode.MIXED: 0b00,
    WeightSignMode.EXCITATORY: 0b01,
    WeightSignMode.INHIBITORY: 0b10,
}
_CODE_TO_SIGN_MODE = {
    code: mode for mode, code in _SIGN_MODE_TO_CODE.items()
}


@dataclass(frozen=True, slots=True)
class PackedSynapseFields:
    """Decoded fields of one 32-bit synapse word."""

    target_neuron: int
    requested_mantissa: int
    format_index: int


@dataclass(frozen=True, slots=True)
class WeightStorageEstimate:
    """Logical capacity estimate for shared-format and inline-format layouts.

    BRAM counts are capacity-only lower bounds. Device width/depth modes,
    banking, parity use, and routing can require additional physical blocks.
    """

    synapse_count: int
    unique_format_count: int
    axon_count: int
    shared_weight_bits: int
    inline_weight_bits: int
    row_pointer_bits: int
    shared_total_bits: int
    inline_total_bits: int
    saved_bits: int
    shared_bram36_lower_bound: int
    inline_bram36_lower_bound: int

    @property
    def savings_fraction(self) -> float:
        if self.inline_total_bits == 0:
            return 0.0
        return self.saved_bits / self.inline_total_bits


@dataclass(frozen=True, slots=True)
class WeightStorageArtifacts:
    """Paths written for direct host or HDL testbench loading."""

    manifest: Path
    formats: Path
    synapses: Path
    axon_rows: Path


@dataclass(frozen=True, slots=True)
class FrozenWeightStorage:
    """Complete v1 weight-memory image.

    ``axon_row_pointers`` is a CSR-style table. For axon ``a``, records occupy
    ``synapse_words[row[a]:row[a + 1]]``. Therefore an axon ID is not repeated
    in every 32-bit synapse word.
    """

    format_words: tuple[int, ...]
    synapse_words: tuple[int, ...]
    axon_row_pointers: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.format_words) > MAX_WEIGHT_FORMATS:
            raise ValueError(
                f"at most {MAX_WEIGHT_FORMATS} weight formats are supported"
            )
        if len(self.synapse_words) > MAX_SYNAPSES:
            raise ValueError(f"at most {MAX_SYNAPSES} synapses are supported")
        if not self.axon_row_pointers:
            raise ValueError(
                "axon_row_pointers must contain at least the terminal zero"
            )
        if self.axon_count > MAX_AXON_ID + 1:
            raise ValueError(
                f"at most {MAX_AXON_ID + 1} axons are supported"
            )

        formats = tuple(
            unpack_weight_format(word) for word in self.format_words
        )
        for word in self.synapse_words:
            fields = unpack_synapse_word(word)
            if fields.format_index >= len(formats):
                raise ValueError(
                    "synapse format index is outside the format table"
                )
            low, high = formats[fields.format_index].mantissa_bounds
            if not low <= fields.requested_mantissa <= high:
                raise ValueError(
                    "synapse mantissa is invalid for its referenced weight format"
                )

        pointers = self.axon_row_pointers
        if pointers[0] != 0:
            raise ValueError("the first axon row pointer must be zero")
        if any(
            isinstance(pointer, bool) or not isinstance(pointer, int)
            for pointer in pointers
        ):
            raise TypeError("axon row pointers must be ints")
        if any(
            pointer < 0 or pointer > len(self.synapse_words)
            for pointer in pointers
        ):
            raise ValueError(
                "axon row pointer is outside the synapse table"
            )
        if any(
            left > right for left, right in zip(pointers, pointers[1:])
        ):
            raise ValueError("axon row pointers must be monotonic")
        if pointers[-1] != len(self.synapse_words):
            raise ValueError(
                "the terminal axon row pointer must equal synapse_count"
            )

    @property
    def format_count(self) -> int:
        return len(self.format_words)

    @property
    def synapse_count(self) -> int:
        return len(self.synapse_words)

    @property
    def axon_count(self) -> int:
        return len(self.axon_row_pointers) - 1

    def decode_synapses(self) -> tuple[Synapse, ...]:
        """Reconstruct encoded synapses in deterministic axon-row order."""

        formats = tuple(
            unpack_weight_format(word) for word in self.format_words
        )
        decoded: list[Synapse] = []
        for axon_id in range(self.axon_count):
            start = self.axon_row_pointers[axon_id]
            stop = self.axon_row_pointers[axon_id + 1]
            for word in self.synapse_words[start:stop]:
                fields = unpack_synapse_word(word)
                decoded.append(
                    Synapse.encoded(
                        axon_id=axon_id,
                        target_neuron=fields.target_neuron,
                        mantissa=fields.requested_mantissa,
                        weight_format=formats[fields.format_index],
                    )
                )
        return tuple(decoded)

    def estimate(self) -> "WeightStorageEstimate":
        return estimate_weight_storage(
            synapse_count=self.synapse_count,
            unique_format_count=self.format_count,
            axon_count=self.axon_count,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": FPGA_WEIGHT_STORAGE_SCHEMA,
            "word_widths": {
                "format": FORMAT_WORD_BITS,
                "synapse": SYNAPSE_WORD_BITS,
                "axon_row_pointer": AXON_ROW_POINTER_BITS,
            },
            "counts": {
                "formats": self.format_count,
                "synapses": self.synapse_count,
                "axons": self.axon_count,
            },
            "format_words": [
                f"0x{word:04x}" for word in self.format_words
            ],
            "synapse_words": [
                f"0x{word:08x}" for word in self.synapse_words
            ],
            "axon_row_pointers": [
                f"0x{pointer:08x}" for pointer in self.axon_row_pointers
            ],
        }

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
    ) -> "FrozenWeightStorage":
        if payload.get("schema") != FPGA_WEIGHT_STORAGE_SCHEMA:
            raise ValueError("unsupported FPGA weight-storage schema")
        widths = payload.get("word_widths")
        expected_widths = {
            "format": FORMAT_WORD_BITS,
            "synapse": SYNAPSE_WORD_BITS,
            "axon_row_pointer": AXON_ROW_POINTER_BITS,
        }
        if widths != expected_widths:
            raise ValueError(
                "weight-storage word widths do not match schema v1"
            )

        storage = cls(
            format_words=tuple(
                _parse_word(value) for value in payload["format_words"]
            ),
            synapse_words=tuple(
                _parse_word(value) for value in payload["synapse_words"]
            ),
            axon_row_pointers=tuple(
                _parse_word(value)
                for value in payload["axon_row_pointers"]
            ),
        )
        counts = payload.get("counts")
        expected_counts = {
            "formats": storage.format_count,
            "synapses": storage.synapse_count,
            "axons": storage.axon_count,
        }
        if counts != expected_counts:
            raise ValueError(
                "weight-storage counts do not match word arrays"
            )
        return storage


def pack_weight_format(weight_format: WeightFormat) -> int:
    """Pack one format into the frozen 16-bit format word."""

    if not isinstance(weight_format, WeightFormat):
        raise TypeError("weight_format must be a WeightFormat")
    exponent = _encode_twos_complement(
        weight_format.exponent,
        FORMAT_EXPONENT_BITS,
    )
    sign_mode = _SIGN_MODE_TO_CODE[weight_format.sign_mode]
    return (
        (exponent << FORMAT_EXPONENT_SHIFT)
        | (weight_format.num_weight_bits << FORMAT_NUM_WEIGHT_BITS_SHIFT)
        | (sign_mode << FORMAT_SIGN_MODE_SHIFT)
    )


def unpack_weight_format(word: int) -> WeightFormat:
    """Decode one v1 format word and reject nonzero reserved bits."""

    _require_word("format word", word, FORMAT_WORD_BITS)
    if word & FORMAT_RESERVED_MASK:
        raise ValueError("format word has nonzero reserved bits")

    sign_code = (
        word >> FORMAT_SIGN_MODE_SHIFT
    ) & _mask(FORMAT_SIGN_MODE_BITS)
    try:
        sign_mode = _CODE_TO_SIGN_MODE[sign_code]
    except KeyError as exc:
        raise ValueError(
            "format word uses reserved sign-mode code 0b11"
        ) from exc

    exponent_raw = (
        word >> FORMAT_EXPONENT_SHIFT
    ) & _mask(FORMAT_EXPONENT_BITS)
    num_weight_bits = (
        word >> FORMAT_NUM_WEIGHT_BITS_SHIFT
    ) & _mask(FORMAT_NUM_WEIGHT_BITS_BITS)
    try:
        return WeightFormat(
            exponent=_decode_twos_complement(
                exponent_raw,
                FORMAT_EXPONENT_BITS,
            ),
            num_weight_bits=num_weight_bits,
            sign_mode=sign_mode,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid packed weight format: {exc}") from exc


def pack_synapse_word(
    *,
    target_neuron: int,
    requested_mantissa: int,
    format_index: int,
) -> int:
    """Pack routing, source mantissa, and format reference into 32 bits."""

    _require_range(
        "target_neuron",
        target_neuron,
        0,
        MAX_TARGET_NEURON,
    )
    _require_range(
        "requested_mantissa",
        requested_mantissa,
        -256,
        255,
    )
    _require_range(
        "format_index",
        format_index,
        0,
        MAX_WEIGHT_FORMATS - 1,
    )
    mantissa = _encode_twos_complement(
        requested_mantissa,
        SYNAPSE_MANTISSA_BITS,
    )
    return (
        (mantissa << SYNAPSE_MANTISSA_SHIFT)
        | (format_index << SYNAPSE_FORMAT_INDEX_SHIFT)
        | (target_neuron << SYNAPSE_TARGET_SHIFT)
    )


def unpack_synapse_word(word: int) -> PackedSynapseFields:
    """Decode one v1 synapse word and reject nonzero reserved bits."""

    _require_word("synapse word", word, SYNAPSE_WORD_BITS)
    if word & SYNAPSE_RESERVED_MASK:
        raise ValueError("synapse word has nonzero reserved bits")

    mantissa_raw = (
        word >> SYNAPSE_MANTISSA_SHIFT
    ) & _mask(SYNAPSE_MANTISSA_BITS)
    format_index = (
        word >> SYNAPSE_FORMAT_INDEX_SHIFT
    ) & _mask(SYNAPSE_FORMAT_INDEX_BITS)
    target_neuron = (
        word >> SYNAPSE_TARGET_SHIFT
    ) & _mask(SYNAPSE_TARGET_BITS)
    return PackedSynapseFields(
        target_neuron=target_neuron,
        requested_mantissa=_decode_twos_complement(
            mantissa_raw,
            SYNAPSE_MANTISSA_BITS,
        ),
        format_index=format_index,
    )


def freeze_encoded_synapses(
    synapses: Iterable[Synapse],
) -> FrozenWeightStorage:
    """Freeze encoded synapses into a shared-format CSR memory image.

    Formats are assigned indices by first appearance. Synapse words are stored
    by ascending axon ID while preserving input order within each axon row.
    Legacy integer-only synapses are rejected because their requested mantissa
    and format cannot always be reconstructed uniquely.
    """

    source = tuple(synapses)
    format_indices: dict[WeightFormat, int] = {}
    formats: list[WeightFormat] = []
    indexed_records: list[tuple[int, int, Synapse, int]] = []

    for source_index, synapse in enumerate(source):
        if not isinstance(synapse, Synapse):
            raise TypeError(
                "synapses must contain only Synapse objects"
            )
        if synapse.encoding is None:
            raise ValueError(
                "FPGA weight storage requires encoded synapses"
            )
        _require_range("axon_id", synapse.axon_id, 0, MAX_AXON_ID)
        _require_range(
            "target_neuron",
            synapse.target_neuron,
            0,
            MAX_TARGET_NEURON,
        )
        fmt = synapse.encoding.weight_format
        if fmt not in format_indices:
            if len(formats) == MAX_WEIGHT_FORMATS:
                raise ValueError(
                    "storage profile v1 supports at most "
                    f"{MAX_WEIGHT_FORMATS} formats"
                )
            format_indices[fmt] = len(formats)
            formats.append(fmt)
        indexed_records.append(
            (
                synapse.axon_id,
                source_index,
                synapse,
                format_indices[fmt],
            )
        )

    indexed_records.sort(key=lambda item: (item[0], item[1]))
    synapse_words = tuple(
        pack_synapse_word(
            target_neuron=synapse.target_neuron,
            requested_mantissa=synapse.encoding.requested_mantissa,
            format_index=format_index,
        )
        for _, _, synapse, format_index in indexed_records
        if synapse.encoding is not None
    )

    axon_count = max(
        (synapse.axon_id for synapse in source),
        default=-1,
    ) + 1
    counts = [0] * axon_count
    for synapse in source:
        counts[synapse.axon_id] += 1
    row_pointers = [0]
    for count in counts:
        row_pointers.append(row_pointers[-1] + count)

    return FrozenWeightStorage(
        format_words=tuple(
            pack_weight_format(fmt) for fmt in formats
        ),
        synapse_words=synapse_words,
        axon_row_pointers=tuple(row_pointers),
    )


def estimate_weight_storage(
    *,
    synapse_count: int,
    unique_format_count: int,
    axon_count: int,
) -> WeightStorageEstimate:
    """Compare v1 shared-format storage with a 36-bit inline-format record."""

    _require_range(
        "synapse_count",
        synapse_count,
        0,
        MAX_SYNAPSES,
    )
    _require_range(
        "unique_format_count",
        unique_format_count,
        0,
        MAX_WEIGHT_FORMATS,
    )
    _require_range(
        "axon_count",
        axon_count,
        0,
        MAX_AXON_ID + 1,
    )
    if synapse_count and unique_format_count == 0:
        raise ValueError(
            "nonempty storage requires at least one format"
        )

    shared_weight_bits = (
        synapse_count * SYNAPSE_WORD_BITS
        + unique_format_count * FORMAT_WORD_BITS
    )
    inline_weight_bits = synapse_count * INLINE_SYNAPSE_WORD_BITS
    row_pointer_bits = (axon_count + 1) * AXON_ROW_POINTER_BITS
    shared_total_bits = shared_weight_bits + row_pointer_bits
    inline_total_bits = inline_weight_bits + row_pointer_bits
    saved_bits = inline_total_bits - shared_total_bits
    return WeightStorageEstimate(
        synapse_count=synapse_count,
        unique_format_count=unique_format_count,
        axon_count=axon_count,
        shared_weight_bits=shared_weight_bits,
        inline_weight_bits=inline_weight_bits,
        row_pointer_bits=row_pointer_bits,
        shared_total_bits=shared_total_bits,
        inline_total_bits=inline_total_bits,
        saved_bits=saved_bits,
        shared_bram36_lower_bound=_ceil_div(
            shared_total_bits,
            BRAM36_CAPACITY_BITS,
        ),
        inline_bram36_lower_bound=_ceil_div(
            inline_total_bits,
            BRAM36_CAPACITY_BITS,
        ),
    )


def write_weight_storage_image(
    storage: FrozenWeightStorage,
    directory: str | Path,
) -> WeightStorageArtifacts:
    """Write a manifest plus one fixed-width hexadecimal word per line."""

    if not isinstance(storage, FrozenWeightStorage):
        raise TypeError("storage must be a FrozenWeightStorage")
    output = Path(directory)
    output.mkdir(parents=True, exist_ok=True)
    formats = output / "weight_formats.mem"
    synapses = output / "weight_synapses.mem"
    axon_rows = output / "weight_axon_rows.mem"
    manifest = output / "weight_storage.json"

    _write_hex_words(
        formats,
        storage.format_words,
        FORMAT_WORD_BITS,
    )
    _write_hex_words(
        synapses,
        storage.synapse_words,
        SYNAPSE_WORD_BITS,
    )
    _write_hex_words(
        axon_rows,
        storage.axon_row_pointers,
        AXON_ROW_POINTER_BITS,
    )
    manifest.write_text(
        json.dumps(storage.to_payload(), indent=2) + "\n",
        encoding="utf-8",
    )
    return WeightStorageArtifacts(
        manifest=manifest,
        formats=formats,
        synapses=synapses,
        axon_rows=axon_rows,
    )


def read_weight_storage_json(
    path: str | Path,
) -> FrozenWeightStorage:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(
            "weight-storage JSON root must be an object"
        )
    return FrozenWeightStorage.from_payload(payload)


def _write_hex_words(
    path: Path,
    words: tuple[int, ...],
    width_bits: int,
) -> None:
    digits = _ceil_div(width_bits, 4)
    text = "".join(
        f"{word:0{digits}x}\n" for word in words
    )
    path.write_text(text, encoding="ascii")


def _parse_word(value: object) -> int:
    if isinstance(value, bool):
        raise TypeError("packed words cannot be bools")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise TypeError(
        "packed words must be ints or base-prefixed strings"
    )


def _encode_twos_complement(value: int, bits: int) -> int:
    low = -(1 << (bits - 1))
    high = (1 << (bits - 1)) - 1
    _require_range("signed value", value, low, high)
    return value & _mask(bits)


def _decode_twos_complement(value: int, bits: int) -> int:
    sign_bit = 1 << (bits - 1)
    return value - (1 << bits) if value & sign_bit else value


def _require_word(name: str, value: object, bits: int) -> None:
    _require_range(name, value, 0, _mask(bits))


def _require_range(
    name: str,
    value: object,
    low: int,
    high: int,
) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if not low <= value <= high:
        raise ValueError(f"{name} must be in {low}..{high}")


def _mask(bits: int) -> int:
    return (1 << bits) - 1


def _ceil_div(value: int, divisor: int) -> int:
    return (value + divisor - 1) // divisor
