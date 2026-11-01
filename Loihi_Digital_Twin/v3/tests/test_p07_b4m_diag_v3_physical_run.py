"""Diagnostic V3 physical launcher checks. Entirely native/synthetic; NO board."""
from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import p07_b4m_diag_v3_physical_run as run


def args(tmp_path):
    build = tmp_path / "diag_build"
    workspace = build / "vitis_workspace"
    workspace.mkdir(parents=True)
    elf = workspace / run.diag_gate.ELF_NAME
    elf.write_bytes(b"SYNTHETIC_V3_ELF_ONLY_" + run.V3_ID.encode())
    elf.with_suffix(".map").write_bytes(b"SYNTHETIC_MAP_ONLY")
    return SimpleNamespace(
        frozen_dir=tmp_path/"frozen",
        staged_dir=tmp_path/"staged",
        bindings_dir=tmp_path/"bindings",
        routes_dir=tmp_path/"routes",
        offline_report=tmp_path/"p07_b4m_diag_v3_offline_synthetic.json",
        reports=tmp_path/"reports",
        b4i_build=tmp_path/"b4i",
        diag_build=build,
        elf=elf,
        evidence=tmp_path/"new_physical_evidence",
        validation_ordinal=0,
        **{name:"YES" for name in (*run.physical.APPROVALS, *run.APPROVALS)}
    )


def staged_receipt(a):
    out = a.evidence
    out.mkdir()
    rb = out / "b4m_physical_route_readback"
    rb.mkdir()
    signed = {}
    readbacks = {}
    originals = {
        "output_routes_80k_physical.bin":run.physical.frozen.OUT_FILENAME,
        "input_routes_896k_physical.bin":run.physical.frozen.IN_FILENAME,
        "original_TRAIN_ingress_physical.bin":"p07_b4m_original_TRAIN_validation_0_ingress.bin",
    }
    for name, source in originals.items():
        data = (name+"\x00").encode() * 5
        (rb/name).write_bytes(data)
        digest = run.physical.old.file_sha(rb/name)
        signed[source] = digest
        readbacks[name] = {"sha256":digest,"byte_exact_vs_signed_host_input":True}
    (out/"independent_staging_receipt.json").write_text(json.dumps({
        "original_27core_contexts_sha256":run.physical.model.ACCEPTED_BUNDLE_SHA,
        "original_descriptor_16k_sha256":run.physical.old.ACCEPTED_DESCRIPTOR_SHA,
        "original_B2_4_routes_and_train_physical_sha256":readbacks,
        "real_elf_downloaded":False,
        "inference_executed":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED"
    }))
    return out, readbacks, signed


@pytest.mark.parametrize("missing", (*run.physical.APPROVALS, *run.APPROVALS))
def test_every_approval_rejected_when_missing(tmp_path, missing):
    a = args(tmp_path)
    setattr(a, missing, "NO")
    with pytest.raises((run.InferenceNoGo, run.physical.StageNoGo), match="NO-GO"):
        run.independent_launch_consent(a)
    assert not a.evidence.exists()


def test_no_v1_replacement_in_diag_v3_admission(tmp_path):
    a = args(tmp_path)
    a.elf = a.diag_build / "vitis_workspace" / "p07_b4m_full_26tick.elf"
    with pytest.raises(run.InferenceNoGo, match="exact V3 build workspace"):
        run.require_v3_original(a)


