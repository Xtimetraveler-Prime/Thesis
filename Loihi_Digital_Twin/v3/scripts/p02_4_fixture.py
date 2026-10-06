#!/usr/bin/env python3
"""Generate and verify deterministic P02.4 physical DDR paging fixtures.

This is transport acceptance tooling, not a Loihi workload.  Payload words are
deliberately high-entropy deterministic bytes so bank/address/width mistakes are
unlikely to alias into a false pass.

The PL page walker does not copy the 4 KiB record header or reserved tail.
Therefore expected page-out records preserve the destination header/tail while
replacing exactly the banks selected by the page command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ABI_MAGIC = b"LTV3CTX1"
ABI_VERSION = 1
HEADER_BYTES = 0x1000
RECORD_BYTES = 0x80000
HEADER_HASH_OFFSET = 0x40
HEADER_HASH_BYTES = 32
PAYLOAD_START = 0x01000
PAYLOAD_END = 0x6C000

BACKING_BASE = 0x40000000
SOURCE_CORE_ID = 0
FULL_SCRATCH_CORE_ID = 126
MUTABLE_SCRATCH_CORE_ID = 127

BANKS = (
    ("config", 0x01000, 16, 1024),
    ("state", 0x05000, 8, 1024),
    ("axon", 0x07000, 8, 4096),
    ("synapse", 0x0F000, 8, 32768),
    ("route_descriptor", 0x4F000, 4, 1024),
    ("route", 0x50000, 4, 4096),
    ("event0", 0x54000, 4, 4096),
    ("event1", 0x58000, 4, 4096),
    ("trace", 0x5C000, 32, 1024),
    ("packet", 0x64000, 8, 4096),
)
MUTABLE_BANKS = frozenset(("state", "event0", "event1", "trace", "packet"))

FULL_TRANSFER_BYTES = sum(word_bytes * depth for _, _, word_bytes, depth in BANKS)
MUTABLE_TRANSFER_BYTES = sum(
    word_bytes * depth
    for name, _, word_bytes, depth in BANKS
    if name in MUTABLE_BANKS
)

FILES = {
    "source": "source_core0.bin",
    "full_initial": "full_scratch_core126.bin",
    "mutable_initial": "mutable_scratch_core127.bin",
    "full_expected": "full_expected_core126.bin",
    "mutable_expected": "mutable_expected_core127.bin",
    "manifest": "manifest.json",
}


def record_address(logical_core_id: int) -> int:
    if not 0 <= logical_core_id < 128:
        raise ValueError("logical_core_id must be in [0, 127]")
    return BACKING_BASE + logical_core_id * RECORD_BYTES


def _bank_bytes(name: str, label: str, size: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < size:
        seed = f"LTV3-P02.4:{label}:{name}:{counter}".encode("ascii")
        out.extend(hashlib.sha256(seed).digest())
        counter += 1
    return bytes(out[:size])


def _payload_sha(record: bytes | bytearray) -> bytes:
    return hashlib.sha256(record[PAYLOAD_START:PAYLOAD_END]).digest()


def build_record(logical_core_id: int, label: str) -> bytes:
    record = bytearray(RECORD_BYTES)
    for name, offset, word_bytes, depth in BANKS:
        size = word_bytes * depth
        record[offset : offset + size] = _bank_bytes(name, label, size)

    # Resource/event counts are zero because these are transport-only fixtures.
    struct.pack_into(
        "<8s12I",
        record,
        0,
        ABI_MAGIC,
        ABI_VERSION,
        HEADER_BYTES,
        RECORD_BYTES,
        logical_core_id,
        0,  # flags
        0,  # current_event_bank
        0,  # compartment_count
        0,  # synapse_count
        0,  # route_count
        0,  # event0_count
        0,  # event1_count
        0,  # packet_count
    )
    record[HEADER_HASH_OFFSET : HEADER_HASH_OFFSET + HEADER_HASH_BYTES] = _payload_sha(record)
    return bytes(record)


def expected_page_out(source: bytes, destination: bytes, *, mutable_only: bool) -> bytes:
    if len(source) != RECORD_BYTES or len(destination) != RECORD_BYTES:
        raise ValueError("P02.4 records must be exactly 512 KiB")
    out = bytearray(destination)
    for name, offset, word_bytes, depth in BANKS:
        if mutable_only and name not in MUTABLE_BANKS:
            continue
        size = word_bytes * depth
        out[offset : offset + size] = source[offset : offset + size]
    # Header and reserved tail deliberately remain the destination's bytes.
    return bytes(out)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bank_hashes(record: bytes) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name, offset, word_bytes, depth in BANKS:
        size = word_bytes * depth
        hashes[name] = sha256_hex(record[offset : offset + size])
    return hashes


def write_fixture_set(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)

    source = build_record(SOURCE_CORE_ID, "source")
    full_initial = build_record(FULL_SCRATCH_CORE_ID, "full-scratch")
    mutable_initial = build_record(MUTABLE_SCRATCH_CORE_ID, "mutable-scratch")
    full_expected = expected_page_out(source, full_initial, mutable_only=False)
    mutable_expected = expected_page_out(source, mutable_initial, mutable_only=True)

    blobs = {
        "source": source,
        "full_initial": full_initial,
        "mutable_initial": mutable_initial,
        "full_expected": full_expected,
        "mutable_expected": mutable_expected,
    }
    for key, data in blobs.items():
        (output_dir / FILES[key]).write_bytes(data)

    manifest: dict[str, object] = {
        "abi": {
            "record_bytes": RECORD_BYTES,
            "payload_start": PAYLOAD_START,
            "payload_end": PAYLOAD_END,
            "full_transfer_bytes": FULL_TRANSFER_BYTES,
            "mutable_transfer_bytes": MUTABLE_TRANSFER_BYTES,
        },
        "addresses": {
            "source": f"0x{record_address(SOURCE_CORE_ID):08X}",
            "full_scratch": f"0x{record_address(FULL_SCRATCH_CORE_ID):08X}",
            "mutable_scratch": f"0x{record_address(MUTABLE_SCRATCH_CORE_ID):08X}",
        },
        "files": FILES,
        "sha256": {key: sha256_hex(data) for key, data in blobs.items()},
        "payload_sha256": {key: sha256_hex(data[PAYLOAD_START:PAYLOAD_END]) for key, data in blobs.items()},
        "bank_sha256": {key: _bank_hashes(data) for key, data in blobs.items()},
    }
    (output_dir / FILES["manifest"]).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _first_difference(actual: bytes, expected: bytes) -> tuple[int, int, int] | None:
    for index, (a, e) in enumerate(zip(actual, expected)):
        if a != e:
            return index, a, e
    if len(actual) != len(expected):
        return min(len(actual), len(expected)), -1, -1
    return None


def _verify_one(label: str, actual_path: Path, expected_path: Path) -> dict[str, object]:
    actual = actual_path.read_bytes()
    expected = expected_path.read_bytes()
    if len(actual) != RECORD_BYTES:
        raise ValueError(f"{label}: dump is {len(actual)} bytes, expected {RECORD_BYTES}")
    diff = _first_difference(actual, expected)
    if diff is not None:
        offset, actual_byte, expected_byte = diff
        bank = "header-or-reserved"
        for name, start, word_bytes, depth in BANKS:
            end = start + word_bytes * depth
            if start <= offset < end:
                bank = name
                break
        raise ValueError(
            f"{label}: first mismatch at 0x{offset:05X} ({bank}); "
            f"actual=0x{actual_byte & 0xFF:02X} expected=0x{expected_byte & 0xFF:02X}"
        )
    return {
        "record_sha256": sha256_hex(actual),
        "payload_sha256": sha256_hex(actual[PAYLOAD_START:PAYLOAD_END]),
        "bank_sha256": _bank_hashes(actual),
    }


def verify_dump_set(
    fixture_dir: Path,
    source_dump: Path,
    full_dump: Path,
    mutable_dump: Path,
) -> dict[str, object]:
    return {
        "source_provision": _verify_one(
            "source_provision", source_dump, fixture_dir / FILES["source"]
        ),
        "full_roundtrip": _verify_one(
            "full_roundtrip", full_dump, fixture_dir / FILES["full_expected"]
        ),
        "mutable_roundtrip": _verify_one(
            "mutable_roundtrip", mutable_dump, fixture_dir / FILES["mutable_expected"]
        ),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate")
    gen.add_argument("--output-dir", type=Path, required=True)

    verify = sub.add_parser("verify")
    verify.add_argument("--fixture-dir", type=Path, required=True)
    verify.add_argument("--source-dump", type=Path, required=True)
    verify.add_argument("--full-dump", type=Path, required=True)
    verify.add_argument("--mutable-dump", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        if args.command == "generate":
            manifest = write_fixture_set(args.output_dir)
            print(json.dumps(manifest, indent=2, sort_keys=True))
            print("PASS: P02.4 deterministic DDR fixture generated")
            return 0

        result = verify_dump_set(
            args.fixture_dir,
            args.source_dump,
            args.full_dump,
            args.mutable_dump,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        print("PASS: P02.4 physical DDR round-trip dumps match expected records")
        return 0
    except (OSError, ValueError) as exc:
        print(f"FAIL: P02.4 fixture verification: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
