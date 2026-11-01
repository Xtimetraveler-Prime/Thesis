"""B4m failure-telemetry V2: distinct build-only candidate, never V1 launch."""
from __future__ import annotations
from pathlib import Path
import importlib.util
import struct
import subprocess
import shutil
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b4m_diagnose_physical_mailbox as diagnose
import p07_b4m_verify_full_receipt as strict


def make_mailbox(*,v2:bool):
    w=[0]*64
    w[0]=strict.MAGIC
    w[1]=1
    w[2]=0xDEAD0000
    w[3]=9
    w[11]=0xFFFFFFFE
    w[44]=0xFFFFFFFB # P03_HW_PROTOCOL=-5
    w[45]=9
    w[46]=1
    w[63]=strict.DONE
    if v2:
        w[47]=diagnose.DIAG_V2_MAGIC
        w[48]=0x1A
        w[49]=17  # trace callback failed in scheduler
        w[50]=3
        w[51]=4  # trace/state mismatch (example only)
        w[52]=0x2
        w[53]=0x0
        w[54]=0x0
        w[55]=0x6
        w[56]=0x0
        w[57]=0x2
        w[58]=0
        w[59]=0
        w[60]=0
        w[61]=0x7000
        w[62]=14
    return struct.pack("<64I",*w)


def test_diagnostic_v2_failure_decodes_genuine_raw_register_fields():
    report=diagnose.diagnose(make_mailbox(v2=True))
    assert report["diagnostic_v2_failure_payload_present"] is True
    assert report["firmware_terminal_status"]=="B4M_FIRMWARE_FAIL"
    assert report["source_reported_first_fault_stage"]==9
    assert report["signed_return_codes"]["p03_hardware_last_error"]==-5
    fields=report["failure_telemetry"]
    assert fields["b3c2_scheduler_first_fault"]["uint32"]==17
    assert fields["real_trace_first_fault"]["uint32"]==4
    assert fields["p03_dispatch_status_raw"]["hex"]=="0x00000002"
    assert fields["p03_debug_status_raw"]["uint32"]==6
    assert fields["p03_debug_config_raw"]["uint32"]==0x7000
    assert report["all_structural_inference_receipt_checks_pass"] is False
    with pytest.raises(strict.FullReceiptError):
        strict.verify(make_mailbox(v2=True))


def test_original_v1_failed_mailbox_decodes_without_v2_invention():
    report=diagnose.diagnose(make_mailbox(v2=False))
    assert report["diagnostic_v2_failure_payload_present"] is False
    assert report["failure_telemetry"] is None
    assert report["physical_dispatch_counter_snapshot"]==1


def test_v2_board_candidate_separate_identity_and_failure_only_telemetry():
    board=(ROOT/"software/p07/p07_b4m_full_board_diag.c").read_text()
    v1=(ROOT/"software/p07/p07_b4m_full_board.c").read_text()
    assert "P07_B4M_A53_TRAIN_26_TICK_CANDIDATE_V1" in v1
    assert "P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V2" in board
    assert "DIAGNOSTIC_V2" in board
    assert "if(mailbox[2]!=B4M_MAILBOX_PASS){" in board
    assert "mailbox[47]=UINT32_C(0x42344432)" in board
    assert "mailbox[63]=B4M_MAILBOX_DONE" in board
    assert "mailbox[2]=(width==0" in board  # no success bypass
    assert "p07_b4m_full_run(" in board
    assert "P03_REG_DISPATCH_STATUS" in board
    assert "P03_REG_DISPATCH_CORE_STATUS" in board
    assert "P03_REG_DISPATCH_ACTIVE" in board
    assert "P03_REG_DEBUG_STATUS" in board
    assert "scheduler.first_fault" in board
    assert "buffers.trace.first_fault" in board
    assert "hw.last_status" in board
    assert "P03_REG_DISPATCH_COMMAND, P03_CMD_START" not in board


def test_isolated_diag_v2_vitis_build_contract_and_no_automatic_physical_launch():
    script=ROOT/"scripts/build_p07_b4m_diag.sh"
    code=(ROOT/"software/p07/build_p07_b4m_diag.py").read_text()
    build=script.read_text()
    assert "P07_B4M_DIAG_BUILD_DIR" in build
    assert "build_p07_b4m_diag.py" in build
    assert "p07_b4m_full_board_diag.c" in code
    assert "p07_b4m_full_board_diag.c" in build
    assert 'APP="p07_b4m_diag_v2_26tick"' in code
    assert "P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V2" in code
    assert "P07_B4M_REAL_BOARD_RUN_AUTHORIZED=0" in build
    assert "52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f" in build
    assert "xsdb" not in build
    assert "p07_b4m_full_board_diag.c" not in (
        ROOT/"scripts/build_p07_b4m_full.sh").read_text()
    assert 'APP="p07_b4m_full_26tick"' in (
        ROOT/"software/p07/build_p07_b4m_full.py").read_text()
    if shutil.which("bash"):
        result=subprocess.run(["bash","-n",str(script)],capture_output=True,text=True)
        assert result.returncode==0,result.stderr
