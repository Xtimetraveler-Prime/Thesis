"""Strictly PC-only P08-B4 non-intrusive mailbox snapshot monitor tests."""
from __future__ import annotations

import inspect
from pathlib import Path
import struct
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p08_b4_2_monitor_mailbox_pc_only as watch

def mailbox(status:int,frame:int,completed:int,
            fault:int=0,done:int=watch.DONE)->bytes:
    words=[0]*64
    words[:6]=[watch.MAGIC,1,status,frame,fault,completed]
    words[63]=done
    return struct.pack("<64I",*words)

@pytest.mark.parametrize("status,frame,count,done,expected",[
    (watch.PROGRESS,0xFFFFFFFF,0,watch.DONE,"PROGRESS"),
    (watch.PROGRESS,0,1,watch.DONE,"PROGRESS"),
    (watch.PROGRESS,15,16,watch.DONE,"PROGRESS"),
    (watch.PROGRESS,1023,1024,watch.DONE,"PROGRESS"),
    (watch.SUCCESS,1023,1024,watch.DONE,"SUCCESS"),
    (watch.SUCCESS,1023,1023,watch.DONE,"INVALID"),
    (watch.SUCCESS,1022,1024,watch.DONE,"INVALID"),
    (watch.PROGRESS,1024,1025,watch.DONE,"INVALID"),
    (watch.PROGRESS,2,2,watch.DONE,"INVALID"),
    (watch.FAILURE,17,17,watch.DONE,"FAILURE"),
    (watch.SUCCESS,1023,1024,0,"INCOMPLETE"),
])
def test_mbox_progress_and_terminal_strict(
        status,frame,count,done,expected):
    result=watch.decode(mailbox(status,frame,count,done=done))
    assert result["state"]==expected
    assert result["completed"]==count
    assert result["last_frame"]==frame

def test_partial_and_invalid_snapshots_not_success():
    assert watch.decode(b"")["state"]=="PARTIAL"
    assert watch.decode(bytes(255))["state"]=="PARTIAL"
    bad=bytearray(mailbox(watch.SUCCESS,1023,1024))
    bad[0]=0
    assert watch.decode(bytes(bad))["state"]=="INVALID"

def test_probe_reads_only_existing_pc_side_snapshot(tmp_path,capsys):
    cap=tmp_path/"full1024_capture"
    cap.mkdir()
    poll=cap/watch.POLL
    poll.write_bytes(mailbox(watch.PROGRESS,3,4))
    pre={p.name:p.read_bytes() for p in cap.iterdir()}
    assert watch.snapshot(tmp_path)["state"]=="PROGRESS"
    assert watch.snapshot(tmp_path)["source"]==watch.POLL
    # Real runner renames poll.tmp -> terminal on completion; read either.
    terminal=cap/watch.TERMINAL
    poll.rename(terminal)
    terminal.write_bytes(mailbox(watch.SUCCESS,1023,1024))
    done=watch.snapshot(tmp_path)
    assert done["state"]=="SUCCESS" and done["source"]==watch.TERMINAL
    assert terminal.read_bytes()==mailbox(watch.SUCCESS,1023,1024)
    assert watch.main(["--evidence",str(tmp_path),"--samples","1",
                       "--interval","0"])==0
    stdout=capsys.readouterr().out
    assert "READ ONLY" in stdout
    assert "1024/1024" in stdout
    assert "no JTAG, board or hardware actions" in stdout
    assert sorted(p.name for p in cap.iterdir())==[watch.TERMINAL]

def test_empty_or_torn_snapshot_is_not_interpreted_as_hang(tmp_path):
    assert watch.snapshot(tmp_path)["state"]=="MISSING"
    cap=tmp_path/"full1024_capture"
    cap.mkdir()
    assert watch.snapshot(tmp_path)["state"]=="MISSING"
    (cap/watch.POLL).write_bytes(bytes(22))
    assert watch.snapshot(tmp_path)["state"]=="PARTIAL"

@pytest.mark.parametrize("args",[
    ["--evidence","relative/file"],
    ["--evidence","/tmp/not-real","--samples","0"],
    ["--evidence","/tmp/not-real","--samples","121"],
    ["--evidence","/tmp/not-real","--interval","-1"],
])
def test_monitor_arguments_fail_closed(args):
    with pytest.raises(SystemExit):
        watch.main(args)

def test_monitor_source_uses_no_hardware_or_filesystem_writes():
    source=inspect.getsource(watch)
    for forbidden in ("subprocess","socket","serial","xsdb ","vivado ",
                      ".write_bytes(", ".write_text(", ".unlink(", ".rename(",
                      ".replace(", ".mkdir(", "connect("):
        assert forbidden not in source,forbidden
    assert "read_bytes()" in source
    assert "full1024_capture" in source
    assert "mailbox_poll.tmp" in source
    assert "mailbox_terminal_physical.bin" in source
