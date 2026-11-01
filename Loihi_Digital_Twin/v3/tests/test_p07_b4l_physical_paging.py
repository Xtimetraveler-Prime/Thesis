"""PC-only native contracts for integrated B4l 27-core real paging pilot."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b4l_physical_paging as p
import p07_b4l_physical_model_deploy as d
import p07_b4l1_stage_frozen_27core as b1

FAKE_HEX="ab"*32


def test_genuine_a53_load_identity_accepted_with_mocked_readelf(tmp_path):
    elf=tmp_path/"paging.elf"
    elf.write_bytes(p.ELF_ID.encode()+b"synthetic fixture not real ELF")
    elf.with_suffix(".map").write_text("Linker script and memory map\n.text\n.bss\nmain\n")
    sha=hashlib.sha256(elf.read_bytes()).hexdigest()
    readelf=("ELF Header:\n  Machine:                           AArch64\n"
             "  Entry point address:               0x0\n"
             "Program Headers:\n"
             "  LOAD  0x010000 0x0000000000000000 0x0000000000000000 "
             "0x010000 0x025000 RWE 0x10000\n")
    with patch.object(p.shutil,"which",return_value="/fake/readelf"),(
            patch.object(p.subprocess,"run",return_value=SimpleNamespace(
                returncode=0,stdout=readelf,stderr=""))):
        assert p.admit_real_elf(elf,sha)["load_end_exclusive"]==0x25000
    with patch.object(p.shutil,"which",return_value="/fake/readelf"),(
            patch.object(p.subprocess,"run",return_value=SimpleNamespace(
                returncode=0,stdout=readelf.replace("0x025000","0x02A000"),stderr=""))):
        with pytest.raises(p.PagingAdmissionError,match="envelope"):
            p.admit_real_elf(elf,sha)
    with pytest.raises(p.PagingAdmissionError,match="SHA"):
        p.admit_real_elf(elf,"0"*64)


def fixture(tmp_path,monkeypatch):
    stage=tmp_path/"b4l_staged"
    stage.mkdir()
    idx=[]
    image=hashlib.sha256()
    with (stage/b1.BUNDLE_NAME).open("wb") as file:
        for i in range(27):
            blob=bytes([i])*b1.STRIDE
            file.write(blob)
            image.update(blob)
            idx.append({"logical_core_id":i,"sha256":hashlib.sha256(blob).hexdigest(),
                        "physical_address":f"0x{0x40000000+i*b1.STRIDE:08X}"})
    monkeypatch.setattr(d,"ACCEPTED_BUNDLE_SHA",image.hexdigest())
    monkeypatch.setattr(b1,"file_sha",b1.file_sha)
    reports=tmp_path/"reports"
    reports.mkdir()
    return SimpleNamespace(
        frozen_dir=tmp_path/"frozen",staged_dir=stage,
        b4i_build=tmp_path/"old_b4i",reports=reports,
        elf=tmp_path/"paging.elf",expected_elf_sha=FAKE_HEX,
        evidence=tmp_path/"new_run",
        dedicated_jtag_owner="YES",cpu_takeover_approved="YES",
        low_ddr_destructive_overwrite_approved="YES",
        ddr_27core_overwrite_approved="YES",
        mailbox_overwrite_approved="YES",
        diagnostic_state_mutation_approved="YES",
        firmware_coexistence_risk_acknowledged="YES",
        pl_program_approved="YES",reboot_recovery_approved="YES",
    ),{"records":idx}


def takeover_log():
    return "\n".join((
        "P07_B4I_A53_0_STOP_COMMAND_PASS=1",
        "P07_B4I_A53_1_STOP_COMMAND_PASS=1",
        "P07_B4I_A53_2_POWERED_DOWN_OBSERVED=1",
        "P07_B4I_A53_3_POWERED_DOWN_OBSERVED=1",
        "P03_2C_PS_FPD_AXIFS_RAW=0x00000A00",
        "P03_2C_PS_FPD_HPM0_WIDTH_BITS=128",
        "P03_2C_PS_LPD_AXIFS_RAW=0x00000200",
        "P03_2C_PS_LPD_HPM0_WIDTH_BITS=128",
        "P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1",
    ))+"\n"


@pytest.mark.parametrize("flag",p.APPROVALS)
def test_flags_prevent_destructive_board_contact(tmp_path,monkeypatch,flag):
    args,index=fixture(tmp_path,monkeypatch)
    setattr(args,flag,"NO")
    with patch.object(p.b4i,"log_call",side_effect=AssertionError("hardware called")):
        with pytest.raises(p.PagingAdmissionError,match=flag.replace("_","-")):
            p.run_hardware(args,index,{"elf_sha256":FAKE_HEX})
    assert not args.evidence.exists()


def test_same_session_order_and_independent_ddr_and_page_receipt(tmp_path,monkeypatch):
    args,index=fixture(tmp_path,monkeypatch)
    args.elf.write_bytes(b"mock-elf")
    new_sha=hashlib.sha256(args.elf.read_bytes()).hexdigest()
    invoked=[]
    def mock_hw(argv,dest):
        invoked.append(argv)
        n=len(invoked)
        if n==1:
            assert argv[:2]==["xsdb",p.b4j.TAKEOVER_TCL]
            dest.write_text(takeover_log())
        elif n==2:
            assert argv[:2]==["vivado","-mode"]
            dest.write_text(p.b4j.PASS_MARKER+"\n")
        elif n==3:
            assert argv[:2]==["xsdb",d.CORE_TCL]
            for i in range(27):
                shutil.copyfile(args.evidence/"transfer_inputs"/d.CORE_INPUT.format(i),
                                args.evidence/"physical_readback"/d.CORE_READBACK.format(i))
            dest.write_text("\n".join(
                [f"P07_B4L_CORE_{i}_512K_PHYSICAL_READBACK_PASS=1" for i in range(27)]
                +["P07_B4L_ALL_27_DDR_CORE_READBACK_TCL_PASS=1"])+"\n")
        elif n==4:
            assert argv[:2]==["xsdb",p.TCL]
            assert (args.evidence/"ddr_verified.json").exists()
            (args.evidence/"paging_mailbox_256.bin").write_bytes(bytes(256))
            dest.write_text(
                "P07_B4L_A53_PAGING_ELF_DOWNLOADED=1\n"
                "P07_B4L_PAGE_PROBE_MAILBOX_CAPTURED_256_BYTES=1\n"
                "P07_B4L_A53_PAGING_CAPTURE_READY_FOR_INDEPENDENT_VERIFIER=1\n")
        elif n==5:
            assert argv[1]=="scripts/p07_b4l_verify_page_probe.py"
            dest.write_text("P07_B4L_PHYSICAL_27_CORE_3_SLOT_PAGE_DIRTY_SAVE_VERIFIED=1\n")
        else:
            raise AssertionError("unexpected XSDB/Vivado/hardware call")
    with patch.object(p.shutil,"which",return_value="/fake/tool"),(
            patch.object(p.b4i,"log_call",side_effect=mock_hw)):
        p.run_hardware(args,index,{"elf_sha256":new_sha})
    assert len(invoked)==5
    assert (args.evidence/"stage.txt").read_text().startswith(
        "REAL_A53_27_CORE_THREE_SLOT_PAGE_DIRTY_SAVE_PASS")
    assert "trained" not in (args.evidence/"a53_page_probe.log").read_text().lower()


def test_no_elf_without_complete_ddr_proof(tmp_path,monkeypatch):
    args,index=fixture(tmp_path,monkeypatch)
    invoked=[]
    def fake(argv,dest):
        invoked.append(argv)
        if len(invoked)==1:dest.write_text(takeover_log())
        elif len(invoked)==2:dest.write_text(p.b4j.PASS_MARKER+"\n")
        elif len(invoked)==3:dest.write_text("no real readback proof\n")
        else:raise AssertionError("ELF must NEVER download")
    with patch.object(p.shutil,"which",return_value="/fake/tool"),(
            patch.object(p.b4i,"log_call",side_effect=fake)):
        with pytest.raises(p.PagingAdmissionError,match="DDR Tcl stage"):
            p.run_hardware(args,index,{"elf_sha256":FAKE_HEX})
    assert len(invoked)==3
    assert not (args.evidence/"a53_page_probe.log").exists()


def test_actual_paging_xsdb_tcl_success_with_mock_debugger(tmp_path):
    if not shutil.which("tclsh"):pytest.skip("tclsh unavailable")
    elf=tmp_path/"fake.elf"
    elf.write_text(p.ELF_ID)
    zeros=tmp_path/"zeros.bin"
    zeros.write_bytes(bytes(256))
    output=tmp_path/"mailbox.bin"
    real=ROOT/"vivado/p07_b4l_xsdb_page_probe_run.tcl"
    script=tmp_path/"run.tcl"
    script.write_text(
        "set ::running 0\nset ::stops 0\n"
        'proc connect {args} {return ok}\n'
        'proc disconnect {} {return ok}\n'
        'proc targets {args} {return ok}\n'
        'proc stop {} {incr ::stops; if {$::stops==1} {error "Already stopped"};return ok}\n'
        'proc rst {args} {puts "MOCK_RESET=1";return ok}\n'
        'proc dow {args} {puts "MOCK_DOWNLOAD=1";return ok}\n'
        'proc con {} {set ::running 1;return ok}\n'
        'proc after {args} {return ok}\n'
        'proc mrd {args} {\n'
        '  set file [lindex $args 2]\n'
        '  set f [open $file wb]\n'
        '  fconfigure $f -translation binary -encoding binary\n'
        '  if {$::running} {\n'
        '    puts -nonewline $f "[string repeat \\x00 252][binary format H* 0df0dec0]"\n'
        '  } else {puts -nonewline $f [string repeat \\x00 256]}\n'
        '  close $f\n'
        '  return ok\n'
        '}\n'
        "set argc 5\n"
        f"set argv [list B4L_SAME_SESSION_27_DDR_EXCLUSIVE_OPERATOR_APPROVED "
        f"{{{elf}}} {{{zeros}}} {{{output}}} tcp:127.0.0.1:3121]\n"
        f"source {{{real}}}\n"
    )
    completed=subprocess.run(["tclsh",str(script)],text=True,capture_output=True)
    assert completed.returncode==0,completed.stderr
    assert "P07_B4L_A53_PAGING_ELF_DOWNLOADED=1" in completed.stdout
    assert "P07_B4L_PAGE_PROBE_MAILBOX_CAPTURED_256_BYTES=1" in completed.stdout
    assert output.is_file() and output.stat().st_size==256


def test_same_session_tcl_only_and_no_old_elf_script():
    source=(ROOT/"scripts/p07_b4l_physical_paging.py").read_text()
    assert "p07_b4l_stage_27_ddr" not in source or "deploy.CORE_TCL" in source
    assert "P07_B4L_PAGE_PROBE_MAILBOX_CAPTURED_256_BYTES=1" in source
    assert "--recovery-note" not in source
    assert 'default="preflight"' in source
    assert "p07_b4i_xsdb_run.tcl" not in source
