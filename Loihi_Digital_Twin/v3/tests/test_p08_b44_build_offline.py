"""P08-B4.4.2 separate profiler Vitis source/build staging, no board."""
from __future__ import annotations

from pathlib import Path
import hashlib
import shutil
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
