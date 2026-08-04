import json

import pytest

from neuromorphic_twin import (
    Synapse,
    WeightFormat,
    WeightSignMode,
    encode_static_weight,
)
from neuromorphic_twin.fpga_weight_storage import (
    FORMAT_RESERVED_MASK,
    MAX_WEIGHT_FORMATS,
    SYNAPSE_RESERVED_MASK,
    FrozenWeightStorage,
    estimate_weight_storage,
    freeze_encoded_synapses,
    pack_synapse_word,
    pack_weight_format,
    read_weight_storage_json,
    unpack_synapse_word,
    unpack_weight_format,
    write_weight_storage_image,
)


def test_all_weight_formats_pack_and_unpack_exactly() -> None:
    for exponent in range(-8, 8):
        for bits in range(9):
            for mode in WeightSignMode:
                fmt = WeightFormat(exponent, bits, mode)
                word = pack_weight_format(fmt)
                assert word & FORMAT_RESERVED_MASK == 0
                assert unpack_weight_format(word) == fmt


def test_format_unpack_rejects_reserved_fields() -> None:
    with pytest.raises(ValueError, match="reserved bits"):
        unpack_weight_format(1 << 15)
    with pytest.raises(ValueError, match="sign-mode"):
        unpack_weight_format(0b11 << 8)
    with pytest.raises(ValueError, match="invalid packed"):
        unpack_weight_format(9 << 4)


def test_synapse_word_boundary_round_trip() -> None:
    for target in (0, 65535):
        for mantissa in (-256, -1, 0, 255):
            for format_index in (0, 15):
                word = pack_synapse_word(
                    target_neuron=target,
                    requested_mantissa=mantissa,
                    format_index=format_index,
                )
                assert word & SYNAPSE_RESERVED_MASK == 0
                fields = unpack_synapse_word(word)
                assert fields.target_neuron == target
                assert fields.requested_mantissa == mantissa
                assert fields.format_index == format_index


def test_synapse_word_rejects_invalid_or_reserved_values() -> None:
    with pytest.raises(ValueError):
        pack_synapse_word(
            target_neuron=65536,
            requested_mantissa=0,
            format_index=0,
        )
    with pytest.raises(ValueError):
        pack_synapse_word(
            target_neuron=0,
            requested_mantissa=256,
            format_index=0,
        )
    with pytest.raises(ValueError):
        pack_synapse_word(
            target_neuron=0,
            requested_mantissa=0,
            format_index=16,
        )
    with pytest.raises(ValueError, match="reserved bits"):
        unpack_synapse_word(1 << 31)


def test_freeze_deduplicates_formats_and_builds_csr_rows() -> None:
    fmt_a = WeightFormat()
    fmt_b = WeightFormat(
        exponent=-1,
        sign_mode=WeightSignMode.INHIBITORY,
    )
    source = (
        Synapse.encoded(2, 3, 124, fmt_a),
        Synapse.encoded(0, 1, -1, fmt_b),
        Synapse.encoded(2, 4, 125, fmt_a),
        Synapse.encoded(1, 2, 3, fmt_a),
    )

    storage = freeze_encoded_synapses(source)
    assert storage.format_words == (
        pack_weight_format(fmt_a),
        pack_weight_format(fmt_b),
    )
    assert storage.axon_row_pointers == (0, 1, 2, 4)
    assert [
        unpack_synapse_word(word).format_index
        for word in storage.synapse_words
    ] == [1, 0, 0, 0]

    decoded = storage.decode_synapses()
    assert [
        (synapse.axon_id, synapse.target_neuron)
        for synapse in decoded
    ] == [
        (0, 1),
        (1, 2),
        (2, 3),
        (2, 4),
    ]
    assert [synapse.encoding for synapse in decoded] == [
        source[1].encoding,
        source[3].encoding,
        source[0].encoding,
        source[2].encoding,
    ]


def test_freeze_rejects_legacy_synapses_and_format_overflow() -> None:
    with pytest.raises(ValueError, match="requires encoded"):
        freeze_encoded_synapses([Synapse(0, 0, 64)])

    formats = [
        WeightFormat(
            exponent=-8 + (index // 9),
            num_weight_bits=index % 9,
        )
        for index in range(MAX_WEIGHT_FORMATS + 1)
    ]
    synapses = [
        Synapse.encoded(0, index, 0, fmt)
        for index, fmt in enumerate(formats)
    ]
    with pytest.raises(ValueError, match="at most 16 formats"):
        freeze_encoded_synapses(synapses)


def test_empty_storage_is_valid_and_round_trips() -> None:
    storage = freeze_encoded_synapses([])
    assert storage == FrozenWeightStorage((), (), (0,))
    assert storage.decode_synapses() == ()


def test_all_147456_valid_encodings_survive_pack_unpack_and_reencode() -> None:
    count = 0
    for exponent in range(-8, 8):
        for bits in range(9):
            for mode in WeightSignMode:
                fmt = WeightFormat(exponent, bits, mode)
                decoded_fmt = unpack_weight_format(
                    pack_weight_format(fmt)
                )
                low, high = fmt.mantissa_bounds
                for mantissa in range(low, high + 1):
                    fields = unpack_synapse_word(
                        pack_synapse_word(
                            target_neuron=65535,
                            requested_mantissa=mantissa,
                            format_index=15,
                        )
                    )
                    original = encode_static_weight(mantissa, fmt)
                    reconstructed = encode_static_weight(
                        fields.requested_mantissa,
                        decoded_fmt,
                    )
                    assert reconstructed == original
                    count += 1
    assert count == 147_456


def test_memory_estimate_compares_shared_and_inline_layouts() -> None:
    estimate = estimate_weight_storage(
        synapse_count=1024,
        unique_format_count=16,
        axon_count=256,
    )
    assert estimate.shared_weight_bits == 33_024
    assert estimate.inline_weight_bits == 36_864
    assert estimate.row_pointer_bits == 8_224
    assert estimate.saved_bits == 3_840
    assert estimate.shared_bram36_lower_bound == 2
    assert estimate.inline_bram36_lower_bound == 2

    break_even = estimate_weight_storage(
        synapse_count=64,
        unique_format_count=16,
        axon_count=0,
    )
    assert break_even.saved_bits == 0


def test_json_and_mem_image_round_trip(tmp_path) -> None:
    storage = freeze_encoded_synapses(
        [
            Synapse.encoded(0, 2, 124, WeightFormat()),
            Synapse.encoded(
                2,
                7,
                -127,
                WeightFormat(
                    2,
                    6,
                    WeightSignMode.MIXED,
                ),
            ),
        ]
    )
    artifacts = write_weight_storage_image(storage, tmp_path)
    assert read_weight_storage_json(artifacts.manifest) == storage

    payload = json.loads(
        artifacts.manifest.read_text(encoding="utf-8")
    )
    assert payload["schema"] == (
        "neuromorphic-twin-fpga-weight-storage-v1"
    )
    assert payload["word_widths"] == {
        "format": 16,
        "synapse": 32,
        "axon_row_pointer": 32,
    }
    assert artifacts.formats.read_text().splitlines() == [
        f"{word:04x}" for word in storage.format_words
    ]
    assert artifacts.synapses.read_text().splitlines() == [
        f"{word:08x}" for word in storage.synapse_words
    ]
    assert artifacts.axon_rows.read_text().splitlines() == [
        f"{word:08x}" for word in storage.axon_row_pointers
    ]
