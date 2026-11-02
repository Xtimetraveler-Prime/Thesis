"""P08-B4.4.2 separate profiler Vitis source/build staging, no board."""
from __future__ import annotations

from pathlib import Path
import hashlib
import shutil
import re
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"software/p08"))
import build_p08_b44_profile_full1024 as builder

def file_for(name:str)->Path:
    for p in (
        ROOT/"software/p08"/name,
        ROOT/"software/p07"/name,
        ROOT/"software/p07/include"/name,
        ROOT/"software/p03"/name,
        ROOT/"software/p03/include"/name,
        ROOT/"software/p05/include"/name,
    ):
        if p.is_file():return p
    raise AssertionError("missing original source "+name)

def prepare(tmp_path:Path)->Path:
    root=tmp_path/"synthetic_original_profile_stage"
    root.mkdir()
    for name in builder.SOURCES+builder.HEADERS:
        if name=="p08_b2_2_original_context_sha256.h":
            data=("#include <stdint.h>\n"
                  "const uint8_t p08_b2_original_context_sha256[27][32]={{1}};\n")
        else:
            data=file_for(name).read_text()
        if name=="p07_b2_packet.h":
            assert "#define P07_B2_MAX_ROUTE_BINDINGS 8192u" in data
            data=data.replace("#define P07_B2_MAX_ROUTE_BINDINGS 8192u",
                              "#define P07_B2_MAX_ROUTE_BINDINGS 10000u")
        if name=="p07_a2_sha256.c":
            data=data.replace('#include "include/p07_a2_sha256.h"',
                              '#include "p07_a2_sha256.h"')
        (root/name).write_text(data)
    return root

def test_separate_profiler_only_source_set_and_vitis_source_admission(tmp_path):
    stage=prepare(tmp_path)
    assert builder.APP=="p08_b44_reset_profile_1024"
    assert builder.IDENTITY=="P08_B44_ORIGINAL_27CORE_RESET_PROFILE_1024_A53_V1"
    assert builder.SOURCES[0]=="p08_b44_profile_full1024_a53.c"
    assert "p08_b4_4_profile_reset.c" in builder.SOURCES
    assert "p08_b2_context_reset.c" in builder.SOURCES
    assert "p08_b4_4_profile_reset.h" in builder.HEADERS
    assert "p08_b2_3_image_only_a53.c" not in builder.SOURCES
    assert len(builder.SOURCES)==len(set(builder.SOURCES))
    assert len(builder.HEADERS)==len(set(builder.HEADERS))
    assert set(builder.SOURCES).isdisjoint(builder.HEADERS)
    builder.check_stage(stage)
    (stage/"p08_b44_profile_full1024_a53.c").write_text("wrong identity")
    with pytest.raises(ValueError):
        builder.check_stage(stage)

@pytest.mark.parametrize("which",[
    "p08_b4_4_profile_reset.c",
    "p08_b4_4_profile_reset.h",
    "p08_b2_context_reset.c",
    "p08_b2_2_original_context_sha256.h",
])
def test_source_stage_missing_fails_closed(tmp_path,which):
    stage=prepare(tmp_path)
    (stage/which).unlink()
    with pytest.raises(ValueError,match="source stage incomplete"):
        builder.check_stage(stage)

def test_new_profiled_a53_portable_gcc_declarations_only_syntax(tmp_path):
    compiler=shutil.which("gcc") or shutil.which("cc")
    if not compiler:pytest.skip("C11 compiler unavailable")
    stage=prepare(tmp_path)
    (stage/"xil_cache.h").write_text(
        "#ifndef FAKE_CACHE_H\n#define FAKE_CACHE_H\n"
        "#include <stdint.h>\n#include <stddef.h>\n"
        "typedef uintptr_t INTPTR;\n"
        "void Xil_DCacheInvalidateRange(INTPTR,uint32_t);\n"
        "void Xil_DCacheFlushRange(INTPTR,uint32_t);\n#endif\n")
    (stage/"xil_io.h").write_text(
        "#ifndef FAKE_IO_H\n#define FAKE_IO_H\n"
        "#include <stdint.h>\ntypedef uintptr_t UINTPTR;\n"
        "uint32_t Xil_In32(UINTPTR);\nvoid Xil_Out32(UINTPTR,uint32_t);\n#endif\n")
    (stage/"xil_printf.h").write_text(
        "#ifndef FAKE_PRINTF_H\n#define FAKE_PRINTF_H\n"
        "int xil_printf(const char *,...);\n#endif\n")
    subprocess.run([
        compiler,"-std=c11","-fsyntax-only","-Wall","-Wextra",
        "-Werror","-pedantic","-I",str(stage),
        str(stage/"p08_b44_profile_full1024_a53.c"),
        str(stage/"p08_b4_4_profile_reset.c"),
    ],check=True,capture_output=True,text=True,timeout=45)

