"""SHA-256 implementation is independently compared with Python hashlib."""
import ctypes
import hashlib
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def c_hash(tmp_path_factory):
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if cc is None:
        pytest.skip("native C compiler unavailable")
    out = tmp_path_factory.mktemp("p07_sha") / "sha256.so"
    proc = subprocess.run([
        cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-O2", "-fPIC", "-shared",
        str(ROOT / "software/p07/p07_a2_sha256.c"), "-o", str(out),
    ], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    fn = ctypes.CDLL(str(out)).p07_a2_sha256
    fn.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
                   ctypes.POINTER(ctypes.c_uint8)]
    fn.restype = None
    return fn


@pytest.mark.parametrize("length", [0, 1, 2, 3, 55, 56, 57, 63, 64, 65,
                                     119, 120, 127, 128, 129, 4096, 524288])
def test_native_matches_reference(c_hash, length):
    data = bytes((i * 97 + i // 23) % 256 for i in range(length))
    data_buf = (ctypes.c_uint8 * max(1, length))()
    for i, value in enumerate(data):
        data_buf[i] = value
    out = (ctypes.c_uint8 * 32)()
    c_hash(data_buf, length, out)
    assert bytes(out) == hashlib.sha256(data).digest()