def test_exact_report_verified_before_hardware(tmp_path, monkeypatch):
    a = args(tmp_path)
    diag = {
        "diagnostic_firmware_identity":run.V3_ID,
        "genuine_diagnostic_v3_elf":{
            "new_elf_sha256":run.V3_ELF_SHA,
            "new_linker_map_sha256":run.V3_MAP_SHA,
            "pt_load_start":"0x00000000",
            "pt_load_end_exclusive":"0x00106B00",
            "pt_load_filesz":106580,
            "pt_load_memsz":1075968,
        },
        "original_route_source":{
            "staged_files_sha256":run.physical.EXPECTED_STAGE_SHA,
        },
        "expanded_low_DDR_boot_firmware_exclusivity_independently_proven":False,
        "diagnostic_v3_physical_launch_authorized":False,
    }
    a.offline_report.write_text(json.dumps(diag))
    monkeypatch.setattr(run.diag_gate, "admit", lambda **kwargs:diag)
    monkeypatch.setattr(run.physical.model, "prepare_verified_contexts", lambda *args:{"original":True})
    monkeypatch.setattr(run.physical.old, "require_real_bindings", lambda *args:{"binding":True})
    monkeypatch.setattr(run.physical, "resolve_elf_inspection_tools", lambda:("readelf","nm"))
    monkeypatch.setattr(run.physical.old.b4i, "preflight", lambda *args, **kwargs:None)
    idx, desc, stage, elf = run.require_v3_original(a)
    assert idx == {"original":True} and desc == {"binding":True}
    assert stage == diag["original_route_source"] and elf == diag["genuine_diagnostic_v3_elf"]
    a.offline_report.write_text(json.dumps({**diag,"diagnostic_firmware_identity":"BAD"}))
    with pytest.raises(run.InferenceNoGo,match="offline report mismatches"):
        run.require_v3_original(a)


def test_same_session_bad_readback_stops_v3_download(tmp_path,monkeypatch):
    a = args(tmp_path)
    out, readbacks, signed = staged_receipt(a)
    monkeypatch.setattr(run.physical, "EXPECTED_STAGE_SHA", signed)
    (out/"b4m_physical_route_readback"/"input_routes_896k_physical.bin").write_bytes(b"MUTATED")
    with patch.object(run.physical.old.b4i, "log_call", side_effect=AssertionError("must NOT touch board")):
        with pytest.raises(run.InferenceNoGo,match="byte mismatch"):
            run.physically_execute_after_verified(a,out,readbacks)


def test_v3_failed_mailbox_preserves_b4d2_and_no_acceptance(tmp_path,monkeypatch):
    a = args(tmp_path)
    out, readbacks, signed = staged_receipt(a)
    monkeypatch.setattr(run.physical, "EXPECTED_STAGE_SHA", signed)
    monkeypatch.setattr(run, "V3_ELF_SHA", run.physical.old.file_sha(a.elf))
    monkeypatch.setattr(run, "V3_MAP_SHA", run.physical.old.file_sha(a.elf.with_suffix(".map")))
    words = [0]*64
    words[0] = run.full_verify.MAGIC
    words[1] = 1
    words[2] = 0xDEAD0000
    words[3] = 9
    words[44] = (1<<32)-5
    words[46] = 1
    words[47] = run.mailbox_diagnosis.DIAG_V3_MAGIC
    words[49] = 10  # dispatch failed after HLS completed
    words[50] = 3   # physical pager dispatch fault
    words[53] = 4   # HLS synapse row bound flag must not be accepted
    words[62] = 0   # V3 metadata fix ran successfully (not inferred hardware pass)
    words[56] = 0x18
    words[63] = run.full_verify.DONE
    def fake_xsdb(command, log):
        assert command[:3] == ["xsdb",run.LAUNCH_TCL,run.LAUNCH_TOKEN]
        assert (out/"diag_v3_launch_contract.json").is_file()
        (out/"diag_v3_physical_mailbox_256.bin").write_bytes(struct.pack("<64I",*words))
        log.write_text("\n".join(run.LAUNCH_MARKERS)+"\n")
    with patch.object(run.physical.old.b4i, "log_call",side_effect=fake_xsdb):
        with pytest.raises(run.full_verify.FullReceiptError):
            run.physically_execute_after_verified(a,out,readbacks)
    diagnostic=json.loads((out/"diag_v3_failed_mailbox_diagnostic.json").read_text())
    assert diagnostic["diagnostic_v3_failure_payload_present"] is True
    assert diagnostic["failure_telemetry"]["b3c2_scheduler_first_fault"]["uint32"] == 10
    assert diagnostic["failure_telemetry"]["pager_first_failure_kind"]["uint32"] == 3
    assert diagnostic["failure_telemetry"]["p03_dispatch_core_status_raw"]["uint32"] == 4
    assert diagnostic["failure_telemetry"]["v3_dispatch_metadata_fix_status"]["uint32"] == 0
    assert diagnostic["firmware_terminal_status"] == "B4M_FIRMWARE_FAIL"
    assert diagnostic["all_structural_inference_receipt_checks_pass"] is False
    assert not (out/"diag_v3_structural_receipt.json").exists()
    assert "REBOOT_REQUIRED" in (out/"stage.txt").read_text()
    assert diagnostic["diagnostic_v2_failure_payload_present"] is False
    assert diagnostic["diagnostic_v3_failure_payload_present"] is True


