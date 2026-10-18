"""A4.2b native portable supervisor and standalone A53 glue syntax gates.

These tests do NOT use Vitis, a cross-compiled ELF, any physical FPGA, or
official MNIST TEST images. Mock per-frame successes/failures prove that
journal completion cannot precede a finished frame or hide an error.
"""
from __future__ import annotations

import ctypes
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
P07 = ROOT/"software/p07"


class Callbacks(ctypes.Structure):
    pass


ExecuteFn = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32)
ProgressFn = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32,
                              ctypes.c_uint32, ctypes.c_uint32)
Callbacks._fields_ = [
    ("cookie", ctypes.c_void_p),
    ("execute_and_commit_image", ExecuteFn),
    ("commit_progress", ProgressFn),
]


@pytest.fixture(scope="module")
def lib(tmp_path_factory):
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("no native C11 compiler available")
    dst=tmp_path_factory.mktemp("a4super")/"a4sup.so"
    proc=subprocess.run([
        cc,"-std=c11","-pedantic","-Werror","-Wall","-Wextra",
        "-O2","-fPIC","-shared",str(P07/"p07_a4_supervisor.c"),
        "-o",str(dst)
    ], capture_output=True,text=True)
    assert proc.returncode == 0,proc.stderr
    api=ctypes.CDLL(str(dst))
    api.p07_a4_run_images.argtypes = [
        ctypes.c_uint32,ctypes.POINTER(Callbacks),
        ctypes.POINTER(ctypes.c_uint32),ctypes.POINTER(ctypes.c_uint32)
    ]
    api.p07_a4_run_images.restype=ctypes.c_int
    return api


def run(lib, count, image_fail=None, progress_fail=None):
    events=[]
    error_once=False

    def on_image(_cookie, frame):
        events.append(("frame",frame))
        return -1 if frame==image_fail else 0

    def on_progress(_cookie, status,done,fault):
        nonlocal error_once
        events.append(("progress",status,done,fault))
        if progress_fail == (status,done) and not error_once:
            error_once=True
            return -1
        return 0

    cb0=ExecuteFn(on_image)
    cb1=ProgressFn(on_progress)
    callbacks=Callbacks(None,cb0,cb1)
    done=ctypes.c_uint32(12345)
    failure=ctypes.c_uint32(99)
    rc=lib.p07_a4_run_images(count,ctypes.byref(callbacks),
                              ctypes.byref(done),ctypes.byref(failure))
    return rc,done.value,failure.value,events


def test_success_commits_every_frame_before_next_progress(lib):
    rc,done,fail,ev=run(lib,16)
    assert (rc,done,fail)==(0,16,0xFFFFFFFF)
    assert ev[0]==("progress",0,0,0xFFFFFFFF)
    for frame in range(16):
        assert ev[1+2*frame]==("frame",frame)
        assert ev[2+2*frame]==("progress",0,frame+1,0xFFFFFFFF)
    assert ev[-1]==("progress",0x600D600D,16,0xFFFFFFFF)


def test_first_frame_failure_preserves_exact_completed_prefix(lib):
    rc,done,fail,ev=run(lib,16,image_fail=0)
    assert (rc,done,fail)==(-2,0,0)
    assert ev==[
        ("progress",0,0,0xFFFFFFFF),
        ("frame",0),
        ("progress",0xDEAD0001,0,0),
    ]


def test_midframe_failure_no_skip_and_no_false_terminal_success(lib):
    rc,done,fail,ev=run(lib,16,image_fail=7)
    assert (rc,done,fail)==(-2,7,7)
    assert ("progress",0xDEAD0001,7,7) in ev
    assert not any(x[0]=="frame" and x[1]>7 for x in ev)
    assert not any(x[0]=="progress" and x[1]==0x600D600D for x in ev)


def test_progress_storage_error_fails_and_cannot_advance(lib):
    rc,done,fail,ev=run(lib,16,progress_fail=(0,3))
    assert (rc,done,fail)==(-3,3,2)
    assert ("progress",0xDEAD0002,3,2) in ev
    assert not any(x[0]=="frame" and x[1]>=3 for x in ev)
    assert not any(x[0]=="progress" and x[1]==0x600D600D for x in ev)


def test_bad_count_never_runs_any_frames(lib):
    for count in (0,10001):
        rc,done,fail,events=run(lib,count)
        assert (rc,done,fail)==(-1,0,0xFFFFFFFF)
        assert not events


def test_separate_a53_glue_syntax_matches_vendor_signatures(tmp_path):
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if cc is None: pytest.skip("native C11 compiler not available")
    (tmp_path/"xil_cache.h").write_text(
        "#include <stdint.h>\n#include <stddef.h>\n"
        "typedef intptr_t INTPTR;\n"
        "extern void Xil_DCacheInvalidateRange(INTPTR,uint32_t);\n"
        "extern void Xil_DCacheFlushRange(INTPTR,uint32_t);\n")
    (tmp_path/"xil_io.h").write_text(
        "#include <stdint.h>\n#include <stddef.h>\n"
        "typedef uintptr_t UINTPTR;\n"
        "extern uint32_t Xil_In32(UINTPTR);\n"
        "extern void Xil_Out32(UINTPTR,uint32_t);\n")
    proc=subprocess.run([
        cc,"-std=c11","-Wall","-Wextra","-Werror","-pedantic",
        "-fsyntax-only","-I",str(tmp_path),
        "-I",str(P07/"include"),"-I",str(ROOT/"software/p03/include"),
        str(P07/"p07_a4_board.c")
    ], capture_output=True,text=True)
    assert proc.returncode == 0,proc.stdout+proc.stderr
    text=(P07/"p07_a4_board.c").read_text()
    assert "P07_A4_2B_PERSISTENT_KV260_A53_FROZEN_TRACK_A_V1" in text
    assert "p07_a2_run_frame" in text
    assert "p07_a4_run_images" in text
    assert "active_runtime->current_timestep" in text
    assert "p07_a4_validate_staging" in text
    assert "commit_frame_result" in text
    assert "P07_A4_JOURNAL_BASE" in text
    assert "P07_A4_TRACE_BASE" in text
    assert "p07_a4_make_ingress" in text


def test_separate_vitis_builder_inputs_and_no_legacy_a2_mutation():
    import ast
    path=P07/"build_p07_a4.py"
    tree=ast.parse(path.read_text())
    values={}
    for expr in tree.body:
        if isinstance(expr,ast.Assign) and len(expr.targets)==1 and isinstance(expr.targets[0],ast.Name):
            if expr.targets[0].id in ("SOURCES","HEADERS","P07_HEADERS"):
                try: values[expr.targets[0].id]=ast.literal_eval(expr.value)
                except ValueError: pass
    sources=values["SOURCES"]
    assert "p07_a4_board.c" in sources
    assert "p07_a4_stream.c" in sources
    assert "p07_a4_supervisor.c" in sources
    assert "p07_a2_runtime.c" in sources
    assert "p07_a2_board.c" not in sources
    assert "p07_a2_batch.c" not in sources
    shell=(ROOT/"scripts/build_p07_a4.sh").read_text()
    assert "P07_A4_2B_PERSISTENT_KV260_A53_FROZEN_TRACK_A_V1" in shell
    assert 'P07_A4_BUILD_DIR' in shell
    assert "refuses to overwrite" in shell
    assert "readelf" in shell
    assert "P07_A4_VITIS_NATIVE_GATE_PASS=1" in shell
