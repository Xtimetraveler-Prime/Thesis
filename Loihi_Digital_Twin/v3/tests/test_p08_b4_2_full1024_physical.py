"""P08-B4.2 NO BOARD: original B2.3 full1024 physical admission/capture gates."""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p08_b4_2_physical_run as physical
import p08_b4_2_verify_full1024 as numerical
import p08_b4_1_merge_scalar_1024 as merge
import p08_b2_4_verify_untrusted_first16 as old_records
import test_p08_b2_4_numerical as former

def test_runner_always_default_denies_without_64_true_shards(tmp_path,monkeypatch):
    def forbid(*args,**kwargs):
        raise AssertionError("no actual board/tool subprocess")
    monkeypatch.setattr(physical.b4i,"log_call",forbid)
    a=argparse.Namespace(
        stage=tmp_path/"nothing",first16=tmp_path/"first16",
        shards=tmp_path/"shards",oracle=tmp_path/"full",
        ingress=tmp_path/"ingress",elf=tmp_path/"elf",
        linker_map=tmp_path/"map",reports=tmp_path/"reports",
        reset_pins=tmp_path/"pins")
    with pytest.raises((physical.FullPhysicalNoGo,
                        physical.prior.PilotPhysicalNoGo,OSError)):
        physical.admission(a)
    assert list(tmp_path.iterdir())==[]

def test_destructive_mode_requires_all_eight_distinct_yes(tmp_path,monkeypatch):
    def forbid(*args,**kwargs):
        raise AssertionError("no physical JTAG")
    monkeypatch.setattr(physical.b4i,"log_call",forbid)
    assert len(physical.APPROVALS)==8
    a=argparse.Namespace(evidence=tmp_path/"never")
    for name in physical.APPROVALS:
        setattr(a,name,"NO")
    with pytest.raises(physical.FullPhysicalNoGo):
        physical.execute(a,{})
    assert not a.evidence.exists()

def test_full1024_tcl_authentic_elf_only_bounded_then_1024(tmp_path):
    script=ROOT/physical.LAUNCH_TCL
    src=script.read_text()
    assert physical.ELF_SHA=="0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1"
    assert physical.MAP_SHA=="f7ce75a736b6b093066b8df09a8b02aaa41b490fd48c36c23151b4ac22125efc"
    assert "P08_B2_3_ORIGINAL_27CORE_1024_IMAGE_ONLY_A53_V1" in src
    assert "P08_B2_3_IMAGE_ONLY_1024_TERMINAL_DONE=1" in src
    assert "P08_B3_ORIGINAL_27CORE_FIRST16_PILOT_A53_V1" not in src
    assert "p08_b4_original_full1024.elf" in src
    assert "0x42200000 65536" in src
    assert "0x42300000 65536" in src
    assert "journal1024_physical.bin" in src
    assert "timing1024_physical.bin" in src
    assert "3 1023 4 0 5 1024" in src
    assert "P08_B4_FULL1024_EXACT_1024_FRAME_HARDWARE_TERMINAL_OBSERVED=1" in src
    assert "if {$state eq \"PROGRESS\"}" in src
    assert "set terminal_state $state" in src
    tcl=shutil.which("tclsh")
    if tcl:
        p=subprocess.run([tcl,str(script)],capture_output=True,text=True,
                         cwd=tmp_path,timeout=20)
        assert p.returncode!=0 and "P08-B4.2:" in p.stderr

def test_actual_1024_tcl_mailbox_classifier_never_stops_on_progress(tmp_path):
    tcl=shutil.which("tclsh")
    if not tcl:pytest.skip("no standalone Tcl interpreter")
    source=(ROOT/physical.LAUNCH_TCL).read_text()
    proc=re.search(r"(?ms)^proc pilot_mailbox_classify \{raw\} \{\n.*?^\}",source)
    assert proc, "Tcl executable classifier must be separately testable"
    cases=(
        (0xC0DE0000,0xFFFFFFFF,0,0,0xC0DEF00D,"PROGRESS"),
        (0xC0DE0000,0,0,1,0xC0DEF00D,"PROGRESS"),
        (0xC0DE0000,15,0,16,0xC0DEF00D,"PROGRESS"),
        (0xC0DE0000,1023,0,1024,0xC0DEF00D,"PROGRESS"),
        (0x600D0823,1023,0,1024,0xC0DEF00D,"SUCCESS"),
        (0x600D0823,1023,0,1023,0xC0DEF00D,"INVALID"),
        (0x600D0823,1022,0,1024,0xC0DEF00D,"INVALID"),
        (0xDEAD0823,160,205,160,0xC0DEF00D,"FAILURE"),
        (0xC0DE0000,17,0,16,0xC0DEF00D,"INVALID"),
        (0x600D0823,1023,0,1024,0,"INCOMPLETE"),
    )
    for status,index,fault,completed,done,expected in cases:
        words=[0]*64
        words[:6]=[0x50384232,1,status,index,fault,completed]
        words[63]=done
        enc=base64.b64encode(struct.pack("<64I",*words)).decode()
        input_=proc.group()+(
            "\nset raw [binary decode base64 {"+enc+"}]\n"+
            "puts [pilot_mailbox_classify $raw]\n")
        call=subprocess.run([tcl],input=input_,capture_output=True,
                            text=True,cwd=tmp_path,timeout=20)
        assert call.returncode==0,call.stderr
        assert call.stdout.strip()==expected,(expected,call.stdout)

