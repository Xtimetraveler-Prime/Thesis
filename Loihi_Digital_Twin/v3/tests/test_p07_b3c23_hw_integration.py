"""P07-B.3c2/3 native original P03 adapter link and fake-bus data-plane gate.

This is a *host fake register bus*, NOT a KV260 run, FPGA performance,
standalone A53 firmware artifact or physical P02 DDR coherence proof.
"""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_p03_original_adapter_27_core_lru_and_next_bank_insertion(tmp_path):
    cc = shutil.which("cc") or shutil.which("gcc")
    assert cc, "A native C11 compiler is required"
    out = tmp_path / "p07_b3c23"
    compile_result = subprocess.run(
        [cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
         "-O1",
         "-I", str(ROOT / "software/p07/include"),
         "-I", str(ROOT / "software/p03/include"),
         "-I", str(ROOT / "software/p05/include"),
         *[
             str(ROOT / path)
             for path in (
                 "software/p03/p03_hw_adapter.c",
                 "software/p07/p07_b3_pager.c",
                 "software/p07/p07_b2_packet.c",
                 "software/p07/p07_b3c_packet_bridge.c",
                 "software/p07/p07_b3c2_hw_scheduler.c",
                 "software/p07/p07_b3c3_next_commit.c",
                 "tests/native/p07_b3c23_hw_scheduler_harness.c",
             )
         ],
         "-o", str(out)],
        check=False, capture_output=True, text=True,
    )
    assert compile_result.returncode == 0, (
        "P07-B.3c2/3 strict C11 compiler failed\n"
        f"EXIT: {compile_result.returncode}\n"
        f"STDOUT:\n{compile_result.stdout}\n"
        f"GCC/CLANG STDERR:\n{compile_result.stderr}"
    )
    run = subprocess.run(
        [str(out)], check=False, capture_output=True, text=True, timeout=120
    )
    assert run.returncode == 0, (
        "P07-B.3c2/3 compiled but native harness failed\n"
        f"EXIT: {run.returncode}\n"
        f"STDOUT:\n{run.stdout}\nSTDERR:\n{run.stderr}"
    )
    assert run.stdout.strip() == "P07_B3C23_REAL_P03_NATIVE_FAKE_BUS_PASS=1"
