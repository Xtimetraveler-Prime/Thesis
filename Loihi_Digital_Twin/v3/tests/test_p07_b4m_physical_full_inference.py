"""P07-B.4m dedicated real full-inference XSDB sequence: native mock only.

NEVER contact a real KV260; the receipt/ELF fixtures are synthetic.
"""
from __future__ import annotations
from pathlib import Path
import json
import shutil
import struct
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b4m_physical_full_inference as run


def args(tmp_path):
    return SimpleNamespace(
        frozen_dir=tmp_path/"frozen",
        staged_dir=tmp_path/"staged",
        bindings_dir=tmp_path/"bindings",
        routes_dir=tmp_path/"routes",
        offline_report=tmp_path/"p07_b4m_admission_test.json",
        reports=tmp_path/"reports",
        b4i_build=tmp_path/"b4i",
        elf=tmp_path/"p07_b4m_full_26tick.elf",
        evidence=tmp_path/"new_physical_evidence",
        validation_ordinal=0,
        **{name:"YES" for name in (*run.physical.APPROVALS,*run.APPROVALS)},
    )


def fixture_mailbox():
    v=run.full_verify
    w=[0]*64
    w[0],w[1],w[2]=v.MAGIC,1,v.PASS
    w[12]=v.FULL_MAGIC
    w[13:18]=[26,702,702,699,3]
    w[18:25]=[19600,1000,800,800,3,21384,1010]
    w[25],w[26]=0x12345678,0xABCDEF01
    mem_read=702*v.PER_PAGE_IN
    mem_write=702*v.PER_MUTABLE_OUT
    w[27],w[28]=mem_read&0xFFFFFFFF,mem_read>>32
    w[29],w[30]=mem_write&0xFFFFFFFF,mem_write>>32
    w[31]=123216
    w[35]=40
    w[46]=702
    w[63]=v.DONE
    return struct.pack("<64I",*w)


@pytest.mark.parametrize("missing",(*run.physical.APPROVALS,*run.APPROVALS))
def test_every_full_inference_physical_approval_required_before_board(
    tmp_path,monkeypatch,missing
):
    a=args(tmp_path)
    setattr(a,missing,"NO")
    monkeypatch.setattr(run.physical.shutil,"which",lambda name:"/mock/tool")
    with pytest.raises((run.InferenceNoGo,run.physical.StageNoGo)):
        run.independent_launch_consent(a)
    assert not a.evidence.exists()


def test_full_inference_preflight_still_read_only(tmp_path):
    code=(ROOT/"scripts/p07_b4m_physical_full_inference.py").read_text()
    assert 'default="preflight"' in code
    assert 'if args.mode=="preflight":' in code
    assert "P07_B4M_KV260_ACCESSED=0" in code
    assert "physical.execute_staging(args,index,desc,staged,elf,on_verified=continuation)" in code
    assert "expanded_low_ddr_1075968_footprint_approved" in code
    assert "unproven_boot_firmware_exclusivity_risk_accepted" in code
    assert "P07_B4M_INDEPENDENT_FULL_NEURON_NUMERICAL_PARITY_VERIFIED=0" in code


def source_receipt(tmp_path):
    a=args(tmp_path)
    out=a.evidence
    out.mkdir()
    (out/"b4m_physical_route_readback").mkdir()
    signed={}
    expected={}
    for name,source in {
        "output_routes_80k_physical.bin":run.physical.frozen.OUT_FILENAME,
        "input_routes_896k_physical.bin":run.physical.frozen.IN_FILENAME,
        "original_TRAIN_ingress_physical.bin":
            "p07_b4m_original_TRAIN_validation_0_ingress.bin",
    }.items():
        b=(name+"\0").encode()*5
        (out/"b4m_physical_route_readback"/name).write_bytes(b)
        signed[source]=run.physical.old.file_sha(out/"b4m_physical_route_readback"/name)
        expected[name]={
            "sha256":signed[source],
            "byte_exact_vs_signed_host_input":True,
        }
    (out/"independent_staging_receipt.json").write_text(json.dumps({
        "original_27core_contexts_sha256":run.physical.model.ACCEPTED_BUNDLE_SHA,
        "original_descriptor_16k_sha256":run.physical.old.ACCEPTED_DESCRIPTOR_SHA,
        "original_B2_4_routes_and_train_physical_sha256":expected,
        "real_elf_downloaded":False,
        "inference_executed":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }))
    a.elf.write_bytes(b"FAKE-SYNTHETIC-ONLY")
    a.elf.with_suffix(".map").write_bytes(b"FAKE-MAP-SYNTHETIC-ONLY")
    return a,out,expected,signed


