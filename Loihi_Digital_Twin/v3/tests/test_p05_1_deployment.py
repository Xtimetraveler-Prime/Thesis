"""P05.1 portable ABI conformance: real Python builder ↔ C11 reader.

This checkpoint is HOST-ONLY. It does not create a new A53 executable
and is not evidence of physical P05.1 or P05.2 acceptance.
"""
from __future__ import annotations

import ctypes
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zlib

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "scripts/p05_deployment.py"
C = ROOT / "software/p05/p05_deployment.c"
INC = ROOT / "software/p05/include"
P03 = ROOT / "scripts/p03_finish_fixture.py"

spec_mod = importlib.util.spec_from_file_location("p05_fixture_generator", SRC)
assert spec_mod is not None and spec_mod.loader is not None
mod = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(mod)


class CInfo(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint32) for name in (
        "timesteps", "core_count", "slot_count", "diagnostic_mode",
        "event_count", "checkpoint_count", "payload_crc32",
        "header_crc32", "dispatch_count",
    )]


@pytest.fixture(scope="module")
def c_validate(tmp_path_factory):
    cc = shutil.which("cc") or shutil.which("gcc")
    if cc is None:
        pytest.skip("A C11 compiler is required for C/Python ABI conformance")
    path = tmp_path_factory.mktemp("p05_c") / "libp05_deployment.so"
    args = [
        cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-O2", "-fPIC", "-shared", "-I", str(INC), str(C), "-o", str(path),
    ]
    proc = subprocess.run(args, capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    function = ctypes.CDLL(str(path)).p05_deployment_validate
    function.argtypes = [
        ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
        ctypes.POINTER(CInfo),
    ]
    function.restype = ctypes.c_int

    def call(header: bytes, payload: bytes) -> tuple[int, CInfo]:
        h = (ctypes.c_uint8 * len(header)).from_buffer_copy(header)
        p = (ctypes.c_uint8 * len(payload)).from_buffer_copy(payload)
        info = CInfo()
        return function(h, len(header), p, len(payload), ctypes.byref(info)), info

    return call


def create_record(path: Path, core: int) -> None:
    # Valid envelope/header, not a neural model! These synthetic records
    # deliberately stay in the HOST-ONLY contract suite.
    image = bytearray(mod.RECORD_BYTES)
    image[:8] = b"LTV3CTX1"
    struct.pack_into("<I", image, 8, 1)
    struct.pack_into("<I", image, 0x10, mod.RECORD_BYTES)
    struct.pack_into("<I", image, 0x14, core)
    struct.pack_into("<I", image, 0x1000, 0x14001000 + core)
    path.write_bytes(image)


def make_spec(tmp_path: Path, n: int = 3, steps: int = 4,
              mode: str = "diagnostic") -> Path:
    # Intentionally non-sorted core order, to prove explicit service rank.
    core_ids = [2, 0, 1][:n] if n <= 3 else list(range(n))
    cores = []
    for cid in core_ids:
        name = f"context_{cid}.bin"
        create_record(tmp_path / name, cid)
        cores.append({"id": cid, "metadata": cid | (1 << 7),
                      "input_axon": 10 + cid, "record": name})
    spec = {
        "schema": mod.SCHEMA, "timesteps": steps,
        "slot_count": min(3, n), "mode": mode,
        "cores": cores,
        "events": [
            {"timestep": step, "core": cid, "axon": 10 + cid}
            for step in range(steps) for cid in reversed(core_ids)
        ],
        "checkpoints": [
            {"timestep": 1, "core": core_ids[0],
             "state_class": "state0", "expected_crc32": "0xABCD1234"},
        ] if mode == "diagnostic" and steps >= 2 else [],
    }
    dest = tmp_path / "spec.json"
    dest.write_text(json.dumps(spec), encoding="utf-8")
    return dest


def deployment(spec: Path):
    out = spec.parent / "out"
    manifest = mod.build(spec, out)
    return manifest, (out / "p05_header.bin").read_bytes(), (
        out / "p05_payload.bin").read_bytes()


@pytest.mark.parametrize("cores,steps,mode", [
    (1, 2, "fast"), (2, 3, "diagnostic"), (3, 4, "diagnostic"),
    (5, 7, "fast"),
])
def test_python_c_roundtrip_and_deterministic_layout(tmp_path, c_validate,
                                                      cores, steps, mode):
    spec = make_spec(tmp_path, cores, steps, mode)
    manifest, head, payload = deployment(spec)
    ret, info = c_validate(head, payload)
    assert ret == 0
    assert info.timesteps == steps
    assert info.core_count == cores
    assert info.slot_count == min(3, cores)
    assert info.dispatch_count == steps * cores
    assert info.event_count == cores * steps
    assert info.checkpoint_count == (1 if mode == "diagnostic" else 0)
    assert info.diagnostic_mode == (mode == "diagnostic")
    words = struct.unpack("<64I", head)
    assert words[22] == zlib.crc32(payload)
    assert words[23] == zlib.crc32(head[:92] + b"\0" * 4 + head[96:])
    assert words[17] == cores * 32
    assert words[18] == cores * 32 + cores * steps * 16
    assert words[12] == len(payload)
    assert words[20] == steps * cores
    assert manifest["status"] == "HOST_CONTRACT_ONLY_NOT_A53_OR_PHYSICAL_ACCEPTANCE"
    assert manifest["logical_core_ids_in_service_order"] == (
        [2, 0, 1][:cores] if cores <= 3 else list(range(cores))
    )
    first_event = struct.unpack_from("<4I", payload, words[17])
    assert first_event[:3] == (
        0, manifest["logical_core_ids_in_service_order"][0],
        10 + manifest["logical_core_ids_in_service_order"][0],
    )
    m2, h2, p2 = deployment(spec)
    assert (m2, h2, p2) == (manifest, head, payload)


def with_header_word(head: bytes, index: int, value: int,
                     recalc_crc: bool = True) -> bytes:
    w = list(struct.unpack("<64I", head))
    w[index] = value
    if recalc_crc:
        w[23] = 0
        w[23] = zlib.crc32(struct.pack("<64I", *w))
    return struct.pack("<64I", *w)


@pytest.mark.parametrize("word,new,error", [
    (0, 0, -2),                  # magic
    (1, 2, -2),                  # schema
    (4, 0, -2),                  # steps
    (5, 127, -2),                # 126 records max, prevent payload overlap
    (6, 0, -2),                  # zero slots
    (7, 2, -2),                  # single physical engine
    (8, 0x41000000, -2),        # fixed backing range
    (11, 0xF0000, -2),          # fixed payload reservation
    (12, 0xF0000, -7),          # claimed payload size outside range
    (13, 0xFFFFFFFF, -7),       # no count overflow
    (16, 4, -7),                # core table must start at 0
    (19, 0x43FE0000, -2),       # cannot overlap descriptor
    (20, 0, -2),                # dispatch-count tampering
    (24, 42, -2),               # reserved word must be zero
])
def test_header_semantics_fail_closed(tmp_path, c_validate, word, new, error):
    spec = make_spec(tmp_path)
    _, head, payload = deployment(spec)
    mutated = with_header_word(head, word, new)
    assert mutated != head
    assert c_validate(mutated, payload)[0] == error


def test_checksum_and_exact_file_length_guards(tmp_path, c_validate):
    spec = make_spec(tmp_path)
    _, head, payload = deployment(spec)
    assert c_validate(head, payload)[0] == 0
    assert c_validate(head[:-1], payload)[0] == -2
    assert c_validate(head, payload[:-1])[0] == -7
    p = bytearray(payload)
    p[0] ^= 1
    assert c_validate(head, bytes(p))[0] == -3
    h = bytearray(head)
    h[40] ^= 1
    assert c_validate(bytes(h), payload)[0] == -2 or (
        c_validate(bytes(h), payload)[0] == -3
    )


@pytest.mark.parametrize("entry,expected", [
    ("duplicate", -4),
    ("bad_axon", -4),
    ("bad_event", -5),
    ("bad_rank", -5),
    ("bad_checkpoint", -6),
    ("dup_checkpoint", -6),
])
def test_semantic_mutation_even_if_crcs_recomputed(
    tmp_path, c_validate, entry, expected
):
    spec = make_spec(tmp_path)
    _, head, original = deployment(spec)
    payload = bytearray(original)
    w = struct.unpack("<64I", head)
    core_b = 32
    event_b = w[17]
    check_b = w[18]
    if entry == "duplicate":
        struct.pack_into("<I", payload, core_b, 2)  # first core id is 2
    elif entry == "bad_axon":
        struct.pack_into("<I", payload, 20, 4096)
    elif entry == "bad_event":
        struct.pack_into("<I", payload, event_b + 8, 999)
    elif entry == "bad_rank":
        # The third entry is lower service rank than the second;
        # CRC recomputation must not bypass order verification.
        struct.pack_into("<I", payload, event_b + 2 * 16 + 4, 2)
    elif entry == "bad_checkpoint":
        struct.pack_into("<I", payload, check_b + 8, 42)
    else:
        # Duplicate checkpoint requires an extra row and a valid
        # header that includes it. This is semantic, not length failure.
        payload.extend(payload[check_b:check_b + 16])
        head = with_header_word(head, 14, 2)
        head = with_header_word(head, 12, len(payload))
    mutated = bytes(payload)
    head = with_header_word(head, 22, zlib.crc32(mutated))
    assert c_validate(head, mutated)[0] == expected


def test_invalid_spec_fails_before_writing_artifacts(tmp_path):
    spec_path = make_spec(tmp_path)
    data = json.loads(spec_path.read_text())
    data["events"].append({"timestep": 99, "core": 2, "axon": 12})
    spec_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="timestep"):
        mod.build(spec_path, tmp_path / "unwritten")
    assert not (tmp_path / "unwritten" / "p05_header.bin").exists()


def test_p03_fixture_interoperability_keeps_frozen_model_unchanged(
    tmp_path, c_validate
):
    p03 = tmp_path / "p03_golden"
    proc = subprocess.run([
        sys.executable, str(P03), "--output-dir", str(p03),
        "--timesteps", "7",
    ], capture_output=True, text=True, timeout=90)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    spec_path = tmp_path / "from_p03.json"
    mod.from_p03_fixture(p03, spec_path)
    manifest, header, payload = deployment(spec_path)
    ret, summary = c_validate(header, payload)
    assert ret == 0
    assert summary.core_count == 5
    assert summary.timesteps == 7
    assert summary.event_count == 35
    assert manifest["logical_core_ids_in_service_order"] == [0, 1, 2, 3, 4]
    for cid in range(5):
        assert (spec_path.parent / "out" /
                f"core{cid}_initial.bin").read_bytes() == (
                    p03 / f"core{cid}_initial.bin").read_bytes()
    assert struct.unpack_from("<I", (p03 / "p03_run_config.bin").read_bytes())[0] == 0x50334346
