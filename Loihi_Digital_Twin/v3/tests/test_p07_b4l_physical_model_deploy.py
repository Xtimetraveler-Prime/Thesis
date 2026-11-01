"""P07-B.4l PC-only physical DDR model staging runner tests (NO hardware)."""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import shutil
import sys
from types import SimpleNamespace
from unittest.mock import patch
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b4l_physical_model_deploy as m
import p07_b4l1_stage_frozen_27core as b1


def fake_record_stage(tmp_path,monkeypatch):
    stage=tmp_path/"original_host_stage"
    stage.mkdir()
    index=[]
    image=hashlib.sha256()
    path=stage/b1.BUNDLE_NAME
    with path.open("wb") as f:
        for cid in range(27):
            data=bytes([cid])*b1.STRIDE
            image.update(data)
            f.write(data)
            index.append({
                "logical_core_id":cid,
                "physical_address":f"0x{0x40000000+cid*b1.STRIDE:08X}",
                "sha256":hashlib.sha256(data).hexdigest(),
            })
    sha=image.hexdigest()
    (stage/b1.INDEX_NAME).write_text(json.dumps({
        "bundle_sha256":sha,"records":index
    }))
    monkeypatch.setattr(m,"ACCEPTED_BUNDLE_SHA",sha)
    monkeypatch.setattr(b1,"verify_bundle",lambda frozen,staged:{
        "bundle_sha256":sha,"core_count":27,
        "bytes":14155776,"physical_start":"0x40000000",
        "physical_end_exclusive":"0x40D80000",
        "freeze_untouched":True,"board_visited":False,
    })
    return stage,index


def args(tmp_path):
    reports=tmp_path/"reports"
    reports.mkdir(exist_ok=True)
    return SimpleNamespace(
        frozen_dir=tmp_path/"original_frozen", staged_dir=tmp_path/"original_host_stage",
        reports=reports,evidence=tmp_path/"physical_board_evidence",
        dedicated_jtag_owner="YES",
        cpu_takeover_approved="YES",
        ddr_27core_overwrite_approved="YES",
        firmware_coexistence_risk_acknowledged="YES",
        pl_program_approved="YES",reboot_recovery_approved="YES",
    )


def takeover():
    return "\n".join([
        "P07_B4I_A53_0_STOP_COMMAND_PASS=1",
        "P07_B4I_A53_1_STOP_COMMAND_PASS=1",
        "P07_B4I_A53_2_POWERED_DOWN_OBSERVED=1",
        "P07_B4I_A53_3_POWERED_DOWN_OBSERVED=1",
        "P03_2C_PS_FPD_AXIFS_RAW=0x00000A00",
        "P03_2C_PS_FPD_HPM0_WIDTH_BITS=128",
        "P03_2C_PS_LPD_AXIFS_RAW=0x00000200",
        "P03_2C_PS_LPD_HPM0_WIDTH_BITS=128",
        "P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1",
    ])+"\n"


def test_first_stage_genuinely_authenticates_frozen_bundle_contract(tmp_path,monkeypatch):
    stage,index=fake_record_stage(tmp_path,monkeypatch)
    assert m.prepare_verified_contexts(tmp_path/"original_frozen",stage)["records"]==index
    with patch.object(b1,"verify_bundle",return_value={
        "bundle_sha256":"0"*64,"core_count":27,"bytes":14155776,
        "physical_start":"0x40000000","physical_end_exclusive":"0x40D80000",
        "freeze_untouched":True,"board_visited":False,
    }):
        with pytest.raises(m.DeployError,match="identity drift"):
            m.prepare_verified_contexts(tmp_path/"original_frozen",stage)


def test_exact_27_transfer_files_are_canonical_and_bounded(tmp_path,monkeypatch):
    stage,index=fake_record_stage(tmp_path,monkeypatch)
    work=tmp_path/"transfer"
    m.prep_transfer_files(stage,work,{"records":index})
    assert len(list(work.iterdir()))==27
    for i,row in enumerate(index):
        f=work/m.CORE_INPUT.format(i)
        assert f.stat().st_size==b1.STRIDE
        assert m.b4l1.file_sha(f)==row["sha256"]
    with pytest.raises(FileExistsError):
        m.prep_transfer_files(stage,work,{"records":index})


def test_complete_27_physical_readback_must_match_each_original_byte(tmp_path,monkeypatch):
    stage,index=fake_record_stage(tmp_path,monkeypatch)
    dest=tmp_path/"readback"
    dest.mkdir()
    with (stage/b1.BUNDLE_NAME).open("rb") as f:
        for i in range(27):
            (dest/m.CORE_READBACK.format(i)).write_bytes(f.read(b1.STRIDE))
    result=m.verify_physical_readback(stage,dest,{"records":index})
    assert result["byte_exact_core_count"]==27
    assert result["physical_readback_sha256"]==m.ACCEPTED_BUNDLE_SHA
    assert result["physical_inference_executed"] is False
    (dest/m.CORE_READBACK.format(24)).write_bytes(b"\x00"*b1.STRIDE)
    with pytest.raises(m.DeployError,match="core 24"):
        m.verify_physical_readback(stage,dest,{"records":index})


