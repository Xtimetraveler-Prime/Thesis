"""P05.2h native device-evidence verifier and independent model replay tests.

All mailboxes/DDRs made in this module are explicitly SYNTHETIC.
None can satisfy real KV260 physical acceptance.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zlib

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p05_2h_barrier_fixture as MODEL
import p05_2h_barrier_verify as CHECK
RUN=ROOT/"scripts/run_p05_2h_barrier.sh"

@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    path=tmp_path_factory.mktemp("p05_2h")/"prepared"
    cmd=subprocess.run(
        ["bash",str(RUN),"prepare",str(path)],
        capture_output=True,text=True,timeout=240,cwd=ROOT
    )
    assert cmd.returncode==0,cmd.stdout+cmd.stderr
    assert "KV260 was NOT touched" in cmd.stdout
    g=json.loads((path/"p05_2h_barrier_gate.json").read_text())
    assert g["profile"]==MODEL.PROFILE
    assert g["status"]=="MODEL_ONLY_NOT_HARDWARE_ACCEPTED"
    assert (g["steps"],g["cores"],g["order"],g["slots"])==(
        16,[0,1,2,3,4],[4,1,3,0,2],3)
    assert g["expected_dispatches"]==80
    assert g["expected_events"]==80
    assert g["expected_checkpoints"]>=240
    s=g["scheduler_model"]
    assert s["replacement_ins"]>=40 and s["runtime_outs"]>=40
    assert s["resident_deliveries"]>=10 and s["nonresident_deliveries"]>=10
    return path

def fake_p05r(root):
    gate=json.loads((root/"p05_2h_barrier_gate.json").read_text())
    pager=gate["scheduler_model"]
    h=struct.unpack("<64I",(root/"p05_artifacts/p05_header.bin").read_bytes())
    w=[0]*64
    w[:20]=[
        0x52353050,1,0x600D600D,0,16,16,5,3,18,0,0,
        80,gate["expected_packets"],16,3,pager["replacement_ins"],
        pager["runtime_outs"],pager["final_outs"],
        pager["evictions"],pager["hits"],
    ]
    for idx,val in ((20,700),(22,1200),(24,1900),(26,220),
                    (28,105),(30,125),(32,99999001),(33,0x4C543302),
                    (34,0x0001031F),(35,80),(36,pager["page_commands"]),
                    (37,106496),(38,0),(39,0),(40,160),(41,160),
                    (42,pager["resident_deliveries"]),(43,80),
                    (44,gate["expected_checkpoints"]),
                    (50,h[23]),(51,h[22]),(54,1),(55,80),
                    (56,gate["expected_checkpoints"]),(57,80)):
        w[idx]=val
    return struct.pack("<64I",*w)

@pytest.fixture
def synthetic(prepared,tmp_path):
    root=tmp_path/"synthetic"
    shutil.copytree(prepared,root)
    final=root/"final_ddr"
    final.mkdir()
    for c in MODEL.CORES:
        shutil.copy2(root/"barrier_physical_golden"/f"core{c}_expected.bin",
                     final/f"core{c}_after.bin")
    (root/"p05_a53_result.bin").write_bytes(fake_p05r(root))
    return root

def test_reconstructed_all_16_checkpoints_cover_all_event_banks(prepared):
    gate=json.loads((prepared/"p05_2h_barrier_gate.json").read_text())
    checkpoints=json.loads((prepared/"p05_2h_barrier_spec.json").read_text())["checkpoints"]
    assert len(checkpoints)==gate["expected_checkpoints"]
    assert len(gate["barrier_timeline"])==16
    for step in range(16):
        rows=[row for row in checkpoints if row["timestep"]==step]
        assert [r["core"] for r in rows if r["state_class"]=="state0"]==list(MODEL.ORDER)
        assert [r["core"] for r in rows if r["state_class"]=="event0"]==list(MODEL.ORDER)
        assert [r["core"] for r in rows if r["state_class"]=="event1"]==list(MODEL.ORDER)
        assert gate["barrier_timeline"][step]["current_bank"]==step%2
        assert gate["barrier_timeline"][step]["next_bank"]==1-step%2
        assert set(gate["barrier_timeline"][step]["current_count_after_barrier"].values())=={0}
    assert any(r["state_class"]=="packet0" for r in checkpoints)
    assert gate["expected_packets"]>0

def test_separate_logical_vs_physical_route_packet_bank_is_surgical(prepared):
    g=json.loads((prepared/"p05_2h_barrier_gate.json").read_text())
    changed=0
    for c in MODEL.CORES:
        logical=(prepared/"barrier_logical_golden"/f"core{c}_expected.bin").read_bytes()
        physical=(prepared/"barrier_physical_golden"/f"core{c}_expected.bin").read_bytes()
        assert len(logical)==len(physical)==0x80000
        assert logical[:0x64000]==physical[:0x64000]
        assert logical[0x64010:]==physical[0x64010:]
        assert hashlib.sha256(physical).hexdigest()==g["physical_final_record_sha256"][str(c)]
        if logical!=physical:changed+=1
    assert changed>=1, "exercise wraparound physical destination-order correction"

def test_synthetic_verified_mailbox_and_full_five_DDR(prepared,synthetic,capsys):
    result=CHECK.verify(synthetic/"p05_a53_result.bin",synthetic)
    out=capsys.readouterr()
    assert result,out.err
    assert "P05_2H_VERIFY_EXIT=0" in out.out
    assert "both event-bank first words" in out.out
    assert "all five complete" in out.out

@pytest.mark.parametrize("cid,offset",[
    (0,0x5000),
    (1,0x54000),
    (2,0x58000),
    (3,0x64000),
    (4,0x5C000),
    (4,0x1000),
    (0,0x7ffff),
])
def test_any_core_any_important_DDR_region_mutation_fails(synthetic,capsys,cid,offset):
    p=synthetic/"final_ddr"/f"core{cid}_after.bin"
    b=bytearray(p.read_bytes());b[offset]^=1;p.write_bytes(b)
    assert not CHECK.verify(synthetic/"p05_a53_result.bin",synthetic)
    assert "FAIL: P05.2h" in capsys.readouterr().err

@pytest.mark.parametrize("field,value",[
    (2,0xDEAD000A),(11,79),(12,0),(13,15),(15,0),
    (16,0),(18,0),(35,79),(36,0),(42,0),(43,79),
    (44,0),(50,0),(54,0),(56,0),(58,1),(60,1),
])
def test_forged_P05R_result_count_fault_or_modes_never_pass(synthetic,capsys,field,value):
    p=synthetic/"p05_a53_result.bin"
    words=list(struct.unpack("<64I",p.read_bytes()))
    if words[field]==value:pytest.skip("chosen mutation already equals synthetic field")
    words[field]=value;p.write_bytes(struct.pack("<64I",*words))
    assert not CHECK.verify(p,synthetic)
    assert "FAIL: P05.2h" in capsys.readouterr().err

def test_bad_event0_barrier_crc_in_payload_fails_before_hardware(synthetic,capsys):
    p=synthetic/"p05_artifacts/p05_payload.bin"
    data=bytearray(p.read_bytes())
    head=struct.unpack("<64I",(synthetic/"p05_artifacts/p05_header.bin").read_bytes())
    checkoffset=head[18]
    first_event0_crc=checkoffset+16
    data[first_event0_crc+12]^=1
    p.write_bytes(data)
    assert not CHECK.verify(synthetic/"p05_a53_result.bin",synthetic)
    assert "FAIL: P05.2h" in capsys.readouterr().err

def test_model_trace_or_physical_order_tampering_fails(synthetic,capsys):
    p=synthetic/"barrier_physical_golden/core3_expected.bin"
    b=bytearray(p.read_bytes());b[0x64000]^=1;p.write_bytes(b)
    assert not CHECK.verify(synthetic/"p05_a53_result.bin",synthetic)
    assert "FAIL: P05.2h" in capsys.readouterr().err

def test_runner_and_tcl_are_guarded_without_bitstream_rebuild():
    text=RUN.read_text()
    for required in ("P05_2H_CONFIRM_KV260_DDR_OVERWRITE",
                     "P03_2C_EXPECTED_XSA_SHA","P03_DIAG_REPORTS",
                     "P05_1_BUILD_DIR","p05_2h_barrier_prepare.tcl",
                     "p05_2h_barrier_verify.py","preflight_identity.txt",
                     "P05_CONFIGURABLE_A53_REGRESSION_V1",
                     "python -m py_compile","set -euo pipefail"):
        assert required in text
    assert subprocess.run(["bash","-n",str(RUN)],
                          capture_output=True,text=True).returncode==0
