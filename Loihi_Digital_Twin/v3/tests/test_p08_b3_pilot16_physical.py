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


def test_pilot_mailbox_done_marker_only_is_never_terminal(tmp_path):
    """Replay real 256B mailbox ABI into PURE Tcl, without loading XSDB.

    C firmware writes DONE at startup and after all intermediate frames,
    so the launch script MUST distinguish progress from final 16/16 PASS.
    """
    import base64
    import re
    import struct
    tcl=shutil.which("tclsh")
    if not tcl:
        pytest.skip("Tcl interpreter required")
    driver=(ROOT/runner.LAUNCH_TCL).read_text()
    pattern=r"(?ms)^proc pilot_mailbox_classify \{raw\} \{\n.*?^\}"
    match=re.search(pattern,driver)
    assert match is not None,"Tcl must expose independently testable classifier"
    proc=match.group()
    assert 'set state [pilot_mailbox_classify $raw]' in driver
    assert 'if {$state eq "PROGRESS"}' in driver
    assert 'if {$state eq "SUCCESS" || $state eq "FAILURE"}' in driver
    assert 'set terminal 1' in driver
    assert 'set terminal_state $state' in driver
    cases=(
        (0xC0DE0000,0xFFFFFFFF,0,0xC0DEF00D,"PROGRESS"),
        (0xC0DE0000,0,1,0xC0DEF00D,"PROGRESS"),
        (0xC0DE0000,14,15,0xC0DEF00D,"PROGRESS"),
        (0xC0DE0000,15,16,0xC0DEF00D,"PROGRESS"),
        (0x600D0823,15,16,0xC0DEF00D,"SUCCESS"),
        (0x600D0823,15,15,0xC0DEF00D,"INVALID"),
        (0x600D0823,14,16,0xC0DEF00D,"INVALID"),
        (0xDEAD0823,2,2,0xC0DEF00D,"FAILURE"),
        (0xC0DE0000,0,0,0xC0DEF00D,"INVALID"),
        (0x600D0823,15,16,0,"INCOMPLETE"),
    )
    for status,idx,completed,done,expected in cases:
        words=[0]*64
        words[0]=0x50384232
        words[1]=1
        words[2]=status
        words[3]=idx
        words[4]=0
        words[5]=completed
        words[63]=done
        blob=struct.pack("<64I",*words)
        encoded=base64.b64encode(blob).decode("ascii")
        script=(proc+"\nset raw [binary decode base64 {"+encoded+"}]\n"+
                "puts [pilot_mailbox_classify $raw]\n")
        p=subprocess.run([tcl],input=script,capture_output=True,text=True,
                         timeout=15,cwd=tmp_path)
        assert p.returncode==0,(expected,p.stderr)
        assert p.stdout.strip()==expected,(
            expected,p.stdout.strip(),hex(status),idx,completed,done)


