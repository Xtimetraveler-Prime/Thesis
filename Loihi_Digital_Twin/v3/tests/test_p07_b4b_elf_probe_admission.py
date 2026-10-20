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
