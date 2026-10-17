"""A53 glue source syntax smoke with minimal vendor-header shims.

This is NOT a Vitis cross-compile, ELF, or KV260 acceptance. It catches
portable C/API signature drift before requesting native vendor tools.
"""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_a53_board_source_compiles_with_vendor_header_signatures(tmp_path):
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if cc is None:
        pytest.skip("native C11 compiler not available")
    (tmp_path / "xil_cache.h").write_text(
        "#include <stdint.h>\n"
        "#include <stddef.h>\n"
        "typedef intptr_t INTPTR;\n"
        "extern void Xil_DCacheInvalidateRange(INTPTR,uint32_t);\n"
        "extern void Xil_DCacheFlushRange(INTPTR,uint32_t);\n",
        encoding="utf-8",
    )
    (tmp_path / "xil_io.h").write_text(
        "#include <stdint.h>\n"
        "#include <stddef.h>\n"
        "typedef uintptr_t UINTPTR;\n"
        "extern uint32_t Xil_In32(UINTPTR);\n"
        "extern void Xil_Out32(UINTPTR,uint32_t);\n",
        encoding="utf-8",
    )
    command = [
        cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-fsyntax-only",
        "-I", str(tmp_path),
        "-I", str(ROOT / "software/p07/include"),
        "-I", str(ROOT / "software/p03/include"),
        str(ROOT / "software/p07/p07_a2_board.c"),
    ]
    result = subprocess.run(command, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    board = (ROOT / "software/p07/p07_a2_board.c").read_text(encoding="utf-8")
    assert "active_runtime->current_timestep" in board
    assert "tick=rt.current_timestep" not in board
    assert "P07_A2_KV260_A53_FROZEN_TRACK_A_V1_TRACE_CONTEXT_FIX" in board
