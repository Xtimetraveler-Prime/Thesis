"""P08-B4.5 pure HOST failure postmortem tests; never open JTAG."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p08_b45_full1024_failed_run_postmortem as triage

def mailbox(frame:int=0,fault:int=201,completed:int|None=None,
            status:int=triage.FAIL)->bytes:
    w=[0]*64
    w[0]=triage.MAILBOX_MAGIC
    w[1]=1
    w[2]=status
    w[3]=frame
    w[4]=fault
    w[5]=frame if completed is None and frame!=0xFFFFFFFF else (completed or 0)
    w[6]=100_000_000
    w[63]=triage.DONE
    return struct.pack("<64I",*w)

def row(index:int,kind:int,*,mode:str="once")->bytes:
    w=[0]*64
    w[0],w[1],w[2],w[3]=kind,1,index,triage.STATUS
    if kind==triage.reset.MAGIC[mode]:
        w[4]=triage.reset.MODE[mode]
        w[5]=index+1
        w[6]=27
        w[7]=14155776
        for i in (8,9,10,11):w[i]=27 if mode=="once" else 0
        w[13]=100_000_000
        w[15]=50
        w[20]=26
        w[21]=702
    w[63]=triage.DONE
    data=struct.pack("<64I",*w)
    w[61]=zlib.crc32(data[:244])
    return struct.pack("<64I",*w)

def fixture_failed(tmp_path:Path,monkeypatch,*,frame:int=0,fault:int=201,
                   valid_prior:int=0):
    evidence=tmp_path/"physical"
    cap=evidence/"performance1024_capture"
    cap.mkdir(parents=True)
    (cap/"mailbox_terminal_physical.bin").write_bytes(mailbox(frame,fault))
    names={
        "journal1024_physical.bin":triage.records.JOURNAL_MAGIC,
        "timing1024_physical.bin":triage.records.TIMING_MAGIC,
        "reset_profile1024_physical.bin":triage.reset.MAGIC["once"]
    }
    for filename,magic in names.items():
        blob=bytearray(triage.COUNT*triage.SIZE)
        for i in range(valid_prior):
            blob[i*triage.SIZE:(i+1)*triage.SIZE]=row(i,magic)
        (cap/filename).write_bytes(blob)
    (evidence/"stage.txt").write_text(
        "B45_PERF1024_DESTRUCTIVE_UNPROTECTED_JTAG_ATTEMPT_STARTED_REBOOT_REQUIRED\n")
    (cap/"progress_state.txt").write_text(
        "schema=p08-b45-perf-full1024-xsdb-progress-v1\n"
        "mode=once\ncompleted=0\ntotal=1024\nstate=FAILED_REBOOT_REQUIRED\n")
    oracle=tmp_path/"original1024.json"
    oracle.write_text(json.dumps({
        "schema":triage.fulloracle.SCHEMA,
        "count":1024,
        "frames":[{"ordinal":i} for i in range(1024)],
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    },sort_keys=True))
    monkeypatch.setattr(triage.pinned,"ORIGINAL_FULL1024_ORACLE_SHA",
                        hashlib.sha256(oracle.read_bytes()).hexdigest())
    return evidence,oracle,tmp_path/"postmortem.json"

@pytest.mark.parametrize(("frame","fault","meaning"),(
    (0,201,"optimized reset_image"),
    (16,208,"26-tick"),
    (1023,210,"neural/hardware/reset receipt"),
    (0xFFFFFFFF,105,"reset bind"),
))
def test_decodes_original_A53_faults(frame,fault,meaning):
    r=triage.decode_mailbox(mailbox(frame,fault))
    assert meaning in r["fault_stage"]
    assert r["failing_frame_ordinal"] == (None if frame==0xFFFFFFFF else frame)
    assert r["terminal_failure"] is True
    assert r["completed_frames_mailbox"] == (0 if frame==0xFFFFFFFF else frame)

@pytest.mark.parametrize("fault_frame", (0,1,16,1023))
def test_saved_failure_not_misreported_as_success(fault_frame):
    assert triage.decode_mailbox(mailbox(fault_frame,201))["terminal_failure"]
    with pytest.raises(triage.PostmortemNoGo):
        triage.decode_mailbox(mailbox(fault_frame,201,status=0x600D0823))
    with pytest.raises(triage.PostmortemNoGo):
        triage.decode_mailbox(mailbox(fault_frame,100))
    with pytest.raises(triage.PostmortemNoGo):
        triage.decode_mailbox(mailbox(fault_frame,999))

def test_v2_failure_only_mailbox_explains_BSS_residual_and_config():
    original=bytearray(mailbox(0xFFFFFFFF,105,completed=1))
    words=list(struct.unpack("<64I",original))
    words[14]=triage.BIND_DIAG_MAGIC
    words[15]=4  # invalid source-record geometry rejected, no state writes
    words[16]=triage.reset.DONE
    words[17]=1024
    words[18]=1
    words[19]=702
    words[20]=26
    words[21]=0
    decoded=triage.decode_mailbox(struct.pack("<64I",*words))
    reason=decoded["v2_failure_only_bootstrap_diagnostic"]
    assert reason["boot_geometry_reason_code"]==4
    assert "GEOMETRY" in reason["boot_geometry_reason"]
    assert reason["prior_pager_dispatches_before_explicit_zero"]==702
    assert reason["prior_pager_barriers_before_explicit_zero"]==26
    assert reason["new_reset_state_zeroed_after_geometry_check"] is False
    assert decoded["completed_frames_mailbox"]==0

def test_original_v1_failure_mailbox_does_not_fabricate_V2_details():
    decoded=triage.decode_mailbox(mailbox(0xFFFFFFFF,105,completed=1))
    assert decoded["v2_failure_only_bootstrap_diagnostic"] is None
    assert decoded["completed_frames_mailbox"]==0

def test_zero_row_capture_frame0_pre_failure(tmp_path,monkeypatch):
    evidence,oracle,out=fixture_failed(tmp_path,monkeypatch)
    report=triage.examine(evidence,oracle,out)
    assert report["failure_mailbox"]["fault_code"]==201
    assert report["contiguous_neural_FNV_spikes_and_reset_receipts_verified_before_failure"]==0
    assert report["physical_1024_complete_pass"] is False
    assert report["postrun_27_backup_readbacks_available_or_verified"] is False
    assert all(v["valid_prefix_rows"]==0 for v in
               report["three_saved_full1024_256KiB_sidecars"].values())
    assert out.is_file()

def test_one_complete_frame_verified_before_failure(tmp_path,monkeypatch):
    evidence,oracle,out=fixture_failed(tmp_path,monkeypatch,frame=1,
                                       fault=208,valid_prior=1)
    neural=[]
    timers=[]
    def good_journal(raw,i,ref):
        neural.append(i)
        assert i==0 and ref["ordinal"]==0
        return {"ordinal":i}
    def good_timing(raw,i,prior):
        timers.append(i)
        assert prior is None
        return {"after_journal_commit_CNTVCT":101,
                "CNTFRQ_EL0_hz":100_000_000,
                "phase_counter_ticks":[200,1,1,1,1,1]}
    monkeypatch.setattr(triage.records,"verify_journal",good_journal)
    monkeypatch.setattr(triage.records,"verify_timing",good_timing)
    report=triage.examine(evidence,oracle,out)
    assert report["contiguous_neural_FNV_spikes_and_reset_receipts_verified_before_failure"]==1
    assert neural==timers==[0]
    assert all(v["valid_prefix_rows"]==1 for v in
               report["three_saved_full1024_256KiB_sidecars"].values())

def test_missing_completed_row_is_a_no_go(tmp_path,monkeypatch):
    evidence,oracle,out=fixture_failed(tmp_path,monkeypatch,frame=3,
                                       fault=201,valid_prior=0)
    with pytest.raises(triage.PostmortemNoGo,match="claimed completed"):
        triage.examine(evidence,oracle,out)
    assert not out.exists()

def test_unsolicited_third_committed_row_is_a_no_go(tmp_path,monkeypatch):
    evidence,oracle,out=fixture_failed(tmp_path,monkeypatch,frame=1,
                                       fault=201,valid_prior=3)
    with pytest.raises(triage.PostmortemNoGo,match="one unacknowledged"):
        triage.examine(evidence,oracle,out)

def test_unequal_sidecar_bytes_report_no_go(tmp_path,monkeypatch):
    evidence,oracle,out=fixture_failed(tmp_path,monkeypatch)
    file=evidence/"performance1024_capture"/"reset_profile1024_physical.bin"
    file.write_bytes(bytes(10))
    with pytest.raises(triage.PostmortemNoGo,match="size mismatch"):
        triage.examine(evidence,oracle,out)

def test_refuses_existing_report_overwrite(tmp_path,monkeypatch):
    evidence,oracle,out=fixture_failed(tmp_path,monkeypatch)
    out.write_text("keep")
    with pytest.raises(triage.PostmortemNoGo,match="no-overwrite"):
        triage.examine(evidence,oracle,out)
    assert out.read_text()=="keep"

def test_source_contains_no_board_tool_subprocesses():
    code=(ROOT/"scripts"/"p08_b45_full1024_failed_run_postmortem.py").read_text()
    assert "import subprocess" not in code
    assert "xsdb " not in code
    assert "devmem" not in code
    assert "mwr " not in code
    assert "socket" not in code
    assert "P08_B45_FULL1024_SUCCESS_CLAIM=0" in code
