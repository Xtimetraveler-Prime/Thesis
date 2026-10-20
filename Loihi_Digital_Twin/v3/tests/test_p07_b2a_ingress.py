"""P07-B.2a: independent native C11 vs accepted Python B1.3 oracle.

No B2 frozen artifact is opened and no official MNIST TEST or board is touched.
The 27-core case is a SYNTHETIC topology stress frame, not trained B2 mapping.
"""
from __future__ import annotations
import struct
import subprocess
import zlib
from pathlib import Path
import pytest
from loihi_twin_v2.compiler import (InputPopulationSpec, InputProjectionSpec, NetworkSpec,
                                    PopulationSpec, ProjectionConnection, ProjectionSpec)
from loihi_twin_v2.compartment import CompartmentConfig
from loihi_twin_v2.p06_b12_partition import B12Options, compile_synapse_aware
from loihi_twin_v2.p06_b13_streaming import encode_ingress_frame, decode_ingress_frame
from loihi_twin_v2.p06_input_contract import pixel_spikes

ROOT = Path(__file__).resolve().parents[1]
B2_COMP_SHA = "02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a"
B2_AUDIT_SHA = "82e9e6c11264c6092dbe94f17496332fae303ac9ef7dfaa01d0ec441869a9498"


@pytest.fixture(scope="module")
def native(tmp_path_factory):
    import shutil
    directory = tmp_path_factory.mktemp("p07_b2a_c11")
    binary = directory / "p07_b2a_native"
    cc = shutil.which("cc") or shutil.which("gcc")
    assert cc, "a host-native C11 compiler is required"
    subprocess.run([
        cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-I", str(ROOT / "software/p07/include"),
        str(ROOT / "software/p07/p07_b2_ingress.c"),
        str(ROOT / "tests/native/p07_b2a_ingress_harness.c"),
        "-o", str(binary),
    ], check=True, capture_output=True, text=True)
    return binary


@pytest.fixture(scope="module")
def real_b13_fixture():
    h = CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=2)
    o = CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=5)
    network = NetworkSpec(
        populations=(PopulationSpec("h", 3, h), PopulationSpec("z", 2, o)),
        input_populations=(InputPopulationSpec("pixels", 784),),
        input_projections=(InputProjectionSpec(
            "input", "pixels", "h", tuple(
                ProjectionConnection(pixel, neuron, 1)
                for pixel in range(784) for neuron in range(3)),
        ),),
        projections=(ProjectionSpec("hidden_out", "h", "z", tuple(
            ProjectionConnection(neuron, target, 2)
            for neuron in range(3) for target in range(2)),),),
    )
    return compile_synapse_aware(network, B12Options(readout_population="z", compartments_per_core=2))


def recalc(raw):
    work = bytearray(raw)
    struct.pack_into("<I", work, 48, zlib.crc32(work[128:]))
    struct.pack_into("<I", work, 52, 0)
    struct.pack_into("<I", work, 52, zlib.crc32(work[:128]))
    return bytes(work)


def pack_synthetic_27(routes, pixels):
    assert len(pixels) == 784
    payload = routes + pixels
    words = (1, 128, len(payload), len(routes)//6, 27, 784, 25, 26, 6, 784,
             zlib.crc32(payload), 0, 0, 0)
    header = bytearray(struct.pack("<8s14I", b"P06B13I1", *words)
                       + bytes.fromhex(B2_COMP_SHA) + bytes.fromhex(B2_AUDIT_SHA))
    struct.pack_into("<I", header, 52, zlib.crc32(header))
    return bytes(header) + payload


def run(native, tmp_path, frame, trusted_routes, comp, audit, cores):
    frame_file = tmp_path / "ingress.frame"
    map_file = tmp_path / "trusted.map"
    frame_file.write_bytes(frame)
    map_file.write_bytes(trusted_routes)
    return subprocess.run([str(native), str(frame_file), str(map_file), comp, audit, str(cores)],
                          capture_output=True, text=True)


