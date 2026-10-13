"""P05.1 source and Vitis build checkpoint; HOST tests, no board claims."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[1]
P05=ROOT/"software/p05"
P03=ROOT/"software/p03"
RUN=P05/"p05_regression_run.c"
BUILD=ROOT/"scripts/build_p05_regression.sh"
VITIS=P05/"build_p05_regression.py"


def test_p05_does_not_modify_accepted_p03_and_has_separate_elf_identity():
    c=RUN.read_text()
    b=BUILD.read_text()
    v=VITIS.read_text()
    assert "P05_CONFIGURABLE_A53_REGRESSION_V1" in c
    assert "P05_CONFIGURABLE_A53_REGRESSION_V1" in b
    assert "P03_AUTONOMOUS_P02_GOLDEN_7_OR_100_V2" not in c
    assert "p05_regression_run.elf" in b
    assert "software/p05/p05_regression_run.c" in b
    assert "p03_finish_run.c" not in b
    assert 'p05_regression_run.c' in v
    assert 'p05_deployment.c' in v
    for reused in ("p03_runtime.c","p03_hw_adapter.c",
                   "p03_hw_runtime_bridge.c","p03_hw_xilinx_io.c"):
        assert reused in b and reused in v


def test_runtime_guards_external_host_autonomy_and_state_observations():
    c=RUN.read_text()
    for required in (
        "p05_deployment_validate(", "P05_DEPLOY_PAYLOAD_CAPACITY",
        "crc_physical(", "P05_DEPLOY_RECORD_BYTES",
        "p03_hw_xilinx_fpd128_ready()",
        "p03_rt_init(&runtime", "p03_rt_execute(&runtime",
        "hardware_dispatch=ops.dispatch", "ops.dispatch=inject_and_dispatch",
        "hardware_route=ops.drain_route", "ops.drain_route=observe_and_route",
        "hardware_barrier=ops.barrier_ready",
        "ops.barrier_ready=barrier_with_checkpoints",
        "P05_DEPLOY_EVENT_DEPTH", "p03_hw_debug_word(&hw",
        "P03_HW_EVENT0_DEBUG_BANK", "P03_HW_EVENT1_DEBUG_BANK",
        "P03_HW_PACKET_DEBUG_BANK", "offset=0x5000u;bank=1u",
        "crc_word(", "diag_flags=1u", "diag_flags=2u",
        "R_FAILED_STEP", "R_FAILED_CORE", "R_FAILED_CLASS",
        "R_EXPECTED_CRC", "R_OBSERVED_CRC",
        "R_HEADER_CRC", "R_PAYLOAD_CRC",
        "R_INPUTS_CONSUMED", "R_CHECKPOINTS_PASSED",
        "result[R_RESULT]=P05_RESULT_OK;",
    ):
        assert required in c, required
    # The deployment schema and FPGA hardware must agree on capacity.
    # Preserve both the compiled ABI equality check and the actual
    # dispatch-time limit; a substring-only source guard is insufficient.
    assert "_Static_assert(P05_DEPLOY_EVENT_DEPTH == P03_HW_EVENT_DEPTH" in c
    assert "if(count>=P05_DEPLOY_EVENT_DEPTH) return -1;" in c
    assert c.count("result[R_RESULT]=P05_RESULT_OK;")==1
    assert c.index("if(runtime.phase!=P03_RT_DONE") < (
        c.index("result[R_RESULT]=P05_RESULT_OK;")
    )
    assert c.index("load_descriptor()!=0") < (
        c.index("p03_hw_init(&hw")
    )
    assert "P05_DEPLOY_PAYLOAD_BASE" in c
    assert "p03_finish_run" not in c


def test_build_shell_syntax_and_platform_identity():
    result=subprocess.run(["bash","-n",str(BUILD)],
                          capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    b=BUILD.read_text()
    assert "P03_2C_EXPECTED_XSA_SHA" in b
    assert "p03_hpm0_data_width_bits=128" in b
    assert "P05_1_BUILD_DIR" in b
    assert "readelf -lW" in b
    assert "0x44000000" in b
    assert "grep -aFq 'P05_CONFIGURABLE_A53_REGRESSION_V1'" in b
    assert "Vitis" in VITIS.read_text()


@pytest.mark.parametrize("name", [
    "p05_regression_run.c", "p05_deployment.c",
    "p03_runtime.c", "p03_hw_adapter.c",
    "p03_hw_runtime_bridge.c", "p03_hw_xilinx_io.c",
])
def test_p05_sources_compile_c11_strict_host_syntax(tmp_path,name):
    cc=shutil.which("cc") or shutil.which("gcc")
    if cc is None: pytest.skip("no C compiler")
    (tmp_path/"xil_io.h").write_text(
        "#ifndef XIL_IO_STUB_H\n#define XIL_IO_STUB_H\n"
        "#include <stdint.h>\n"
        "typedef uintptr_t UINTPTR;\n"
        "typedef intptr_t INTPTR;\n"
        "typedef unsigned int u32;\n"
        "static inline uint32_t Xil_In32(UINTPTR a){(void)a;return 0;}\n"
        "static inline void Xil_Out32(UINTPTR a,uint32_t v)"
        "{(void)a;(void)v;}\n"
        "#endif\n",encoding="utf-8"
    )
    (tmp_path/"xil_cache.h").write_text(
        '#include "xil_io.h"\n'
        "static inline void Xil_DCacheFlushRange(INTPTR a,u32 n)"
        "{(void)a;(void)n;}\n"
        "static inline void Xil_DCacheInvalidateRange(INTPTR a,u32 n)"
        "{(void)a;(void)n;}\n",encoding="utf-8"
    )
    file=(P05 if name.startswith("p05") else P03)/name
    proc=subprocess.run(
        [cc,"-std=c11","-Wall","-Wextra","-Werror","-pedantic",
         "-fsyntax-only","-I",str(tmp_path),
         "-I",str(P05/"include"),"-I",str(P03/"include"),str(file)],
        capture_output=True,text=True,timeout=30,
    )
    assert proc.returncode==0,name+"\n"+proc.stderr
