"""P05.2i host-only exact page AXI counter model and verifier tamper gates.

The mailbox/PL MMIO images built here are explicitly SYNTHETIC;
only an independent KV260 physical run may approve Phase 5 closure.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p05_2i_axi_closeout as CLOSE
import p05_2h_barrier_fixture as MODEL
RUN=ROOT/"scripts/run_p05_2i_axi_closeout.sh"

@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    path=tmp_path_factory.mktemp("p05_2i")/"offline"
    proc=subprocess.run(
        ["bash",str(RUN),"prepare",str(path)],
        cwd=ROOT,capture_output=True,text=True,timeout=240,
    )
    assert proc.returncode==0,proc.stdout+proc.stderr
    assert "KV260 NOT TOUCHED" in proc.stdout
    d=json.loads((path/CLOSE.OUTFILE).read_text())
    assert d["status"]=="MODEL_ONLY_NOT_PHYSICAL_ACCEPTANCE"
    assert (d["steps"],d["dispatches"],d["barriers"],d["checkpoints"])==(
        16,80,16,318)
    assert (d["routed_packets"],d["resident_deliveries"],
            d["nonresident_deliveries"],d["evictions"])==(156,78,78,77)
    assert d["full_page_in_commands"]==d["mutable_page_out_commands"]==80
    assert d["expect_axi_read_bursts"]==136960
    assert d["expect_axi_write_bursts"]==33280
    assert d["expect_axi_successful_bytes"]==43581440
    return path

def fake_p05r(p):
    gate=json.loads((p/"p05_2h_barrier_gate.json").read_text())
    s=gate["scheduler_model"]
    h=struct.unpack("<64I",(p/"p05_artifacts/p05_header.bin").read_bytes())
    w=[0]*64
    w[:20]=[
        0x52353050,1,0x600D600D,0,16,16,5,3,18,0,0,
        80,156,16,3,s["replacement_ins"],s["runtime_outs"],
        s["final_outs"],s["evictions"],s["hits"],
    ]
    for i,value in (
        (20,700),(22,1250),(24,8000),(26,300),
        (28,120),(30,250),(32,99999001),
        (33,0x4C543302),(34,0x0001031F),(35,80),
        (36,s["page_commands"]),(37,0x1A000),
        (38,0),(39,0),(40,136960),(41,33280),
        (42,s["resident_deliveries"]),(43,80),
        (44,318),(50,h[23]),(51,h[22]),
        (54,1),(55,80),(56,318),(57,80),
    ):
        w[i]=value
    return struct.pack("<64I",*w)

@pytest.fixture
def synthetic(tmp_path,prepared):
    d=tmp_path/"device-fake"
    shutil.copytree(prepared,d)
    (d/"final_ddr").mkdir()
    for cid in MODEL.CORES:
        shutil.copy2(
            d/"barrier_physical_golden"/f"core{cid}_expected.bin",
            d/"final_ddr"/f"core{cid}_after.bin"
        )
    (d/"p05_a53_result.bin").write_bytes(fake_p05r(d))
    expected=json.loads((d/CLOSE.OUTFILE).read_text())
    raw=struct.pack("<4I",
        expected["expect_axi_read_bursts"],
        expected["expect_axi_write_bursts"],
        expected["expect_axi_successful_bytes"] & 0xffffffff,
        expected["expect_axi_successful_bytes"] >> 32,
    )
    (d/CLOSE.WITNESS).write_bytes(raw)
    return d

def test_native_fixture_has_real_AXI_protocol_geometry_and_correct_accounting(prepared):
    d=json.loads((prepared/CLOSE.OUTFILE).read_text())
    assert d==CLOSE.calculation(prepared)
    assert d["axi_burst_bytes"]==16*16==256
    assert d["full_page_in_bytes_each"]==0x6b000
    assert d["mutable_page_out_bytes_each"]==0x1a000
    assert d["expect_axi_read_bytes"]==80*0x6b000
    assert d["expect_axi_write_bytes"]==80*0x1a000
    assert d["expect_axi_successful_bytes"]==(
        d["expect_axi_read_bytes"]+d["expect_axi_write_bytes"]
    )
    assert d["expect_axi_read_bursts"]+d["expect_axi_write_bursts"]==170240
    assert d["hardware_source"]["axi_page_payload_only"] is True
    assert d["status"]=="MODEL_ONLY_NOT_PHYSICAL_ACCEPTANCE"

def test_synthetic_verifier_success_still_not_physical_acceptance(synthetic,capsys):
    assert CLOSE.verify(synthetic)
    out=capsys.readouterr().out
    assert "P05_2I_VERIFY_EXIT=0" in out
    assert "direct read-only hardware bytes" in out
    assert "scope" in out
    assert not (synthetic/"P05_2I_PHYSICAL_ACCEPTANCE.txt").exists()

@pytest.mark.parametrize("index,value",[
    (0,136959), (0,136961), (1,33279), (1,33281),
    (2,43581439), (2,43581441), (3,1),
])
def test_incorrect_direct_mmio_read_counter_or_bytes_never_passes(
        synthetic,capsys,index,value):
    path=synthetic/CLOSE.WITNESS
    w=list(struct.unpack("<4I",path.read_bytes()))
    assert w[index]!=value
    w[index]=value
    path.write_bytes(struct.pack("<4I",*w))
    assert not CLOSE.verify(synthetic)
    assert "FAIL: P05.2i physical" in capsys.readouterr().err

@pytest.mark.parametrize("index,value",[
    (2,0xDEAD000A),(11,79),(12,155),(13,15),(35,79),
    (36,159),(37,0),(38,1),(39,1),(40,136959),(41,33279),
    (42,77),(44,317),(54,0),(60,1),
])
def test_invalid_hardware_A53_mailbox_is_never_accepted(
        synthetic,capsys,index,value):
    target=synthetic/"p05_a53_result.bin"
    w=list(struct.unpack("<64I",target.read_bytes()))
    assert w[index]!=value
    w[index]=value
    target.write_bytes(struct.pack("<64I",*w))
    assert not CLOSE.verify(synthetic)
    assert "FAIL: P05.2i" in capsys.readouterr().err

@pytest.mark.parametrize("cid,offset",[
    (0,0x5000),(1,0x54000),(2,0x58000),
    (3,0x64000),(4,0x1000),(0,0x7ffff),
])
def test_any_mutated_five_core_physical_DDR_fails(synthetic,capsys,cid,offset):
    path=synthetic/"final_ddr"/f"core{cid}_after.bin"
    raw=bytearray(path.read_bytes());raw[offset]^=1
    path.write_bytes(raw)
    assert not CLOSE.verify(synthetic)
    assert "FAIL: P05.2i" in capsys.readouterr().err

def test_missing_direct_read_only_byte_counter_is_never_faked(synthetic,capsys):
    (synthetic/CLOSE.WITNESS).unlink()
    assert not CLOSE.verify(synthetic)
    assert "FAIL: P05.2i" in capsys.readouterr().err

def test_unattested_counter_ledger_or_golden_is_rejected(synthetic,capsys):
    path=synthetic/CLOSE.OUTFILE
    obj=json.loads(path.read_text())
    obj["expect_axi_read_bursts"]+=1
    path.write_text(json.dumps(obj)+"\n")
    assert not CLOSE.verify(synthetic)
    assert "FAIL: P05.2i" in capsys.readouterr().err

def test_no_new_HLS_RTL_A53_source_or_acceptance_from_host():
    shell=RUN.read_text()
    for required in (
        "P05_2I_CONFIRM_KV260_DDR_OVERWRITE",
        "run_p05_2h_barrier.sh",
        "p05_2i_read_axi_counters.tcl",
        "p05_2i_axi_closeout.py",
        "P05_2H_CONFIRM_KV260_DDR_OVERWRITE",
        "p05_2i_preflight_identity.txt",
        "py_compile",
        "0x40000000..0x43FFFFFF",
        "set -euo pipefail",
    ):
        assert required in shell
    tcl=(ROOT/"vivado/p05_2i_read_axi_counters.tcl").read_text()
    for address in ("0xA4000044","0xA4000048","0xA400004C","0xA4000050"):
        assert address in tcl
    assert "mrd -bin -file" in tcl
    # Inspect Tcl COMMANDS rather than text substrings: "burst" itself
    # contains "rst", and comments may mention forbidden operations.
    import re
    assert not re.search(r"(?m)^\s*(?:mwr|dow|rst|reset)\b",tcl)
    assert subprocess.run(["bash","-n",str(RUN)],capture_output=True).returncode==0
