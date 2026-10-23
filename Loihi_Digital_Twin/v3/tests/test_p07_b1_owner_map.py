"""P07-B.1 native C11 build/execution, without FPGA or B2 TEST."""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_native_p07_b1_layout_and_admission(tmp_path):
    cc = shutil.which("cc") or shutil.which("gcc")
    if cc is None:
        pytest.fail("P07-B.1 C11 native compiler is required (cc/gcc)")
    binary = tmp_path / "p07_b1_native"
    source = ROOT / "tests/native/p07_b1_owner_map_harness.c"
    command = [
        cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-I", str(ROOT / "software/p07/include"),
        "-I", str(ROOT / "software/p03/include"),
        "-I", str(ROOT / "software/p05/include"),
        str(source), "-o", str(binary),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    completed = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
    assert completed.stdout.strip() == "P07_B1_NATIVE_OWNER_MAP_PASS=1"
