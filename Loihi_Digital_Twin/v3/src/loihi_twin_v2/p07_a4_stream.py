"""P07-A4.2a persistent A53 DDR transport ABI, independent host reference.

No MNIST dataset loading, PyTorch or hardware. Only caller-supplied raw
28x28 frames. NOT the accepted P07-A2 batch envelope or P05G ABI.
The official 10k TEST partition remains sealed while engineering this ABI.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
import zlib

from .p07_a1_ingress import encode_ingress, decode_ingress
from .p07_a2_batch import DDR_SHA256, COMPILED_FINGERPRINT

MAGIC = b"P07A4P01"
RESULT_MAGIC = b"P07A4R01"
VERSION = 1
HEADER_BYTES = 256
MAP_COUNT = 784
MAP_BYTES = MAP_COUNT * 2
IMAGE_BYTES = 784
MAX_FRAMES = 10000
IMAGE_BASE = 0x41000000
IMAGE_CAPACITY = 0x800000
RESULT_BASE = 0x42000000
RESULT_CAPACITY = 0x100000
RESULT_HEADER_BYTES = 256
RESULT_RECORD_BYTES = 96
TRACE_BASE = 0x43FF0000
DESCRIPTOR_BASE = 0x43FE0000
MAP_BASE = 0x43FE0100
MASTER_BASE = 0x43F00000
BACKING_BASE = 0x40000000
SUCCESS = 0x600D600D
NO_FAILURE = 0xFFFFFFFF
IMAGE_HEADER_FIELDS = (
    VERSION, HEADER_BYTES, IMAGE_BYTES, IMAGE_BASE, IMAGE_CAPACITY,
    RESULT_BASE, RESULT_CAPACITY, RESULT_RECORD_BYTES, TRACE_BASE,
)


def crc(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _check_mapping(mapping: tuple[int, ...]) -> bytes:
    if (not isinstance(mapping, tuple) or len(mapping) != MAP_COUNT or
            any(type(x) is not int or not 0 <= x < 4096 for x in mapping) or
            len(set(mapping)) != MAP_COUNT):
        raise ValueError("A4.2 mapped pixels require 784 distinct uint12 axon IDs")
    return struct.pack("<784H", *mapping)


def _check_capacity(count: int, trace_frame: int) -> None:
    if (type(count) is not int or not 1 <= count <= MAX_FRAMES or
            type(trace_frame) is not int or not 0 <= trace_frame < count or
            count * IMAGE_BYTES > IMAGE_CAPACITY or
            RESULT_HEADER_BYTES + count * RESULT_RECORD_BYTES > RESULT_CAPACITY):
        raise ValueError("A4.2 sample/trace index or fixed DDR capacity invalid")


@dataclass(frozen=True)
class Stream:
    header: bytes
    mapping_bytes: bytes
    images: bytes
    mapping: tuple[int, ...]
    image_count: int
    trace_index: int

    def image(self, index: int) -> bytes:
        if type(index) is not int or not 0 <= index < self.image_count:
            raise ValueError("A4.2 invalid image index")
        return self.images[index * IMAGE_BYTES:(index + 1) * IMAGE_BYTES]

    def ingress(self, index: int) -> bytes:
        """Byte-exact existing accepted P07-A1 wire, never a new encoder."""
        return encode_ingress(self.image(index), self.mapping,
                              ddr_sha256=DDR_SHA256,
                              deployment_fingerprint=COMPILED_FINGERPRINT)


def make_stream(images: bytes, mapping: tuple[int, ...],
                *, trace_index: int = 0) -> Stream:
    if not isinstance(images, bytes) or not images or len(images) % IMAGE_BYTES:
        raise ValueError("A4.2 raw image stream must contain complete uint8 frames")
    count = len(images) // IMAGE_BYTES
    _check_capacity(count, trace_index)
    packed_map = _check_mapping(mapping)
    head = bytearray(HEADER_BYTES)
    struct.pack_into("<8s19I", head, 0,
                     MAGIC, VERSION, HEADER_BYTES, count, IMAGE_BYTES,
                     IMAGE_BASE, IMAGE_CAPACITY, RESULT_BASE, RESULT_CAPACITY,
                     RESULT_RECORD_BYTES, TRACE_BASE, trace_index, 0,
                     crc(images), crc(packed_map), MAP_COUNT, MAP_BASE,
                     MASTER_BASE, BACKING_BASE, 0)
    # 19th integer (offset 80) must NOT be written: header offset 80
    # is the beginning of the 32B DDR SHA. Repack the 18 fields only.
    # The temporary word above is overwritten by exact 32B immutable SHA.
    head[80:112] = bytes.fromhex(DDR_SHA256)
    head[112:144] = bytes.fromhex(COMPILED_FINGERPRINT)
    struct.pack_into("<I", head, 252, crc(head[:252]))
    return Stream(bytes(head), packed_map, images, mapping, count, trace_index)


def parse_stream(header: bytes, mapping_bytes: bytes, images: bytes) -> Stream:
    if (not isinstance(header, bytes) or len(header) != HEADER_BYTES or
            header[:8] != MAGIC):
        raise ValueError("A4.2 descriptor header magic/length mismatch")
    fields = struct.unpack_from("<18I", header, 8)
    (version, header_len, count, stride, image_base, image_cap,
     result_base, result_cap, result_stride, trace_base, trace_index,
     flags, image_crc, mapping_crc, map_count, map_base, master, backing) = fields
    _check_capacity(count, trace_index)
    if (version, header_len, stride, image_base, image_cap,
        result_base, result_cap, result_stride, trace_base, flags,
        map_count, map_base, master, backing) != (
        VERSION, HEADER_BYTES, IMAGE_BYTES, IMAGE_BASE, IMAGE_CAPACITY,
        RESULT_BASE, RESULT_CAPACITY, RESULT_RECORD_BYTES, TRACE_BASE, 0,
        MAP_COUNT, MAP_BASE, MASTER_BASE, BACKING_BASE):
        raise ValueError("A4.2 descriptor layout or physical DDR addresses changed")
    if (header[80:112] != bytes.fromhex(DDR_SHA256) or
            header[112:144] != bytes.fromhex(COMPILED_FINGERPRINT) or
            any(header[144:252]) or
            struct.unpack_from("<I", header, 252)[0] != crc(header[:252])):
        raise ValueError("A4.2 descriptor digest/CRC/reserved field failure")
    if (not isinstance(mapping_bytes, bytes) or len(mapping_bytes) != MAP_BYTES or
            mapping_crc != crc(mapping_bytes)):
        raise ValueError("A4.2 mapping CRC/length mismatch")
    mapping = struct.unpack("<784H", mapping_bytes)
    _check_mapping(mapping)
    if (not isinstance(images, bytes) or len(images) != count * IMAGE_BYTES or
            image_crc != crc(images)):
        raise ValueError("A4.2 raw image payload length/CRC mismatch")
    return Stream(header, mapping_bytes, images, mapping, count, trace_index)


def initial_journal(stream: Stream) -> bytes:
    """Zeroed 1MiB physical journal staging, NOT a completed result."""
    header = bytearray(RESULT_HEADER_BYTES)
    struct.pack_into("<8s9I", header, 0,
                     RESULT_MAGIC, VERSION, RESULT_HEADER_BYTES,
                     0, stream.image_count, 0, NO_FAILURE,
                     struct.unpack_from("<I", stream.header, 252)[0],
                     stream.trace_index, 0)
    struct.pack_into("<I", header, 252, crc(header[:252]))
    return bytes(header) + bytes(RESULT_CAPACITY - RESULT_HEADER_BYTES)


def encode_result(index: int, pixels: bytes, output_spikes: tuple[tuple[int, ...], ...],
                  *, routes: int = 0, discarded: int = 0,
                  input_events: int = 0, cycles: int = 0) -> bytes:
    """HOST-ONLY synthetic test helper; NEVER represents physical evidence."""
    if (type(index) is not int or not 0 <= index < MAX_FRAMES or
            not isinstance(pixels, bytes) or len(pixels) != IMAGE_BYTES or
            len(output_spikes) != 26 or
            any(len(row) != 10 or any(type(v) is not int or v not in (0, 1)
                                      for v in row) for row in output_spikes) or
            any(type(v) is not int or not 0 <= v <= 0xFFFFFFFF
                for v in (routes, discarded, input_events, cycles))):
        raise ValueError("A4.2 invalid synthetic packed result values")
    counts = [sum(output_spikes[t][cls] for t in range(26)) for cls in range(10)]
    winner = max(range(10), key=lambda cls: counts[cls])
    silent = int(not any(counts))
    wordbits = [0] * 9
    for t in range(26):
        for cls in range(10):
            if output_spikes[t][cls]:
                bit = t*10+cls
                wordbits[bit//32] |= 1 << (bit%32)
    raw = bytearray(RESULT_RECORD_BYTES)
    struct.pack_into("<8I", raw, 0, index, crc(pixels), SUCCESS,
                     winner, silent, routes, discarded, input_events)
    struct.pack_into("<10H", raw, 32, *counts)
    struct.pack_into("<9I", raw, 52, *wordbits)
    struct.pack_into("<I", raw, 88, cycles)
    struct.pack_into("<I", raw, 92, crc(raw[:92]))
    return bytes(raw)


@dataclass(frozen=True)
class Result:
    image_index: int
    predicted: int
    counts: tuple[int, ...]
    all_silent: bool
    routes: int
    discarded: int
    external_events: int
    elapsed_cycles: int
    output_spikes: tuple[tuple[int, ...], ...]


def parse_result(record: bytes, *, expected_index: int, pixels: bytes) -> Result:
    if not isinstance(record, bytes) or len(record) != RESULT_RECORD_BYTES:
        raise ValueError("A4.2 result record length invalid")
    (index, image_crc, status, pred, silent, routes,
     discarded, input_events) = struct.unpack_from("<8I", record)
    if (index != expected_index or image_crc != crc(pixels) or
            status != SUCCESS or pred > 9 or silent not in (0, 1) or
            input_events > 25*784 or
            struct.unpack_from("<I", record, 92)[0] != crc(record[:92])):
        raise ValueError("A4.2 result index/CRC/completion/readout invalid")
    counts = struct.unpack_from("<10H", record, 32)
    packed = struct.unpack_from("<9I", record, 52)
    value = int.from_bytes(record[52:88], "little")
    if value >> 260:
        raise ValueError("A4.2 reserved output-spike tail bits nonzero")
    spikes = tuple(tuple((value >> (t*10+cls)) & 1 for cls in range(10))
                   for t in range(26))
    if (counts != tuple(sum(spikes[t][cls] for t in range(26)) for cls in range(10)) or
            pred != max(range(10), key=lambda cls: counts[cls]) or
            silent != int(not any(counts))):
        raise ValueError("A4.2 output bit/count/class/silent disagreement")
    return Result(index, pred, counts, bool(silent), routes, discarded,
                  input_events, struct.unpack_from("<I", record, 88)[0], spikes)


def parse_journal(raw: bytes, stream: Stream) -> tuple[Result, ...]:
    """Fail before scoring if progress is incomplete, corrupted, or misbound."""
    if not isinstance(raw, bytes) or len(raw) != RESULT_CAPACITY:
        raise ValueError("A4.2 physical journal wrong allocation size")
    head = raw[:RESULT_HEADER_BYTES]
    if head[:8] != RESULT_MAGIC:
        raise ValueError("A4.2 journal magic mismatch")
    (version, size, status, requested, completed, first_fault,
     bound_crc, trace_index, flags) = struct.unpack_from("<9I", head, 8)
    if (version, size, status, requested, completed, first_fault,
        bound_crc, trace_index, flags) != (
        VERSION, RESULT_HEADER_BYTES, SUCCESS, stream.image_count,
        stream.image_count, NO_FAILURE,
        struct.unpack_from("<I", stream.header, 252)[0], stream.trace_index, 0):
        raise ValueError("A4.2 journal not entirely completed / wrong descriptor")
    if any(head[44:252]) or struct.unpack_from("<I", head, 252)[0] != crc(head[:252]):
        raise ValueError("A4.2 journal reserved/CRC mismatch")
    limit = RESULT_HEADER_BYTES + stream.image_count*RESULT_RECORD_BYTES
    if any(raw[limit:]):
        raise ValueError("A4.2 journal trailing unowned data unexpectedly nonzero")
    return tuple(
        parse_result(raw[RESULT_HEADER_BYTES+i*RESULT_RECORD_BYTES:
                         RESULT_HEADER_BYTES+(i+1)*RESULT_RECORD_BYTES],
                     expected_index=i, pixels=stream.image(i))
        for i in range(stream.image_count)
    )
