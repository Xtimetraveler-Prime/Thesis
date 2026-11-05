"""Pure tclsh exercise of REAL full1024 XSDB mailbox classifier/progress writer.

Only source proc declarations extracted, NEVER source top-level Tcl or
connect JTAG. Synthesizes scalar 64-word mailbox flags and atomically
created host progress to verify exact final 1024 vs 16/early fake DONE.
"""
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p08_b45_perf_full1024_monitor as monitor


@pytest.fixture
def extracted():
    source=(ROOT/"vivado"/"p08_b45_perf_full1024_run_and_capture.tcl").read_text()
    first=source.index("proc pilot_mailbox_classify {raw} {")
    last=source.index("\n# Pure HOST FILE progress feed",first)
    mailbox=source[first:last]
    begin=source.index("proc p08_perf1024_progress {out mode completed state started} {")
    end=source.index("\nset started [clock seconds]",begin)
    progress=source[begin:end]
    assert "connect -url" not in mailbox+progress
    assert "mrd " not in mailbox+progress and "mwr " not in mailbox+progress
    return mailbox,progress


def tclrun(script:str,tmp_path:Path)->str:
    if not shutil.which("tclsh"):pytest.skip("tclsh unavailable")
    p=subprocess.run(["tclsh"],input=script,capture_output=True,text=True,
                     cwd=tmp_path,timeout=20)
    assert p.returncode==0,p.stdout+p.stderr
    return p.stdout


def payload(kind:str,completed:int,frame:int|None=None,wrong:bool=False)->bytes:
    words=[0]*64
    words[0]=0x50384232
    words[1]=1
    words[2]={"progress":0xC0DE0000,"success":0x600D0823,
              "failure":0xDEAD0823}[kind]
    words[3]= (0xFFFFFFFF if completed==0 else completed-1) if frame is None else frame
    words[4]=0
    words[5]=completed
    words[63]=0xC0DEF00D
    if wrong:words[4]=1
    return struct.pack("<64I",*words)


@pytest.mark.parametrize(("kind","count","frame","expected"),(
    ("progress",0,None,"PROGRESS"),
    ("progress",17,None,"PROGRESS"),
    ("progress",1024,None,"PROGRESS"),
    ("success",1024,None,"SUCCESS"),
    ("success",16,None,"INVALID"),
    ("success",1024,16,"INVALID"),
    ("failure",101,None,"FAILURE"),
))
def test_real_classifier_zero_to_final_and_fake_early_done(extracted,tmp_path,
                                                            kind,count,frame,expected):
    mailbox,_=extracted
    file=tmp_path/"mailbox.bin"
    file.write_bytes(payload(kind,count,frame))
    tcl=mailbox+"\nset f [open "+str(file)+" rb]\n"
    tcl+="fconfigure $f -translation binary -encoding binary\n"
    tcl+="set raw [read $f]\nclose $f\nputs [pilot_mailbox_classify $raw]\n"
    assert tclrun(tcl,tmp_path).strip()==expected


def test_real_atomic_host_progress_writer_and_monitor_parsing(extracted,tmp_path):
    _,fn=extracted
    began=int(time.time())-5
    script=fn+"\np08_perf1024_progress "+str(tmp_path)
    script+=" once 17 POLLING "+str(began)+"\n"
    script+="p08_perf1024_progress "+str(tmp_path)
    script+=" once 1024 CAPTURE_DONE_PENDING_INDEPENDENT "+str(began)+"\n"
    script+="puts P08_B45_FULL1024_PROGRESS_TCL_NATIVE_PASS=1\n"
    assert "P08_B45_FULL1024_PROGRESS_TCL_NATIVE_PASS=1" in tclrun(script,tmp_path)
    snapshot=tmp_path/"progress_state.txt"
    assert snapshot.is_file()
    assert not (tmp_path/"progress_state.tmp").exists()
    parsed=monitor.parse_snapshot(snapshot.read_text(),expected_mode="once")
    assert parsed["completed"]==1024
    assert parsed["state"]=="CAPTURE_DONE_PENDING_INDEPENDENT"
    assert parsed["elapsed_seconds"]>=5
    assert parsed["total"]==1024
