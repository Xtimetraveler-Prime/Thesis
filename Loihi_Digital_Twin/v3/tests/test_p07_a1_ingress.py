"""P07-A1 host ABI parity, negative testing, and independent C11 probe.

Only synthetic raw bytes; does not access MNIST official TEST or artifacts.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import random
import shutil
import struct
import subprocess
import zlib

import pytest

from loihi_twin_v2.p06_input_contract import pixel_spikes
from loihi_twin_v2.p07_a1_ingress import (
    AXON_CAPACITY, HEADER_BYTES, RECORD_BYTES, P07IngressError,
    decode_ingress, encode_compiled_ingress, encode_ingress,
    event_axons_for_tick, ingress_sha256, mapping_from_compiled,
)

ROOT = Path(__file__).resolve().parents[1]
DDR = "12" * 32
DEPLOY = "ab" * 32
# Not equal to pixel indices and deliberately NOT sorted.
MAP = tuple((i * 73 + 17) % AXON_CAPACITY for i in range(784))


def _packed(image: bytes = bytes(range(256)) * 3 + bytes(range(16))) -> bytes:
    assert len(image) == 784
    return encode_ingress(image, MAP, ddr_sha256=DDR, deployment_fingerprint=DEPLOY)


def _repair_crc(data: bytearray) -> bytes:
    struct.pack_into("<I", data, 56, zlib.crc32(data[HEADER_BYTES:]))
    struct.pack_into("<I", data, 60, 0)
    struct.pack_into("<I", data, 60, zlib.crc32(data[:HEADER_BYTES]))
    return bytes(data)


def _compiled(routes=None):
    if routes is None:
        routes = tuple(SimpleNamespace(
            input_population="pixels", input_index=i,
            destination_core=0, destination_axon=MAP[i],
        ) for i in range(784))
    return SimpleNamespace(ingress_routes=routes, fingerprint=DEPLOY)


def test_record_exact_layout_and_binary_identity():
    blob = _packed()
    assert len(blob) == RECORD_BYTES == 2480
    assert blob[:8] == b"P07A1IN1"
    assert len(blob[128:1696]) == 784 * 2
    assert struct.unpack_from("<784H", blob, 128) == MAP
    assert blob[1696:] == bytes(range(256)) * 3 + bytes(range(16))
    assert blob == encode_ingress(
        decode_ingress(blob).pixels, MAP, ddr_sha256=DDR,
        deployment_fingerprint=DEPLOY,
    )
    assert len(ingress_sha256(blob)) == 64
    rec = decode_ingress(blob)
    assert rec.core_id == 0 and rec.ddr_sha256 == DDR
    assert rec.deployment_fingerprint == DEPLOY


@pytest.mark.parametrize("image", [
    bytes(784), bytes([255]) * 784,
    bytes((i * 19 + 7) % 256 for i in range(784)),
    bytes([255 if i % 2 else 0 for i in range(784)]),
])
def test_all_26_ticks_against_frozen_p06_encoder(image):
    blob = _packed(image)
    rec = decode_ingress(blob)
    for tick in range(26):
        expected = tuple(MAP[i] for i in pixel_spikes(image, tick))
        assert rec.event_axons(tick) == expected
        assert event_axons_for_tick(blob, tick) == expected
        assert len(expected) <= 784
    assert rec.event_axons(25) == ()
    assert rec.event_axons(0) != tuple(sorted(rec.event_axons(0))) if any(image) and image != bytes([255])*784 else True


def test_random_bytes_and_frozen_quota():
    rng = random.Random(20261017)
    for _ in range(8):
        image = bytes(rng.randrange(256) for _ in range(784))
        rec = decode_ingress(_packed(image))
        for tick in range(26):
            assert rec.event_axons(tick) == tuple(MAP[i] for i in pixel_spikes(image, tick))
        for i in (0, 1, 101, 783):
            assert sum(MAP[i] in rec.event_axons(t) for t in range(25)) == (25 * image[i]) // 255


def test_compiled_ingress_explicit_routes_and_rejections():
    comp = _compiled()
    assert mapping_from_compiled(comp) == MAP
    assert encode_compiled_ingress(bytes(784), comp, ddr_sha256=DDR) == _packed(bytes(784))
    shuffled = _compiled(tuple(reversed(comp.ingress_routes)))
    assert mapping_from_compiled(shuffled) == MAP
    for bad in (
        comp.ingress_routes[:-1],
        comp.ingress_routes + (comp.ingress_routes[1],),
        tuple(SimpleNamespace(input_population="unexpected", input_index=route.input_index,
                              destination_core=0, destination_axon=route.destination_axon)
              if i == 2 else route for i, route in enumerate(comp.ingress_routes)),
        tuple(SimpleNamespace(input_population="pixels", input_index=route.input_index,
                              destination_core=1, destination_axon=route.destination_axon)
              if i == 2 else route for i, route in enumerate(comp.ingress_routes)),
        tuple(SimpleNamespace(input_population="pixels", input_index=route.input_index,
                              destination_core=0, destination_axon=MAP[0])
              if i == 2 else route for i, route in enumerate(comp.ingress_routes)),
    ):
        with pytest.raises(P07IngressError):
            mapping_from_compiled(_compiled(bad))


@pytest.mark.parametrize("mapping", [
    MAP[:-1], MAP + (3,), MAP[:1] + (MAP[0],) + MAP[2:],
    MAP[:7] + (-1,) + MAP[8:], MAP[:7] + (4096,) + MAP[8:],
    MAP[:7] + (True,) + MAP[8:],
])
def test_host_invalid_mapping_rejected(mapping):
    with pytest.raises(P07IngressError):
        encode_ingress(bytes(784), mapping, ddr_sha256=DDR, deployment_fingerprint=DEPLOY)


@pytest.mark.parametrize("bad_sha", ["", "0"*64, "zy"*32, "aa"*31])
def test_invalid_provenance_fails_closed(bad_sha):
    with pytest.raises(P07IngressError):
        encode_ingress(bytes(784), MAP, ddr_sha256=bad_sha, deployment_fingerprint=DEPLOY)
    with pytest.raises(P07IngressError):
        encode_ingress(bytes(784), MAP, ddr_sha256=DDR, deployment_fingerprint=bad_sha)


@pytest.mark.parametrize("offset,value", [
    (0, 0), (8, 2), (12, 64), (16, 7), (20, 7), (24, 7), (28, 7),
    (32, 26), (36, 25), (40, 1), (44, 783), (48, 8192), (52, 1),
])
def test_even_rechecksummed_invalid_header_rejected(offset, value):
    b = bytearray(_packed())
    if offset == 0:
        b[0] = value
    else:
        struct.pack_into("<I", b, offset, value)
    with pytest.raises(P07IngressError, match="header"):
        decode_ingress(_repair_crc(b))


def test_truncation_bad_crc_and_invalid_fingerprint_rejected():
    b = _packed()
    for raw in (b[:-1], b + b"x", bytes([b[0] ^ 1]) + b[1:],
                b[:1800] + bytes([b[1800] ^ 1]) + b[1801:]):
        with pytest.raises(P07IngressError):
            decode_ingress(raw)
    bad = bytearray(b)
    bad[64:96] = bytes(32)
    with pytest.raises(P07IngressError):
        decode_ingress(_repair_crc(bad))


def test_rechecksummed_duplicate_and_out_of_range_axon_rejected():
    for axon in (MAP[0], 4096, 65535):
        bad = bytearray(_packed())
        struct.pack_into("<H", bad, 128 + 2 * 9, axon)
        with pytest.raises(P07IngressError, match="axon"):
            decode_ingress(_repair_crc(bad))


def test_tick_and_pixel_fail_closed():
    raw = _packed()
    for tick in (-1, 26, True, 0.0):
        with pytest.raises(ValueError):
            event_axons_for_tick(raw, tick)
    with pytest.raises(P07IngressError):
        encode_ingress(bytes(783), MAP, ddr_sha256=DDR, deployment_fingerprint=DEPLOY)


def _fnv(axons: tuple[int, ...]) -> str:
    h = 14695981039346656037
    for axon in axons:
        for value in axon.to_bytes(2, "little"):
            h = (h ^ value) * 1099511628211 & ((1 << 64) - 1)
    return f"{h:016x}"


@pytest.fixture(scope="module")
def native_probe(tmp_path_factory):
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if cc is None:
        pytest.skip("no native C11 compiler; user must run native verification")
    dest = tmp_path_factory.mktemp("p07_a1_native") / "p07_a1_probe"
    subprocess.run([
        cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        str(ROOT / "software/p07/p07_a1_ingress.c"),
        str(ROOT / "software/p07/p07_a1_probe.c"),
        "-o", str(dest),
    ], check=True, capture_output=True, text=True)
    return dest


@pytest.mark.parametrize("image", [
    bytes(784), bytes([255]) * 784,
    bytes((index * 71 + 19) % 256 for index in range(784)),
])
def test_native_c_26_tick_cross_language_parity(native_probe, tmp_path, image):
    record = tmp_path / "frame.bin"
    record.write_bytes(_packed(image))
    run = subprocess.run([str(native_probe), str(record)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    lines = run.stdout.splitlines()
    assert lines[-1] == "P07_A1_C_NATIVE_PASS=1"
    expected = [
        f"{t} {len(row)} {_fnv(row)}"
        for t in range(26)
        for row in [tuple(MAP[i] for i in pixel_spikes(image, t))]
    ]
    assert lines[:-1] == expected


def test_native_c_rejects_corrupted_and_semantically_invalid(native_probe, tmp_path):
    good = _packed()
    cases = [good[:-1], good[:1700] + bytes([good[1700] ^ 1]) + good[1701:]]
    invalid = bytearray(good)
    struct.pack_into("<H", invalid, 128 + 2 * 9, MAP[0])
    cases.append(_repair_crc(invalid))
    invalid = bytearray(good)
    struct.pack_into("<I", invalid, 52, 1)
    cases.append(_repair_crc(invalid))
    for index, blob in enumerate(cases):
        file = tmp_path / f"bad{index}.bin"
        file.write_bytes(blob)
        run = subprocess.run([str(native_probe), str(file)], capture_output=True, text=True)
        assert run.returncode != 0