def ref(i):
    # Historical 16-frame fixture uses bytes([i]), which is intentionally
    # limited to uint8 range. Reuse its verified field construction
    # with a bounded pixel pattern while preserving unique ordinals.
    r=former.fake_ref(i%200)
    r["ordinal"]=i
    r["TRAIN_source_index"]=37384+i
    # Historical journal fixture stores FNV = 1000+physical ordinal.
    r["expected_all_26_ticks_1010_neuron_FNV64"]=f"0x{1000+i:016X}"
    return r

@pytest.fixture
def synthetic_full1024(tmp_path,monkeypatch):
    refs=[ref(i) for i in range(1024)]
    first16=tmp_path/"original16.json"
    first16.write_text(json.dumps({"frames":refs[:16]}))
    monkeypatch.setattr(numerical.original16,"source_oracle",
                        lambda _p: {"frames":refs[:16]})
    oracle=tmp_path/"full1024.json"
    oracle.write_text(json.dumps({
        "schema":merge.SCHEMA,"count":1024,
        "shard_count":64,"shard_size":16,
        "original_first16_physically_verified_scalar_oracle_sha256":
            numerical.original16.ORACLE_SHA,
        "original_raw1024_sha256":merge.baseline.RAW_POOL_SHA,
        "original_B24_compiled_sha256":
            "02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a",
        "original_B24_source_sha256":
            "0a3ec838a9f95a73de118e37f31d596bf38e63cd8cf82e6f5c9d0dd48b22797a",
        "actual_KV260_1024_physical_execution":False,
        "physical_latency_accepted":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "frames":refs,
    }))
    journals=tmp_path/"journal1024.bin"
    journals.write_bytes(b"".join(former.journal(i,r) for i,r in enumerate(refs)))
    timers=tmp_path/"timing1024.bin"
    timers.write_bytes(b"".join(former.timing(i) for i in range(1024)))
    words=[0]*64
    words[:6]=[old_records.MAILBOX_MAGIC,1,old_records.PASS,1023,0,1024]
    words[6]=99999001
    words[8:14]=[1024,702,26,0,0,0]
    words[63]=old_records.DONE
    mb=tmp_path/"terminal1024.bin"
    mb.write_bytes(struct.pack("<64I",*words))
    return oracle,first16,journals,timers,mb,refs

def test_original_full1024_unverified_format_parity_and_six_service_phases(
        synthetic_full1024,tmp_path):
    oracle,first16,journal,timing,mailbox,refs=synthetic_full1024
    output=tmp_path/"reported.json"
    out=numerical.verify(oracle,first16,journal,timing,mailbox,output)
    assert out["count"]==1024
    assert out["all_1024_original_full26_tick_neural_FNV_equal_scalar"]
    assert out["complete_service_counter_ticks"]["median"]==8500
    assert out["terminal"]["last_completed_ordinal"]==1023
    assert len(out["six_separate_phase_counter_tick_summaries"])==6
    assert out["genuine_physical_provenance_verified"] is False
    assert out["actual_KV260_1024_numerical_accepted"] is False
    assert output.is_file()
    with pytest.raises(numerical.FullRecordNoGo,match="new external"):
        numerical.verify(oracle,first16,journal,timing,mailbox,output)

@pytest.mark.parametrize("kind",[
    "wrong_terminal_count","wrong_terminal_generation","wrong_journal_sha",
    "wrong_journal_fnv","wrong_journal_crc","missing_row",
    "timing_backtrack","timing_crc","wrong_model",
    "wrong_first16","not_original_test_seal",
])
def test_all_1024_failclosed_on_corrupt_physical_oracle_and_journal(
        synthetic_full1024,tmp_path,kind):
    oracle,first16,journal,timing,mailbox,refs=synthetic_full1024
    if kind.startswith("wrong_terminal"):
        words=list(struct.unpack("<64I",mailbox.read_bytes()))
        if kind=="wrong_terminal_count":words[5]=1023
        else:words[8]=1023
        mailbox.write_bytes(struct.pack("<64I",*words))
    elif kind.startswith("wrong_journal") or kind=="missing_row":
        raw=bytearray(journal.read_bytes())
        pos=734*256
        if kind=="wrong_journal_sha":raw[pos+34*4]^=1
        elif kind=="wrong_journal_fnv":raw[pos+17*4]^=1
        elif kind=="wrong_journal_crc":raw[pos+61*4]^=1
        else:raw=raw[:-256]
        journal.write_bytes(raw)
    elif kind.startswith("timing"):
        raw=bytearray(timing.read_bytes())
        pos=501*256
        if kind=="timing_backtrack":raw[pos+6*4:pos+7*4]=bytes(4)
        else:raw[pos+61*4]^=1
        timing.write_bytes(raw)
    else:
        doc=json.loads(oracle.read_text())
        if kind=="wrong_model":
            doc["original_B24_compiled_sha256"]="0"*64
        elif kind=="wrong_first16":
            doc["frames"][7]["expected_prediction"]=99
        else:doc["official_MNIST_TEST"]="OPENED"
        oracle.write_text(json.dumps(doc))
    output=tmp_path/"reject.json"
    with pytest.raises((numerical.FullRecordNoGo,old_records.RecordNoGo)):
        numerical.verify(oracle,first16,journal,timing,mailbox,output)
    assert not output.exists()
