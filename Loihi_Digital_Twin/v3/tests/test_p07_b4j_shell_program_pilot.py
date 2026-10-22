"""P07-B.4j native-only shell-program checkpoint, never contacts hardware."""
from __future__ import annotations
from pathlib import Path
import importlib.util
import json
import sys
from types import SimpleNamespace
from unittest.mock import patch
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b4j_shell_program_pilot as j

B4I_ELF_SHA="5fcdb0586564f3abef477804a54e0a87163c74654f9d15d1f9600ab2cb85e807"
B4I_MAP_SHA="4deb41d9f47bd397ced6a15027b83b74f1d689f25220088bce62e5d2363551ad"

def manifest():
    return {"sha256":{"elf":B4I_ELF_SHA,"map":B4I_MAP_SHA},
            "entry":0,"loads":[(0,145984)]}

def log_ok():
    return "\n".join([
        "P07_B4I_A53_0_STOP_COMMAND_PASS=1",
        "P07_B4I_A53_1_STOP_COMMAND_PASS=1",
        "P07_B4I_A53_2_POWERED_DOWN_OBSERVED=1",
        "P07_B4I_A53_3_POWERED_DOWN_OBSERVED=1",
        "P07_B4I_PS_WIDTH_TARGET=PSU",
        "P03_2C_PS_FPD_AXIFS_RAW=0x00000A00",
        "P03_2C_PS_FPD_HPM0_WIDTH_BITS=128",
        "P03_2C_PS_LPD_AXIFS_RAW=0x00000200",
        "P03_2C_PS_LPD_HPM0_WIDTH_BITS=128",
        "P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1",
    ])+"\n"

def args(tmp_path):
    note=tmp_path/"owner_recovery.txt"
    note.write_text("Dedicated JTAG-only physical experiment; no other board users. "
                    "Discard Linux, do not resume stopped kernels, power-cycle after. "
                    "No ELF/DDR access approved for this shell-only checkpoint.")
    reports=tmp_path/"reports"
    reports.mkdir()
    return SimpleNamespace(
        build=tmp_path/"build",reports=reports,
        dedicated_jtag_owner="YES",cpu_takeover_approved="YES",
        pl_program_approved="YES",reboot_recovery_approved="YES",
        recovery_note=note,evidence=tmp_path/"evidence"
    )

def test_result_requires_exact_program_marker():
    j.require_programmed_shell(j.PASS_MARKER+"\n")

@pytest.mark.parametrize("body",[
    "", "WARNING: PL programming attempted","PASS: something else",
    j.PASS_MARKER+"\n"+j.PASS_MARKER
])
def test_no_fabric_pass_without_unique_marker(body):
    with pytest.raises(ValueError,match="marker"):
        j.require_programmed_shell(body)

def test_physical_approvals_required_before_evidence_or_hw(tmp_path):
    for approval in j.APPROVAL_FLAGS:
        a=args(tmp_path)
        setattr(a,approval,"NO")
        with patch.object(j.b4i,"log_call",side_effect=AssertionError("hardware called")):
            with pytest.raises(ValueError,match=approval):
                j.execute(a,manifest())
        assert not a.evidence.exists()

def test_owner_note_required_before_hardware(tmp_path):
    a=args(tmp_path)
    a.recovery_note=None
    with patch.object(j.b4i,"log_call",side_effect=AssertionError("hardware called")):
        with pytest.raises(ValueError,match="note"):
            j.execute(a,manifest())
    assert not a.evidence.exists()

def test_out_of_repo_fresh_evidence_refusal(tmp_path):
    a=args(tmp_path)
    a.evidence.mkdir()
    with patch.object(j.b4i,"log_call",side_effect=AssertionError("hardware called")):
        with pytest.raises(ValueError,match="NEW absolute"):
            j.execute(a,manifest())

