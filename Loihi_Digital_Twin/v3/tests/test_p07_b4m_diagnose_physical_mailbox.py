"""Offline diagnostic-only B4m real-mailbox and firmware failure decoding."""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import struct
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b4m_diagnose_physical_mailbox as diag
import p07_b4m_verify_full_receipt as acceptance


def capture(*,state=0xDEAD0000,fault=7,done=True):
    words=[0]*64
    words[0]=acceptance.MAGIC
    words[1]=1
    words[2]=state
    words[3]=fault
    words[4:11]=[0,0,0,0,0,0,0]
    words[11]=0xFFFFFFFE
    words[23]=21384
    words[31]=123216
    words[44]=0
    words[45]=fault
    words[46]=27
    words[63]=acceptance.DONE if done else 0
    return struct.pack("<64I",*words)


def test_terminal_done_is_not_success_and_diagnoses_original_stage_7():
    data=capture()
    got=diag.diagnose(data)
    assert got["firmware_terminal_DONE_marker_seen"] is True
    assert got["firmware_terminal_status"]=="B4M_FIRMWARE_FAIL"
    assert got["firmware_identity_magic_valid"] is True
    assert got["all_structural_inference_receipt_checks_pass"] is False
    assert got["source_reported_first_fault_stage"]==7
    assert "TRAIN CURRENT ingress" in got["source_reported_first_fault_interpretation"]
    assert got["signed_return_codes"]["full_inference_return_status"]==-2
    assert got["physical_dispatch_counter_snapshot"]==27
    assert got["not_a_physical_inference_acceptance_receipt"] is True
    assert got["mailbox_words"][63]["hex"]=="0xC0DEF00D"
    with pytest.raises(acceptance.FullReceiptError,match="terminal magic"):
        acceptance.verify(data)


@pytest.mark.parametrize("status,label",[
    (0xDEAD0000,"B4M_FIRMWARE_FAIL"),
    (0xC0DE0000,"B4M_FIRMWARE_IN_PROGRESS"),
    (0xFFFFFFFF,"UNKNOWN_OR_INVALID"),
])
def test_rejected_terminal_statuses_never_trigger_acceptance(status,label):
    got=diag.diagnose(capture(state=status))
    assert got["firmware_terminal_status"]==label
    assert not got["all_structural_inference_receipt_checks_pass"]
    assert got["independent_full_neuron_numerical_parity_verified"] is False


def test_short_capture_refused_without_padding_or_guess():
    with pytest.raises(ValueError,match="exactly 256"):
        diag.diagnose(capture()[:-1])


def test_real_cli_decodes_saved_existing_capture_read_only(tmp_path):
    mailbox=tmp_path/"full_26tick_physical_mailbox_256.bin"
    mailbox.write_bytes(capture(fault=13))
    report=tmp_path/"failed_mailbox_diagnostics.json"
    run=subprocess.run([
        sys.executable,str(ROOT/"scripts/p07_b4m_diagnose_physical_mailbox.py"),
        "--mailbox",str(mailbox),"--out",str(report),
    ],capture_output=True,text=True,timeout=20)
    assert run.returncode==0,run.stderr
    assert "P07_B4M_PHYSICAL_MAILBOX_DIAGNOSTIC_ONLY_NO_BOARD_CONTACT=1" in run.stdout
    assert "P07_B4M_DIAGNOSTIC_NOT_AN_ACCEPTANCE_RECEIPT=1" in run.stdout
    report_data=json.loads(report.read_text())
    assert report_data["sha256"]==hashlib.sha256(mailbox.read_bytes()).hexdigest()
    assert report_data["source_reported_first_fault_stage"]==13
    assert report_data["all_structural_inference_receipt_checks_pass"] is False
    assert mailbox.read_bytes()==capture(fault=13)
    again=subprocess.run([
        sys.executable,str(ROOT/"scripts/p07_b4m_diagnose_physical_mailbox.py"),
        "--mailbox",str(mailbox),"--out",str(report),
    ],capture_output=True,text=True,timeout=20)
    assert again.returncode!=0
    assert "NEW absolute" in again.stderr


def test_diagnose_does_not_dow_or_import_hardware_runner():
    source=(ROOT/"scripts/p07_b4m_diagnose_physical_mailbox.py").read_text()
    assert "import p07_b4m_physical_full_inference" not in source
    assert "xsdb" not in source
    assert "P07_B4M_FULL_26TICK_PHYSICAL_INFERENCE_VERIFIED=1" not in source
    assert "independent_full_neuron_numerical_parity_verified" in source
