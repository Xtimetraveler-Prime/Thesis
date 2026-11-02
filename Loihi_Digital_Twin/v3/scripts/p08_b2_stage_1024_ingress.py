#!/usr/bin/env python3
"""P08-B2.1: frozen original B2.4-route, matched 1024 raw MNIST TRAIN stage.

PC-only. Independently validates existing A stage and 33 immutable B2.4
assets; NEVER reads official TEST, touches KV260 or edits accepted evidence.
Precomputes host B1.3 ingress SHA for all 1024 raw frames, without storing
126MiB of redundant encoded frames in the new stage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

import p08_b1_matched_source_audit as b1
from loihi_twin_v2.compiler import NetworkSpec
from loihi_twin_v2.p06_b12_partition import B12Result
from loihi_twin_v2.p06_b13_streaming import (
    B13_INGRESS_MAGIC, _ingress_routes, encode_ingress_frame,
    decode_ingress_frame,
)
from loihi_twin_v2.p06_b24_freeze import verify_frozen_directory

ROUTE_FILENAME = "p07_b4m_original_input_routes_896k.bin"
ROUTE_SHA256 = "380268c5e8faa2664a31f993683c6759316239932d96b8e681ddb458c81574e8"
RAW_FILENAME = "p08_b2_original_track_a_raw1024_uint8.bin"
HASH_FILENAME = "p08_b2_original_27core_1024_ingress_sha256_lines.txt"
MANIFEST_FILENAME = "p08_b2_1_original_same1024_ingress_manifest.json"
COUNT = 1024
FRAME_BYTES = 123216
RAW_IMAGE_BYTES = 784
ROUTES = 20384
PREFIX_BYTES = 128
ROUTE_BYTES = ROUTES * 6
RAW_DDR_BASE = 0x42100000
RAW_DDR_END = RAW_DDR_BASE + COUNT * RAW_IMAGE_BYTES

# Design candidates only, NOT proof of PS/Linux/boot DMA memory ownership.
RANGES = {
    "mutable_27_P02_contexts": (0x40000000, 0x40D80000),
    "input_route_image": (0x41000000, 0x410E0000),
    "single_B1_3_ingress_buffer": (0x41100000, 0x411E0000),
    "original_B5_raw_trace_reserved_avoid": (0x42000000, 0x420CD280),
    "1024_raw_pixels_pool": (RAW_DDR_BASE, RAW_DDR_END),
    "image_neural_journal_candidate": (0x42200000, 0x42300000),
    "image_timing_candidate": (0x42300000, 0x42400000),
    "tick_timing_candidate": (0x42400000, 0x42800000),
    "selected_full_26x1010_trace_candidate": (0x42800000, 0x428CD280),
    "immutable_27_P02_backup_candidate": (0x43000000, 0x43D80000),
    "original_16KiB_binding": (0x43FC0000, 0x43FC4000),
    "original_80KiB_output_routes": (0x43FC4000, 0x43FD8000),
    "original_V3_mailbox_reserved": (0x43FF0000, 0x43FF0100),
    "original_B5_mailbox_reserved": (0x43FF0100, 0x43FF0200),
    "new_B2_mailbox_candidate": (0x43FF0200, 0x43FF0300),
}


class B2NoGo(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_memory_ranges(ranges=RANGES) -> dict:
    ordered = sorted((start, end, label) for label, (start, end) in ranges.items())
    if not ordered:
        raise B2NoGo("empty proposed DDR allocation list")
    for n, (start, end, label) in enumerate(ordered):
        if (type(start) is not int or type(end) is not int or
            not 0x40000000 <= start < end <= 0x44000000 or
            (start & 0x3f) or (end & 0x3f)):
            raise B2NoGo("invalid 64MiB DDR range: " + label)
        if n and start < ordered[n-1][1]:
            raise B2NoGo("overlapping proposed DDR: " +
                         ordered[n-1][2] + " / " + label)
    if (ranges["immutable_27_P02_backup_candidate"][1] -
            ranges["immutable_27_P02_backup_candidate"][0] != 27*512*1024 or
        ranges["1024_raw_pixels_pool"][1] -
            ranges["1024_raw_pixels_pool"][0] != COUNT*RAW_IMAGE_BYTES or
        ranges["single_B1_3_ingress_buffer"][1] -
            ranges["single_B1_3_ingress_buffer"][0] < FRAME_BYTES):
        raise B2NoGo("immutable-context backup, raw pool or ingress insufficient")
    return {
        "ranges": {k: [f"0x{s:08X}", f"0x{e:08X}"] for k, (s, e) in ranges.items()},
        "static_disjoint_with_listed_regions": True,
        "physical_DDR_owner_exclusivity_proven": False,
        "new_Vitis_ELF_PT_LOAD_checked": False,
        "standalone_KV260_launch_authorized": False,
    }


def pinned_route_payload(route_file: Path, compiled: B12Result) -> bytes:
    if route_file.is_symlink() or not route_file.is_file():
        raise B2NoGo("original route image absent or symlinked")
    original = route_file.read_bytes()
    if len(original) != 0xE0000 or sha(original) != ROUTE_SHA256:
        raise B2NoGo("original 896KiB B4MING01 input-route full SHA changed")
    if (original[:8] != b"B4MING01" or
            struct.unpack_from("<6I", original, 8) !=
            (1, 0xE0000, 27, ROUTES, 6, PREFIX_BYTES) or
            original[32:64] != bytes.fromhex(b1.B24_COMPILED_SHA) or
            original[64:96] != bytes.fromhex(
                "82e9e6c11264c6092dbe94f17496332fae303ac9ef7dfaa01d0ec441869a9498") or
            original[96:128] != hashlib.sha256(original[PREFIX_BYTES:]).digest()):
        raise B2NoGo("original B4MING01 SHA/header/route digest mismatch")
    compiled_routes = _ingress_routes(compiled)
    expected = b"".join(struct.pack("<3H", *row) for row in compiled_routes)
    if len(compiled_routes) != ROUTES or len(expected) != ROUTE_BYTES:
        raise B2NoGo("original frozen B2.4 ingress route count changed")
    if original[PREFIX_BYTES:PREFIX_BYTES + ROUTE_BYTES] != expected:
        raise B2NoGo("original route table differs from B2.4 compiler's exact mapping")
    if any(original[PREFIX_BYTES + ROUTE_BYTES:]):
        raise B2NoGo("nonzero trailing original input-route memory")
    return expected


def wire_from_pinned_route_bytes(routes: bytes, pixels: bytes) -> bytes:
    if len(routes) != ROUTE_BYTES or len(pixels) != RAW_IMAGE_BYTES:
        raise B2NoGo("unexpected fixed 27-core encoded frame dimensions")
    payload = routes + pixels
    ints = (1, 128, len(payload), ROUTES, 27, 784, 25, 26,
            6, 784, zlib.crc32(payload), 0, 0, 0)
    header = bytearray(struct.pack("<8s14I", B13_INGRESS_MAGIC, *ints))
    header += bytes.fromhex(b1.B24_COMPILED_SHA)
    header += bytes.fromhex(
        "82e9e6c11264c6092dbe94f17496332fae303ac9ef7dfaa01d0ec441869a9498")
    if len(header) != PREFIX_BYTES:
        raise B2NoGo("fixed B1.3 frame header width drift")
    struct.pack_into("<I", header, 52, zlib.crc32(header))
    wire = bytes(header) + payload
    if len(wire) != FRAME_BYTES:
        raise B2NoGo("original 27-core B1.3 frame is not 123216 bytes")
    return wire


def build(stage_dir: Path, raw_data_dir: Path, frozen_dir: Path,
          routes_dir: Path, output_dir: Path) -> dict:
    root = Path(__file__).resolve().parents[3]  # Thesis Git root
    if (not output_dir.is_absolute() or output_dir.exists() or
            output_dir.is_symlink() or not output_dir.parent.is_dir() or
            output_dir.resolve().is_relative_to(root)):
        raise B2NoGo("NEW external absolute output directory required")
    source = b1.generate_report(stage_dir, raw_data_dir, frozen_dir)
    if (len(source["frames"]) != COUNT or
            source["B24_original_33_assets_verified"] is not True or
            source["original_MNIST_TEST"] != "SEALED_NOT_ACCESSED"):
        raise B2NoGo("B1 canonical source admission did not pass")
    verify_frozen_directory(frozen_dir, deep=False)
    compiled = B12Result.from_json(
        (frozen_dir / "packed_deployment.json").read_text(encoding="utf-8"))
    network = NetworkSpec.from_json(
        (frozen_dir / "network_source.json").read_text(encoding="utf-8"))
    if (compiled.compiled.fingerprint != b1.B24_COMPILED_SHA or
            compiled.compiled.source_fingerprint != network.fingerprint or
            compiled.capacity_audit["logical_core_count"] != 27):
        raise B2NoGo("original frozen network and packed deployment differ")
    route_bytes = pinned_route_payload(routes_dir / ROUTE_FILENAME, compiled)
    pixels = b1.read_regular(stage_dir, b1.STAGE_FILES["pixels"])
    if (len(pixels) != COUNT * RAW_IMAGE_BYTES or
            sha(pixels) != source["track_A_stage"]["original_A_stage_sha256"]["pixels"]):
        raise B2NoGo("new raw pool not exactly original Track A first1024 stage bytes")
    mem = validate_memory_ranges()
    lines = []
    frames = []
    for index in range(COUNT):
        raw = pixels[index * RAW_IMAGE_BYTES:(index+1)*RAW_IMAGE_BYTES]
        frame = wire_from_pinned_route_bytes(route_bytes, raw)
        # Independent original B1.3 compiler/decoder on predeclared control frames.
        if index in (0, 1, 2, 15, 1023):
            expected = encode_ingress_frame(compiled, raw)
            if frame != expected or decode_ingress_frame(frame, compiled).pixels != raw:
                raise B2NoGo(f"original B1.3 encoder disagrees at frame {index}")
        digest = sha(frame)
        lines.append(digest)
        frames.append({
            "frame": index,
            "TRAIN_source_index": source["frames"][index]["TRAIN_source_index"],
            "raw_pixels_sha256": source["frames"][index]["raw_pixels_sha256"],
            "B24_27core_B13_ingress_sha256": digest,
            "encoded_wire_bytes": FRAME_BYTES,
            "selected_trace": index == 1023,
        })
    hashes = "".join(x + "\n" for x in lines).encode("ascii")
    result = {
        "schema": "p08-b2-1-original27-matched1024-train-only-ingress-v1",
        "source": "accepted original A3.2 first1024 original TRAIN validation",
        "count": COUNT,
        "frame_bytes": FRAME_BYTES,
        "raw_pool_bytes": len(pixels),
        "selected_trace_frame": 1023,
        "ordinary_frames": 1023,
        "B24_original_compiled_sha256": b1.B24_COMPILED_SHA,
        "original_input_route_896k_sha256": ROUTE_SHA256,
        "original_A_stage_manifest_sha256":
            source["track_A_stage"]["original_A_manifest_sha256"],
        "original_A_ledger_sha256":
            source["track_A_stage"]["original_A_ledger_sha256"],
        "original_B24_frozen_manifest_sha256": source["B24_original_frozen_manifest_sha256"],
        "raw_pool_sha256": sha(pixels),
        "encoded_frames_sha256_lines_file_sha256": sha(hashes),
        "memory_proposal": mem,
        "frames": frames,
        "B_embedded_runtime_implemented": False,
        "new_A53_ELF_built": False,
        "KV260_physical_latency": "NOT_RUN",
        "physical_run_authorized": False,
        "original_OFFICIAL_MNIST_TEST": "SEALED_NOT_ACCESSED",
    }
    # A successful stage is immutable at the application layer; never replace.
    output_dir.mkdir(mode=0o700)
    (output_dir / RAW_FILENAME).write_bytes(pixels)
    (output_dir / HASH_FILENAME).write_bytes(hashes)
    (output_dir / MANIFEST_FILENAME).write_text(
        json.dumps(result, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("stage-dir", "train-data-dir", "frozen-dir", "routes-dir", "out"):
        p.add_argument("--"+name, type=Path, required=True)
    a = p.parse_args()
    try:
        result = build(a.stage_dir, a.train_data_dir, a.frozen_dir,
                       a.routes_dir, a.out)
        print("P08_B2_ORIGINAL_27CORE_1024_INGRESS_HOST_STAGE_PASS=1")
        print("P08_B2_RAW_POOL_BYTES=" + str(result["raw_pool_bytes"]))
        print("P08_B2_FRAME_BYTES=" + str(result["frame_bytes"]))
        print("P08_B2_B24_INGRESS_ORIGINAL_PIXEL_SHA_LEDGER=1024")
        print("P08_B2_DDR_OWNERSHIP_INDEPENDENTLY_PROVEN=0")
        print("P08_B2_NEW_A53_ELF=NOT_BUILT")
        print("P08_B2_PHYSICAL_KV260_RUN=NOT_RUN")
        print("P08_B2_STAGE=" + str(a.out))
    except (B2NoGo, ValueError, TypeError, KeyError, OSError, AssertionError) as exc:
        print("P08_B2_NO_GO=" + str(exc), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
