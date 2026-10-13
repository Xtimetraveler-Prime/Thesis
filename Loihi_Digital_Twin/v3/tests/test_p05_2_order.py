"""P05.2c host-only 2,0,1 service-order neural-model and verifier.

A synthetic mailbox is never a board PASS. Only the actual KV260
A53 terminal plus independently captured 3×512KiB DDR can accept it.
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
RUN=ROOT/"scripts/run_p05_2_order.sh"
CHECK=ROOT/"scripts/p05_2_order_verify.py"


def load():
    s=importlib.util.spec_from_file_location("p05_2c_order_verify_test",CHECK)
    assert s and s.loader
    module=importlib.util.module_from_spec(s)
    s.loader.exec_module(module)
    return module


VERIFY=load()


@pytest.fixture(scope="module")
def seed(tmp_path_factory):
    p=tmp_path_factory.mktemp("p05_reordered")/"golden"
    proc=subprocess.run(
        ["bash",str(RUN),"prepare",str(p)],
        cwd=ROOT,capture_output=True,text=True,timeout=150,
    )
    assert proc.returncode==0,proc.stdout+proc.stderr
    assert "KV260 was NOT touched" in proc.stdout
    gate=json.loads((p/"p05_2_order_gate.json").read_text())
    manifest=json.loads((p/"p05_artifacts/p05_manifest.json").read_text())
    assert gate["original_order"]==[0,1,2]
    assert gate["permuted_service_order"]==[2,0,1]
    assert gate["expected_dispatches"]==15
    assert gate["expected_packets"]==12
    assert gate["expected_resident_deliveries"]==12
    assert gate["expected_checkpoints"]==15
    assert manifest["logical_core_ids_in_service_order"]==[2,0,1]
    return p


@pytest.fixture
def staged(tmp_path,seed):
    p=tmp_path/"evidence"
    shutil.copytree(seed,p)
    dump=p/"final_ddr"
    dump.mkdir()
    for core in range(3):
        shutil.copy2(
            p/"reordered_golden"/f"core{core}_expected.bin",
            dump/f"core{core}_after.bin"
        )
    return p


def good_mailbox(root:Path)->bytes:
    w=[0]*64
    w[:20]=[
        0x52353050,1,0x600D600D,0,5,5,3,3,18,0,0,
        15,12,5,3,0,0,3,0,15,
    ]
    w[20]=10
    w[22]=250
    w[24]=300
    w[32:42]=[
        99999001,0x4C543302,0x1031F,15,6,
        106496,0,0,100,100,
    ]
    w[42:45]=[12,15,15]
    head=struct.unpack("<64I",(root/"p05_artifacts/p05_header.bin").read_bytes())
    w[50],w[51]=head[23],head[22]
    w[54:58]=[1,15,15,15]
    return struct.pack("<64I",*w)


def execute(root,capsys):
    ok=VERIFY.verify(root/"p05_a53_result.bin",root)
    log=capsys.readouterr()
    return ok,log.out+log.err


def test_ordered_network_unchanged_exact_model_states_and_ddr(staged):
    base=staged/"triangle_golden"
    alter=staged/"reordered_golden"
    gate=json.loads((staged/"p05_2_order_gate.json").read_text())
    # A service-order permutation is real even if a normalized
    # model trace fingerprint happens to be schedule-invariant.
    assert gate["permuted_service_order"]==[2,0,1]
    assert gate["original_order"]==[0,1,2]
    assert len(gate["baseline_model_trace_sha256"])==64
    assert len(gate["permuted_model_trace_sha256"])==64
    for core in range(3):
        for tag in ("initial","expected"):
            assert (base/f"core{core}_{tag}.bin").read_bytes()==(
                alter/f"core{core}_{tag}.bin").read_bytes()
        expect=hashlib.sha256((alter/f"core{core}_expected.bin").read_bytes()).hexdigest()
        assert expect==gate["accepted_original_service_order_physical_sha256"][str(core)]
    spec=json.loads((staged/"p05_2_order_spec.json").read_text())
    assert [r["id"] for r in spec["cores"]]==[2,0,1]
    assert [r["core"] for r in spec["events"][:3]]==[2,0,1]
    assert [r["core"] for r in spec["checkpoints"][:3]]==[2,0,1]
    assert set((e["timestep"],e["core"]) for e in spec["events"])=={
        (t,c) for t in range(5) for c in range(3)
    }


def test_host_synthetic_permuted_hardware_mailbox(staged,capsys):
    (staged/"p05_a53_result.bin").write_bytes(good_mailbox(staged))
    ok,output=execute(staged,capsys)
    assert ok,output
    assert "order=2,0,1" in output
    assert "checkpoints=15" in output
    assert "BOTH independently reordered and baseline Python models" in output


@pytest.mark.parametrize("word,bad,label",[
    (2,0xDEAD000A,"result"),
    (11,14,"dispatches"),
    (12,11,"packets"),
    (13,4,"barriers"),
    (17,2,"final_outs"),
    (19,14,"hits"),
    (35,14,"hw_dispatches"),
    (42,11,"resident_deliveries"),
    (43,14,"inputs_consumed"),
    (44,14,"checkpoints_passed"),
    (50,0,"header_crc"),
    (51,0,"payload_crc"),
    (54,0,"diagnostic_mode"),
    (58,1,"diag_flags"),
    (60,1,"reserved"),
])
def test_any_wrong_physical_counts_rejected(staged,capsys,word,bad,label):
    w=list(struct.unpack("<64I",good_mailbox(staged)))
    assert w[word]!=bad
    w[word]=bad
    (staged/"p05_a53_result.bin").write_bytes(struct.pack("<64I",*w))
    ok,output=execute(staged,capsys)
    assert not ok
    assert label in output


def test_corrupt_live_final_ddr_breaks_permuted_model(staged,capsys):
    (staged/"p05_a53_result.bin").write_bytes(good_mailbox(staged))
    file=staged/"final_ddr/core1_after.bin"
    raw=bytearray(file.read_bytes())
    raw[0x5000]^=1
    file.write_bytes(raw)
    ok,output=execute(staged,capsys)
    assert not ok
    assert "P05_2_ORDER_FINAL_DDR=FAIL" in output


def test_tampered_order_manifest_rejected(staged,capsys):
    (staged/"p05_a53_result.bin").write_bytes(good_mailbox(staged))
    gate_file=staged/"p05_2_order_gate.json"
    gate=json.loads(gate_file.read_text())
    gate["permuted_service_order"]=[0,1,2]
    gate_file.write_text(json.dumps(gate))
    ok,output=execute(staged,capsys)
    assert not ok
    assert "unexpected source service permutation" in output


def test_recomputed_crc_shas_cannot_forge_wrong_ordered_ingress(staged,capsys):
    (staged/"p05_a53_result.bin").write_bytes(good_mailbox(staged))
    art=staged/"p05_artifacts"
    words=list(struct.unpack("<64I",(art/"p05_header.bin").read_bytes()))
    payload=bytearray((art/"p05_payload.bin").read_bytes())
    # First ordered t0 destination is core 2. Change it to core 1,
    # then repair all CRCs/SHAs to verify independent order checker.
    assert struct.unpack_from("<I",payload,words[17]+4)[0]==2
    struct.pack_into("<I",payload,words[17]+4,1)
    words[22]=zlib.crc32(payload)
    words[23]=0
    words[23]=zlib.crc32(struct.pack("<64I",*words))
    header=struct.pack("<64I",*words)
    (art/"p05_header.bin").write_bytes(header)
    (art/"p05_payload.bin").write_bytes(payload)
    manifest=json.loads((art/"p05_manifest.json").read_text())
    manifest["header_sha256"]=hashlib.sha256(header).hexdigest()
    manifest["payload_sha256"]=hashlib.sha256(payload).hexdigest()
    (art/"p05_manifest.json").write_text(json.dumps(manifest))
    gate_file=staged/"p05_2_order_gate.json"
    gate=json.loads(gate_file.read_text())
    gate["p05_header_sha256"]=manifest["header_sha256"]
    gate["p05_payload_sha256"]=manifest["payload_sha256"]
    gate_file.write_text(json.dumps(gate))
    ok,output=execute(staged,capsys)
    assert not ok
    assert "permuted ingress event 0 invalid" in output


def test_order_physical_shell_safety_and_same_elf():
    proc=subprocess.run(["bash","-n",str(RUN)],
                        capture_output=True,text=True,timeout=30)
    assert proc.returncode==0,proc.stderr
    shell=RUN.read_text()
    assert "P05_2_CONFIRM_KV260_DDR_OVERWRITE=YES" in shell
    assert "p05_2_order_fixture.py" in shell
    assert "p05_2_order_verify.py" in shell
    assert "p05_1_triangle_prepare.tcl" in shell
    assert "p05_1_triangle_dump.tcl" in shell
    assert "p03_finish_xsdb_run.tcl" in shell
    assert "p03_2c_program_bitstream.tcl" in shell
    assert "p05_regression_run.elf" in shell
    assert "P05_CONFIGURABLE_A53_REGRESSION_V1" in shell
    assert "cmp -s" in shell
    assert "reordered_golden/manifest.json" in shell
