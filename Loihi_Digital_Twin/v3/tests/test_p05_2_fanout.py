"""P05.2d fanout/next-event aggregation HOST regressions.

Synthesized mailbox does not establish KV260 operation. Physical
acceptance requires 24 actual packet commits + 15 device-observed
state checkpoints + all three complete final DDR model records.
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
RUN=ROOT/"scripts/run_p05_2_fanout.sh"
CHECK=ROOT/"scripts/p05_2_fanout_verify.py"


def module_at(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    o=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(o)
    return o


VERIFY=module_at("p05_2d_fanout_test_check",CHECK)


@pytest.fixture(scope="module")
def seed(tmp_path_factory):
    dest=tmp_path_factory.mktemp("p05_fanout")/"prepared"
    proc=subprocess.run(
        ["bash",str(RUN),"prepare",str(dest)],
        cwd=ROOT,capture_output=True,text=True,timeout=150,
    )
    assert proc.returncode==0,proc.stdout+proc.stderr
    assert "KV260 was NOT touched" in proc.stdout
    gate=json.loads((dest/"p05_2_fanout_gate.json").read_text())
    manifest=json.loads((dest/"p05_artifacts/p05_manifest.json").read_text())
    assert gate["topology"]=={"0":[1,2],"1":[0,2],"2":[0,1]}
    assert gate["per_core_routes"]==2
    assert gate["expected_packets"]==24
    assert gate["expected_direct_resident_deliveries"]==24
    assert gate["expected_checkpoints"]==15
    assert gate["expected_max_current_input_events_per_core"]==3
    assert gate["expected_max_packets_from_one_dispatch"]==2
    assert manifest["events"]==15 and manifest["checkpoints"]==15
    return dest


@pytest.fixture
def prepared(tmp_path,seed):
    p=tmp_path/"fanout"
    shutil.copytree(seed,p)
    out=p/"final_ddr"
    out.mkdir()
    for core in range(3):
        shutil.copy2(p/"fanout_golden"/f"core{core}_expected.bin",
                     out/f"core{core}_after.bin")
    return p


def mailbox(p):
    words=[0]*64
    words[:20]=[
        0x52353050,1,0x600D600D,0,
        5,5,3,3,18,0,0,15,24,5,
        3,0,0,3,0,15,
    ]
    words[20]=100
    words[22]=200
    words[24]=500
    words[32:42]=[
        99999001,0x4C543302,0x0001031F,15,6,
        106496,0,0,200,100,
    ]
    words[42:45]=[24,15,15]
    h=struct.unpack("<64I",(p/"p05_artifacts/p05_header.bin").read_bytes())
    words[50:52]=[h[23],h[22]]
    words[54:58]=[1,15,15,15]
    return struct.pack("<64I",*words)


def check(p,capsys):
    ok=VERIFY.verify(p/"p05_a53_result.bin",p)
    results=capsys.readouterr()
    return ok,results.out+results.err


def test_model_generates_two_real_routes_each_core_and_nontrivial_input_multiplicity(prepared):
    gate=json.loads((prepared/"p05_2_fanout_gate.json").read_text())
    model=json.loads((prepared/"fanout_golden/manifest.json").read_text())
    assert gate["expected_packets"]==model["expected_packet_count_total"]==24
    assert model["dispatch_count"]==15
    assert model["final_next_events"]
    source=json.loads((prepared/"p05_2_fanout_spec.json").read_text())
    assert len(source["events"])==len(source["checkpoints"])==15
    assert [(e["timestep"],e["core"]) for e in source["events"]]==[
        (t,c) for t in range(5) for c in range(3)
    ]
    desc=(prepared/"p05_artifacts/p05_payload.bin").read_bytes()
    for c in range(3):
        meta=struct.unpack_from("<Q",desc,c*32+4)[0]
        assert (meta>>34)&0x1FFF==2, f"core {c} must physically encode 2 routes"


def test_synthetic_good_fanout_mailbox_matches_three_full_goldens(prepared,capsys):
    (prepared/"p05_a53_result.bin").write_bytes(mailbox(prepared))
    ok,logs=check(prepared,capsys)
    assert ok,logs
    assert "packets=24 resident_deliveries=24" in logs
    assert "two NEXT deliveries/destination" in logs
    assert "P05_2_FANOUT_METADATA=" in logs


@pytest.mark.parametrize("index,bad,label",[
    (2,0xDEAD0008,"result"),
    (11,14,"dispatches"),
    (12,12,"packets"),
    (13,4,"barriers"),
    (17,2,"final_outs"),
    (35,14,"hw_dispatches"),
    (36,5,"hw_pages"),
    (42,23,"resident_deliveries"),
    (43,14,"inputs_consumed"),
    (44,14,"checkpoints_passed"),
    (50,0,"header_crc"),
    (51,0,"payload_crc"),
    (54,0,"diagnostic_mode"),
    (58,1,"diag_flags"),
    (60,1,"reserved"),
])
def test_wrong_fanout_mailbox_count_is_not_pass(prepared,capsys,index,bad,label):
    values=list(struct.unpack("<64I",mailbox(prepared)))
    assert values[index]!=bad
    values[index]=bad
    (prepared/"p05_a53_result.bin").write_bytes(struct.pack("<64I",*values))
    ok,logs=check(prepared,capsys)
    assert not ok
    assert label in logs


def test_corrupt_full_ddr_fails_even_when_mailbox_says_pass(prepared,capsys):
    (prepared/"p05_a53_result.bin").write_bytes(mailbox(prepared))
    file=prepared/"final_ddr/core2_after.bin"
    raw=bytearray(file.read_bytes())
    raw[0x64000]^=1
    file.write_bytes(raw)
    ok,logs=check(prepared,capsys)
    assert not ok
    assert "P05_2_FANOUT_FINAL_DDR=FAIL" in logs


def test_model_connectivity_forgery_fails(prepared,capsys):
    (prepared/"p05_a53_result.bin").write_bytes(mailbox(prepared))
    gatefile=prepared/"p05_2_fanout_gate.json"
    gate=json.loads(gatefile.read_text())
    gate["topology"]["0"]=[1]
    gatefile.write_text(json.dumps(gate))
    ok,logs=check(prepared,capsys)
    assert not ok
    assert "fanout connectivity drift" in logs


def test_forged_input_event_and_repaired_crc_sha_still_fail(prepared,capsys):
    (prepared/"p05_a53_result.bin").write_bytes(mailbox(prepared))
    art=prepared/"p05_artifacts"
    words=list(struct.unpack("<64I",(art/"p05_header.bin").read_bytes()))
    blob=bytearray((art/"p05_payload.bin").read_bytes())
    struct.pack_into("<I",blob,words[17]+8,11)
    words[22]=zlib.crc32(blob)
    words[23]=0
    words[23]=zlib.crc32(struct.pack("<64I",*words))
    h=struct.pack("<64I",*words)
    (art/"p05_header.bin").write_bytes(h)
    (art/"p05_payload.bin").write_bytes(blob)
    m=json.loads((art/"p05_manifest.json").read_text())
    m["header_sha256"]=hashlib.sha256(h).hexdigest()
    m["payload_sha256"]=hashlib.sha256(blob).hexdigest()
    (art/"p05_manifest.json").write_text(json.dumps(m))
    gatefile=prepared/"p05_2_fanout_gate.json"
    gate=json.loads(gatefile.read_text())
    gate["p05_header_sha256"]=m["header_sha256"]
    gate["p05_payload_sha256"]=m["payload_sha256"]
    gatefile.write_text(json.dumps(gate))
    ok,logs=check(prepared,capsys)
    assert not ok
    assert "fanout event 0 != independent stimulus" in logs


def test_fanout_physical_shell_guarded_and_preserves_p03():
    p=subprocess.run(["bash","-n",str(RUN)],
                     capture_output=True,text=True,timeout=30)
    assert p.returncode==0,p.stderr
    s=RUN.read_text()
    assert "P05_2_CONFIRM_KV260_DDR_OVERWRITE=YES" in s
    assert "p05_2_fanout_fixture.py" in s
    assert "p05_2_fanout_verify.py" in s
    assert "p05_2_fanout_prepare.tcl" in s
    assert "p05_1_triangle_dump.tcl" in s
    assert "p03_finish_xsdb_run.tcl" in s
    assert "p03_2c_program_bitstream.tcl" in s
    assert "P05_CONFIGURABLE_A53_REGRESSION_V1" in s
    assert "p05_regression_run.elf" in s
    assert "cmp -s" in s
