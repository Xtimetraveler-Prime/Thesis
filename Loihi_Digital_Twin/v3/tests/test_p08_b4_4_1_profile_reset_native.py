"""P08-B4.4.1 portable native DIFFERENTIAL reset profiler, no board."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]
SW=ROOT/"software"
P08=SW/"p08"
P07=SW/"p07"

def test_native_original_27_core_sized_sha_cache_copy_and_fault_equivalence(tmp_path):
    cc=shutil.which("gcc") or shutil.which("cc")
    if not cc:
        pytest.skip("native C compiler unavailable")
    exe=tmp_path/"p08_b44_original_diff"
    cmd=[
        cc,"-std=c11","-O2","-Wall","-Wextra","-Werror",
        "-I",str(P08),"-I",str(P07/"include"),
        str(ROOT/"tests/native/p08_b44_reset_profile_diff.c"),
        str(P08/"p08_b2_context_reset.c"),
        str(P08/"p08_b4_4_profile_reset.c"),
        str(P07/"p07_a2_sha256.c"),
        "-o",str(exe),
    ]
    result=subprocess.run(cmd,cwd=tmp_path,capture_output=True,
                          text=True,timeout=90)
    assert result.returncode==0, result.stderr
    done=subprocess.run([str(exe)],cwd=tmp_path,capture_output=True,
                        text=True,timeout=180)
    assert done.returncode==0,done.stdout+"\n"+done.stderr
    for marker in (
        "P08_B4_4_1_ORIGINAL_RESET_VS_PROFILED_MUTABLE_BYTE_EQUAL_PASS=1",
        "P08_B4_4_1_RESET_ORIGINAL_27_SHA_SOURCE_DEST_EQUIVALENCE_PASS=1",
        "P08_B4_4_1_ORIGINAL_POISON_FAULT_AND_NO_PARTIAL_COPY_EQUIVALENCE_PASS=1",
        "P08_B4_4_1_PHYSICAL_KV260_PROFILE_EXECUTED=0",
    ):
        assert done.stdout.splitlines().count(marker)==1

def test_profiler_is_strictly_separate_from_accepted_firmware():
    original=(P08/"p08_b2_context_reset.c").read_text()
    accepted=(P08/"p08_b2_3_image_only_a53.c").read_text()
    profiler=(P08/"p08_b4_4_profile_reset.c").read_text()
    header=(P08/"p08_b4_4_profile_reset.h").read_text()
    assert "p08_b44_profile_reset_image" not in original
    assert "p08_b44_profile_reset_image" not in accepted
    assert "p08_b44_profile_reset_image" in profiler
    assert "p08_b44_profile_reset_image" in header
    assert "p08_b2_reset_image" in accepted
    assert "p08_b2_reset_image" in original
    assert "p07_a2_sha256" in profiler
    assert "memcpy(dest,src,P08_B2_CONTEXT_STRIDE)" in profiler
    assert "P08_B44_SOURCE_SHA256" in profiler
    assert "P08_B44_MUTABLE_SHA256" in profiler
    assert "P08_B44_MUTABLE_CACHE_CLEAN_INVALIDATE" in profiler
    assert "P08_B44_MUTABLE_MEMCPY" in profiler
    assert "P08_B44_RESET_PROFILE_VERSION 1u" in header
    assert "xsdb" not in profiler.lower()
    assert "xil_" not in profiler.lower()
    assert "P08_B2_CONTEXT_TOTAL==14155776u" in profiler
