"""P07-A1 versioned one-image, 784-axon A53 ingress wire format.

This is a host/firmware input contract only. It does not claim PL inference or
alter accepted P03/P05 arithmetic, pages, routing, or diagnostic ABI.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
import zlib
from collections.abc import Sequence

from .p06_input_contract import INPUT_CHANNELS, INPUT_TICKS, TOTAL_TICKS, pixel_spikes

MAGIC = b"P07A1IN1"
VERSION = 1
HEADER_BYTES = 128
MAP_BYTES = INPUT_CHANNELS * 2
IMAGE_BYTES = INPUT_CHANNELS
PAYLOAD_BYTES = MAP_BYTES + IMAGE_BYTES
RECORD_BYTES = HEADER_BYTES + PAYLOAD_BYTES
CORE_ID = 0
AXON_CAPACITY = 4096
MAX_EXTERNAL_EVENTS_PER_TICK = INPUT_CHANNELS
_HEADER_FORMAT = "<8s14I"


class P07IngressError(ValueError):
    """Malformed or nonconforming P07-A1 transfer. Reject before PL access."""


@dataclass(frozen=True, slots=True)
class P07IngressRecord:
    pixels: bytes
    pixel_to_axon: tuple[int, ...]
    ddr_sha256: str
    deployment_fingerprint: str
    core_id: int = CORE_ID

    def event_axons(self, tick: int) -> tuple[int, ...]:
        """Order is ascending source pixel index, NOT sorted axon ID."""
        return tuple(self.pixel_to_axon[i] for i in pixel_spikes(self.pixels, tick))


def _digest(value: str, label: str) -> bytes:
    if not isinstance(value, str) or len(value) != 64:
        raise P07IngressError(label + " must be 64 hexadecimal characters")
    try:
        raw = bytes.fromhex(value)
    except ValueError as exc:
        raise P07IngressError(label + " must be hexadecimal") from exc
    if len(raw) != 32 or not any(raw):
        raise P07IngressError(label + " cannot be zero")
    return raw


def _validate_mapping(mapping: Sequence[int]) -> tuple[int, ...]:
    if len(mapping) != INPUT_CHANNELS:
        raise P07IngressError("exactly 784 explicitly mapped pixels required")
    if any(type(a) is not int or not 0 <= a < AXON_CAPACITY for a in mapping):
        raise P07IngressError("axon ID must be a uint12 integer")
    if len(set(mapping)) != INPUT_CHANNELS:
        raise P07IngressError("duplicate external destination axon")
    return tuple(mapping)


def mapping_from_compiled(compiled: object) -> tuple[int, ...]:
    """Extract actual compiler ingress IDs without assuming pixel ID == axon ID.

    P07 Track A requires exactly one distinct core-0 destination per pixel.
    Additional cores/fanout require a separately accepted Track B format.
    """
    routes = getattr(compiled, "ingress_routes", None)
    if routes is None:
        raise P07IngressError("compiled deployment has no ingress_routes")
    by_pixel: dict[int, int] = {}
    for route in routes:
        if (route.input_population != "pixels" or
                route.destination_core != CORE_ID or
                type(route.input_index) is not int or
                not 0 <= route.input_index < INPUT_CHANNELS or
                route.input_index in by_pixel):
            raise P07IngressError("wrong population, destination core, or duplicate pixel route")
        by_pixel[route.input_index] = route.destination_axon
    if set(by_pixel) != set(range(INPUT_CHANNELS)):
        raise P07IngressError("missing pixel ingress routes")
    return _validate_mapping(tuple(by_pixel[i] for i in range(INPUT_CHANNELS)))


def encode_ingress(
    pixels: bytes, pixel_to_axon: Sequence[int], *,
    ddr_sha256: str, deployment_fingerprint: str,
) -> bytes:
    """Build one complete CRC-protected little-endian transfer.

    Header layout: 8s magic; 14 x uint32 (version, header_bytes,
    payload_bytes, map_bytes, image_bytes, channels, input_ticks, total_ticks,
    core_id, map_count, axon_capacity, flags, payload_crc32, header_crc32);
    32B DDR SHA256; 32B compiled deployment SHA256/fingerprint.
    Payload: 784 LE uint16 destination axons indexed by pixel, then 784 uint8.
    Header CRC is computed with its own four bytes zero. No native C structs.
    """
    if not isinstance(pixels, bytes) or len(pixels) != IMAGE_BYTES:
        raise P07IngressError("image must be exactly 784 raw uint8 bytes")
    mapping = _validate_mapping(pixel_to_axon)
    ddr = _digest(ddr_sha256, "DDR full-file SHA256")
    deployment = _digest(deployment_fingerprint, "compiled deployment fingerprint")
    payload = struct.pack("<784H", *mapping) + pixels
    prefix = struct.pack(
        _HEADER_FORMAT, MAGIC, VERSION, HEADER_BYTES, PAYLOAD_BYTES, MAP_BYTES,
        IMAGE_BYTES, INPUT_CHANNELS, INPUT_TICKS, TOTAL_TICKS, CORE_ID,
        INPUT_CHANNELS, AXON_CAPACITY, 0, zlib.crc32(payload), 0,
    )
    header = bytearray(prefix + ddr + deployment)
    assert len(header) == HEADER_BYTES
    struct.pack_into("<I", header, 60, zlib.crc32(header))
    return bytes(header) + payload


def encode_compiled_ingress(
    pixels: bytes, compiled: object, *, ddr_sha256: str,
) -> bytes:
    """Bind the transfer to the real frozen compiler fingerprint and ingress."""
    return encode_ingress(
        pixels, mapping_from_compiled(compiled), ddr_sha256=ddr_sha256,
        deployment_fingerprint=getattr(compiled, "fingerprint"),
    )


def decode_ingress(raw: bytes) -> P07IngressRecord:
    """Validate ALL wire fields and checksums before returning image or mapping."""
    if not isinstance(raw, bytes) or len(raw) != RECORD_BYTES:
        raise P07IngressError("wrong P07-A1 transfer length")
    fields = struct.unpack_from(_HEADER_FORMAT, raw)
    (magic, version, header_size, payload_size, map_size, image_size,
     channels, input_ticks, total_ticks, core, mapped, axon_capacity,
     flags, payload_crc, header_crc) = fields
    if (magic, version, header_size, payload_size, map_size, image_size,
            channels, input_ticks, total_ticks, core, mapped, axon_capacity, flags) != (
            MAGIC, VERSION, HEADER_BYTES, PAYLOAD_BYTES, MAP_BYTES, IMAGE_BYTES,
            INPUT_CHANNELS, INPUT_TICKS, TOTAL_TICKS, CORE_ID, INPUT_CHANNELS,
            AXON_CAPACITY, 0):
        raise P07IngressError("invalid or unsupported P07-A1 header")
    header = bytearray(raw[:HEADER_BYTES])
    struct.pack_into("<I", header, 60, 0)
    if zlib.crc32(header) != header_crc:
        raise P07IngressError("header CRC32 mismatch")
    payload = raw[HEADER_BYTES:]
    if zlib.crc32(payload) != payload_crc:
        raise P07IngressError("payload CRC32 mismatch")
    ddr = raw[64:96].hex()
    deployment = raw[96:128].hex()
    _digest(ddr, "DDR full-file SHA256")
    _digest(deployment, "compiled deployment fingerprint")
    mapping = _validate_mapping(struct.unpack_from("<784H", payload))
    pixels = payload[MAP_BYTES:]
    return P07IngressRecord(pixels, mapping, ddr, deployment)


def event_axons_for_tick(raw: bytes, tick: int) -> tuple[int, ...]:
    """Validated tick planning; no writes to hardware or NEXT bank."""
    return decode_ingress(raw).event_axons(tick)


def ingress_sha256(raw: bytes) -> str:
    decode_ingress(raw)
    return hashlib.sha256(raw).hexdigest()
