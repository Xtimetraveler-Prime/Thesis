"""B5.3 actual standalone A53 C entry-point syntax with tiny native BSP stubs.

PC-only compilation: does not create any executable/bitstream, contact FPGA,
prove DDR ownership, or test actual Vitis BSP and startup linker.
"""
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def test_new_b5_a53_main_syntax_against_original_real_headers(tmp_path):
    cc=shutil.which("cc")
    assert cc, "native C compiler required"
    # Only the three unavailable Xilinx BSP hardware interfaces are stubbed.
    # The P03/P07/P05 headers are the ACTUAL repository contracts.
    (tmp_path/"xil_cache.h").write_text("""
#ifndef XIL_CACHE_H
#define XIL_CACHE_H
#include <stdint.h>
typedef uintptr_t INTPTR;
static inline void Xil_DCacheFlushRange(INTPTR a,unsigned n)
{(void)a;(void)n;}
static inline void Xil_DCacheInvalidateRange(INTPTR a,unsigned n)
{(void)a;(void)n;}
#endif
""")
    (tmp_path/"xil_io.h").write_text("""
#ifndef XIL_IO_H
#define XIL_IO_H
#include <stdint.h>
typedef uintptr_t UINTPTR;
static inline uint32_t Xil_In32(UINTPTR a){(void)a;return 0u;}
#endif
""")
    (tmp_path/"xil_printf.h").write_text("""
#ifndef XIL_PRINTF_H
#define XIL_PRINTF_H
static inline int xil_printf(const char *fmt,...){(void)fmt;return 0;}
#endif
""")
    cmd=[
        cc,"-std=c11","-O0","-Wall","-Wextra","-Werror",
        "-fsyntax-only",
        "-I",str(tmp_path),
        "-I",str(ROOT/"software/p07/include"),
        "-I",str(ROOT/"software/p03/include"),
        "-I",str(ROOT/"software/p05/include"),
        str(ROOT/"software/p07/p07_b5_full_board_raw_trace_v1.c")
    ]
    proc=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
    assert proc.returncode==0,proc.stderr+proc.stdout

def test_b5_sidecar_host_only_build_never_claims_physical_authority():
    s=(ROOT/"scripts/p07_b5_raw_trace_offline_admission.py").read_text()
    assert '"actual_B5_physical_launch_authorized":False' in s
    assert '"actual_raw_840320B_FPGA_captured":False' in s
    assert '"independent_actual_B5_DDR_owners_verified":False' in s
    assert '"board_accessed":False' in s
    assert '"accepted_original_V3_elf_or_map_changed":False' in s
