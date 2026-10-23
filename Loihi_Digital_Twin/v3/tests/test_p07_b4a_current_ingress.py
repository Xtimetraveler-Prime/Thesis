"""P07-B.4a ORIGINAL P03 adapter / B1.3 exact CURRENT merge fake-bus gate.
No KV260 execution, no real A53 ELF, and no B2 official MNIST TEST.
"""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_original_p03_current_event_ingress_and_capacities(tmp_path):
    cc = shutil.which("cc") or shutil.which("gcc")
    assert cc, "native C11 compiler required"
    executable = tmp_path / "p07_b4a_current_ingress"
    cmd = [
        cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic", "-O1",
        "-I", str(ROOT / "software/p07/include"),
        "-I", str(ROOT / "software/p03/include"),
        "-I", str(ROOT / "software/p05/include"),
        str(ROOT / "software/p03/p03_hw_adapter.c"),
        str(ROOT / "software/p07/p07_b3_pager.c"),
        str(ROOT / "software/p07/p07_b2_ingress.c"),
        str(ROOT / "software/p07/p07_b4a_current_ingress.c"),
        str(ROOT / "tests/native/p07_b4a_current_ingress_harness.c"),
        "-o", str(executable),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, (
        f"Strict C11 compile failed: {result.returncode}\n{result.stderr}"
    )
    run = subprocess.run([str(executable)], capture_output=True, text=True,
                         timeout=120)
    assert run.returncode == 0, (
        f"P07-B.4a fake-bus runtime failed: {run.returncode}\n"
        f"STDOUT:\n{run.stdout}\nSTDERR:\n{run.stderr}"
    )
    assert run.stdout.strip() == "P07_B4A_CURRENT_INGRESS_P03_FAKE_BUS_PASS=1"
