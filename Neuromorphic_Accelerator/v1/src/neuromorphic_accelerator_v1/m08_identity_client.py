"""M08.2 typed read-only PL identity client (NO physical MMIO backend).

Only accepts a caller-supplied authenticated read32 adapter. Never maps
/dev/mem or constructs a physical address. The standalone identity RTL has
no DMA and a default zero build tag; a real deployment must separately pin
and verify actual routed bitstream SHA and platform memory ownership.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

MAGIC=0x4D303831
VERSION=0x00010000
CAPABILITY_NO_DMA=0
OFFSETS=(0x00,0x04,0x08,0x0C,0x10,0x14,0x18,0x1C)


class RegisterReadOnly(Protocol):
    def read32(self, offset: int) -> int: ...


class IdentityProtocolError(RuntimeError):
    pass


@dataclass(frozen=True)
class PLIdentitySnapshot:
    magic: int
    version: int
    capabilities: int
    build_tag_hex: str
    locally_consistent: bool
    actual_bitstream_sha_verified: bool = False
    physically_attested: bool = False
    dma_buffer_owner_verified: bool = False


def _word(adapter: RegisterReadOnly, offset: int) -> int:
    try:
        value=adapter.read32(offset)
    except (OSError, ValueError, RuntimeError) as e:
        raise IdentityProtocolError("MMIO adapter read failed") from e
    if type(value) is not int or value<0 or value>0xffffffff:
        raise IdentityProtocolError("non-uint32 value or malformed MMIO decode")
    return value


def inspect_identity(adapter: RegisterReadOnly,
                     *, require_nonzero_build_tag: bool=True) -> PLIdentitySnapshot:
    """Read twice to detect gross stale/unstable decode; not silicon proof.

    BUILD_TAG is four supplied 32-bit words. It is NOT itself cryptographic
    proof that the loaded bitstream matches the claimed commit/XSA.
    """
    if type(require_nonzero_build_tag) is not bool:
        raise ValueError("require_nonzero_build_tag must be a bool")
    reads=[tuple(_word(adapter,off) for off in OFFSETS)
           for _ in range(2)]
    if reads[0] != reads[1]:
        raise IdentityProtocolError("unstable PL readback; cannot identify build")
    magic,version,caps,reserved,*tag=reads[0]
    if magic!=MAGIC or version!=VERSION:
        raise IdentityProtocolError("unexpected identity magic/protocol version")
    if caps!=CAPABILITY_NO_DMA or reserved!=0:
        raise IdentityProtocolError("unknown control/memory capabilities")
    if require_nonzero_build_tag and not any(tag):
        raise IdentityProtocolError("unprovisioned zero bitstream build tag")
    return PLIdentitySnapshot(
        magic=magic,version=version,capabilities=caps,
        build_tag_hex="".join(f"{word:08x}" for word in tag),
        locally_consistent=True,
        actual_bitstream_sha_verified=False,
        physically_attested=False,
        dma_buffer_owner_verified=False,
    )
