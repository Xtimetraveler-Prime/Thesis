"""B.4b offline ELF read-only probe guard: synthetic parser fixtures only.

A successful synthetic parser test is NOT a real linked A53 ELF acceptance.
"""
from pathlib import Path
import sys
import pytest

SRC = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SRC))
from p07_b3c3_elf_admission import Span
from p07_b4b_elf_probe_admission import validate_elf_evidence

HEADER = (
    "ELF Header:\n"
    "  Class: ELF64\n"
    "  Data: 2's complement, little endian\n"
    "  Type: EXEC (Executable file)\n"
    "  Machine: AArch64\n"
)
LOADS = (
    "  LOAD 0x000000 0x0000000000100000 0x0000000000100000 "
    "0x000100 0x100000 RWE 0x1000\n"
)
FUNCTIONS = (
    "main", "p07_b4b_probe", "p07_b4b_xilinx_read_phys",
    "p03_hw_init", "p03_hw_identify", "p03_hw_quiescent",
    "p03_hw_xilinx_io",
)
SYMBOLS = "".join(
    f"{0x100000+i*0x20:016x} 00000010 T {name}\n"
    for i,name in enumerate(FUNCTIONS)
) + "0000000000110000 00011000 b hw\n"
MAP = ".text main\n.bss hw\n"
STACK = Span("physical stack",0x300000,0x310000)
HEAP = Span("physical heap",0x320000,0x340000)


def gate(header=HEADER,program=LOADS,symbols=SYMBOLS,linker=MAP,
         stack=STACK,heap=HEAP):
    return validate_elf_evidence(header,program,symbols,linker,stack,heap)


def test_readonly_probe_accepts_valid_synthetic_a53_program_layout():
    result = gate()
    assert result["inference_authorized"] is False
    assert result["KV260_live_shell_verified"] is False
    assert result["required_symbols_checked"] == len(FUNCTIONS)


@pytest.mark.parametrize("field,mutation,expected",[
    ("header",HEADER.replace("AArch64","Advanced Micro Devices X86-64"),"AArch64"),
    ("header",HEADER.replace("little endian","big endian"),"little-endian"),
    ("header",HEADER.replace("EXEC","REL"),"EXEC"),
    ("symbols",SYMBOLS.replace("p03_hw_quiescent","missing_function"),"missing"),
    ("symbols",SYMBOLS.replace("00011000 b hw","00000100 b hw"),"full-sized"),
    ("symbols",SYMBOLS.replace("0000000000110000 00011000 b hw",
                               "0000000040000000 00011000 b hw"),"contained"),
    ("linker",MAP.replace(".bss","missing_bss"),"text/BSS"),
    ("linker",MAP.replace("main","renamed_entry"),"entry"),
])
def test_bad_elf_or_linker_admission_fails_closed(field,mutation,expected):
    kwargs={field:mutation}
    with pytest.raises(ValueError,match=expected):
        gate(**kwargs)


def test_original_64mb_p02_and_fpd_mmio_load_overlap_rejected():
    for start in (0x40000000,0x43F00000,0x43FE0000,
                  0x43FF0000,0xA4000000):
        bad = ("  LOAD 0x000000 0x0000000000100000 "
               f"0x{start:016x} 0x000100 0x001000 RWE 0x1000\n")
        with pytest.raises(ValueError,match="overlaps"):
            gate(program=bad)


def test_declared_stack_heap_are_required_to_be_outside_elf_and_reserved_ddr():
    with pytest.raises(ValueError,match="overlaps"):
        gate(stack=Span("physical stack",0x40000000,0x40100000))
    with pytest.raises(ValueError,match="overlaps"):
        gate(heap=Span("physical heap",0x110000,0x118000))


# Real Vitis standalone ELF .heap/.stack are NOBITS ALLOC sections INSIDE
# PT_LOAD. This synthetic layout mirrors the user's *actual* 2026-10-21
# physical addresses (readelf -W -S); it is not a copy of an actual ELF.
ACTUAL_SECTIONS = (
    "Section Headers:\n"
    "  [ 1] .text PROGBITS 0000000000000000 010000 005f6c 00 AX 0 0 256\n"
    "  [25] .bss NOBITS 000000000000e080 01e054 0109c0 00 WA 0 0 8\n"
    "  [26] .heap NOBITS 000000000001ea40 01e054 002000 00 WA 0 0 1\n"
    "  [27] .stack NOBITS 0000000000020a40 01e054 003000 00 WA 0 0 1\n"
)
VITIS_LOAD=(
    "LOAD 0x010000 0x0000000000000000 0x0000000000000000 "
    "0x00e054 0x023a40 RWE 0x10000\n"
)
VITIS_NM = SYMBOLS.replace(
    "0000000000110000 00011000 b hw",
    "000000000000e0b8 000106d8 b hw",
)
VITIS_HEAP=Span("physical heap",0x1ea40,0x20a40)
VITIS_STACK=Span("physical stack",0x20a40,0x23a40)


def test_real_vitis_embedded_heap_stack_in_load_allowed_when_sections_match():
    result=validate_elf_evidence(
        HEADER,VITIS_LOAD,VITIS_NM,MAP,
        VITIS_STACK,VITIS_HEAP,ACTUAL_SECTIONS,
    )
    assert result["embedded_stack_heap_within_elf_load"] is True
    assert result["heap_section_verified"] is True
    assert result["stack_section_verified"] is True
    assert result["inference_authorized"] is False


def test_real_vitis_rejects_declared_heap_stack_forgery_or_allocated_overlap():
    with pytest.raises(ValueError,match="differs from actual ELF"):
        validate_elf_evidence(
            HEADER,VITIS_LOAD,VITIS_NM,MAP,VITIS_STACK,
            Span("physical heap",0x1ea44,0x20a40),ACTUAL_SECTIONS,
        )
    altered=ACTUAL_SECTIONS.replace(
        "000000000000e080 01e054 0109c0",
        "000000000000e080 01e054 010ac0",
    )
    with pytest.raises(ValueError,match="overlaps allocated"):
        validate_elf_evidence(
            HEADER,VITIS_LOAD,VITIS_NM,MAP,
            VITIS_STACK,VITIS_HEAP,altered,
        )
    with pytest.raises(ValueError,match="allocated section missing"):
        validate_elf_evidence(
            HEADER,VITIS_LOAD,VITIS_NM,MAP,
            VITIS_STACK,VITIS_HEAP,
            ACTUAL_SECTIONS.replace(".stack","stack_absent"),
        )
