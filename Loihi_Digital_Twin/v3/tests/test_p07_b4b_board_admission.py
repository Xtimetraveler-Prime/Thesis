"""P07-B.4b original P03 READ-ONLY boot admission + bounded DDR access.

Fake Xilinx BSP host gate only. Does not claim an A53 ELF, PL execution,
PS ownership, independent HLS provenance, or B2 official TEST opening.
"""
from pathlib import Path
import shutil
import subprocess
ROOT = Path(__file__).resolve().parents[1]

def test_read_only_shell_admission_and_event_only_ddr_reader(tmp_path):
    cc=shutil.which("cc") or shutil.which("gcc")
    assert cc
    out=tmp_path/"p07_b4b_readonly"
    cmd=[
        cc,"-std=c11","-Wall","-Wextra","-Werror","-pedantic","-O1",
        "-DP07_B4B_TEST_HOST_BSP=1",
        "-I",str(ROOT/"tests/native/p07_b4b_stub"),
        "-I",str(ROOT/"software/p03/include"),
        "-I",str(ROOT/"software/p07/include"),
        "-I",str(ROOT/"software/p05/include"),
        str(ROOT/"software/p03/p03_hw_adapter.c"),
        str(ROOT/"software/p07/p07_b3_pager.c"),
        str(ROOT/"software/p07/p07_b4b_mutable_audit.c"),
        str(ROOT/"software/p07/p07_b4b_board_admission.c"),
        str(ROOT/"software/p07/p07_b4b_xilinx_platform.c"),
        str(ROOT/"tests/native/p07_b4b_admission_harness.c"),
        "-o",str(out),
    ]
    result=subprocess.run(cmd,capture_output=True,text=True)
    assert result.returncode==0,(
        f"strict C11 fake BSP compile failed: {result.returncode}\n"
        f"{result.stdout}\n{result.stderr}")
    run=subprocess.run([str(out)],capture_output=True,text=True,timeout=45)
    assert run.returncode==0,(
        f"fake BSP runtime failed: {run.returncode}\n"
        f"{run.stdout}\n{run.stderr}")
    assert run.stdout.strip()=="P07_B4B_READONLY_A53_ADMISSION_NATIVE_PASS=1"
