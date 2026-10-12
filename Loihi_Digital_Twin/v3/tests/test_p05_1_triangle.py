"""P05.1 second *different neural network* host rehearsal.

A synthetic mailbox is only verifier testing; no physical acceptance
until the KV260 actually reports 15 direct-resident packet deliveries,
15 checkpoints and three byte-exact oracle final records.
"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
TRI=ROOT/"scripts/p05_1_triangle_fixture.py"
VER=ROOT/"scripts/p05_1_triangle_verify.py"
RUN=ROOT/"scripts/run_p05_1_triangle.sh"

spec=importlib.util.spec_from_file_location("p05_triangle_verify_module",VER)
assert spec and spec.loader
verify_module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_module)


@pytest.fixture(scope="module")
def triangle_seed(tmp_path_factory):
    target=tmp_path_factory.mktemp("p05_triangle")/"model_seed"
    proc=subprocess.run(
        ["bash",str(RUN),"prepare",str(target)],
        capture_output=True,text=True,timeout=120,cwd=ROOT,
    )
    assert proc.returncode==0,proc.stdout+proc.stderr
    assert "KV260 was NOT touched" in proc.stdout
    gate=json.loads((target/"triangle_gate.json").read_text())
    assert gate["expected_dispatches"]==15
    assert gate["expected_packets"]==12
    assert gate["expected_resident_deliveries"]==12
    assert gate["expected_checkpoints"]==15
    assert gate["expected_page_operations"]==6
    assert gate["neural_parameters"]["threshold"]==4
    assert gate["topology"]=={"0":1,"1":2,"2":0}
    return target


@pytest.fixture
def triangle(tmp_path,triangle_seed):
    target=tmp_path/"triangle"
    shutil.copytree(triangle_seed,target)
    dst=target/"final_ddr"
    dst.mkdir()
    for cid in range(3):
        shutil.copy2(target/"triangle_golden"/f"core{cid}_expected.bin",
                     dst/f"core{cid}_after.bin")
    return target


def synthetic_mailbox(root:Path):
    words=[0]*64
    words[:20]=[
        0x52353050,1,0x600D600D,0,
        5,5,3,3,18,0,0,
        15,12,5,
        3,0,0,3,0,15,
    ]
    words[20]=10
    words[22]=100
    words[24]=1000
    words[32:42]=[
        99999001,0x4C543302,0x1031F,15,6,106496,0,0,50,50
    ]
    words[42:45]=[12,15,15]
    head=struct.unpack("<64I",(root/"p05_artifacts/p05_header.bin").read_bytes())
    words[50],words[51]=head[23],head[22]
    words[54:58]=[1,15,15,15]
    return struct.pack("<64I",*words)


def run_verify(root,capsys):
    ret=verify_module.verify(root/"p05_a53_result.bin",root)
    captured=capsys.readouterr()
    return ret,captured.out+captured.err


def test_triangle_new_neural_profile_is_not_frozen_p03(triangle):
    model=json.loads((triangle/"triangle_golden/manifest.json").read_text())
    gate=json.loads((triangle/"triangle_gate.json").read_text())
    desc=json.loads((triangle/"p05_artifacts/p05_manifest.json").read_text())
    assert model["logical_core_ids"]==[0,1,2]
    assert model["expected_packet_count_total"]==12
    assert desc["timesteps"]==5
    assert desc["events"]==desc["checkpoints"]==15
    assert gate["oracle_trace_sha256"]!=(
        "9a925277fdeffbcce837954b6d44ce118d88e839f3a6b2d9d6e4956cf32747ac"
    )
    for cid in range(3):
        raw=(triangle/"triangle_golden"/f"core{cid}_initial.bin").read_bytes()
        cfg=int.from_bytes(raw[0x1000:0x1010],"little")
        assert (cfg>>26)&0xFFFFFF==4
        route=int.from_bytes(raw[0x50000:0x50004],"little")
        assert route&127==(cid+1)%3


def test_synthetic_complete_triangle_mailbox_and_three_exact_ddr(triangle,capsys):
    (triangle/"p05_a53_result.bin").write_bytes(synthetic_mailbox(triangle))
    success,logs=run_verify(triangle,capsys)
    assert success,logs
    assert "resident_deliveries=12" in logs
    assert "three 512KiB final DDR records byte-exact" in logs
    assert "P05_TRIANGLE_METADATA=" in logs


@pytest.mark.parametrize("word,value,fragment",[
    (2,0xDEAD0008,"result"),
    (6,5,"cores"),
    (11,14,"dispatches"),
    (12,14,"packets"),
    (13,4,"barriers"),
    (15,1,"replacement_ins"),
    (16,1,"runtime_outs"),
    (35,14,"hw_dispatches"),
    (36,5,"hw_pages"),
    (42,14,"resident_deliveries"),
    (44,14,"checkpoints_passed"),
    (50,0,"header_crc"),
    (58,1,"diag_flags"),
])
def test_triangle_mailbox_bad_counts_fail_closed(triangle,capsys,word,value,fragment):
    words=list(struct.unpack("<64I",synthetic_mailbox(triangle)))
    assert words[word]!=value
    words[word]=value
    (triangle/"p05_a53_result.bin").write_bytes(
        struct.pack("<64I",*words)
    )
    success,logs=run_verify(triangle,capsys)
    assert not success
    assert fragment in logs
    assert "P05_TRIANGLE_FINAL_DDR_COMPARISON=PASS" in logs


def test_triangle_checkpoint_failure_reports_first_mismatch(triangle,capsys):
    words=list(struct.unpack("<64I",synthetic_mailbox(triangle)))
    words[2],words[3],words[8],words[9]=0xDEAD000A,10,19,11
    words[44]=7
    words[45:50]=[2,1,1,0x01020304,0xDEADBEEF]
    words[58]=1
    (triangle/"p05_a53_result.bin").write_bytes(struct.pack("<64I",*words))
    success,logs=run_verify(triangle,capsys)
    assert not success
    assert "P05_TRIANGLE_FIRST_DIAGNOSTIC=" in logs
    assert '"failed_core": 1' in logs
    assert '"failed_step": 2' in logs


def test_triangle_bad_real_final_ddr_rejected(triangle,capsys):
    (triangle/"p05_a53_result.bin").write_bytes(synthetic_mailbox(triangle))
    file=triangle/"final_ddr/core1_after.bin"
    raw=bytearray(file.read_bytes())
    raw[0x5000]^=1
    file.write_bytes(raw)
    success,logs=run_verify(triangle,capsys)
    assert not success
    assert "P05_TRIANGLE_FINAL_DDR_COMPARISON=FAIL" in logs
    assert "core 1 final record mismatch" in logs


def test_triangle_fixture_tampering_refused(triangle,capsys):
    (triangle/"p05_a53_result.bin").write_bytes(synthetic_mailbox(triangle))
    header=triangle/"p05_artifacts/p05_header.bin"
    blob=bytearray(header.read_bytes())
    blob[0]^=1
    header.write_bytes(blob)
    success,logs=run_verify(triangle,capsys)
    assert not success
    assert "triangle evidence admission" in logs


def test_triangle_destructive_scripts_opt_in_and_source_identities():
    p=subprocess.run(["bash","-n",str(RUN)],
                     capture_output=True,text=True,timeout=30)
    assert p.returncode==0,p.stderr
    t=RUN.read_text()
    assert "P05_1_CONFIRM_KV260_DDR_OVERWRITE" in t
    assert "p05_1_triangle_prepare.tcl" in t
    assert "p05_1_triangle_dump.tcl" in t
    assert "p03_2c_program_bitstream.tcl" in t
    assert "p03_finish_xsdb_run.tcl" in t
    assert "p05_1_triangle_verify.py" in t
    assert "P05_CONFIGURABLE_A53_REGRESSION_V1" in t
    assert "source/p05_regression_run.c" not in t or (
        "cmp -s" in t
    )
    assert "p05_regression_run.elf" in t
    prep=(ROOT/"vivado/p05_1_triangle_prepare.tcl").read_text()
    dump=(ROOT/"vivado/p05_1_triangle_dump.tcl").read_text()
    assert "0x43F00000" in prep
    assert "0x43FE0000" in prep
    assert "0x43FF0000" in prep
    assert "p05_equal" in prep
    assert "mrd -bin -file" in dump
    assert "{$core < 3}" in prep
    assert "{$core < 3}" in dump
