"""P03.3a portable C runtime test and static architecture guard.

This is a host-native policy validation, NOT physical Cortex-A53 inference.
The physical callback adapter and packet encoding remain in P03.3b.
"""

from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
HDR = ROOT / "software/p03/include/p03_runtime.h"
SRC = ROOT / "software/p03/p03_runtime.c"
HARNESS = ROOT / "tests/native/p03_3a_runtime_harness.c"


def test_p03_3a_runtime_c_policy_against_native_hardware_mock(tmp_path: Path):
    cc = shutil.which("cc") or shutil.which("gcc")
    if cc is None:
        pytest.skip("Host C compiler not installed; this suite needs gcc/clang")
    executable = tmp_path / "p03_3a_runtime_harness"
    build = subprocess.run([
        cc,
        "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-O0", "-g",
        "-I", str(HDR.parent),
        str(SRC), str(HARNESS),
        "-o", str(executable),
    ], check=False, text=True, capture_output=True, timeout=60)
    assert build.returncode == 0, build.stdout + build.stderr
    result = subprocess.run(
        [str(executable)],
        check=False, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for expected in (
        "PASS: P03.3a native five-over-three seven-barrier scheduling",
        "PASS: P03.3a partial packet route fails closed",
        "PASS: P03.3a dirty victim must save before reload",
        "PASS: P03.3a barrier quiescence required for bank swap",
        "PASS: P03.3a invalid configuration blocked and reset explicit",
        "PASS: P03.3a complete host-native C runtime policy suite",
    ):
        assert expected in result.stdout


def test_p03_3a_preserves_p03_1_fault_contract_and_ddr_layout_boundary():
    h = HDR.read_text(encoding="utf-8")
    s = SRC.read_text(encoding="utf-8")
    for token in (
        "#define P03_RT_MAX_CORES 128u",
        "#define P03_RT_MAX_SLOTS 3u",
        "P03_RT_SAVE_VICTIM",
        "P03_RT_LOAD_REQUESTED",
        "P03_RT_DRAIN_AND_ROUTE_PACKETS",
        "P03_RT_BARRIER_CHECK",
        "P03_RT_SWAP_EVENT_BANKS",
        "P03_RT_FAULT_BARRIER_INCOMPLETE = 11",
        "P03_RT_FAULT_CONTROL_PROTOCOL = 12",
        "P03_RT_FAULT_TIMEOUT = 13",
        "external_control_locked",
        "on_error",
    ):
        assert token in h
    for token in (
        "rt->current_event_bank = next_bank",
        "rt->pending_packets -= committed",
        "rt->first_fault == P03_RT_FAULT_NONE",
        "rt->next_victim_slot",
        "rt->dirty[resident_slot] = 1",
        "rt->phase = P03_RT_SAVE_VICTIM",
        "rt->phase = P03_RT_BARRIER_CHECK",
        "rt->phase = P03_RT_WRITE_RESULT",
    ):
        assert token in s
    for forbidden in (
        "#include \"xil_io.h\"",
        "Xil_Out32(",
        "Xil_In32(",
        "0x40000000",
        "0x43FF0000",
        "malloc(",
    ):
        assert forbidden not in s