@pytest.mark.skipif(shutil.which("tclsh") is None,reason="tclsh unavailable")
def test_v3_tcl_fail_closed_without_token_or_pinned_elf():
    script=ROOT/run.LAUNCH_TCL
    p=subprocess.run(["tclsh",str(script)],capture_output=True,text=True)
    assert p.returncode!=0
    assert run.LAUNCH_TOKEN in p.stderr
    source=script.read_text()
    assert run.V3_ELF_SHA in source
    assert run.V3_ID in source
    assert "p07_b4m_diag_v3_26tick.elf" in source
    assert "P07_B4M_A53_TRAIN_26_TICK_CANDIDATE_V1" not in source
    assert run.LAUNCH_TCL != "vivado/p07_b4m_xsdb_full_26tick_run.tcl"


@pytest.mark.skipif(shutil.which("tclsh") is None,reason="tclsh unavailable")
def test_v3_xsdb_mock_terminal_capture(tmp_path):
    a=args(tmp_path)
    a.elf.write_bytes(run.V3_ID.encode()+bytes(106600))
    zero=tmp_path/"zero.bin"
    zero.write_bytes(bytes(256))
    mail=tmp_path/"mailbox.bin"
    captured=tmp_path/"simulated_done.bin"
    words=[0]*64
    words[63]=run.full_verify.DONE
    captured.write_bytes(struct.pack("<64I",*words))
    mock=tmp_path/"mock.tcl"
    mock.write_text(
        'proc exec {args} {\n'
        ' if {[lindex $args 0] eq "sha256sum"} {return "'+run.V3_ELF_SHA+' fake"}\n'
        ' if {[lindex $args 0] eq "grep"} {return ""}\n'
        ' error "unexpected OS command"\n}\n'
        'proc connect {args} {return connected}\n'
        'proc disconnect {} {return disconnected}\n'
        'proc targets {args} {return okay}\n'
        'proc stop {} {return halted}\n'
        'proc rst {args} {return reset}\n'
        'proc dow {args} {if {[lindex $args 0] eq "-data"} {set ::zero_source [lindex $args 1]} else {set ::elf_downloaded 1}}\n'
        'proc con {} {set ::running 1}\n'
        'proc mrd {args} {set f [lindex $args 2]\n'
        ' if {[info exists ::running]} {file copy -force $::captured $f} else {file copy -force $::zero_source $f}}\n'
        f'set ::captured {{{captured}}}\n'
        'set argc 5\n'
        f'set argv [list {run.LAUNCH_TOKEN} {{{a.elf}}} {{{zero}}} '
        f'{{{mail}}} tcp:127.0.0.1:3121]\n'
        f'source {{{ROOT/run.LAUNCH_TCL}}}\n'
    )
    result=subprocess.run(["tclsh",str(mock)],capture_output=True,text=True,timeout=30)
    assert result.returncode==0, result.stderr+"\n"+result.stdout
    for item in run.LAUNCH_MARKERS:
        assert item in result.stdout
    assert mail.read_bytes()==captured.read_bytes()

def test_v3_rejects_stale_historical_v2_artifact_and_launch_script(tmp_path):
    a=args(tmp_path)
    v2=a.diag_build/"vitis_workspace"/"p07_b4m_diag_v2_26tick.elf"
    v2.write_bytes(b"DO_NOT_SWAP_HISTORICAL_V2_ELF")
    a.elf=v2
    with pytest.raises(run.InferenceNoGo,match="exact V3 build workspace"):
        run.require_v3_original(a)
    assert run.LAUNCH_TCL=="vivado/p07_b4m_diag_v3_xsdb_run.tcl"
    assert run.V3_ELF_SHA=="66d628bebed753ae9a5c61b993936b558f00dc31e63bf5748a8d9858ac15f904"
    assert run.V3_MAP_SHA=="148b8720bc41253c5d06cece22ffaf59f8f70be7af3976726f5e504f2c379ede"
    assert run.V3_ID=="P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V3"