def test_full_inference_launch_only_after_real_stager_and_receipt(tmp_path,monkeypatch):
    a,out,readbacks,source_shas=source_receipt(tmp_path)
    # Fake identities stand in for prior strict physical stager; never
    # substitute these in production. One hardware command only: ELF launch.
    monkeypatch.setattr(run.physical,"EXPECTED_STAGE_SHA",source_shas)
    monkeypatch.setattr(run.physical,"EXPECTED_ELF_SHA",
                        run.physical.old.file_sha(a.elf))
    monkeypatch.setattr(run.physical,"EXPECTED_MAP_SHA",
                        run.physical.old.file_sha(a.elf.with_suffix(".map")))
    calls=[]
    def fake_xsdb(command,log):
        calls.append(command)
        assert command[:3]==["xsdb",run.LAUNCH_TCL,run.LAUNCH_TOKEN]
        assert (out/"independent_staging_receipt.json").exists()
        assert (out/"full_inference_launch_contract.json").exists()
        (out/"full_26tick_physical_mailbox_256.bin").write_bytes(fixture_mailbox())
        log.write_text("\n".join(run.LAUNCH_MARKERS)+"\n")
    with patch.object(run.physical.old.b4i,"log_call",side_effect=fake_xsdb):
        result=run.physically_execute_after_verified(a,out,readbacks)
    assert len(calls)==1
    assert result["full_26tick_trained_physical_execution_structurally_verified"] is True
    assert result["independent_full_neuron_numerical_parity_verified"] is False
    assert result["expanded_low_DDR_boot_firmware_exclusivity_independently_proven"] is False
    assert result["official_MNIST_TEST"]=="SEALED_NOT_ACCESSED"
    assert (out/"stage.txt").read_text().startswith("P07_B4M_GENUINE_26TICK_PHYSICAL_INFERENCE_RECEIPT_ACCEPTED_")


def test_corrupt_same_session_readback_cannot_download_elf(tmp_path,monkeypatch):
    a,out,readbacks,source_shas=source_receipt(tmp_path)
    monkeypatch.setattr(run.physical,"EXPECTED_STAGE_SHA",source_shas)
    original=out/"b4m_physical_route_readback"/"output_routes_80k_physical.bin"
    original.write_bytes(b"TAMPERED")
    with patch.object(run.physical.old.b4i,"log_call",
                      side_effect=AssertionError("must not contact board")):
        with pytest.raises(run.InferenceNoGo,match="byte mismatch"):
            run.physically_execute_after_verified(a,out,readbacks)
    assert not (out/"full_26tick_a53_run.log").exists()


def test_terminal_counter_failure_never_claims_receipt(tmp_path,monkeypatch):
    a,out,readbacks,source_shas=source_receipt(tmp_path)
    monkeypatch.setattr(run.physical,"EXPECTED_STAGE_SHA",source_shas)
    monkeypatch.setattr(run.physical,"EXPECTED_ELF_SHA",
                        run.physical.old.file_sha(a.elf))
    monkeypatch.setattr(run.physical,"EXPECTED_MAP_SHA",
                        run.physical.old.file_sha(a.elf.with_suffix(".map")))
    w=list(struct.unpack("<64I",fixture_mailbox()))
    w[14]=701
    def fake_xsdb(command,log):
        (out/"full_26tick_physical_mailbox_256.bin").write_bytes(
            struct.pack("<64I",*w))
        log.write_text("\n".join(run.LAUNCH_MARKERS)+"\n")
    with patch.object(run.physical.old.b4i,"log_call",side_effect=fake_xsdb):
        with pytest.raises(run.full_verify.FullReceiptError,match="paging"):
            run.physically_execute_after_verified(a,out,readbacks)
    assert not (out/"independent_full_26tick_physical_receipt.json").exists()


