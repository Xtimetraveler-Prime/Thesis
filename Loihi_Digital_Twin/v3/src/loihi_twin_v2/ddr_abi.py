"""FPGA-v3 P02.1 DDR backing-image ABI.

This module defines a deterministic byte layout for one complete logical-core
context in K26 DDR. It is an implementation contract below the accepted
Loihi-like logical architecture; it is not a claim about native Loihi SRAM
layout.

The first ABI uses a fixed 512 KiB record per logical core. A 4 KiB versioned
header is followed by dense images of the ten accepted P05 resident-memory
banks. The remaining tail is reserved and zero-filled so future ABI versions
can grow without changing logical-core-to-DDR address arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct

from .hardware_p03 import OneCoreHardwareImage, SparseWord
from .hardware_p08 import BackingLogicalContextImage
from .resources import MAX_LOGICAL_CORES


P02_DDR_ABI_MAGIC = b"LTV3CTX1"
P02_DDR_ABI_VERSION = 1
P02_DDR_HEADER_BYTES = 0x1000
P02_DDR_CONTEXT_STRIDE_BYTES = 0x80000
P02_DDR_MAX_LOGICAL_CORES = MAX_LOGICAL_CORES
P02_DDR_BACKING_REGION_BYTES = (
    P02_DDR_CONTEXT_STRIDE_BYTES * P02_DDR_MAX_LOGICAL_CORES
)

P02_DDR_HEADER_HASH_OFFSET = 0x40
P02_DDR_HEADER_HASH_BYTES = 32


@dataclass(frozen=True, slots=True)
class DdrBankLayout:
    name: str
    offset: int
    word_bytes: int
    depth: int

    @property
    def size_bytes(self) -> int:
        return self.word_bytes * self.depth

    @property
    def end(self) -> int:
        return self.offset + self.size_bytes


P02_DDR_BANK_LAYOUT = (
    DdrBankLayout("config", 0x01000, 16, 1024),
    DdrBankLayout("state", 0x05000, 8, 1024),
    DdrBankLayout("axon", 0x07000, 8, 4096),
    DdrBankLayout("synapse", 0x0F000, 8, 32768),
    DdrBankLayout("route_descriptor", 0x4F000, 4, 1024),
    DdrBankLayout("route", 0x50000, 4, 4096),
    DdrBankLayout("event0", 0x54000, 4, 4096),
    DdrBankLayout("event1", 0x58000, 4, 4096),
    DdrBankLayout("trace", 0x5C000, 32, 1024),
    DdrBankLayout("packet", 0x64000, 8, 4096),
)
P02_DDR_PAYLOAD_START = P02_DDR_BANK_LAYOUT[0].offset
P02_DDR_PAYLOAD_END = P02_DDR_BANK_LAYOUT[-1].end
P02_DDR_RESERVED_TAIL_BYTES = P02_DDR_CONTEXT_STRIDE_BYTES - P02_DDR_PAYLOAD_END

_BANK_BY_NAME = {bank.name: bank for bank in P02_DDR_BANK_LAYOUT}


@dataclass(frozen=True, slots=True)
class DdrContextHeader:
    version: int
    header_bytes: int
    record_bytes: int
    logical_core_id: int
    flags: int
    current_event_bank: int
    compartment_count: int
    synapse_count: int
    route_count: int
    event0_count: int
    event1_count: int
    packet_count: int
    payload_sha256: str


def _require_uint(name: str, value: int, bits: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if not 0 <= value < (1 << bits):
        raise ValueError(f"{name} must fit unsigned {bits} bits")
    return value


def _bank(name: str) -> DdrBankLayout:
    try:
        return _BANK_BY_NAME[name]
    except KeyError as exc:
        raise KeyError(f"unknown P02 DDR bank {name!r}") from exc


def ddr_context_offset(logical_core_id: int) -> int:
    """Return the byte offset of one logical-core record in the backing region."""

    _require_uint("logical_core_id", logical_core_id, 7)
    if logical_core_id >= P02_DDR_MAX_LOGICAL_CORES:
        raise ValueError("logical_core_id exceeds configured backing-region capacity")
    return logical_core_id * P02_DDR_CONTEXT_STRIDE_BYTES


def ddr_context_address(backing_base: int, logical_core_id: int) -> int:
    """Return an absolute DDR address for one logical-core record."""

    if isinstance(backing_base, bool) or not isinstance(backing_base, int):
        raise TypeError("backing_base must be an int")
    if backing_base < 0:
        raise ValueError("backing_base must be non-negative")
    if backing_base % P02_DDR_CONTEXT_STRIDE_BYTES:
        raise ValueError("backing_base must be 512 KiB aligned")
    return backing_base + ddr_context_offset(logical_core_id)


def ddr_bank_slice(name: str) -> slice:
    bank = _bank(name)
    return slice(bank.offset, bank.end)


def _write_dense_words(
    record: bytearray,
    bank: DdrBankLayout,
    words: tuple[int, ...],
) -> None:
    if len(words) > bank.depth:
        raise ValueError(f"{bank.name} word count exceeds depth {bank.depth}")
    max_word = 1 << (bank.word_bytes * 8)
    for index, word in enumerate(words):
        if isinstance(word, bool) or not isinstance(word, int):
            raise TypeError(f"{bank.name}[{index}] must be an int")
        if not 0 <= word < max_word:
            raise ValueError(
                f"{bank.name}[{index}] does not fit {bank.word_bytes * 8} bits"
            )
        start = bank.offset + index * bank.word_bytes
        record[start : start + bank.word_bytes] = word.to_bytes(
            bank.word_bytes, "little"
        )


def _write_sparse_words(
    record: bytearray,
    bank: DdrBankLayout,
    words: tuple[SparseWord, ...],
) -> None:
    max_word = 1 << (bank.word_bytes * 8)
    seen: set[int] = set()
    for entry in words:
        if not 0 <= entry.index < bank.depth:
            raise ValueError(
                f"{bank.name} sparse index {entry.index} exceeds depth {bank.depth}"
            )
        if entry.index in seen:
            raise ValueError(f"{bank.name} contains duplicate sparse index {entry.index}")
        seen.add(entry.index)
        if not 0 <= entry.word < max_word:
            raise ValueError(
                f"{bank.name}[{entry.index}] does not fit {bank.word_bytes * 8} bits"
            )
        start = bank.offset + entry.index * bank.word_bytes
        record[start : start + bank.word_bytes] = entry.word.to_bytes(
            bank.word_bytes, "little"
        )


def _validate_event_words(name: str, words: tuple[int, ...]) -> None:
    if len(words) > 4096:
        raise ValueError(f"{name} event count exceeds 4096")
    for index, word in enumerate(words):
        _require_uint(f"{name}[{index}]", word, 32)


def _payload_digest(record: bytes | bytearray) -> bytes:
    return hashlib.sha256(record[P02_DDR_PAYLOAD_START:P02_DDR_PAYLOAD_END]).digest()


def build_initial_ddr_context_record(
    context: BackingLogicalContextImage,
    *,
    current_event_bank: int = 0,
    event0_words: tuple[int, ...] = (),
    event1_words: tuple[int, ...] = (),
) -> bytes:
    """Serialize one backing context into the fixed P02.1 DDR ABI."""

    if current_event_bank not in (0, 1):
        raise ValueError("current_event_bank must be 0 or 1")
    _require_uint("logical_core_id", context.logical_core_id, 7)
    if context.logical_core_id >= P02_DDR_MAX_LOGICAL_CORES:
        raise ValueError("logical_core_id exceeds P02 DDR backing capacity")
    if context.image.core_id != context.logical_core_id:
        raise ValueError("backing context logical_core_id does not match image.core_id")

    _validate_event_words("event0_words", event0_words)
    _validate_event_words("event1_words", event1_words)

    image: OneCoreHardwareImage = context.image
    record = bytearray(P02_DDR_CONTEXT_STRIDE_BYTES)

    _write_dense_words(record, _bank("config"), image.config_words)
    _write_dense_words(record, _bank("state"), image.state_words)
    _write_sparse_words(record, _bank("axon"), image.axon_words)
    _write_dense_words(record, _bank("synapse"), image.synapse_words)
    _write_sparse_words(
        record, _bank("route_descriptor"), image.route_descriptor_words
    )
    _write_dense_words(record, _bank("route"), image.route_words)
    _write_dense_words(record, _bank("event0"), event0_words)
    _write_dense_words(record, _bank("event1"), event1_words)

    struct.pack_into(
        "<8s12I",
        record,
        0,
        P02_DDR_ABI_MAGIC,
        P02_DDR_ABI_VERSION,
        P02_DDR_HEADER_BYTES,
        P02_DDR_CONTEXT_STRIDE_BYTES,
        context.logical_core_id,
        0,
        current_event_bank,
        image.compartment_count,
        image.synapse_count,
        image.route_count,
        len(event0_words),
        len(event1_words),
        0,
    )
    digest = _payload_digest(record)
    record[
        P02_DDR_HEADER_HASH_OFFSET :
        P02_DDR_HEADER_HASH_OFFSET + P02_DDR_HEADER_HASH_BYTES
    ] = digest
    return bytes(record)


def parse_ddr_context_header(
    record: bytes,
    *,
    verify_payload: bool = True,
) -> DdrContextHeader:
    """Validate a serialized record and return its v1 header."""

    if len(record) != P02_DDR_CONTEXT_STRIDE_BYTES:
        raise ValueError(
            f"DDR context record must be exactly {P02_DDR_CONTEXT_STRIDE_BYTES} bytes"
        )

    (
        magic,
        version,
        header_bytes,
        record_bytes,
        logical_core_id,
        flags,
        current_event_bank,
        compartment_count,
        synapse_count,
        route_count,
        event0_count,
        event1_count,
        packet_count,
    ) = struct.unpack_from("<8s12I", record, 0)

    if magic != P02_DDR_ABI_MAGIC:
        raise ValueError("invalid P02 DDR context magic")
    if version != P02_DDR_ABI_VERSION:
        raise ValueError(f"unsupported P02 DDR ABI version {version}")
    if header_bytes != P02_DDR_HEADER_BYTES:
        raise ValueError("P02 DDR header size mismatch")
    if record_bytes != P02_DDR_CONTEXT_STRIDE_BYTES:
        raise ValueError("P02 DDR record size mismatch")
    if flags != 0:
        raise ValueError("P02 DDR ABI v1 reserved flags must be zero")
    _require_uint("logical_core_id", logical_core_id, 7)
    if current_event_bank not in (0, 1):
        raise ValueError("P02 DDR current_event_bank must be 0 or 1")
    if compartment_count > 1024:
        raise ValueError("P02 DDR compartment_count exceeds 1024")
    if synapse_count > 32768:
        raise ValueError("P02 DDR synapse_count exceeds 32768")
    if route_count > 4096:
        raise ValueError("P02 DDR route_count exceeds 4096")
    if event0_count > 4096 or event1_count > 4096:
        raise ValueError("P02 DDR event count exceeds 4096")
    if packet_count > 4096:
        raise ValueError("P02 DDR packet_count exceeds 4096")

    stored_digest = record[
        P02_DDR_HEADER_HASH_OFFSET :
        P02_DDR_HEADER_HASH_OFFSET + P02_DDR_HEADER_HASH_BYTES
    ]
    if verify_payload and stored_digest != _payload_digest(record):
        raise ValueError("P02 DDR payload SHA-256 mismatch")

    return DdrContextHeader(
        version=version,
        header_bytes=header_bytes,
        record_bytes=record_bytes,
        logical_core_id=logical_core_id,
        flags=flags,
        current_event_bank=current_event_bank,
        compartment_count=compartment_count,
        synapse_count=synapse_count,
        route_count=route_count,
        event0_count=event0_count,
        event1_count=event1_count,
        packet_count=packet_count,
        payload_sha256=stored_digest.hex(),
    )


def ddr_context_record_fingerprint(record: bytes) -> str:
    """Return the deterministic identity of the complete 512 KiB record."""

    parse_ddr_context_header(record)
    return hashlib.sha256(record).hexdigest()
