"""P08-B44 NEW distinct 1024 profile JTAG capture/original neuron CRC gates (NO BOARD)."""
from __future__ import annotations
import argparse
import base64
import json
import re
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zlib

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p08_b44_profile_physical_run as physical
import p08_b44_profile_independent_physical_verify as independent
import p08_b44_reset_profile_sidecar as subphase
import p08_b4_2_verify_full1024 as numerical
from test_p08_b4_2_full1024_physical import synthetic_full1024

def test_exact_original_1024_new_profile_file_sha_and_no_original_elf():
    assert physical.PROFILE_ELF_SHA=="bed1301c69594bf7ebeaa37765ad2cb3035aa0f6d5e9cb4d1fb4637042be3ab3"
    assert physical.PROFILE_MAP_SHA=="d94fa2695e82cc3a501442313bb77e89eb046f01450167108832a190fd9fd2c9"
    assert physical.PROFILE_ELF_AUDIT_SHA=="7a5818dc5469ea288fefcefb87ebc4fd3ab1e5c7bdce0bbfda717a6f2787b129"
    assert physical.PROFILE_ELF_SHA!=physical.base.ELF_SHA
    assert physical.RUN_TCL!=physical.base.LAUNCH_TCL
    assert physical.RUN_TOKEN!=physical.base.RUN_TOKEN
    assert len(physical.APPROVALS)==9
    assert "extra_profile_ddr_region_overwrite_approved" in physical.APPROVALS

