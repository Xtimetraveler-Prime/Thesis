"""B4l 1st-epoch scheduler-to-original-P03 native bridge. NO BOARD.
Runs real unchanged B3a/B3c2/B3c3/P03 software with accepted fake bus.
"""
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def test_one_epoch_genuine_b3_scheduler_original_p03_adapter(tmp_path):
    compiler=shutil.which("cc") or shutil.which("gcc")
    assert compiler,"A C11 compiler is required to admit this milestone"
    exe=tmp_path/"b4l_b3_single_epoch"
    sources=(
        "software/p03/p03_hw_adapter.c",
        "software/p07/p07_b3_pager.c",
        "software/p07/p07_b2_packet.c",
        "software/p07/p07_b3c_packet_bridge.c",
        "software/p07/p07_b3c2_hw_scheduler.c",
        "software/p07/p07_b3c3_next_commit.c",
        "software/p07/p07_b4l_b3_epoch.c",
        "tests/native/p07_b4l_b3_epoch_harness.c",
    )
    result=subprocess.run(
        [compiler,"-std=c11","-Wall","-Wextra","-Werror","-pedantic",
         "-O1",
         "-I",str(ROOT/"software/p07/include"),
         "-I",str(ROOT/"software/p03/include"),
         "-I",str(ROOT/"software/p05/include"),
         "-I",str(ROOT/"tests/native"),
         *(str(ROOT/p) for p in sources),"-o",str(exe)],
        capture_output=True,text=True,timeout=90,
    )
    assert result.returncode==0,result.stderr
    actual=subprocess.run([str(exe)],capture_output=True,text=True,timeout=120)
    assert actual.returncode==0,actual.stderr+actual.stdout
    assert actual.stdout.splitlines()==[
        "P07_B4L_B3_NATIVE_ORIGINAL_P03_27_DISPATCH_BARRIER_PENDING_PASS=1",
        "P07_B4L_B3_NATIVE_UNVERIFIED_NEXT_NOT_ACKED=1",
        "P07_B4L_B3_NATIVE_DIRTY_EVICTION_FAULT_STICKY_PASS=1",
    ]


def test_first_epoch_has_no_fabricated_barrier_ack_or_inference_claim():
    source=(ROOT/"software/p07/p07_b4l_b3_epoch.c").read_text()
    header=(ROOT/"software/p07/include/p07_b4l_b3_epoch.h").read_text()
    assert "p07_b3c2_step(s,&op)" in source
    assert "p07_b3_next(s->pager,&next)" in source
    assert "r->barrier_acked=0u" in source
    assert "r->pending_barrier=1u" in source
    assert "p07_b3c2_barrier_ack(" not in source
    assert "p07_b3c3_commit(" not in source
    assert "P07_B3_CORES==27u" in source
    assert "no neural" not in header.lower() or "trained parity" in header.lower()
