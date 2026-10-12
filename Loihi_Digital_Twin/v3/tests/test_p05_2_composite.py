"""P05.2e combined FIVE-over-THREE physical acceptance HOST rehearsal.

Synthetic P05R records here are only verifier unit tests.
Only a real KV260 packet+page+checkpoint mailbox plus FIVE
complete physical DDR dumps can establish physical acceptance.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import zlib

import pytest

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/"scripts/run_p05_2_composite.sh"
CHECK=ROOT/"scripts/p05_2_composite_verify.py"


def load(name:str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


VERIFY=load("p05_2e_composite_host_verifier",CHECK)


@pytest.fixture(scope="module")
def original(tmp_path_factory):
    out=tmp_path_factory.mktemp("p05_2e_composite")/"prepared"
    p=subprocess.run(["bash",str(RUN),"prepare",str(out)],
                     cwd=ROOT,capture_output=True,text=True,timeout=210)
    assert p.returncode==0,p.stdout+p.stderr
    assert "KV260 was NOT touched" in p.stdout
    gate=json.loads((out/"p05_2_composite_gate.json").read_text())
    manifest=json.loads((out/"p05_artifacts/p05_manifest.json").read_text())
    counts=gate["scheduler_model"]
    assert gate["service_order"]==[4,1,3,0,2]
    assert gate["threshold_by_core"]=={
        "0":4,"1":5,"2":6,"3":7,"4":8
    }
    assert gate["expected_dispatches"]==40
    assert gate["expected_checkpoints"]==40
    assert gate["max_current_events_per_core"]>=3
    assert counts["initial_ins"]==3
    assert counts["replacement_ins"]==37
    assert counts["runtime_outs"]==37
    assert counts["evictions"]==37
    assert counts["hits"]==3
    assert counts["final_outs"]==3
    assert counts["page_commands"]==80
    assert counts["programmed_page_in_payload_bytes"]==40*0x6B000
    assert counts["programmed_page_out_payload_bytes"]==40*0x1A000
    assert counts["programmed_total_page_payload_bytes"]==40*(0x6B000+0x1A000)
    assert counts["resident_deliveries"]>0
    assert counts["nonresident_deliveries"]>0
    assert counts["emitted_packets"]==(
        counts["resident_deliveries"]+counts["nonresident_deliveries"]
    )
    assert counts["max_packets_from_dispatch"]==2
    assert manifest["logical_core_ids_in_service_order"]==[4,1,3,0,2]
    assert manifest["events"]==manifest["checkpoints"]==40
    return out


@pytest.fixture
def staged(tmp_path,original):
    target=tmp_path/"composite"
    shutil.copytree(original,target)
    dump=target/"final_ddr"
    dump.mkdir()
    for core in range(5):
        shutil.copy2(target/"composite_golden"/f"core{core}_expected.bin",
                     dump/f"core{core}_after.bin")
    return target


def plausible_mailbox(root:Path)->bytes:
    gate=json.loads((root/"p05_2_composite_gate.json").read_text())
    stats=gate["scheduler_model"]
    h=struct.unpack("<64I",(root/"p05_artifacts/p05_header.bin").read_bytes())
    w=[0]*64
    w[:20]=[
        0x52353050,1,0x600D600D,0,
        8,8,5,3,18,0,0,40,stats["emitted_packets"],8,
        3,stats["replacement_ins"],stats["runtime_outs"],
        stats["final_outs"],stats["evictions"],stats["hits"],
    ]
    w[20]=600
    w[22]=800
    w[24]=1500
    w[26]=100
    w[28]=100
    w[30]=200
    w[32:42]=[
        99999001,0x4C543302,0x0001031F,40,
        stats["page_commands"],106496,0,0,500,500,
    ]
    w[42:45]=[stats["resident_deliveries"],40,40]
    w[50:52]=[h[23],h[22]]
    w[54:58]=[1,40,40,40]
    return struct.pack("<64I",*w)


def run_check(root,capsys):
    ok=VERIFY.verify(root/"p05_a53_result.bin",root)
    out=capsys.readouterr()
    return ok,out.out+out.err


def test_independent_model_packets_and_c_scheduler_paging_match(staged):
    mod=VERIFY.MODEL
    expected=mod.scheduler_prediction(mod.vectors(
        staged/"composite_golden","P02B_EXPECT_PACKETS"
    ))
    stored=json.loads((staged/"p05_2_composite_gate.json").read_text())
    assert stored["scheduler_model"]==expected
    assert expected["page_commands"]==80
    assert expected["replacement_ins"]==37
    assert expected["runtime_outs"]==37
    assert expected["resident_deliveries"]>0
    assert expected["nonresident_deliveries"]>0
    assert expected["emitted_packets"]>=40
    assert max(mod.vectors(staged/"composite_golden",
                           "P02B_EXPECT_EVENT_COUNT").values())>=3


def test_synthetic_five_full_records_and_all_telemetry_valid(staged,capsys):
    (staged/"p05_a53_result.bin").write_bytes(plausible_mailbox(staged))
    good,output=run_check(staged,capsys)
    assert good,output
    assert "FIVE-over-THREE composite" in output
    assert "checkpoints=40" in output
    assert "runtime_outs=37" in output
    assert "five complete 512KiB physical DDR records byte-exact" in output
    assert "P05_2E_COMPOSITE_METADATA=" in output


@pytest.mark.parametrize("word,change,term",[
    (2,0xDEAD0008,"result"),
    (4,7,"steps"),
    (6,3,"cores"),
    (7,2,"slots"),
    (11,39,"dispatches"),
    (13,7,"barriers"),
    (14,2,"initial_ins"),
    (15,36,"replacement_ins"),
    (16,36,"runtime_outs"),
    (17,2,"final_outs"),
    (18,36,"evictions"),
    (19,4,"hits"),
    (35,39,"hw_dispatches"),
    (36,79,"hw_pages"),
    (42,0,"resident_deliveries"),
    (43,39,"inputs_consumed"),
    (44,39,"checkpoints_passed"),
    (50,0,"header_crc"),
    (51,0,"payload_crc"),
    (54,0,"diagnostic_mode"),
    (58,1,"diag_flags"),
    (60,1,"reserved"),
])
def test_false_mailbox_cannot_pass(staged,capsys,word,change,term):
    w=list(struct.unpack("<64I",plausible_mailbox(staged)))
    assert w[word]!=change
    w[word]=change
    (staged/"p05_a53_result.bin").write_bytes(struct.pack("<64I",*w))
    good,output=run_check(staged,capsys)
    assert not good
    assert term in output


def test_corrupt_one_physical_page_rejected_even_if_mailbox_ok(staged,capsys):
    (staged/"p05_a53_result.bin").write_bytes(plausible_mailbox(staged))
    for core in (3,):
        file=staged/"final_ddr"/f"core{core}_after.bin"
        record=bytearray(file.read_bytes())
        record[0x5000]^=1
        file.write_bytes(record)
    good,out=run_check(staged,capsys)
    assert not good
    assert "P05_2E_COMPOSITE_FINAL_DDR=FAIL" in out


def test_corrupt_model_generated_paging_gate_rejected(staged,capsys):
    (staged/"p05_a53_result.bin").write_bytes(plausible_mailbox(staged))
    file=staged/"p05_2_composite_gate.json"
    gate=json.loads(file.read_text())
    gate["scheduler_model"]["runtime_outs"]-=1
    file.write_text(json.dumps(gate))
    good,out=run_check(staged,capsys)
    assert not good
    assert "composite independent scheduling predictions disagree" in out


def test_forged_crc_sha_still_cannot_change_event_order(staged,capsys):
    (staged/"p05_a53_result.bin").write_bytes(plausible_mailbox(staged))
    a=staged/"p05_artifacts"
    header=list(struct.unpack("<64I",(a/"p05_header.bin").read_bytes()))
    payload=bytearray((a/"p05_payload.bin").read_bytes())
    assert struct.unpack_from("<I",payload,header[17]+4)[0]==4
    struct.pack_into("<I",payload,header[17]+4,1)
    header[22]=zlib.crc32(payload)
    header[23]=0
    header[23]=zlib.crc32(struct.pack("<64I",*header))
    raw=struct.pack("<64I",*header)
    (a/"p05_header.bin").write_bytes(raw)
    (a/"p05_payload.bin").write_bytes(payload)
    m=json.loads((a/"p05_manifest.json").read_text())
    m["header_sha256"]=hashlib.sha256(raw).hexdigest()
    m["payload_sha256"]=hashlib.sha256(payload).hexdigest()
    (a/"p05_manifest.json").write_text(json.dumps(m))
    gatefile=staged/"p05_2_composite_gate.json"
    gate=json.loads(gatefile.read_text())
    gate["p05_header_sha256"]=m["header_sha256"]
    gate["p05_payload_sha256"]=m["payload_sha256"]
    gatefile.write_text(json.dumps(gate))
    good,out=run_check(staged,capsys)
    assert not good
    assert "composite event 0 no longer original model input" in out


def test_composite_reuses_frozen_accepted_fpga_and_A53_only():
    proc=subprocess.run(["bash","-n",str(RUN)],
                        capture_output=True,text=True,timeout=30)
    assert proc.returncode==0,proc.stderr
    c=RUN.read_text()
    t=(ROOT/"vivado/p05_2_composite_prepare.tcl").read_text()
    assert "P05_2_CONFIRM_KV260_DDR_OVERWRITE=YES" in c
    assert "p05_2_composite_fixture.py" in c
    assert "p05_2_composite_verify.py" in c
    assert "p05_2_composite_prepare.tcl" in c
    assert "p03_finish_xsdb_dump.tcl" in c
    assert "p03_finish_xsdb_run.tcl" in c
    assert "p03_2c_program_bitstream.tcl" in c
    assert "P05_CONFIGURABLE_A53_REGRESSION_V1" in c
    assert "p05_regression_run.elf" in c
    assert "cmp -s" in c
    assert "composite_golden" in t
    assert "{$core < 5}" in t
    assert "mrd -bin -file" in t
    assert "0x43F00000" in t
    assert "0x43FE0000" in t
    assert "0x43FF0000" in t