def test_no_board_default_denies_unsigned_new_build(tmp_path,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError("CI must not contact JTAG")
    monkeypatch.setattr(physical.base.b4i,"log_call",forbidden)
    args=argparse.Namespace(
        stage=tmp_path/"missing",shards=tmp_path/"missing",
        ingress=tmp_path/"missing",oracle=tmp_path/"missing",
        first16=tmp_path/"missing",b3_report=tmp_path/"missing",
        elf=tmp_path/"missing",linker_map=tmp_path/"missing",
        reset_pins=tmp_path/"missing",reports=tmp_path/"missing",
        profile_elf=tmp_path/"missing",
        profile_map=tmp_path/"missing",
        profile_elf_audit=tmp_path/"missing",
        b4_independent_report=tmp_path/"missing",
        b44_timing_report=tmp_path/"missing",
        evidence=tmp_path/"evidence",out=tmp_path/"out")
    for key in physical.APPROVALS:
        setattr(args,key,"NO")
    with pytest.raises((physical.base.FullPhysicalNoGo,
                        physical.base.prior.PilotPhysicalNoGo,
                        physical.NewProfileNoGo,OSError)):
        physical.admission(args)
    with pytest.raises(physical.NewProfileNoGo,match="explicitly approved"):
        physical.execute(args,{})
    assert not args.evidence.exists()

def test_actual_distinct_physical_tcl_four_regions_exact_terminal(tmp_path):
    tcl=ROOT/physical.RUN_TCL
    source=tcl.read_text()
    assert "p08_b44_reset_profile_1024.elf" in source
    assert "P08_B44_ORIGINAL_27CORE_RESET_PROFILE_1024_A53_V1" in source
    assert "P08_B44_RESET_PROFILE_1024_TERMINAL_DONE=1" in source
    assert physical.PROFILE_ELF_SHA in source
    assert "0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1" not in source
    for addr,name in (
        ("0x43FF0200","mailbox_zero_physical.bin"),
        ("0x42200000","journal_zero_physical.bin"),
        ("0x42300000","timing_zero_physical.bin"),
        ("0x42400000","reset_profile_zero_physical.bin")):
        assert addr in source and name in source
    for n in ("journal1024_physical.bin","timing1024_physical.bin",
              "reset_profile1024_physical.bin","mailbox_terminal_physical.bin"):
        assert n in source
    assert "P08_B44_PROFILE1024_EXPERIMENTAL_DDR_0x42400000_ZERO_READBACK_PASS=1" in source
    assert "P08_B44_PROFILE1024_EXACT_1024_FRAME_HARDWARE_TERMINAL_OBSERVED=1" in source
    assert "if {$attempt - $last_advance_attempt > 3600}" in source
    assert "if {$completed>$previous_completed}" in source
    assert "3 1023 4 0 5 1024" in source
    shell=shutil.which("tclsh")
    if shell:
        result=subprocess.run([shell,str(tcl)],capture_output=True,
                              cwd=tmp_path,text=True,timeout=20)
        assert result.returncode!=0 and "P08-B4.4 PROFILE:" in result.stderr

def test_real_new_profile_tcl_progress_never_terminal(tmp_path):
    shell=shutil.which("tclsh")
    if not shell:pytest.skip("tclsh missing")
    source=(ROOT/physical.RUN_TCL).read_text()
    matcher=re.search(r"(?ms)^proc pilot_mailbox_classify \{raw\} \{\n.*?^\}",source)
    assert matcher
    test_cases=[
        (0xC0DE0000,0xFFFFFFFF,0,0,"PROGRESS"),
        (0xC0DE0000,22,23,0,"PROGRESS"),
        (0xC0DE0000,1023,1024,0,"PROGRESS"),
        (0x600D0823,1023,1024,0,"SUCCESS"),
        (0x600D0823,1022,1024,0,"INVALID"),
        (0x600D0823,1023,1023,0,"INVALID"),
        (0xDEAD0823,12,12,203,"FAILURE"),
    ]
    for status,index,count,fault,expected in test_cases:
        words=[0]*64
        words[:6]=[0x50384232,1,status,index,fault,count]
        words[63]=0xC0DEF00D
        encoded=base64.b64encode(struct.pack("<64I",*words)).decode()
        command=matcher.group()+f"\nset raw [binary decode base64 {{{encoded}}}]\nputs [pilot_mailbox_classify $raw]\n"
        completed=subprocess.run([shell],input=command,text=True,capture_output=True,
                                 cwd=tmp_path,timeout=20)
        assert completed.returncode==0,completed.stderr
        assert completed.stdout.strip()==expected

@pytest.fixture
def synthetic_new_four_captures(synthetic_full1024,tmp_path):
    oracle,first16,journal,timing,mailbox,_=synthetic_full1024
    capture=tmp_path/"new_profile_capture"
    capture.mkdir()
    for src,dst in ((journal,"journal1024_physical.bin"),
                    (timing,"timing1024_physical.bin"),
                    (mailbox,"mailbox_terminal_physical.bin")):
        (capture/dst).write_bytes(src.read_bytes())
    rows=[]
    for i in range(1024):
        w=[0]*64
        w[:9]=[subphase.MAGIC,1,i,subphase.PASS,i+1,27,subphase.COPIED,27,27]
        w[9]=99999001
        # Fixture's actual first phase 1000 ticks, so profile is subordinate.
        w[11]=80
        for j,phase_ticks in enumerate((5,20,10,15,20)):
            w[13+j*2]=phase_ticks
        w[23]=10
        w[61]=zlib.crc32(struct.pack("<61I",*w[:61]))
        w[63]=subphase.DONE
        rows.append(struct.pack("<64I",*w))
    (capture/"reset_profile1024_physical.bin").write_bytes(b"".join(rows))
    return oracle,first16,capture

def test_complete_1024_original_frozen_scalar_and_new_reset_microprofile(
        synthetic_new_four_captures,tmp_path):
    oracle,first16,cap=synthetic_new_four_captures
    result=physical.structural_profile_check(
        oracle,first16,cap,tmp_path/"new_b44_untrusted.json")
    assert result["all_original_1024_neural_spike_vectors_and_trace_fnv_match_scalar"]
    assert result["new_original_27core_reset_profile_1024_records_structural_pass"]
    assert result["new_reset_profile_descriptive"]["n_ordinary"]==1023
    assert result["new_reset_profile_descriptive"][
        "actual_KV260_physical_provenance_independently_proven"] is False
    assert result["actual_profile_physical_KV260_numerical_accepted"] is False

@pytest.mark.parametrize("fault",[
    "wrong_neural_FNv","wrong_neural_crc","wrong_timing_crc",
    "wrong_profile_sha_count","wrong_profile_crc",
    "profile_missing_frame","wrong_terminal",
    "profile_subspans_exceed_reset",
])
def test_new_jtag_profile_precheck_rejects_corrupt_1024_data(
        synthetic_new_four_captures,tmp_path,fault):
    oracle,first16,cap=synthetic_new_four_captures
    files={
        "wrong_neural_FNv":"journal1024_physical.bin",
        "wrong_neural_crc":"journal1024_physical.bin",
        "wrong_timing_crc":"timing1024_physical.bin",
        "wrong_profile_sha_count":"reset_profile1024_physical.bin",
        "wrong_profile_crc":"reset_profile1024_physical.bin",
        "profile_missing_frame":"reset_profile1024_physical.bin",
        "profile_subspans_exceed_reset":"reset_profile1024_physical.bin",
        "wrong_terminal":"mailbox_terminal_physical.bin",
    }
    dest=cap/files[fault]
    raw=bytearray(dest.read_bytes())
    pos=512*256 if dest.name!="mailbox_terminal_physical.bin" else 0
    if fault=="profile_missing_frame":
        raw=raw[:-256]
    elif fault=="wrong_terminal":
        w=list(struct.unpack("<64I",raw))
        w[5]=1023
        raw=bytearray(struct.pack("<64I",*w))
    elif fault in ("wrong_neural_FNv","wrong_neural_crc","wrong_timing_crc","wrong_profile_crc"):
        offs={
            "wrong_neural_FNv":17*4,
            "wrong_neural_crc":61*4,
            "wrong_timing_crc":61*4,
            "wrong_profile_crc":61*4,
        }
        raw[pos+offs[fault]]^=1
    else:
        w=list(struct.unpack("<64I",raw[pos:pos+256]))
        if fault=="wrong_profile_sha_count":w[7]=26
        else:w[11]=2000
        w[61]=zlib.crc32(struct.pack("<61I",*w[:61]))
        raw[pos:pos+256]=struct.pack("<64I",*w)
    dest.write_bytes(raw)
    with pytest.raises((physical.NewProfileNoGo,subphase.ProfileNoGo,
                        numerical.FullRecordNoGo)):
        physical.structural_profile_check(
            oracle,first16,cap,tmp_path/"never.json")
    assert not (tmp_path/"never.json").exists(), "no combined report may be published before all 1024 neural AND profile rows validate"

def test_separate_independent_provenance_requires_authentic_receipts(tmp_path,monkeypatch):
    def fake_admission(_a):return {"schema":"synthetic"}
    monkeypatch.setattr(experimental:=independent.experimental,
                        "admission",fake_admission)
    evidence=tmp_path/"attempt"
    evidence.mkdir()
    out=tmp_path/"independent.json"
    args=argparse.Namespace(evidence=evidence,out=out)
    with pytest.raises((independent.ProfileAttestationNoGo,
                        KeyError,OSError)):
        independent.verify(args)
    assert not out.exists()

def test_independent_physical_jtag_4th_ddr_requires_all_real_markers():
    assert "profile1024_a53_physical_run.log" in independent.LOGS
    assert "six_original_ddr_physical_stage.log" in independent.LOGS
    assert "P08_B44_PROFILE1024_REAL_1024_RESET_PROFILE_SIDECAR_PHYSICAL_CAPTURED=1" in (
        independent.LOGS["profile1024_a53_physical_run.log"])
    assert independent.STAGE_OK if hasattr(independent,"STAGE_OK") else physical.STAGE_OK
