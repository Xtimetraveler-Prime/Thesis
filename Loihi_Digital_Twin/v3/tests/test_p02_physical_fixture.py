from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

from loihi_twin_v2.ddr_abi import (
    P02_DDR_BANK_LAYOUT,
    P02_DDR_CONTEXT_STRIDE_BYTES,
    P02_DDR_PAYLOAD_END,
    P02_DDR_PAYLOAD_START,
    parse_ddr_context_header,
)


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p02_4_fixture.py"
SPEC = importlib.util.spec_from_file_location("p02_4_fixture", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture)


def test_p02_4_fixture_contract_matches_accepted_ddr_abi() -> None:
    assert fixture.RECORD_BYTES == P02_DDR_CONTEXT_STRIDE_BYTES
    assert fixture.PAYLOAD_START == P02_DDR_PAYLOAD_START
    assert fixture.PAYLOAD_END == P02_DDR_PAYLOAD_END
    assert fixture.BANKS == tuple(
        (bank.name, bank.offset, bank.word_bytes, bank.depth)
        for bank in P02_DDR_BANK_LAYOUT
    )
    assert fixture.FULL_TRANSFER_BYTES == 0x6B000
    assert fixture.MUTABLE_TRANSFER_BYTES == 0x1A000


def test_p02_4_fixture_records_are_valid_and_addressed_safely() -> None:
    source = fixture.build_record(fixture.SOURCE_CORE_ID, "source")
    full = fixture.build_record(fixture.FULL_SCRATCH_CORE_ID, "full")
    mutable = fixture.build_record(fixture.MUTABLE_SCRATCH_CORE_ID, "mutable")

    assert parse_ddr_context_header(source).logical_core_id == 0
    assert parse_ddr_context_header(full).logical_core_id == 126
    assert parse_ddr_context_header(mutable).logical_core_id == 127

    assert fixture.record_address(0) == 0x40000000
    assert fixture.record_address(126) == 0x43F00000
    assert fixture.record_address(127) == 0x43F80000
    assert fixture.record_address(127) + fixture.RECORD_BYTES == 0x44000000


def test_p02_4_full_expected_replaces_payload_only() -> None:
    source = fixture.build_record(0, "source")
    destination = fixture.build_record(126, "destination")
    expected = fixture.expected_page_out(source, destination, mutable_only=False)

    assert expected[: fixture.PAYLOAD_START] == destination[: fixture.PAYLOAD_START]
    assert expected[fixture.PAYLOAD_START : fixture.PAYLOAD_END] == source[
        fixture.PAYLOAD_START : fixture.PAYLOAD_END
    ]
    assert expected[fixture.PAYLOAD_END :] == destination[fixture.PAYLOAD_END :]


def test_p02_4_mutable_expected_replaces_only_mutable_banks() -> None:
    source = fixture.build_record(0, "source")
    destination = fixture.build_record(127, "destination")
    expected = fixture.expected_page_out(source, destination, mutable_only=True)

    for name, offset, word_bytes, depth in fixture.BANKS:
        size = word_bytes * depth
        expected_bank = expected[offset : offset + size]
        if name in fixture.MUTABLE_BANKS:
            assert expected_bank == source[offset : offset + size]
        else:
            assert expected_bank == destination[offset : offset + size]


def test_p02_4_fixture_write_and_verify_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest = fixture.write_fixture_set(root)

        assert manifest["addresses"]["source"] == "0x40000000"
        assert (root / fixture.FILES["source"]).stat().st_size == fixture.RECORD_BYTES

        result = fixture.verify_dump_set(
            root,
            root / fixture.FILES["source"],
            root / fixture.FILES["full_expected"],
            root / fixture.FILES["mutable_expected"],
        )
        assert set(result) == {
            "source_provision",
            "full_roundtrip",
            "mutable_roundtrip",
        }