def test_new_Vitis_shell_safe_and_requires_signed_original(tmp_path):
    path=ROOT/"scripts/build_p08_b44_profile_full1024.sh"
    s=path.read_text()
    assert "xsdb " not in s.lower()
    assert "vivado -mode batch" not in s.lower()
    assert "P08_B44_BUILD_DIR" in s
    assert "P08_B44_ORIGINAL_ELF" in s
    assert "p08_b44_profile_elf_admission.py" in s
    assert "P08_B44_ORIGINAL_27CORE_RESET_PROFILE_1024_A53_V1" in s
    assert "P08_B44_EXPERIMENTAL_DESTRUCTIVE_JTAG_PERMISSION=NOT_GRANTED" in s
    assert "0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1" in s
    subprocess.run(["bash","-n",str(path)],capture_output=True,
                   check=True,text=True,timeout=15)


def test_actual_shell_cp_lists_exactly_match_python_vitis_inventory():
    """The bug: shell staged old B2.3 main while builder wanted new B44 C/H.

    Parse the REAL six shell cp loops, not a separately invented
    test-only stage created from builder.SOURCES/HEADERS. This catches
    omissions, extras and resurrection of the frozen production main.
    """
    script=(ROOT/"scripts/build_p08_b44_profile_full1024.sh").read_text()
    source_loops=re.findall(
        r'for n in ([\s\S]*?); do\n\s*'
        r'cp -- "\$V3/software/(p08|p07|p03)/(include/)?\$n" '
        r'"\$BUILD/source/"',
        script,
    )
    assert len(source_loops)==6, "expected 3 .c and 3 .h source-stage loops"
    copies=[]
    for content,subsystem,include in source_loops:
        names=re.findall(r"\b[a-zA-Z][a-zA-Z0-9_]*\.[ch]\b",content)
        assert names, "empty real shell cp loop"
        assert len(names)==len(set(names)), "duplicate staged C/H"
        assert all(name.endswith(".h") for name in names) == bool(include)
        copies.extend(names)
    assert 'cp -- "$PIN_HEADER" "$BUILD/source/p08_b2_2_original_context_sha256.h"' in script
    assert 'cp -- "$V3/software/p05/include/p05_deployment.h" "$BUILD/source/"' in script
    copies.extend(["p08_b2_2_original_context_sha256.h","p05_deployment.h"])
    assert len(copies)==len(set(copies)), "shell has duplicate C/H copy"
    assert set(copies)==set(builder.SOURCES+builder.HEADERS), (
        "shell actually copies wrong Vitis C/H source set: "
        f"missing={set(builder.SOURCES+builder.HEADERS)-set(copies)}, "
        f"extra={set(copies)-set(builder.SOURCES+builder.HEADERS)}"
    )
    assert "p08_b2_3_image_only_a53.c" not in copies
    for required in (
        "p08_b44_profile_full1024_a53.c",
        "p08_b4_4_profile_reset.c",
        "p08_b4_4_profile_reset.h",
    ):
        assert copies.count(required)==1
    assert "--check-stage-only" in script
    assert script.index("--check-stage-only")<script.index("vitis -s")


def test_actual_stage_check_cli_accepts_right_sources_and_rejects_old_main(
        tmp_path,capsys):
    stage=prepare(tmp_path)
    assert builder.main(["--check-stage-only",str(stage)])==0
    result=capsys.readouterr()
    assert "P08_B44_ACTUAL_SHELL_STAGED_PROFILE_SOURCE_EXACT_PASS=1" in result.out
    assert "P08_B44_SOURCE_STAGE_CHECK_VITIS_INVOCATIONS=0" in result.out

    (stage/"p08_b44_profile_full1024_a53.c").unlink()
    (stage/"p08_b4_4_profile_reset.c").unlink()
    (stage/"p08_b4_4_profile_reset.h").unlink()
    (stage/"p08_b2_3_image_only_a53.c").write_text(
        "/* synthetic historical staging bug */\n")
    assert builder.main(["--check-stage-only",str(stage)])==3
    out=capsys.readouterr()
    for wrong in ("p08_b44_profile_full1024_a53.c",
                  "p08_b4_4_profile_reset.c",
                  "p08_b4_4_profile_reset.h",
                  "p08_b2_3_image_only_a53.c"):
        assert wrong in out.err
    assert builder.main(["--check-stage-only",str(stage),
                         "--workspace",str(tmp_path/"w")])==3
