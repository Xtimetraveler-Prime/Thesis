"""P05.2b host-only conformance; synthetic fast-mode mailbox is NOT KV260.

The real acceptance gate requires exactly matching all three full
512KiB physical DDR images, independent model and previously accepted
diagnostic-mode physical SHA256s.
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
RUN=ROOT/"scripts/run_p05_2_fast.sh"
CHECK=ROOT/"scripts/p05_2_fast_verify.py"


def load():
    spec=importlib.util.spec_from_file_location("p05_fast_checker",CHECK)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VERIFIER=load()


@pytest.fixture(scope="module")
def prepared_seed(tmp_path_factory):
    directory=tmp_path_factory.mktemp("p05_fast")/"seed"
    process=subprocess.run(
        ["bash",str(RUN),"prepare",str(directory)],
        cwd=ROOT,capture_output=True,text=True,timeout=120,
    )
    assert process.returncode==0,process.stdout+process.stderr
    assert "KV260 was NOT touched" in process.stdout
    gate=json.loads((directory/"p05_2_fast_gate.json").read_text())
    info=json.loads((directory/"p05_artifacts/p05_manifest.json").read_text())
    assert gate["expected_dispatches"]==15
    assert gate["expected_packets"]==12
    assert gate["expected_resident_deliveries"]==12
    assert gate["expected_checkpoints"]==0
    assert info["diagnostic_mode"] is False
    assert info["events"]==15 and info["checkpoints"]==0
    return directory


@pytest.fixture
def physical_mock(tmp_path,prepared_seed):
    folder=tmp_path/"prepared"
    shutil.copytree(prepared_seed,folder)
    dump=folder/"final_ddr"
    dump.mkdir()
    for core in range(3):
        shutil.copy2(folder/"triangle_golden"/f"core{core}_expected.bin",
                     dump/f"core{core}_after.bin")
    return folder


def plausible_mailbox(root:Path):
    words=[0]*64
    words[:20]=[
        0x52353050,1,0x600D600D,0,5,5,3,3,18,0,0,
        15,12,5,3,0,0,3,0,15,
    ]
    words[20]=12
    words[22]=200
    words[24]=300
    words[32:42]=[
        99999001,0x4C543302,0x1031F,15,6,106496,0,0,100,100,
    ]
    words[42:45]=[12,15,0]
    head=struct.unpack("<64I",(root/"p05_artifacts/p05_header.bin").read_bytes())
    words[50],words[51]=head[23],head[22]
    words[54:58]=[0,15,0,15]
    return struct.pack("<64I",*words)


def checked(root:Path,capsys):
    passed=VERIFIER.verify(root/"p05_a53_result.bin",root)
    log=capsys.readouterr()
    return passed,log.out+log.err


def test_fast_deployment_does_not_change_any_neural_bytes(physical_mock):
    root=physical_mock
    fast=json.loads((root/"p05_2_fast_spec.json").read_text())
    diagnostic=json.loads((root/"triangle_spec.json").read_text())
    assert fast["mode"]=="fast"
    assert fast["checkpoints"]==[]
    assert diagnostic["mode"]=="diagnostic"
    assert len(diagnostic["checkpoints"])==15
    assert {k:v for k,v in fast.items() if k not in ("mode","checkpoints")}=={
        k:v for k,v in diagnostic.items() if k not in ("mode","checkpoints")
    }
    diag_header=struct.unpack("<64I",(
        root/"p05_diag_reference_header.bin").read_bytes())
    fast_header=struct.unpack("<64I",(
        root/"p05_artifacts/p05_header.bin").read_bytes())
    assert diag_header[3:7]==(1,5,3,3)
    assert fast_header[3:7]==(0,5,3,3)
    assert diag_header[14]==15
    assert fast_header[14]==0
    diag_payload=(root/"p05_diag_reference_payload.bin").read_bytes()
    fast_payload=(root/"p05_artifacts/p05_payload.bin").read_bytes()
    assert fast_payload==diag_payload[:diag_header[18]]
    for core in range(3):
        assert (root/"triangle_golden"/f"core{core}_initial.bin").read_bytes()==(
            root/"p05_artifacts"/f"core{core}_initial.bin").read_bytes()


def test_host_synthetic_fast_mode_mailbox_and_golden(physical_mock,capsys):
    (physical_mock/"p05_a53_result.bin").write_bytes(
        plausible_mailbox(physical_mock)
    )
    passed,log=checked(physical_mock,capsys)
    assert passed,log
    assert "events=15 checkpoints=0" in log
    assert "BOTH independent Python oracle and earlier physical diagnostic-mode" in log
    assert "P05_2_FAST_METADATA=" in log


@pytest.mark.parametrize("word,changed,term",[
    (2,0xDEAD000A,"result"),
    (3,10,"error"),
    (8,19,"phase"),
    (11,14,"dispatches"),
    (12,11,"packets"),
    (13,4,"barriers"),
    (15,1,"replacement_ins"),
    (17,2,"final_outs"),
    (35,14,"hw_dispatches"),
    (36,7,"hw_pages"),
    (42,11,"resident_deliveries"),
    (43,14,"inputs_consumed"),
    (44,15,"checkpoints_passed"),
    (50,0,"header_crc"),
    (51,0,"payload_crc"),
    (54,1,"diagnostic_mode"),
    (56,15,"expected_checks"),
    (58,1,"diag_flags"),
    (60,1,"reserved"),
])
def test_fast_incorrect_mailbox_never_passes(physical_mock,capsys,word,changed,term):
    words=list(struct.unpack("<64I",plausible_mailbox(physical_mock)))
    assert words[word]!=changed
    words[word]=changed
    (physical_mock/"p05_a53_result.bin").write_bytes(struct.pack("<64I",*words))
    passed,log=checked(physical_mock,capsys)
    assert not passed
    assert term in log


def test_fast_corrupted_actual_record_rejected(physical_mock,capsys):
    (physical_mock/"p05_a53_result.bin").write_bytes(
        plausible_mailbox(physical_mock)
    )
    file=physical_mock/"final_ddr/core2_after.bin"
    record=bytearray(file.read_bytes())
    record[0x5000]^=1
    file.write_bytes(record)
    passed,log=checked(physical_mock,capsys)
    assert not passed
    assert "P05_2_FAST_FINAL_DDR_COMPARISON=FAIL" in log


def test_fast_historical_physical_sha_pin_is_required(physical_mock,capsys):
    (physical_mock/"p05_a53_result.bin").write_bytes(
        plausible_mailbox(physical_mock)
    )
    gatefile=physical_mock/"p05_2_fast_gate.json"
    gate=json.loads(gatefile.read_text())
    gate["accepted_prior_physical_final_ddr_sha256"]["2"]="0"*64
    gatefile.write_text(json.dumps(gate))
    passed,log=checked(physical_mock,capsys)
    assert not passed
    assert "differs from accepted diagnostic physical P05.1" in log


def test_fast_forged_crc_sha_still_cannot_change_neural_events(physical_mock,capsys):
    (physical_mock/"p05_a53_result.bin").write_bytes(
        plausible_mailbox(physical_mock)
    )
    # Proof: real independent neural source comparator detects altered
    # input event bytes even when someone recomputes matching payload
    # and header CRC plus matching gate + manifest sha.
    import hashlib,zlib
    art=physical_mock/"p05_artifacts"
    header=list(struct.unpack("<64I",(art/"p05_header.bin").read_bytes()))
    payload=bytearray((art/"p05_payload.bin").read_bytes())
    struct.pack_into("<I",payload,header[17]+8,11)
    header[22]=zlib.crc32(payload)
    header[23]=0
    header[23]=zlib.crc32(struct.pack("<64I",*header))
    raw=struct.pack("<64I",*header)
    (art/"p05_header.bin").write_bytes(raw)
    (art/"p05_payload.bin").write_bytes(payload)
    info=json.loads((art/"p05_manifest.json").read_text())
    info["header_sha256"]=hashlib.sha256(raw).hexdigest()
    info["payload_sha256"]=hashlib.sha256(payload).hexdigest()
    (art/"p05_manifest.json").write_text(json.dumps(info))
    gatefile=physical_mock/"p05_2_fast_gate.json"
    gate=json.loads(gatefile.read_text())
    gate["fast_header_sha256"]=info["header_sha256"]
    gate["fast_payload_sha256"]=info["payload_sha256"]
    gatefile.write_text(json.dumps(gate))
    passed,log=checked(physical_mock,capsys)
    assert not passed
    assert "fast mode differs in exact core/event payload bytes" in log


def test_fast_physical_shell_is_guarded_and_does_not_rebuild_vitis():
    p=subprocess.run(["bash","-n",str(RUN)],
                     capture_output=True,text=True,timeout=30)
    assert p.returncode==0,p.stderr
    code=RUN.read_text()
    assert "P05_2_CONFIRM_KV260_DDR_OVERWRITE=YES" in code
    assert "p05_2_fast_fixture.py" in code
    assert "p05_2_fast_verify.py" in code
    assert "p05_1_triangle_prepare.tcl" in code
    assert "p05_1_triangle_dump.tcl" in code
    assert "p03_finish_xsdb_run.tcl" in code
    assert "p03_2c_program_bitstream.tcl" in code
    assert "P05_CONFIGURABLE_A53_REGRESSION_V1" in code
    assert "p05_regression_run.elf" in code
    assert "cmp -s" in code
    assert "python scripts/p05_1_triangle_fixture.py" not in code
    assert "scripts/build_p05_regression.sh" not in code
