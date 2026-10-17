"""P07-A2 autonomous batch header and exact wire/native parsing gates."""
from __future__ import annotations

import ctypes
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import zlib

import pytest

from loihi_twin_v2.p07_a1_ingress import encode_ingress
from loihi_twin_v2.p07_a2_batch import (
    COMPILED_FINGERPRINT, DDR_SHA256, create_batch, parse_batch, write_batch,
)

ROOT = Path(__file__).resolve().parents[1]
AXONS = tuple((index * 73 + 17) % 4096 for index in range(784))


def make_record(first_pixel: int = 0) -> bytes:
    return encode_ingress(bytes([first_pixel] + [0]*783), AXONS,
                          ddr_sha256=DDR_SHA256,
                          deployment_fingerprint=COMPILED_FINGERPRINT)


class BatchInfo(ctypes.Structure):
    _fields_ = [("frame_count", ctypes.c_uint32),
                ("trace_frame", ctypes.c_uint32)]


@pytest.fixture(scope="module")
def c_batch(tmp_path_factory):
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if cc is None:
        pytest.skip("native C11 compiler unavailable")
    out = tmp_path_factory.mktemp("a2batch") / "batch.so"
    result = subprocess.run([
        cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-fPIC", "-shared", "-O2",
        str(ROOT / "software/p07/p07_a2_batch.c"), "-o", str(out),
    ], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    fn = ctypes.CDLL(str(out)).p07_a2_batch_validate
    fn.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
                   ctypes.POINTER(BatchInfo)]
    fn.restype = ctypes.c_int
    return fn


def check_c(fn, header: bytes) -> tuple[int, BatchInfo]:
    arr = (ctypes.c_uint8 * len(header)).from_buffer_copy(header)
    info = BatchInfo()
    rc = fn(arr, len(header), ctypes.byref(info))
    return rc, info


@pytest.mark.parametrize("count", [1, 2, 4, 16])
def test_batch_python_c_parity(c_batch, count):
    records = tuple(make_record((index * 17) % 256) for index in range(count))
    header, payload = create_batch(records, trace_frame=count - 1)
    assert len(header) == 64
    assert len(payload) == 2480 * count
    assert parse_batch(header, payload) == records
    status, info = check_c(c_batch, header)
    assert status == 0
    assert (info.frame_count, info.trace_frame) == (count, count - 1)


def fix_crc(h: bytearray) -> bytes:
    struct.pack_into("<I", h, 32, 0)
    struct.pack_into("<I", h, 32, zlib.crc32(h))
    return bytes(h)


@pytest.mark.parametrize("offset,value", [
    (0,0), (8,2), (12,0), (12,17), (16,1), (20,1),
    (24,1), (28,9), (36,1), (63,1),
])
def test_rechecksummed_mutation_fail_closed(c_batch, offset, value):
    h, p = create_batch((make_record(),), trace_frame=0)
    bad = bytearray(h)
    if offset in (0, 36, 63):
        bad[offset] = value if value else 1
    else:
        struct.pack_into("<I", bad, offset, value)
    invalid = fix_crc(bad)
    with pytest.raises(ValueError):
        parse_batch(invalid, p)
    assert check_c(c_batch, invalid)[0] != 0


def test_truncated_crc_corrupt_and_wrong_frame_model_rejected(c_batch):
    head, data = create_batch((make_record(),))
    for bad in (head[:-1], head + bytes(1), bytes([head[0]^1])+head[1:],
                head[:28]+bytes([head[28]^1])+head[29:]):
        with pytest.raises(ValueError):
            parse_batch(bad, data)
        assert check_c(c_batch, bad)[0] != 0
    with pytest.raises(ValueError):
        parse_batch(head, data[:-1])
    wrong = encode_ingress(bytes(784), AXONS, ddr_sha256="12"*32,
                           deployment_fingerprint=COMPILED_FINGERPRINT)
    with pytest.raises(ValueError):
        create_batch((wrong,))
    with pytest.raises(ValueError):
        create_batch(tuple(make_record() for _ in range(17)))


def test_static_batch_manifest_and_no_overwrite(tmp_path):
    a = tmp_path / "imageA.bin"
    b = tmp_path / "imageB.bin"
    a.write_bytes(make_record())
    b.write_bytes(make_record(255))
    dest = tmp_path / "deployment"
    manifest = write_batch((a,b),dest,trace_frame=1)
    assert manifest["frame_count"] == 2 and manifest["trace_frame"] == 1
    header = (dest / "p07_a2_header_64.bin").read_bytes()
    data = (dest / "p07_a2_ingress_payload.bin").read_bytes()
    assert parse_batch(header,data) == (a.read_bytes(), b.read_bytes())
    assert manifest["sha256"]["payload"] == hashlib.sha256(data).hexdigest()
    assert (dest / "p07_a2_mailbox_zero_64k.bin").stat().st_size == 65536
    with pytest.raises(FileExistsError):
        write_batch((a,b),dest,trace_frame=0)