def verify_26_ticks(result, envelope, expected_routes, pixels):
    lines = result.stdout.splitlines()
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert lines[-1] == "P07_B2A_NATIVE_INGRESS_PASS=1"
    assert len(lines) == 27
    for tick in range(26):
        _, label_tick, number, actual_crc = lines[tick].split()
        assert int(label_tick) == tick
        active = set(pixel_spikes(pixels, tick))
        intended = b"".join(struct.pack("<HH", core, axon)
                            for pix, core, axon in expected_routes if pix in active)
        assert int(number) == len(intended) // 4
        assert int(actual_crc, 16) == zlib.crc32(intended)
        if envelope is not None:
            expected = envelope.events(tick)
            assert len(expected) == int(number)
            assert intended == b"".join(struct.pack("<HH", p.destination_core, p.destination_axon)
                                        for p in expected)


@pytest.mark.parametrize("level", [0, 255, 53])
def test_genuine_b13_compiled_three_core_oracle(native, real_b13_fixture, tmp_path, level):
    result = real_b13_fixture
    pixels = bytes((level + 31 * i) % 256 for i in range(784)) if level == 53 else bytes([level] * 784)
    frame = encode_ingress_frame(result, pixels)
    envelope = decode_ingress_frame(frame, result)
    routes = envelope.routes
    mapping = frame[128:128 + 6 * len(routes)]
    actual = run(native, tmp_path, frame, mapping, result.compiled.fingerprint,
                 result.capacity_audit["audit_sha256"], 3)
    verify_26_ticks(actual, envelope, routes, pixels)


@pytest.mark.parametrize("pixels", [bytes(784), bytes([255]) * 784,
                                     bytes((i * 17 + 43) % 256 for i in range(784))])
def test_synthetic_27_full_fanout_all_ticks(native, tmp_path, pixels):
    routes = tuple((pix, core, pix) for pix in range(784) for core in range(26))
    mapping = b"".join(struct.pack("<HHH", *item) for item in routes)
    frame = pack_synthetic_27(mapping, pixels)
    assert len(frame) == 123216
    actual = run(native, tmp_path, frame, mapping, B2_COMP_SHA, B2_AUDIT_SHA, 27)
    verify_26_ticks(actual, None, routes, pixels)


def test_repaired_crc_cannot_overwrite_trusted_mapping(native, real_b13_fixture, tmp_path):
    result = real_b13_fixture
    frame = encode_ingress_frame(result, bytes([255]) * 784)
    mapping = frame[128:-784]
    fingerprint = result.compiled.fingerprint
    audit = result.capacity_audit["audit_sha256"]
    variants = []
    variants.append(b"P07A1IN1" + frame[8:])
    variants.append(frame[:-1] + bytes([frame[-1] ^ 1]))
    forged = bytearray(frame)
    forged[128] ^= 1
    variants.append(recalc(forged))
    forged = bytearray(frame)
    forged[64] ^= 1
    variants.append(recalc(forged))
    forged = bytearray(frame)
    forged[56] = 1
    variants.append(recalc(forged))
    forged = bytearray(frame)
    struct.pack_into("<I", forged, 24, 27)
    variants.append(recalc(forged))
    variants.append(frame[:-1])
    forged = bytearray(frame)
    forged[8] = 2
    variants.append(recalc(forged))
    forged = bytearray(frame)
    forged[36] = 25
    variants.append(recalc(forged))
    for candidate in variants:
        actual = run(native, tmp_path, candidate, mapping, fingerprint, audit, 3)
        assert actual.returncode == 10, actual.stdout
        assert actual.stdout.startswith("P07_B2A_REJECT=")


def test_self_consistent_but_illegal_map_order_and_axon(native, tmp_path):
    routes = [(pix, core, pix) for pix in range(784) for core in range(26)]
    for illegal in ("duplicate_core", "axon_overflow", "missing_pixel", "reorder"):
        malformed = routes.copy()
        if illegal == "duplicate_core":
            malformed[1] = malformed[0]
        elif illegal == "axon_overflow":
            malformed[1] = (0, 1, 4096)
        elif illegal == "missing_pixel":
            malformed[-1] = (782, 25, 783)
        else:
            malformed[1], malformed[2] = malformed[2], malformed[1]
        mapbytes = b"".join(struct.pack("<HHH", *r) for r in malformed)
        frame = pack_synthetic_27(mapbytes, bytes([255]) * 784)
        actual = run(native, tmp_path, frame, mapbytes, B2_COMP_SHA, B2_AUDIT_SHA, 27)
        assert actual.returncode == 10
        assert actual.stdout.strip() == "P07_B2A_REJECT=-6"
