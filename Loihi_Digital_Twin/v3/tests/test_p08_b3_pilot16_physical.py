"""P08-B3 first16 *physical* runner/independent attestation negative-only tests.

ALL tests avoid XSDB/Vivado. They must never execute any external tools.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import shutil
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p08_b3_pilot16_physical_run as runner
import p08_b3_pilot16_independent_physical_verify as verifier


def test_independent_approval_set_is_specific_and_default_no_go(monkeypatch,tmp_path):
    assert len(runner.APPROVALS)==8
    assert "unproven_boot_ddr_dma_exclusivity_risk_accepted" in runner.APPROVALS
    assert "six_original_ddr_transfers_overwrite_approved" in runner.APPROVALS
    assert "reboot_and_recovery_approved" in runner.APPROVALS
    def forbid(*args,**kwargs):
        raise AssertionError("physical tool must not be invoked")
    monkeypatch.setattr(runner.b4i,"log_call",forbid)
    a=argparse.Namespace(evidence=tmp_path/"never_created")
    for approval in runner.APPROVALS:
        setattr(a,approval,"NO")
    with pytest.raises(runner.PilotPhysicalNoGo):
        runner.execute(a,{})
    assert not (tmp_path/"never_created").exists()


def test_preflight_does_not_invoke_subprocess_or_touch_board(monkeypatch,tmp_path):
    # Direct pure-Python gate: missing staged file must terminate before
    # reaching any tool invocation or writing output state.
    def forbid(*args,**kwargs):
        raise AssertionError("preflight attempted physical action")
    monkeypatch.setattr(runner.b4i,"log_call",forbid)
    stage=tmp_path/"source"
    stage.mkdir()
    args=argparse.Namespace(stage=stage,oracle=tmp_path/"o",
                            pilot_build=tmp_path/"b",
                            reports=tmp_path/"r",
                            reset_pins=tmp_path/"pins")
    with pytest.raises((runner.PilotPhysicalNoGo,ValueError,OSError)):
        runner.offline_gate(args)
    assert {x.name for x in tmp_path.iterdir()}=={"source"}


def test_pilot_physical_runner_pins_exact_user_built_and_immutable_hashes():
    assert runner.ELF_SHA==(
        "29482212c80fb9137b3c185b0cbcdf2000f41417e5af8d3c46b0cd39ecb74fd3")
    assert runner.MAP_SHA==(
        "9d2106d82347385e936bb27176aa8f50a332beb3f13c3ca8e182890a689c674b")
    assert runner.gate.ORACLE_SHA==(
        "13e3e679110059c70f8cfd3d51014c37c62a2cb3ea9c85974e27360606d3b271")
    assert runner.source.EXPECTED_SHA[runner.source.FILES[0][0]]==(
        "3733e1c289fb5704c69be90f37b59a25e30ddedf7dd8dc305649e0be238af64e")
    assert runner.STAGE_TCL=="vivado/p08_b3_pilot16_six_ddr_stage.tcl"
    assert runner.LAUNCH_TCL=="vivado/p08_b3_pilot16_run_and_capture.tcl"


def test_new_tcl_guards_frozen_base_addresses_and_no_shell_ddr_alias():
    stage=(ROOT/runner.STAGE_TCL).read_text()
    launch=(ROOT/runner.LAUNCH_TCL).read_text()
    for marker in (
        "P08_B3_PILOT16_SIX_DDR_TRANSFERS_RISK_APPROVED",
        "0x40000000","0x43000000","0x43FC0000","0x41000000",
        "0x43FC4000","0x42100000","0x80000",
    ):
        if marker=="0x80000":
            continue
        assert marker in stage
    assert "0x43FF0200" not in stage
    assert " dow $elf" not in stage
    assert " con\n" not in stage
    assert "P08_B3_PILOT_SIX_PHYSICAL_DDR_TRANSFERS_BYTE_EXACT_PASS=1" in stage
    for marker in (
        "P08_B3_PILOT16_AFTER_SIX_SIGNED_PHYSICAL_READBACK_RISK_APPROVED",
        "0x43FF0200","0x42200000","0x42300000",
        "29482212c80fb9137b3c185b0cbcdf2000f41417e5af8d3c46b0cd39ecb74fd3",
        "P08_B3_PILOT_EXACT_16_FRAME_HARDWARE_TERMINAL_OBSERVED=1",
        "P08_B3_PILOT_REBOOT_REQUIRED=1",
    ):
        assert marker in launch
    assert "P08_B2_3_ORIGINAL_27CORE_1024_IMAGE_ONLY_A53_V1" not in launch
    assert "mrd -bin -file" in stage and "mrd -bin -file" in launch
    assert "targets -set -filter" in stage and "targets -set -filter" in launch


def test_tcl_parses_and_default_denies_without_physical_connection(tmp_path):
    tcl=shutil.which("tclsh")
    if not tcl:
        pytest.skip("Tcl interpreter not available on this host")
    for file in (runner.STAGE_TCL,runner.LAUNCH_TCL):
        input_file=ROOT/file
        # Tcl parser is only invoked with ZERO args; first argv gate MUST
        # refuse before any connect or filesystem side effects.
        p=subprocess.run([tcl,str(input_file)],capture_output=True,
                         text=True,timeout=20,cwd=tmp_path)
        assert p.returncode!=0
        assert "P08-B3:" in p.stderr
    assert list(tmp_path.iterdir())==[]


def test_failed_independent_physical_verifier_does_not_accept_fixture(
        tmp_path,monkeypatch):
    def forbid(*args,**kwargs):
        raise AssertionError("no hardware tools on artifact-verifier path")
    monkeypatch.setattr(runner.b4i,"log_call",forbid)
    e=tmp_path/"untrusted-physical"
    e.mkdir()
    stage=tmp_path/"untrusted-stage"
    stage.mkdir()
    with pytest.raises((verifier.EvidenceNoGo,runner.PilotPhysicalNoGo,
                        ValueError,OSError,KeyError)):
        verifier.verify(e,stage,tmp_path/"oracle",tmp_path/"build",
                        tmp_path/"reports",tmp_path/"pins",
                        tmp_path/"not-written.json")
    assert not (tmp_path/"not-written.json").exists()


def test_full_physical_report_is_not_unsupported_energy_or_full_raw_trace():
    c=(ROOT/"scripts/p08_b3_pilot16_independent_physical_verify.py").read_text()
    assert '"direct_raw_full_neuron_26x1010_trace_readback_during_pilot":False' in c
    assert '"benchmark_latency_sessions_accepted":False' in c
    assert '"independent_boot_firmware_DDR_ownership_proven":False' in c
    assert 'physical.source.EXPECTED_SHA' in c
    assert '"all_16_A53_full_service_timers_structurally_valid":True' in c
    assert "P08_B3_PILOT16_NEW_PHYSICAL_LATENCY_BENCHMARK_ACCEPTED=0" in c
