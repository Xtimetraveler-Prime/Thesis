"""P08-B2.3 offline new A53 image-only source/build/ELF source gates.

Native source syntax with Xilinx DECLARATION-ONLY stubs, NO hardware/API
emulation: this is NOT Vitis 2025.2 linking and NOT physical PL proof.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"software/p08"))
import p08_b2_3_elf_admission as elf_gate
import build_p08_b2_3_image_only as build
import p08_b2_2_prepare_reset_pins as pins


def test_new_a53_source_isolated_and_includes_all_service_phases():
    src=(ROOT/"software/p08/p08_b2_3_image_only_a53.c").read_text()
    assert build.IDENTITY in src
    for exact in (
        "p08_b2_reset_bind(", "p08_b2_reset_image(",
        "p08_b2_encode_frame(", "p07_b4m_full_run(",
        "p03_hw_xilinx_fpd128_ready(",
        "p08_b2_meter_start(", "P08_B2_AFTER_STATE_RESTORE",
        "P08_B2_AFTER_B13_INGRESS", "P08_B2_AFTER_SCHEDULER_REINIT",
        "P08_B2_AFTER_ALL_26_TICKS", "P08_B2_AFTER_RECEIPT_VALIDATE",
        "P08_B2_AFTER_JOURNAL_COMMIT", "p08_b2_meter_finish(",
        "commit_journal(", "commit_timing(",
        "P08_B2_3_IMAGE_ONLY_1024_TERMINAL_DONE=1",
    ):
        assert exact in src
    assert "mrs %0, cntvct_el0" in src
    assert "mrs %0, cntfrq_el0" in src
    assert "P08_B2_3_ORIGINAL_27CORE_1024_IMAGE_ONLY_A53_V1" in src
    assert "P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V3" not in src


def test_vitis_build_source_set_has_no_accepted_old_main():
    assert build.SOURCES[0]=="p08_b2_3_image_only_a53.c"
    assert len(build.SOURCES)==len(set(build.SOURCES))
    assert len(build.HEADERS)==len(set(build.HEADERS))
    assert "p07_b4m_full_board_diag_v3.c" not in build.SOURCES
    assert "p08_b2_2_original_context_sha256.h" in build.HEADERS
    assert "p07_b4m_full_inference.c" in build.SOURCES


def test_new_image_only_xilinx_headers_syntax_compile_native_stubs(tmp_path):
    compiler=shutil.which("cc")
    assert compiler,"native C11 compiler required"
    source=(ROOT/"software/p08/p08_b2_3_image_only_a53.c")
    include=tmp_path/"isolated_staged_headers"
    include.mkdir()
    for name in build.HEADERS:
        if name=="p08_b2_2_original_context_sha256.h":
            rows=[{"logical_core_id":n,
                   "sha256":hashlib.sha256(bytes([n])).hexdigest()}
                  for n in range(27)]
            data=pins.generate_header(rows)
        elif (ROOT/"software/p08"/name).is_file():
            data=(ROOT/"software/p08"/name).read_text()
        elif (ROOT/"software/p07/include"/name).is_file():
            data=(ROOT/"software/p07/include"/name).read_text()
        elif (ROOT/"software/p03/include"/name).is_file():
            data=(ROOT/"software/p03/include"/name).read_text()
        else:
            data=(ROOT/"software/p05/include"/name).read_text()
        if name=="p07_b2_packet.h":
            assert "#define P07_B2_MAX_ROUTE_BINDINGS 8192u" in data
            data=data.replace("#define P07_B2_MAX_ROUTE_BINDINGS 8192u",
                              "#define P07_B2_MAX_ROUTE_BINDINGS 10000u")
        (include/name).write_text(data)
    (include/"xil_cache.h").write_text(
        "#ifndef FAKE_XIL_CACHE_H\n#define FAKE_XIL_CACHE_H\n"
        "#include <stdint.h>\n#include <stddef.h>\n"
        "typedef uintptr_t INTPTR;\n"
        "void Xil_DCacheInvalidateRange(INTPTR,uint32_t);\n"
        "void Xil_DCacheFlushRange(INTPTR,uint32_t);\n"
        "#endif\n")
    (include/"xil_io.h").write_text(
        "#ifndef FAKE_XIL_IO_H\n#define FAKE_XIL_IO_H\n"
        "#include <stdint.h>\ntypedef uintptr_t UINTPTR;\n"
        "uint32_t Xil_In32(UINTPTR);\nvoid Xil_Out32(UINTPTR,uint32_t);\n"
        "#endif\n")
    (include/"xil_printf.h").write_text(
        "#ifndef FAKE_XIL_PRINTF_H\n#define FAKE_XIL_PRINTF_H\n"
        "int xil_printf(const char *,...);\n#endif\n")
    subprocess.run([
        compiler,"-std=c11","-fsyntax-only","-Wall","-Wextra",
        "-Werror","-pedantic","-I",str(include),str(source),
    ],check=True,capture_output=True,text=True,timeout=30)


def make_elf(*,vaddr=0x1000,paddr=0x1000,memsz=0x1000,ident=True):
    elf_id=b"\\x7fELF\\x02\\x01\\x01"+bytes(9)
    header=struct.pack(elf_gate.ELF_HDR,elf_id,2,183,1,vaddr,
                       elf_gate.ELF_HDR_SIZE,0,0,elf_gate.ELF_HDR_SIZE,
                       elf_gate.PHDR_SIZE,1,0,0,0)
    ph=struct.pack(elf_gate.PHDR,1,5,0x1000,vaddr,paddr,64,memsz,0x1000)
    payload=(elf_gate.IDENTITY if ident else b"synthetic invalid ELF")
    return header+ph+bytes(0x1000-len(header)-len(ph))+payload.ljust(64,b"\\x00")


def test_aarch64_elf64_strict_low_ddr_load_and_entry():
    seg=elf_gate.load_segments(make_elf())
    assert len(seg)==1
    assert seg[0]["vaddr_start"]=="0x0000000000001000"
    assert seg[0]["paddr_end_exclusive"]=="0x0000000000002000"


@pytest.mark.parametrize("vaddr,paddr,memsz",[
    (0x40000000,0x40000000,0x1000),
    (0x3FFFF000,0x3FFFF000,0x2000),
    (0x1000,0x3FFFF000,0x2000),
    (0x1000,0x40000000,0x1000),
    (0x1000,0x1000,0),
])
def test_elf_load_rejects_proposed_p03_64m_overlap_or_zero(vaddr,paddr,memsz):
    with pytest.raises(elf_gate.ElfNoGo):
        elf_gate.load_segments(make_elf(vaddr=vaddr,paddr=paddr,memsz=memsz))


def test_elf_rejects_corrupt_header_and_wrong_machine():
    with pytest.raises(elf_gate.ElfNoGo):
        elf_gate.load_segments(b"invalid")
    bad=bytearray(make_elf())
    bad[18:20]=(62).to_bytes(2,"little")
    with pytest.raises(elf_gate.ElfNoGo):
        elf_gate.load_segments(bytes(bad))


def test_p08_new_build_script_is_bash_syntax_valid_and_never_jtag():
    path=ROOT/"scripts/build_p08_b2_3_image_only.sh"
    assert "xsdb " not in path.read_text().lower()
    assert "vivado -mode batch" not in path.read_text().lower()
    subprocess.run(["bash","-n",str(path)],check=True,
                   capture_output=True,text=True,timeout=20)
