"""M08.2b pure PS-page register protocol: caller-supplied transport ONLY.

No operating-system device access, mmap, /dev/mem, /dev/uio, SSH or hardware
programming. Passing these checks against a synthetic adapter is NOT physical
proof. A future separately approved transport must establish kernel ownership,
thermal continuity, actual bus response behavior and fault/timeout containment.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Protocol, Sequence

from .m08_identity_client import IdentityProtocolError, inspect_identity

PAGE_MAGIC = 0x4D303850
PAGE_VERSION = 0x00020002
PAGE_CAPABILITY = 1
PAGE_WORDS = 64
PAGE_BYTES = 256
PAGE_DATA = 0x100
STATUS = 0x00C
SELECTED = 0x010
COMMAND = 0x014
RESIDENT = 0x018
LOADED_BYTES = 0x01C
EMPTY, LOADING, READY = 0, 1, 2
FAULT_BITS = (1 << 8) | (1 << 6) | (1 << 5) | (1 << 3)


class ReadWrite32(Protocol):
    def read32(self, offset: int) -> int: ...
    def write32(self, offset: int, value: int) -> None: ...


class PageProtocolError(RuntimeError):
    """Stop; do not retry/COMMIT after an unverified page operation."""


def _word(value: object, description: str) -> int:
    if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
        raise PageProtocolError(f"invalid uint32 {description}")
    return value


def _read(io: ReadWrite32, offset: int) -> int:
    try:
        result = io.read32(offset)
    except (OSError, ValueError, RuntimeError) as e:
        raise PageProtocolError(f"read32 failed at 0x{offset:03x}; stop") from e
    return _word(result, f"read at 0x{offset:03x}")


def _write(io: ReadWrite32, offset: int, value: int) -> None:
    _word(value, "write data")
    try:
        io.write32(offset, value)
    except (OSError, ValueError, RuntimeError) as e:
        raise PageProtocolError(f"write32 failed at 0x{offset:03x}; stop") from e


def _status(io: ReadWrite32, phase: int, *, valid: bool) -> int:
    word = _read(io, STATUS)
    if word & FAULT_BITS or (word & 0x7) != phase or bool(word & 0x10) != valid:
        raise PageProtocolError(f"unexpected status 0x{word:08x}; no further commands")
    # Bit 7 is the bank host_busy indicator: allowed during LOADING only.
    if word & ~0x1FF or (word & 0x80 and phase != LOADING):
        raise PageProtocolError(f"unexpected status bits 0x{word:08x}")
    return word


def check_idle_pair(identity: ReadWrite32, page: ReadWrite32) -> dict:
    """Read identity and EMPTY page metadata twice; zero build tag is untrusted."""
    try:
        ident = inspect_identity(identity, require_nonzero_build_tag=False)
    except IdentityProtocolError as e:
        raise PageProtocolError("identity protocol mismatch") from e
    offsets = (0, 4, 8, STATUS, SELECTED, RESIDENT, LOADED_BYTES)
    first = tuple(_read(page, off) for off in offsets)
    second = tuple(_read(page, off) for off in offsets)
    if first != second:
        raise PageProtocolError("page metadata unstable across two reads")
    magic, version, capability, status, _selected, _resident, loaded = first
    if (magic, version, capability) != (PAGE_MAGIC, PAGE_VERSION, PAGE_CAPABILITY):
        raise PageProtocolError("page magic/version/capability mismatch")
    if loaded != 0:
        raise PageProtocolError("page is not reset/empty; no overwrite permitted")
    if status != EMPTY:
        raise PageProtocolError("page is not EMPTY; no overwrite permitted")
    return {
        "identity_build_tag": ident.build_tag_hex,
        "identity_build_tag_provisioned": any(int(ident.build_tag_hex[i:i+8], 16)
                                               for i in range(0, 32, 8)),
        "identity_magic": f"0x{ident.magic:08x}",
        "page_magic": f"0x{magic:08x}",
        "page_version": f"0x{version:08x}",
        "page_capability": capability,
        "initial_phase": "EMPTY",
        "physical_attestation": False,
    }


def stage_and_compare(identity: ReadWrite32, page: ReadWrite32,
                      values: Sequence[int], logical_id: int, *,
                      allow_transport_writes: bool = False) -> dict:
    """Exact 64-word load/readback/commit via injected transport.

    Only a distinct outside-the-repository, independently approved hardware
    transport may ever perform physical IO. Do not treat Python write32 return
    as AXI BRESP or attempt DISPATCH via a UIO mmap.
    """
    if allow_transport_writes is not True:
        raise PageProtocolError("explicit transport write authorization required")
    logical_id = _word(logical_id, "logical_id")
    if len(values) != PAGE_WORDS:
        raise PageProtocolError("exactly 64 page words required")
    expected = tuple(_word(v, f"word[{i}]") for i, v in enumerate(values))
    baseline = check_idle_pair(identity, page)  # MUST precede first write
    _write(page, SELECTED, logical_id)
    if _read(page, SELECTED) != logical_id:
        raise PageProtocolError("selected logical ID did not read back")
    _write(page, COMMAND, 1)  # BEGIN
    _status(page, LOADING, valid=False)
    for i, value in enumerate(expected):
        _write(page, PAGE_DATA + 4*i, value)
    if _read(page, LOADED_BYTES) != PAGE_BYTES:
        raise PageProtocolError("loaded byte count != 256; COMMIT withheld")
    # Fresh register transactions AFTER all writes, not cached input values.
    observed = tuple(_read(page, PAGE_DATA + 4*i) for i in range(PAGE_WORDS))
    for i, (wanted, got) in enumerate(zip(expected, observed)):
        if got != wanted:
            raise PageProtocolError(
                f"word[{i}] mismatch expected=0x{wanted:08x} got=0x{got:08x}; COMMIT withheld"
            )
    _status(page, LOADING, valid=False)
    _write(page, COMMAND, 2)  # COMMIT only AFTER all 64 independently compared
    _status(page, READY, valid=True)
    if _read(page, RESIDENT) != logical_id or _read(page, LOADED_BYTES) != PAGE_BYTES:
        raise PageProtocolError("post-COMMIT resident/loaded registers mismatch")
    payload = b"".join(v.to_bytes(4, "little") for v in observed)
    return {
        "schema": "m08-uio-256-byte-transport-contract-v1",
        "result": "64_WORDS_MATCHED_AFTER_INJECTED_TRANSPORT_COMMIT",
        "logical_id": logical_id,
        "words_compared": PAGE_WORDS,
        "bytes_compared": PAGE_BYTES,
        "readback_sha256_little_endian": sha256(payload).hexdigest(),
        "identity": baseline,
        "dispatch_attempted": False,
        "axi_bresp_or_rresp_observed": False,
        "linux_uio_mmap_exercised_by_module": False,
        "physical_ps_axi_verified": False,
        "neural_inference_verified": False,
    }
