"""P07-B.5.3.2 real C hook + raw capture native integration, NO actual board.

Compiles separate B5 new trace hook with actual C recorder, with fake
P03 hardware only; source ABI tests cannot authorize DDR or KV260 launch.
"""
from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import importlib.util

ROOT=Path(__file__).resolve().parents[1]

def test_b5_real_new_source_trace_hook_26tick_order_and_fail_closed(tmp_path):
    cc=shutil.which("cc")
    assert cc,"native cc compiler required"
    exe=tmp_path/"b5_fake_p03_trace_integration"
    cmd=[
        cc,"-std=c11","-O2","-Wall","-Wextra","-Werror","-pedantic",
        "-I",str(ROOT/"software/p07/include"),
        "-I",str(ROOT/"software/p03/include"),
        "-I",str(ROOT/"software/p05/include"),
        str(ROOT/"software/p07/p07_b5_raw_capture.c"),
        str(ROOT/"software/p07/p07_b5_spike_trace.c"),
        str(ROOT/"tests/native/p07_b5_raw_trace_hook_harness.c"),
        "-o",str(exe)
    ]
    built=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
    assert built.returncode==0,built.stderr+built.stdout
    ran=subprocess.run([str(exe)],capture_output=True,text=True,timeout=90)
    assert ran.returncode==0,ran.stdout+ran.stderr
    assert ran.stdout.strip().splitlines()==[
        "P07_B5_NATIVE_26260_ORIGINAL_P03_DEBUG_WORDS_SERIALIZED_PASS=1",
        "P07_B5_NATIVE_TRACE_HOOK_METADATA_MISMATCH_FAIL_CLOSED=1",
        "P07_B5_NATIVE_CORRUPTED_TRACE_ABORTS_BEFORE_ACCEPTANCE=1",
        "P07_B5_PHYSICAL_BOARD_CONTACT=0",
    ]

def test_b5_separate_firmware_source_original_V3_unchanged_and_no_direct_board_path():
    original=(ROOT/"software/p07/p07_b4m_full_board_diag_v3.c").read_text()
    b5=(ROOT/"software/p07/p07_b5_full_board_raw_trace_v1.c").read_text()
    hook=(ROOT/"software/p07/p07_b5_spike_trace.c").read_text()
    orig_hook=(ROOT/"software/p07/p07_b4m_spike_trace.c").read_text()
    assert "P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V3" in original
    assert "P07_B5_A53_TRAIN_RAW_TRACE_DIAGNOSTIC_V1" in b5
    # Check the real firmware status print as well as its declared identity.
    # The first B5 Vitis ELF failed admission because this print still
    # contained the old V3 identity even after the B5 identity was changed.
    assert 'xil_printf("P07_B5_A53_TRAIN_RAW_TRACE_DIAGNOSTIC_V1 status=' in b5
    assert "P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V3" not in b5
    assert "P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V2" not in b5
    assert "P07_B4M_A53_TRAIN_26_TICK_CANDIDATE_V1" not in b5
    assert 'xil_printf("P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V3 status=' in original
    assert "B5_MAILBOX UINT32_C(0x43FF0100)" in b5
    assert "B4M_MAILBOX UINT32_C(0x43FF0000)" in original
    assert "P07_B5_CAPTURE_DDR_CANDIDATE_BASE" in b5
    assert "Xil_DCacheFlushRange(" in b5
    assert "raw_finalize==P07_B5_CAPTURE_OK" in b5
    assert "raw_capture.next_record==P07_B5_CAPTURE_RECORDS" in b5
    assert "p07_b5_capture_begin" in b5
    assert "p07_b5_trace_attach" in b5
    assert "p07_b5_capture_finalize" in b5
    assert "p07_b5_capture_record" in hook
    assert hook.index("p03_hw_debug_word(hw,slot,7u") < hook.index("p07_b5_capture_record")
    assert hook.index("p03_hw_debug_word(hw,slot,1u") < hook.index("p07_b5_capture_record")
    assert hook.index("p07_b5_capture_record") < hook.index("t->fnv64=fnv_u32")
    assert "p07_b5_capture_record" not in orig_hook
    assert "P07_B5_CAPTURE_DDR_CANDIDATE_BASE" not in original
    assert not (ROOT/"vivado/p07_b5_raw_trace_xsdb_run.tcl").exists()
    assert not (ROOT/"scripts/p07_b5_raw_trace_physical_run.py").exists()

def test_b5_isolated_vitis_source_contract_disallows_original_v3_trace_and_main():
    modfile=ROOT/"software/p07/build_p07_b5_raw_trace.py"
    spec=importlib.util.spec_from_file_location("b5_new_compiler",modfile)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert module.IDENTITY=="P07_B5_A53_TRAIN_RAW_TRACE_DIAGNOSTIC_V1"
    assert module.APP=="p07_b5_raw_trace_v1"
    assert module.SOURCES[0]=="p07_b5_full_board_raw_trace_v1.c"
    assert {"p07_b5_raw_capture.c","p07_b5_spike_trace.c"}<=set(module.SOURCES)
    assert {"p07_b5_raw_capture.h","p07_b5_trace_hook.h"}<=set(module.HEADERS)
    assert "p07_b4m_spike_trace.c" not in module.SOURCES
    assert "p07_b4m_full_board_diag_v3.c" not in module.SOURCES
    assert len(module.SOURCES)==len(set(module.SOURCES))
    assert len(module.HEADERS)==len(set(module.HEADERS))
    script=(ROOT/"scripts/build_p07_b5_raw_trace.sh").read_text()
    assert "P07_B5_RAW_REAL_BOARD_RUN_AUTHORIZED=0" in script
    assert "P07_B5_RAW_SIDECAR_DDR_OWNERSHIP_INDEPENDENTLY_PROVEN=0" in script
    assert "p07_b4m_diag_v3_26tick.elf" not in script