def test_no_silent_missing_extra_or_short_readbacks(tmp_path,monkeypatch):
    stage,index=fake_record_stage(tmp_path,monkeypatch)
    dest=tmp_path/"readback"
    dest.mkdir()
    (dest/"unexpected.txt").write_text("junk")
    with pytest.raises(m.DeployError,match="missing/extra"):
        m.verify_physical_readback(stage,dest,{"records":index})


@pytest.mark.parametrize("flag",m.APPROVALS)
def test_each_destructive_approval_required_without_hardware(tmp_path,flag):
    a=args(tmp_path)
    setattr(a,flag,"NO")
    with patch.object(m.b4i,"log_call",side_effect=AssertionError("hardware called")):
        with pytest.raises(m.DeployError,match=flag.replace("_","-")):
            m.run_physical(a,{"records":[]})
    assert not a.evidence.exists()


def test_no_evidence_overwrite(tmp_path):
    a=args(tmp_path)
    a.evidence.mkdir()
    with patch.object(m.b4i,"log_call",side_effect=AssertionError("hardware called")):
        with pytest.raises(m.DeployError,match="NEW absolute"):
            m.run_physical(a,{"records":[]})


def test_physical_hardware_calls_are_ordered_and_zero_inference(tmp_path,monkeypatch,capsys):
    staged,index=fake_record_stage(tmp_path,monkeypatch)
    a=args(tmp_path)
    states={0:"halted",1:"halted",2:"powered_down",3:"powered_down"}
    hardware=[]
    def fake_call(argv,dest):
        hardware.append(argv)
        if len(hardware)==1:
            assert argv[:2]==["xsdb",m.b4j.TAKEOVER_TCL]
            dest.write_text(takeover())
        elif len(hardware)==2:
            assert argv[:5]==["vivado","-mode","batch","-source",m.b4j.PROGRAM_TCL]
            dest.write_text(m.b4j.PASS_MARKER+"\n")
        elif len(hardware)==3:
            assert argv[:2]==["xsdb",m.CORE_TCL]
            assert "DEDICATED_27_DDR_OVERWRITE_APPROVED" in argv
            source=a.evidence/"transfer_inputs"
            destdir=a.evidence/"physical_readback"
            with dest.open("w") as log:
                for i in range(27):
                    shutil.copyfile(source/m.CORE_INPUT.format(i),
                                    destdir/m.CORE_READBACK.format(i))
                    log.write(f"P07_B4L_CORE_{i}_512K_PHYSICAL_READBACK_PASS=1\n")
                log.write("P07_B4L_ALL_27_DDR_CORE_READBACK_TCL_PASS=1\n")
        else:
            raise AssertionError("no additional invocation permitted")
    with patch.object(m.shutil,"which",return_value="/fake/tool"),(
            patch.object(m.b4i,"log_call",side_effect=fake_call)):
        result=m.run_physical(a,{"records":index})
    assert len(hardware)==3
    assert result["physical_readback_sha256"]==m.ACCEPTED_BUNDLE_SHA
    assert "ALL_27_ORIGINAL_FROZEN_P02_PHYSICAL_DDR_BYTE_EXACT_PASS" in (a.evidence/"stage.txt").read_text()
    assert "P07_B4L_PHYSICAL_PL_PAGE_IN_EXECUTED=0" in capsys.readouterr().out
    for argv in hardware:
        assert "p07_b4i_xsdb_run.tcl" not in argv
        assert "dow" not in argv
    assert (a.evidence/"independent_receipt.json").is_file()


def test_early_ps_width_failure_blocks_both_programming_and_ddr(tmp_path,monkeypatch):
    staged,index=fake_record_stage(tmp_path,monkeypatch)
    a=args(tmp_path)
    calls=[]
    def fake_hw(argv,dest):
        calls.append(argv)
        if len(calls)>1: raise AssertionError("no more hardware calls")
        dest.write_text(takeover().replace("0x00000A00","0x00002560"))
    with patch.object(m.shutil,"which",return_value="/fake/tool"),(
            patch.object(m.b4i,"log_call",side_effect=fake_hw)):
        with pytest.raises(ValueError,match="FPD"):
            m.run_physical(a,{"records":index})
    assert len(calls)==1
    assert not (a.evidence/"ddr_stage.log").exists()


def test_program_failure_blocks_ddr(tmp_path,monkeypatch):
    staged,index=fake_record_stage(tmp_path,monkeypatch)
    a=args(tmp_path)
    calls=[]
    def fake_hw(argv,dest):
        calls.append(argv)
        if len(calls)==1:dest.write_text(takeover())
        elif len(calls)==2:dest.write_text("no success marker\n")
        else:raise AssertionError("no DDR staging when P03 programming fails")
    with patch.object(m.shutil,"which",return_value="/fake/tool"),(
            patch.object(m.b4i,"log_call",side_effect=fake_hw)):
        with pytest.raises(ValueError,match="marker"):
            m.run_physical(a,{"records":index})
    assert len(calls)==2


