"""P07-A2.1 REAL P03 C scheduler host-execution with mocked PL/DDR.

This tests control correctness, not FPGA numerical accuracy. Official MNIST
TEST is never opened; input images are synthetic, label-free patterns.
"""
from pathlib import Path
import shutil
import subprocess

import pytest

from loihi_twin_v2.p07_a1_ingress import encode_ingress

ROOT = Path(__file__).resolve().parents[1]
DDR = "9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955"
FINGERPRINT = "e612a971cda11fae3f1be215c0ca3ed7de7b2af7339446e926ce559658db2f7f"
MAP = tuple((i * 73 + 17) % 4096 for i in range(784))


@pytest.fixture(scope="module")
def scheduler_binary(tmp_path_factory):
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if cc is None:
        pytest.skip("native C11 compiler required; run on user's Linux terminal")
    out = tmp_path_factory.mktemp("p07_a2") / "p07_a2_probe"
    result = subprocess.run([
        cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic", "-O2",
        "-I", str(ROOT / "software/p03/include"),
        str(ROOT / "software/p03/p03_runtime.c"),
        str(ROOT / "software/p07/p07_a1_ingress.c"),
        str(ROOT / "software/p07/p07_a2_runtime.c"),
        str(ROOT / "software/p07/p07_a2_probe.c"),
        "-o", str(out),
    ], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout
    return out


def _record(image: bytes) -> bytes:
    return encode_ingress(image, MAP, ddr_sha256=DDR,
                          deployment_fingerprint=FINGERPRINT)


def test_two_frame_reset_and_exact_one_step_bank_ownership(scheduler_binary, tmp_path):
    black, white = tmp_path / "black.bin", tmp_path / "white.bin"
    black.write_bytes(_record(bytes(784)))
    white.write_bytes(_record(bytes([255]) * 784))
    cmd = subprocess.run([str(scheduler_binary), str(black), str(white)],
                         capture_output=True, text=True)
    assert cmd.returncode == 0, cmd.stderr + cmd.stdout
    assert "frame=0 inputs=0 class=0 silent=1 routes=25 dropped=1" in cmd.stdout
    assert "frame=1 inputs=19600 class=7 silent=0 routes=25 dropped=1" in cmd.stdout
    assert "P07_A2_NATIVE_SCHEDULER_PASS=1" in cmd.stdout


def test_empty_and_pattern_frames_reset_without_cross_contamination(scheduler_binary, tmp_path):
    # Ensure frame 0 is non-silent and second frame is silent; no leak.
    first, second = tmp_path / "first.bin", tmp_path / "second.bin"
    first.write_bytes(_record(bytes([255] + [0] * 783)))
    second.write_bytes(_record(bytes(784)))
    cmd = subprocess.run([str(scheduler_binary), str(first), str(second)],
                         capture_output=True, text=True)
    assert cmd.returncode == 0, cmd.stderr + cmd.stdout
    assert "frame=0 inputs=25 class=7 silent=0" in cmd.stdout
    assert "frame=1 inputs=0 class=0 silent=1" in cmd.stdout


def test_truncated_record_fails_before_mock_hardware(scheduler_binary, tmp_path):
    first, truncated = tmp_path / "first.bin", tmp_path / "truncated.bin"
    first.write_bytes(_record(bytes(784)))
    truncated.write_bytes(_record(bytes(784))[:-1])
    cmd = subprocess.run([str(scheduler_binary), str(first), str(truncated)],
                         capture_output=True, text=True)
    assert cmd.returncode != 0
