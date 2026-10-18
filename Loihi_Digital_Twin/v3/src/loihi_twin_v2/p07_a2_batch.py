"""P07-A2 independent, fixed-size batch envelope for autonomous A53 work.

Only accepts already signed-off P07-A1 ingress records. No MNIST labels or
test-set loading, no new training or binary DDR generation.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import zlib

from .p07_a1_ingress import RECORD_BYTES, decode_ingress

MAGIC = b"P07A2B01"
VERSION = 1
HEADER_BYTES = 64
MAX_FRAMES = 16
INPUT_BASE = 0x43F80000
HEADER_BASE = 0x43FE0000
MASTER_BASE = 0x43F00000
RESULT_BASE = 0x43FF0000
RESULT_BYTES = 65536
DDR_SHA256 = "9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955"
COMPILED_FINGERPRINT = "e612a971cda11fae3f1be215c0ca3ed7de7b2af7339446e926ce559658db2f7f"


def validate_frame(record: bytes) -> None:
    parsed = decode_ingress(record)
    if parsed.ddr_sha256 != DDR_SHA256:
        raise ValueError("P07-A2 image references an unaccepted DDR record")
    if parsed.deployment_fingerprint != COMPILED_FINGERPRINT:
        raise ValueError("P07-A2 image references the wrong compiled deployment")


def create_batch(records: tuple[bytes, ...], *, trace_frame: int = 0) -> tuple[bytes, bytes]:
    if not isinstance(records, tuple) or not 1 <= len(records) <= MAX_FRAMES:
        raise ValueError("P07-A2 requires 1..16 immutable P07-A1 image records")
    if type(trace_frame) is not int or not 0 <= trace_frame < len(records):
        raise ValueError("trace_frame must select a valid input frame")
    for record in records:
        validate_frame(record)
    payload = b"".join(records)
    if len(payload) > HEADER_BASE - INPUT_BASE:
        raise ValueError("ingress batch overlaps descriptor region")
    header = bytearray(HEADER_BYTES)
    struct.pack_into("<8s7I", header, 0, MAGIC, VERSION, len(records),
                     RECORD_BYTES, INPUT_BASE, 0, trace_frame, 0)
    struct.pack_into("<I", header, 32, zlib.crc32(header))
    return bytes(header), payload


def parse_batch(header: bytes, payload: bytes) -> tuple[bytes, ...]:
    if len(header) != HEADER_BYTES or header[:8] != MAGIC:
        raise ValueError("unsupported P07-A2 batch header")
    (version, count, record_size, base, flags, trace_index, crc) = struct.unpack_from("<7I", header, 8)
    checked = bytearray(header)
    struct.pack_into("<I", checked, 32, 0)
    if (version != VERSION or not 1 <= count <= MAX_FRAMES or
            record_size != RECORD_BYTES or base != INPUT_BASE or flags or
            trace_index >= count or header[36:] != bytes(28) or
            zlib.crc32(checked) != crc):
        raise ValueError("invalid P07-A2 batch envelope")
    if len(payload) != count * RECORD_BYTES:
        raise ValueError("P07-A2 ingress frame count/length mismatch")
    records = tuple(payload[i:i+RECORD_BYTES] for i in range(0, len(payload), RECORD_BYTES))
    for record in records:
        validate_frame(record)
    return records


def write_batch(record_paths: tuple[Path, ...], output_dir: Path,
                *, trace_frame: int = 0) -> dict:
    import json
    if output_dir.exists():
        raise FileExistsError("refuse overwrite of P07-A2 deployment directory")
    inputs = tuple(path.read_bytes() for path in record_paths)
    header, payload = create_batch(inputs, trace_frame=trace_frame)
    out = output_dir
    out.mkdir(parents=True, exist_ok=False)
    (out / "p07_a2_header_64.bin").write_bytes(header)
    (out / "p07_a2_ingress_payload.bin").write_bytes(payload)
    (out / "p07_a2_mailbox_zero_64k.bin").write_bytes(bytes(RESULT_BYTES))
    manifest = {
        "schema": "p07-a2-kv260-autonomous-batch-v1",
        "scope": "deployment only; FPGA execution NOT RUN",
        "frame_count": len(inputs), "trace_frame": trace_frame,
        "ddr_sha256": DDR_SHA256,
        "compiled_fingerprint": COMPILED_FINGERPRINT,
        "input_base": f"0x{INPUT_BASE:08X}", "master_base": f"0x{MASTER_BASE:08X}",
        "header_base": f"0x{HEADER_BASE:08X}", "mailbox_base": f"0x{RESULT_BASE:08X}",
        "sha256": {
            "header": hashlib.sha256(header).hexdigest(),
            "payload": hashlib.sha256(payload).hexdigest(),
            "mailbox_initial": hashlib.sha256(bytes(RESULT_BYTES)).hexdigest(),
            "records": [hashlib.sha256(record).hexdigest() for record in inputs],
        },
        "official_mnist_test": "SEALED",
    }
    (out / "p07_a2_manifest.json").write_text(
        json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return manifest
