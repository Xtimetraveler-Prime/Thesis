"""P05.2 FIRST directed hardware-fault localization HOST rehearsal.

All mailbox instances here are SYNTHETIC; P05.2 physical acceptance
requires the actual KV260 to produce the expected early ERROR and
the independent strict verifier to pass on that REAL mailbox.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[1]
FIX=ROOT/"scripts/p05_2_fault_fixture.py"
VERIFY=ROOT/"scripts/p05_2_fault_verify.py"
RUN=ROOT/"scripts/run_p05_2_fault.sh"
TRI_VER=ROOT/"scripts/p05_1_triangle_verify.py"


def module_at(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    assert s and s.loader
    o=importlib.util.module_from_spec(s)
    s.loader.exec_module(o)
    return o


verifier=module_at("p05_2_negative_host_verifier",VERIFY)
positive=module_at("p05_1_triangle_positive_verifier",TRI_VER)


@pytest.fixture(scope="module")
def seed(tmp_path_factory):
    target=tmp_path_factory.mktemp("p05_2_diagnostic")/"seed"
    p=subprocess.run(["bash",str(RUN),"prepare",str(target)],
                     cwd=ROOT,capture_output=True,text=True,timeout=120)
    assert p.returncode==0,p.stdout+p.stderr
    assert "KV260 untouched" in p.stdout
    gate=json.loads((target/"p05_2_fault_gate.json").read_text())
    assert gate["expected_terminal"]=="0xDEAD000A"
    assert (gate["target_step"],gate["target_core"],
            gate["target_checkpoint_index"])==(2,1,7)
    assert gate["expected_dispatches_before_stop"]==9
    assert gate["expected_packets_before_stop"]==6
    assert gate["expected_resident_deliveries_before_stop"]==6
    return target


@pytest.fixture
def negative(tmp_path,seed):
    root=tmp_path/"evidence"
    shutil.copytree(seed,root)
    return root


def expected_error_mailbox(root):
    h=struct.unpack("<64I",(root/"p05_artifacts/p05_header.bin").read_bytes())
    gate=json.loads((root/"p05_2_fault_gate.json").read_text())
    w=[0]*64
    w[:20]=[
        0x52353050,1,0xDEAD000A,10,
        5,2,3,3,19,11,13,
        9,6,2,3,0,0,0,0,9,
    ]
    w[20]=9
    w[22]=100
    # ps_inference_ticks remains zero until successful finalization
    w[26]=50
    w[28]=50
    w[30]=200
    w[42:45]=[6,9,7]
    w[45:50]=[
        2,1,1,int(gate["expected_bad_crc32"],0),
        int(gate["expected_observed_crc32"],0)
    ]
    w[50:52]=[h[23],h[22]]
    w[54:58]=[1,15,15,15]
    w[58]=1
    return struct.pack("<64I",*w)


def run(root,capsys):
    success=verifier.verify(root/"p05_a53_result.bin",root)
    output=capsys.readouterr()
    return success,output.out+output.err


def test_fault_fixture_only_mutates_expected_checksum(negative):
    baseline=json.loads((negative/"triangle_spec.json").read_text())
    injected=json.loads((negative/"p05_2_fault_spec.json").read_text())
    assert baseline["events"]==injected["events"]
    assert baseline["cores"]==injected["cores"]
    assert len(baseline["checkpoints"])==15
    assert [i for i,(a,b) in enumerate(zip(
        baseline["checkpoints"],injected["checkpoints"]
    )) if a!=b]==[7]
    old=int(baseline["checkpoints"][7]["expected_crc32"],0)
    new=int(injected["checkpoints"][7]["expected_crc32"],0)
    assert new==old^1
    for cid in range(3):
        assert (negative/"p05_artifacts"/f"core{cid}_initial.bin").read_bytes()==(
            negative/"triangle_golden"/f"core{cid}_initial.bin").read_bytes()


def test_synthetic_planned_a53_failure_is_accepted_as_negative(negative,capsys):
    (negative/"p05_a53_result.bin").write_bytes(
        expected_error_mailbox(negative)
    )
    success,logs=run(negative,capsys)
    assert success,logs
    assert "first_mismatch_timestep=2 core=1 class=state0" in logs
    assert "checkpoints_passed=7" in logs
    assert "NO final-DDR equality" in logs
    assert "P05_2_NEGATIVE_VERIFY_EXIT=0" in logs


@pytest.mark.parametrize("index,wrong,fragment",[
    (2,0x600D600D,"result"),
    (3,8,"error"),
    (5,5,"completed_steps"),
    (8,18,"phase"),
    (9,12,"fault"),
    (10,17,"fault_phase"),
    (11,15,"dispatches"),
    (12,7,"packets"),
    (13,3,"barriers"),
    (16,1,"runtime_outs"),
    (17,3,"final_outs"),
    (19,8,"hits"),
    (35,9,"hw_dispatches"),
    (42,5,"resident_deliveries"),
    (43,8,"inputs_consumed"),
    (44,8,"checkpoints_passed"),
    (45,1,"failed_step"),
    (46,0,"failed_core"),
    (47,2,"failed_class"),
    (48,0,"expected_crc"),
    (49,0,"observed_crc"),
    (50,0,"header_crc"),
    (51,0,"payload_crc"),
    (58,0,"diag_flags"),
    (60,1,"reserved"),
])
def test_unrelated_failure_or_bad_diagnostic_is_not_accepted(
    negative,capsys,index,wrong,fragment
):
    w=list(struct.unpack("<64I",expected_error_mailbox(negative)))
    assert w[index]!=wrong
    w[index]=wrong
    (negative/"p05_a53_result.bin").write_bytes(struct.pack("<64I",*w))
    success,logs=run(negative,capsys)
    assert not success
    assert fragment in logs
    assert "FAIL: P05.2 first-mismatch mailbox" in logs


def test_manifest_corruption_fail_closed(negative,capsys):
    (negative/"p05_a53_result.bin").write_bytes(
        expected_error_mailbox(negative)
    )
    file=negative/"p05_artifacts/p05_payload.bin"
    raw=bytearray(file.read_bytes())
    raw[8]^=1
    file.write_bytes(raw)
    success,logs=run(negative,capsys)
    assert not success
    assert "negative evidence admission" in logs


def test_correct_positive_triangle_pass_cannot_satisfy_negative(negative,capsys):
    # The test must REJECT a genuine A53 PASS because that would prove
    # the wrong checkpoint was not actually compared.
    w=list(struct.unpack("<64I",expected_error_mailbox(negative)))
    w[2],w[3],w[5],w[8],w[9],w[10]=0x600D600D,0,5,18,0,0
    (negative/"p05_a53_result.bin").write_bytes(struct.pack("<64I",*w))
    success,logs=run(negative,capsys)
    assert not success
    assert "result" in logs


def test_hardware_script_never_claims_final_ddr_equality_or_rewrites_elf():
    p=subprocess.run(["bash","-n",str(RUN)],
                     capture_output=True,text=True,timeout=30)
    assert p.returncode==0,p.stderr
    c=RUN.read_text()
    assert "P05_2_CONFIRM_KV260_DDR_OVERWRITE=YES" in c
    assert "p05_2_fault_fixture.py" in c
    assert "p05_2_fault_verify.py" in c
    assert "p05_1_triangle_prepare.tcl" in c
    assert "p03_finish_xsdb_run.tcl" in c
    assert "p05_regression_run.elf" in c
    assert "P05_CONFIGURABLE_A53_REGRESSION_V1" in c
    assert "p03_2c_program_bitstream.tcl" in c
    assert "p05_1_triangle_dump.tcl" not in c
    assert "p03_finish_xsdb_dump.tcl" not in c
    assert "final-DDR golden" in c


def test_p03_live_source_unchanged_during_diagnostics():
    c=(ROOT/"software/p05/p05_regression_run.c").read_text()
    assert "diag_flags=1u" in c
    assert "report_failure(diag_flags?E_CHECKPOINT:E_RUNTIME)" in c
    assert "P05_RESULT_FAIL | first_error" in c
    assert "failed_step=step;failed_core=id;failed_class=cls" in c
    assert "expected_crc=expected;observed_crc=measured" in c
