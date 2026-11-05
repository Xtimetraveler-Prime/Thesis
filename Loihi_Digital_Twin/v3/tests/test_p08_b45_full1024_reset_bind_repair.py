"""No-board P08-B4.5 REAL full1024 -1 reset-bind repair for BOTH modes."""
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
P08=ROOT/"software"/"p08"
sys.path.insert(0,str(P08))
sys.path.insert(0,str(ROOT/"scripts"))
import build_p08_b45_perf_full1024 as builder

@pytest.mark.parametrize("mode",builder.MODES)
def test_both_new_full1024_mains_require_BSS_bootstrap_and_reason_mailbox(mode):
    p=P08/builder.MAINS[mode]
    s=p.read_text()
    assert builder.IDENTITIES[mode].endswith("_V2")
    assert builder.IDENTITIES[mode] in s
    assert '#include "p08_b45_perf_startup.h"' in s
    assert "prepare_first_entry_workspaces();" in s
    assert "p08_b45_perf_prepare_new_session(" in s
    assert "explain_preloop_bind_failure(" in s
    assert s.index("prepare_first_entry_workspaces();") < s.index("begin_frozen_runtime();")
    assert s.index("p08_b45_perf_prepare_new_session(") < s.index(
        "p08_b45_perf_reset_bind(")
    assert s.index("old_pager_dispatches=pager.counters.dispatches") < s.index(
        "prepare_first_entry_workspaces();")
    assert "m[14]=UINT32_C(0x504D4244);" in s
    assert "m[15]=r->reason;" in s
    assert "m[16]=r->prezero_magic;" in s
    assert "m[19]=old_dispatches;" in s
    assert "m[20]=old_barriers;" in s
    assert "memset(&reset_state,0," not in s
    for name in ("hw","pager","scheduler","frozen","buffers","receipt",
                 "meter","binding_receipt","b23_input_routes","cookie",
                 "packet_words","p03_scratch","route_buffer",
                 "compartment_buffer","verified_spikes","current_words",
                 "packet_scratch","packet_frame"):
        assert (f"memset(&{name},0," in s or f"memset({name},0," in s)
    assert "words[19]=0u;" in s
    assert "p08_b45_a53_backup_lock" not in s
    assert "B23_FRAMES 1024u" in s

def test_isolated_bootstrap_only_and_protected_code_unmodified():
    main=(P08/"p08_b45_perf_startup.c").read_text()
    assert "memset(state, 0, sizeof(*state))" in main
    assert main.index("P08_B45_START_MUTABLE_BACKUP_OVERLAP") < main.index(
        "memset(state, 0, sizeof(*state))")
    assert "Xil_Out32" not in main
    assert "p08_b45_a53_backup_lock" not in main
    assert "p07_a2_sha256" not in main
    assert "p08_b45_perf_reset_image" not in main
    assert (P08/"p08_b45_a53_backup_guard.c").read_text().count("return -1;")==2
    assert "p08_b45_perf_startup.c" in builder.SHARED_SOURCES
    assert "p08_b45_perf_startup.h" in builder.HEADERS
    assert "p08_b45_perf_startup.c" not in (
        ROOT/"software"/"p08"/"build_p08_b45_perf_pilot16.py"
    ).read_text()

def test_strict_C11_native_stale_magic_and_fail_closed_ranges(tmp_path):
    if not shutil.which("gcc"):
        pytest.skip("native C gcc missing")
    exe=tmp_path/"b45_startup"
    cmd=[
        "gcc","-std=c11","-O2","-Wall","-Wextra","-Werror",
        "-pedantic","-I",str(P08),
        str(ROOT/"tests"/"native"/"p08_b45_perf_full1024_startup_native.c"),
        str(P08/"p08_b45_perf_startup.c"),
        "-o",str(exe),
    ]
    built=subprocess.run(cmd,text=True,capture_output=True,timeout=90)
    assert built.returncode==0,built.stdout+built.stderr
    tested=subprocess.run([str(exe)],text=True,capture_output=True,timeout=90)
    assert tested.returncode==0,tested.stdout+tested.stderr
    for marker in (
        "P08_B45_FULL1024_V2_STALE_BSS_RESET_ONLY_AFTER_VALIDATED_GEOMETRY_PASS=1",
        "P08_B45_FULL1024_V2_BOTH_ONCE_AND_UNCHECKED_FRESH_SESSION_PASS=1",
        "P08_B45_FULL1024_V2_INVALID_CONFIG_NO_STATE_WRITE_AND_DIAGNOSTIC_PASS=1",
        "P08_B45_FULL1024_V2_NATIVE_NO_BOARD=1",
    ):
        assert tested.stdout.splitlines().count(marker)==1

def test_V2_identifies_both_new_modes_and_pins_fresh_elf():
    gate=(ROOT/"scripts"/"p08_b45_perf_full1024_elf_admission.py").read_text()
    xsdb=(ROOT/"vivado"/"p08_b45_perf_full1024_run_and_capture.tcl").read_text()
    assert "ORIGINAL_27CORE_1024_A53_V2" in gate
    assert "ORIGINAL_27CORE_1024_A53_V2" in xsdb
    assert "ORIGINAL_27CORE_1024_A53_V1" not in gate
    assert "ORIGINAL_27CORE_1024_A53_V1" not in xsdb
    assert 'b"p08_b45_perf_prepare_new_session"' in gate
    assert '"startup_reset_state_guarded_zero_after_geometry_check": True' in gate
    assert '"new_failure_only_bind_reason_mailbox_v2": True' in gate
    assert "p08_b45_perf_startup.c" in (
        ROOT/"software"/"p08"/"build_p08_b45_perf_full1024.py"
    ).read_text()