def test_six_original_ddr_stage_full_mock_xsdb_byte_roundtrip(tmp_path):
    """Execute actual original staging Tcl with mock PSU/XSDB in tclsh.

    Use entirely synthetic host bytes and fake hash gate ONLY for this
    untrusted native fixture. Tests 54 independent staged P02 cores + four
    signed-input transfer receipts and repro of observed old Tcl abort.
    No actual hardware tools, JTAG, genuine frozen model or DDR accessed.
    """
    tcl=shutil.which("tclsh")
    if not tcl:
        pytest.skip("Tcl interpreter required for actual full stage exercise")
    script=ROOT/runner.STAGE_TCL
    code=script.read_text()
    fixed='puts "P08_B3_PILOT_${name}_BYTE_EXACT_PASS=1"'
    bad_line='puts "P08_B3_PILOT_$name_BYTE_EXACT_PASS=1"'
    assert fixed in code and bad_line not in code
    cases=(
        ("synthetic_p02.bin",14155776,b"LTV3CTX1"),
        ("synthetic_bind.bin",16384,b"B4BIND01"),
        ("synthetic_in.bin",917504,b"B4MING01"),
        ("synthetic_out.bin",81920,b"B4MROUT1"),
        ("synthetic_raw.bin",802816,b"\x00"*8),
    )
    files=[]
    for name,size,magic in cases:
        p=tmp_path/name
        with p.open("wb") as fd:
            fd.write(magic)
            fd.truncate(size)
        files.append(p)
    harness=tmp_path/"mock_xsdb_no_board.tcl"
    harness.write_text(r'''
set script [lindex $argv 0]
set argv [lrange $argv 1 end]
set argc [llength $argv]
proc exec {args} {
    if {[llength $args]!=2 || [lindex $args 0] ne "sha256sum"} {
        error "SYNTHETIC: refusing any external command"
    }
    set names {synthetic_p02.bin synthetic_bind.bin synthetic_in.bin synthetic_out.bin synthetic_raw.bin}
    set sums {
      3733e1c289fb5704c69be90f37b59a25e30ddedf7dd8dc305649e0be238af64e
      2f0a5299a3948d7e0d4d48c265d199616fd3709d966343629596464687f611eb
      380268c5e8faa2664a31f993683c6759316239932d96b8e681ddb458c81574e8
      2405269110585a3921dfc64ed1b2adbf0622c520cfdce8bb6b1ac6d825f23103
      739006f03b37c36d7aa11b6b68612338fc5249c7f48b9d854520ee7e3ea9c06e
    }
    set found [lsearch -exact $names [file tail [lindex $args 1]]]
    if {$found<0} {error "SYNTHETIC: unknown fake original source"}
    return [format "%s  %s" [lindex $sums $found] [lindex $args 1]]
}
proc connect {args} {puts "SYNTHETIC_MOCK_NO_BOARD_CONNECT"}
proc disconnect {args} {}
proc targets {args} {return "SYNTHETIC_MOCK_PSU"}
set ::ddr [dict create]
proc dow {args} {
    if {[llength $args]!=3 || [lindex $args 0] ne "-data"} {
        error "SYNTHETIC: rejecting any ELF/unknown download"
    }
    dict set ::ddr [lindex $args 2] [p08_read_binary [lindex $args 1]]
}
proc mrd {args} {
    if {[llength $args]!=5 || [lindex $args 0] ne "-bin" ||
        [lindex $args 1] ne "-file"} {
        error "SYNTHETIC: bad readback request"
    }
    set address [lindex $args 3]
    if {![dict exists $::ddr $address]} {
        error "SYNTHETIC: unwritten DDR address"
    }
    set payload [dict get $::ddr $address]
    if {[string length $payload]!=4*[lindex $args 4]} {
        error "SYNTHETIC: mismatch 32bit word count"
    }
    set out [open [lindex $args 2] wb]
    fconfigure $out -translation binary -encoding binary
    puts -nonewline $out $payload
    close $out
}
source $script
''',encoding="utf-8")
    dest=tmp_path/"mock_psu_readbacks"
    dest.mkdir()
    cmd=[tcl,str(harness),str(script),runner.STAGE_TOKEN,
         *(str(f) for f in files),str(dest),"tcp:127.0.0.1:3121"]
    done=subprocess.run(cmd,capture_output=True,text=True,
                        timeout=120,cwd=tmp_path)
    assert done.returncode==0,done.stderr[-3000:]+done.stdout[-2000:]
    assert "SYNTHETIC_MOCK_NO_BOARD_CONNECT" in done.stdout
    assert len([x for x in done.stdout.splitlines()
                if "_CORE_" in x and "_READBACK_PASS=1" in x])==54
    for name in (
        "binding_16k_physical.bin",
        "input_routes_896k_physical.bin",
        "output_routes_80k_physical.bin",
        "raw1024_physical.bin",
    ):
        assert done.stdout.splitlines().count(
            f"P08_B3_PILOT_{name}_BYTE_EXACT_PASS=1")==1
    assert done.stdout.splitlines().count(
        "P08_B3_PILOT_SIX_PHYSICAL_DDR_TRANSFERS_BYTE_EXACT_PASS=1")==1
    for source_file,rb_name in (
        (files[1],"binding_16k_physical.bin"),
        (files[2],"input_routes_896k_physical.bin"),
        (files[3],"output_routes_80k_physical.bin"),
        (files[4],"raw1024_physical.bin"),
    ):
        assert (dest/rb_name).read_bytes()==source_file.read_bytes()
    with files[0].open("rb") as fd:
        source_bytes=fd.read()
    for label in ("mutable","backup"):
        subdir=dest/(label+"_original_p02_readback")
        assert len(list(subdir.glob("core_??_physical.bin")))==27
        for n in range(27):
            assert (subdir/f"core_{n:02d}_physical.bin").read_bytes()==(
                source_bytes[n*524288:(n+1)*524288])
    # Re-inject exact previously observed bug in a disposable Tcl copy:
    # a new run MUST fail there, proving this test catches the regression.
    broken=tmp_path/"old_broken_tcl.tcl"
    broken.write_text(code.replace(fixed,bad_line),encoding="utf-8")
    bad_dest=tmp_path/"failed_mock_stage"
    bad_dest.mkdir()
    bad=subprocess.run(
        [tcl,str(harness),str(broken),runner.STAGE_TOKEN,
         *(str(f) for f in files),str(bad_dest),"tcp:127.0.0.1:3121"],
        capture_output=True,text=True,timeout=120,cwd=tmp_path)
    assert bad.returncode!=0,"old Tcl interpolation must be rejected"
    assert 'name_BYTE_EXACT_PASS' in bad.stderr
    assert "P08_B3_PILOT_STAGING_FAILED_REBOOT_REQUIRED=1" in bad.stdout