@pytest.mark.skipif(shutil.which("tclsh") is None,reason="tclsh unavailable")
def test_new_26tick_xsdb_launcher_requires_approval_before_connect(tmp_path):
    tcl=ROOT/run.LAUNCH_TCL
    result=subprocess.run(["tclsh",str(tcl)],capture_output=True,text=True)
    assert result.returncode!=0
    assert "B4M_FULL_26TICK_AFTER_SAME_SESSION_SIGNED_READBACK_APPROVED" in result.stderr


@pytest.mark.skipif(shutil.which("tclsh") is None,reason="tclsh unavailable")
def test_actual_new_tcl_with_mock_physical_mailbox_then_success(tmp_path):
    elf=tmp_path/"p07_b4m_full_26tick.elf"
    elf.write_bytes(b"P07_B4M_A53_TRAIN_26_TICK_CANDIDATE_V1"+bytes(106600))
    zero=tmp_path/"zeros256.bin"
    zero.write_bytes(bytes(256))
    mailbox=tmp_path/"readback.bin"
    mock=tmp_path/"mock_full_xsdb.tcl"
    good=tmp_path/"fake_done.bin"
    good.write_bytes(fixture_mailbox())
    mock.write_text(
        'proc exec {args} {\n'
        ' if {[lindex $args 0] eq "sha256sum"} {return "ccbd8c531e5571f929e81613cfee71f54abf341c36412ebcfa7d98e2313e6b70  fake"}\n'
        ' if {[lindex $args 0] eq "grep"} {return ""}\n'
        ' error "unexpected OS command"\n}\n'
        'proc connect {args} {return connected}\n'
        'proc disconnect {} {return disconnected}\n'
        'proc targets {args} {return okay}\n'
        'proc stop {} {return halted}\n'
        'proc rst {args} {return reset}\n'
        'proc dow {args} {\n'
        ' if {[lindex $args 0] eq "-data"} {set ::zero_source [lindex $args 1]} else {set ::elf_downloaded 1}\n'
        ' return okay\n'
        '}\n'
        'proc con {} {set ::running 1}\n'
        'proc mrd {args} {\n'
        ' set file [lindex $args 2]\n'
        ' if {[info exists ::running]} {file copy -force $::captured $file} else {file copy -force $::zero_source $file}\n'
        ' return okay\n'
        '}\n'
        f'set ::captured {{{good}}}\n'
        'set argc 5\n'
        f'set argv [list {run.LAUNCH_TOKEN} {{{elf}}} {{{zero}}} '
        f'{{{mailbox}}} tcp:127.0.0.1:3121]\n'
        f'source {{{ROOT/run.LAUNCH_TCL}}}\n'
    )
    result=subprocess.run(["tclsh",str(mock)],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr+result.stdout
    assert "P07_B4M_A53_26TICK_TERMINAL_DONE_PHYSICALLY_OBSERVED=1" in result.stdout
    assert "P07_B4M_256B_MAILBOX_ZERO_PHYSICAL_READBACK_PASS=1" in result.stdout
    assert mailbox.read_bytes()==good.read_bytes()


def test_no_official_test_or_prior_epoch_launcher_in_full_driver():
    source=(ROOT/"scripts/p07_b4m_physical_full_inference.py").read_text()
    assert "p07_b4l_b3_xsdb_first_epoch_run.tcl" not in source
    assert "official_MNIST_TEST" in source
    assert "independent_full_neuron_numerical_parity_verified" in source
