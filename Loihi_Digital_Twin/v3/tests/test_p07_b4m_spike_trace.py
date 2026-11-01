"""Original P03 HLS trace bank7/state bank1 integration under native fake MMIO.
C11 source files + original B3a/B3c1/2/3; no actual KV260 contacted.
"""
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def test_original_hls_trace_independent_spikes_702_dispatches(tmp_path):
    cc=shutil.which("cc") or shutil.which("gcc")
    assert cc,"C11 compiler required"
    output=tmp_path/"p07_b4m_real_trace_native"
    files=(
        "software/p03/p03_hw_adapter.c",
        "software/p07/p07_b3_pager.c",
        "software/p07/p07_b2_packet.c",
        "software/p07/p07_b3c_packet_bridge.c",
        "software/p07/p07_b3c2_hw_scheduler.c",
        "software/p07/p07_b3c3_next_commit.c",
        "software/p07/p07_b4m_epoch_bridge.c",
        "software/p07/p07_b4m_spike_trace.c",
        "tests/native/p07_b4m_real_trace_integration_harness.c",
    )
    compile_cmd=[
        cc,"-std=c11","-Wall","-Wextra","-Werror","-pedantic","-O1",
        "-I",str(ROOT/"software/p07/include"),
        "-I",str(ROOT/"software/p03/include"),
        "-I",str(ROOT/"software/p05/include"),
        *(str(ROOT/path) for path in files),"-o",str(output),
    ]
    built=subprocess.run(compile_cmd,capture_output=True,text=True,timeout=120)
    assert built.returncode==0,built.stderr+built.stdout
    ran=subprocess.run([str(output)],capture_output=True,text=True,timeout=120)
    assert ran.returncode==0,ran.stderr+ran.stdout
    assert ran.stdout.splitlines()==[
        "P07_B4M_TRACE_702_DISPATCH_26_BARRIER_SIMULATED_PASS=1",
        "P07_B4M_TRACE_REAL_DEBUG_BANK_SEMANTICS_NEGATIVE_PASS=1",
        "P07_B4M_TRACE_REAL_BOARD_TESTED=0",
    ]


def test_accepted_first_epoch_elf_keeps_trace_hook_disabled():
    source=(ROOT/"software/p07/p07_b4l_b3_epoch_board.c").read_text()
    assert "p07_b3c2_set_trace_hook" not in source
    assert "P07_B4L_A53_B3_ONE_EPOCH_V1" in source
    hls=(ROOT/"hls/core_v2/src/loihi_core_v2.cpp").read_text()
    bridge=(ROOT/"software/p07/p07_b4m_spike_trace.c").read_text()
    assert "trace[192] = spiked;" in hls
    assert "trace.range(191, 128) = after_word;" in hls
    assert "p03_hw_debug_word(hw,slot,7u" in bridge
    assert "p03_hw_debug_word(hw,slot,1u" in bridge
    assert "trace[6]&1u" in bridge