def test_missing_dram_receipt_refuses_fake_tcl_success(tmp_path,monkeypatch):
    staged,index=fake_record_stage(tmp_path,monkeypatch)
    a=args(tmp_path)
    count=0
    def fake_hw(argv,dest):
        nonlocal count
        count+=1
        if count==1:dest.write_text(takeover())
        elif count==2:dest.write_text(m.b4j.PASS_MARKER+"\n")
        elif count==3:dest.write_text("unproven DDR stage\n")
    with patch.object(m.shutil,"which",return_value="/fake/tool"),(
            patch.object(m.b4i,"log_call",side_effect=fake_hw)):
        with pytest.raises(m.DeployError,match="receipt"):
            m.run_physical(a,{"records":index})
    assert not (a.evidence/"independent_receipt.json").exists()


def test_source_runner_has_no_operator_note_or_trained_dispatch():
    script=(ROOT/"scripts/p07_b4l_physical_model_deploy.py").read_text()
    assert "--recovery-note" not in script
    assert "operator_note" not in script
    assert 'default="preflight"' in script
    assert "p07_b4l_stage_27_ddr.tcl" in script
    assert "p07_b4i_xsdb_run.tcl" not in script
    assert "P07_B4L_PHYSICAL_PL_PAGE_IN_EXECUTED=0" in script


def test_real_ddr_stage_tcl_with_simulated_xsdb_and_all_27_records(tmp_path,monkeypatch):
    """Run the actual XSDB Tcl program using tclsh fake DAP/mrd/dow only."""
    import subprocess
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    staged,index=fake_record_stage(tmp_path,monkeypatch)
    input_dir=tmp_path/"inputs"
    m.prep_transfer_files(staged,input_dir,{"records":index})
    output_dir=tmp_path/"readback"
    output_dir.mkdir()
    script=tmp_path/"mock_xsdb.tcl"
    real_tcl=ROOT/"vivado/p07_b4l_stage_27_ddr.tcl"
    script.write_text(
        "set ::physical_target \"\"\n"
        "array set ::physical_memory {}\n"
        "proc connect {args} {puts MOCK_XSDB_CONNECTED; return ok}\n"
        "proc disconnect {} {puts MOCK_XSDB_DISCONNECTED; return ok}\n"
        'proc targets {args} {set ::physical_target [lindex $args end]; return ok}\n'
        "proc dow {args} {\n"
        '  if {[string first "PSU" $::physical_target] < 0} {error "CPU target forbidden"}\n'
        '  set ::physical_memory([lindex $args 2]) [lindex $args 1]\n'
        "  return ok\n"
        "}\n"
        "proc mrd {args} {\n"
        '  set dest [lindex $args 2]\n'
        '  set addr [lindex $args 3]\n'
        '  if {[lindex $args 4] != 131072} {error "bad word count"}\n'
        '  if {![info exists ::physical_memory($addr)]} {error "no DDR at address"}\n'
        "  file copy $::physical_memory($addr) $dest\n"
        "  return ok\n"
        "}\n"
        "set argc 4\n"
        f"set argv [list DEDICATED_27_DDR_OVERWRITE_APPROVED "
        f"{{{input_dir}}} {{{output_dir}}} tcp:127.0.0.1:3121]\n"
        f"source {{{real_tcl}}}\n"
    )
    proc=subprocess.run(["tclsh",str(script)],capture_output=True,text=True)
    assert proc.returncode==0,proc.stderr
    assert "P07_B4L_ALL_27_DDR_CORE_READBACK_TCL_PASS=1" in proc.stdout
    assert proc.stdout.count("_512K_PHYSICAL_READBACK_PASS=1")==27
    assert "P07_B4L_PHYSICAL_DDR_TARGET=PSU" in proc.stdout
    result=m.verify_physical_readback(staged,output_dir,{"records":index})
    assert result["physical_readback_sha256"]==m.ACCEPTED_BUNDLE_SHA


def test_real_tcl_fails_closed_without_connect_on_malformed_core(tmp_path):
    import subprocess
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    input_dir=tmp_path/"in"
    input_dir.mkdir()
    output=tmp_path/"out"
    output.mkdir()
    for core in range(27):
        (input_dir/m.CORE_INPUT.format(core)).write_bytes(bytes(512) if core==26 else bytes(b1.STRIDE))
    script=tmp_path/"reject.tcl"
    real_tcl=ROOT/"vivado/p07_b4l_stage_27_ddr.tcl"
    script.write_text(
        "proc connect {args} {puts MOCK_CONNECTED_UNEXPECTED}\n"
        "set argc 4\n"
        f"set argv [list DEDICATED_27_DDR_OVERWRITE_APPROVED "
        f"{{{input_dir}}} {{{output}}} tcp:127.0.0.1:3121]\n"
        f"source {{{real_tcl}}}\n"
    )
    proc=subprocess.run(["tclsh",str(script)],capture_output=True,text=True)
    assert proc.returncode!=0
    assert "core 26" in proc.stderr
    assert "MOCK_CONNECTED_UNEXPECTED" not in proc.stdout