def test_elf_sha_and_layout_drift_prevent_hardware(tmp_path):
    for change in ({"entry":4},{"loads":[(0,145983)]},
                   {"sha256":{"elf":"f"*64,"map":B4I_MAP_SHA}},
                   {"sha256":{"elf":B4I_ELF_SHA,"map":"e"*64}}):
        a=args(tmp_path)
        m=manifest()
        m.update(change)
        with patch.object(j.b4i,"log_call",side_effect=AssertionError("hardware called")),(
                patch.object(j.shutil,"which",return_value="/test/tool")):
            with pytest.raises(ValueError,match="NO-GO"):
                j.execute(a,m)
        assert not a.evidence.exists()

def test_shell_only_sequence_and_no_ddr_or_elf(tmp_path):
    a=args(tmp_path)
    operations=[]
    def simulated_hardware(command,dest):
        operations.append((command,dest))
        if len(operations)==1:
            dest.write_text(log_ok())
        else:
            dest.write_text(j.PASS_MARKER+"\n")
    with patch.object(j.b4i,"log_call",side_effect=simulated_hardware),(
            patch.object(j.shutil,"which",return_value="/test/tool")):
        j.execute(a,manifest())
    assert len(operations)==2
    assert operations[0][0][:2]==["xsdb",j.TAKEOVER_TCL]
    assert operations[1][0][:5]==["vivado","-mode","batch","-source",j.PROGRAM_TCL]
    for argv,_ in operations:
        command=" ".join(argv)
        assert " dow " not in " "+command+" "
        assert "p07_b4i_xsdb_run" not in command
        assert "43FF0000" not in command
    result=(a.evidence/"result.txt").read_text()
    assert "P07_B4J_PHYSICAL_SHELL_PROGRAM_VIO_RESET_PASS=1" in result
    assert "P07_B4J_A53_ELF_DOWNLOADED=0" in result
    assert "P07_B4J_DDR_MAILBOX_TOUCHED=0" in result
    provenance=json.loads((a.evidence/"provenance.json").read_text())
    assert provenance["no_ddr_access"] is True
    assert provenance["no_elf_download"] is True

def test_bad_real_cpu_or_width_log_prevents_bitstream_program(tmp_path):
    a=args(tmp_path)
    operations=[]
    def fake_hardware(command,dest):
        operations.append(command)
        if len(operations)>1: raise AssertionError("programming must be blocked")
        dest.write_text(log_ok().replace("0x00000A00","0x00002560"))
    with patch.object(j.b4i,"log_call",side_effect=fake_hardware),(
            patch.object(j.shutil,"which",return_value="/test/tool")):
        with pytest.raises(ValueError,match="FPD_AXIFS"):
            j.execute(a,manifest())
    assert len(operations)==1
    assert not (a.evidence/"result.txt").exists()

def test_program_tool_failure_keeps_evidence_and_requires_reboot(tmp_path,capsys):
    a=args(tmp_path)
    count=0
    def fake_hardware(command,dest):
        nonlocal count
        count+=1
        if count==1: dest.write_text(log_ok())
        else:
            dest.write_text("Vivado error: cannot program FPGA\n")
            raise RuntimeError("Vivado program failed")
    with patch.object(j.b4i,"log_call",side_effect=fake_hardware),(
            patch.object(j.shutil,"which",return_value="/test/tool")):
        with pytest.raises(RuntimeError):
            j.execute(a,manifest())
    assert count==2
    assert (a.evidence/"ps_width.log").exists()
    assert (a.evidence/"program.log").exists()
    assert not (a.evidence/"result.txt").exists()
    assert "P07_B4J_REBOOT_REQUIRED=1" in capsys.readouterr().out

def test_default_mode_is_nonhardware_and_pins_artifacts():
    text=(ROOT/"scripts/p07_b4j_shell_program_pilot.py").read_text()
    assert 'choices=("preflight","execute"),default="preflight"' in text
    assert "b4i.preflight(args.build,args.reports)" in text
    assert "P07_B4J_OFFLINE_ONLY_NO_HARDWARE_ACCESS=1" in text
    assert "p03_2c_program_bitstream.tcl" in text
    assert "p07_b4i_stop_and_width_gate.tcl" in text
