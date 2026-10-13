"""P05.2f HOST rehearsal and fail-closed tests; NOT independent KV260 evidence.

The physical run must have real A53 P05R and FIVE complete DDR dumps.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p05_2f_arithmetic_verify as CHECK
import p05_2f_arithmetic_fixture as MODEL
RUN=ROOT/"scripts/run_p05_2f_arithmetic.sh"

@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    out=tmp_path_factory.mktemp("p05_2f")/"prepared"
    p=subprocess.run(["bash",str(RUN),"prepare",str(out)],cwd=ROOT,
                     capture_output=True,text=True,timeout=240)
    assert p.returncode==0,p.stdout+p.stderr
    assert "KV260 was NOT touched" in p.stdout
    gate=json.loads((out/"p05_2f_gate.json").read_text())
    assert gate["status"]=="MODEL_ONLY_NOT_HARDWARE_ACCEPTED"
    assert gate["expected_dispatches"]==30
    assert gate["expected_checks"]==30
    assert gate["expected_events"]==30
    assert gate["steps"]==6 and gate["order"]==[4,1,3,0,2]
    assert gate["scheduler_model"]["replacement_ins"]>=15
    assert gate["scheduler_model"]["runtime_outs"]>=15
    assert gate["expected_packets"]>0
    return out

@pytest.fixture
def synthetic(tmp_path,prepared):
    p=tmp_path/"synth"
    shutil.copytree(prepared,p)
    d=p/"final_ddr"
    d.mkdir()
    for cid in MODEL.CORES:
        shutil.copy2(p/"arithmetic_golden"/f"core{cid}_expected.bin",
                     d/f"core{cid}_after.bin")
    (p/"p05_a53_result.bin").write_bytes(fake_p05r(p))
    return p

def fake_p05r(p):
    # Synthetic VALID mailbox exists solely to unit-test verifier negatives.
    g=json.loads((p/"p05_2f_gate.json").read_text())
    s=g["scheduler_model"]
    h=struct.unpack("<64I",(p/"p05_artifacts/p05_header.bin").read_bytes())
    w=[0]*64
    w[:20]=[
        0x52353050,1,0x600D600D,0,6,6,5,3,18,0,0,
        30,g["expected_packets"],6,3,s["replacement_ins"],
        s["runtime_outs"],s["final_outs"],s["evictions"],s["hits"],
    ]
    w[20]=600
    w[22]=800
    w[24]=1500
    w[26]=100
    w[28]=100
    w[30]=200
    w[32:42]=[
        99999001,0x4C543302,0x0001031F,30,
        s["page_commands"],106496,0,0,500,500,
    ]
    w[42:45]=[s["resident_deliveries"],30,30]
    w[50:52]=[h[23],h[22]]
    w[54:58]=[1,30,30,30]
    return struct.pack("<64I",*w)

def test_model_uses_independent_signed_saturation_and_fractional_decay(prepared):
    from loihi_twin_v2.hardware_p03 import (
        unpack_compartment_state,unpack_compartment_config,unpack_synapse_word
    )
    states=MODEL.read_vectors(prepared/"arithmetic_golden","P02B_EXPECT_STATE")
    for t in range(6):
        assert unpack_compartment_state(states[t,0]).voltage==MODEL.MAX24
        assert unpack_compartment_state(states[t,1]).voltage==MODEL.MIN24
        assert unpack_compartment_state(states[t,2]).current<0
    assert any(unpack_compartment_state(states[t,3]).refractory_remaining>0
               for t in range(6))
    for cid,p in MODEL.PARAMETERS.items():
        initial=(prepared/"arithmetic_golden"/f"core{cid}_initial.bin").read_bytes()
        cfg=unpack_compartment_config(int.from_bytes(initial[0x1000:0x1010],"little"))
        syn=unpack_synapse_word(int.from_bytes(initial[0xF000:0xF008],"little"))
        for key in ("current_decay","voltage_decay","bias","threshold","refractory_ticks"):
            assert cfg[key]==p[key]
        assert syn["weight"]==p["weight"]

def test_signed_boundary_synthetic_whole_DDR_oracle_pass(synthetic,capsys):
    assert CHECK.verify(synthetic/"p05_a53_result.bin",synthetic)
    captured=capsys.readouterr().out
    assert "five complete 512KiB" in captured
    assert "P05_2F_VERIFY_EXIT=0" in captured
    # Every physical-bank byte must be compared, not just membrane state.
    for c in MODEL.CORES:
        actual=(synthetic/"final_ddr"/f"core{c}_after.bin").read_bytes()
        expected=(synthetic/"arithmetic_golden"/f"core{c}_expected.bin").read_bytes()
        assert actual==expected and len(actual)==0x80000

@pytest.mark.parametrize("core,offset",[
    (0,0x5000),  # saturated positive state
    (1,0x5001),  # saturated negative state
    (2,0x0F002),# negative synapse / static context
    (3,0x5C000),# trace state
    (4,0x54000),# event bank
    (4,0x64000),# packet RAM
])
def test_any_corrupted_full_DDR_bank_fails(synthetic,capsys,core,offset):
    target=synthetic/"final_ddr"/f"core{core}_after.bin"
    data=bytearray(target.read_bytes())
    data[offset]^=1
    target.write_bytes(data)
    assert not CHECK.verify(synthetic/"p05_a53_result.bin",synthetic)
    assert "full golden DDR" in capsys.readouterr().err

@pytest.mark.parametrize("field,value",[
    (2,0xDEAD000A), # terminal success cannot be forged
    (11,29),        # dispatch count
    (12,0),         # packet count
    (13,5),         # barrier count
    (16,0),         # dirty writeback
    (35,29),        # actual hardware dispatch count
    (36,0),         # page counters
    (44,29),        # checkpoint count
    (50,0),         # header CRC
    (54,0),         # diagnostic mode
    (60,1),         # reserved fields
])
def test_mailbox_mutation_fails_even_if_whole_DDR_is_golden(synthetic,capsys,field,value):
    path=synthetic/"p05_a53_result.bin"
    mb=list(struct.unpack("<64I",path.read_bytes()))
    assert mb[field]!=value
    mb[field]=value
    path.write_bytes(struct.pack("<64I",*mb))
    assert not CHECK.verify(path,synthetic)
    assert "FAIL: P05.2f" in capsys.readouterr().err

def test_corrupt_independent_P05G_descriptor_rejected(synthetic,capsys):
    path=synthetic/"p05_artifacts/p05_payload.bin"
    data=bytearray(path.read_bytes());data[1]^=1
    path.write_bytes(data)
    assert not CHECK.verify(synthetic/"p05_a53_result.bin",synthetic)
    assert "FAIL" in capsys.readouterr().err

def test_scripts_are_guarded_and_reuse_frozen_C_and_FPGA():
    text=RUN.read_text()
    assert "P05_2F_CONFIRM_KV260_DDR_OVERWRITE" in text
    assert "P03_DIAG_REPORTS" in text
    assert "P03_2C_EXPECTED_XSA_SHA" in text
    assert "p05_regression_run.elf" in text
    assert "p05_2f_arithmetic_verify.py" in text
    assert "p05_2f_arithmetic_prepare.tcl" in text
    assert "sha256sum" in text and "preflight_identity.txt" in text
    assert "set -euo pipefail" in text
    assert subprocess.run(["bash","-n",str(RUN)],capture_output=True).returncode==0
