"""Single P07-B.4m full 26-tick C11 integration gate, no real FPGA accessed.

Tests original P03 adapter / B3 pager / B4a CURRENT / live HLS trace
semantics / B2b canonical packet route / B3c3 NEXT / B3c2 barrier,
using a synthetic fake-MMIO bus and B2.4-compatible signed digests.
Physical-trained B2.4 numerical parity is deliberately NOT claimed.
"""
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def test_complete_26_tick_raw784_current_trace_next_readout_native(tmp_path):
    cc=shutil.which("cc") or shutil.which("gcc")
    assert cc
    exe=tmp_path/"b4m_full"
    files=[
        "software/p03/p03_hw_adapter.c",
        "software/p07/p07_b2_ingress.c",
        "software/p07/p07_b4a_current_ingress.c",
        "software/p07/p07_b3_pager.c",
        "software/p07/p07_b2_packet.c",
        "software/p07/p07_b3c_packet_bridge.c",
        "software/p07/p07_b3c2_hw_scheduler.c",
        "software/p07/p07_b3c3_next_commit.c",
        "software/p07/p07_b4m_spike_trace.c",
        "software/p07/p07_b4m_epoch_bridge.c",
        "software/p07/p07_b4m_full_inference.c",
        "tests/native/p07_b4m_full_inference_harness.c",
    ]
    command=[
        cc,"-std=c11","-Wall","-Wextra","-Werror","-pedantic","-O1",
        "-I",str(ROOT/"software/p07/include"),
        "-I",str(ROOT/"software/p03/include"),
        "-I",str(ROOT/"software/p05/include"),
        *(str(ROOT/p) for p in files),"-o",str(exe),
    ]
    built=subprocess.run(command,capture_output=True,text=True,timeout=120)
    assert built.returncode==0,built.stderr+built.stdout
    run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=120)
    assert run.returncode==0,run.stderr+run.stdout
    assert run.stdout.splitlines()==[
        "P07_B4M_FULL_26_TICK_A53_CONTROL_FAKE_P03_PASS=1",
        "P07_B4M_FULL_REAL_CURRENT_TRACE_NEXT_702_SIMULATED=1",
        "P07_B4M_FULL_REAL_KV260_INFERENCE_VERIFIED=0",
    ]


def test_full_coordinator_is_standalone_new_code_not_b4l_frozen_rebuild():
    old=(ROOT/"software/p07/p07_b4l_b3_epoch_board.c").read_text()
    new=(ROOT/"software/p07/p07_b4m_full_inference.c").read_text()
    assert "p07_b4m_full_run" not in old
    for symbol in (
        "p07_b4a_prepare(", "p07_b4a_commit(",
        "p07_b3c2_step(", "p07_b4m_trace_finalize(",
        "p07_b4m_commit_pending_barrier(", "p07_b4m_trace_advance("
    ):
        assert symbol in new
    assert "compiled_sha" in new and "capacity_sha" in new
    assert "1010u" in new
    assert "702u" not in new or "P07_B3_CORES*P07_B3_TICKS" in new
