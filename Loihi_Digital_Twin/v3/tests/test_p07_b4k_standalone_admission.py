"""P07-B.4k strict native-only physical workflow checks. NO board access."""
from __future__ import annotations
from pathlib import Path
import shutil
import struct
import sys
from types import SimpleNamespace
from unittest.mock import patch
import pytest

V3=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(V3/"scripts"))
import p07_b4k_standalone_admission as k

def candidate():
    return {
        "entry":0,"loads":[(0,0x23A40)],
        "sha256":{"elf":k.ELF_SHA,"map":k.MAP_SHA,"p03_2_ps_mmio.xsa":"hashxsa"},
    }

def args(tmp_path):
    reports=tmp_path/"reports"
    reports.mkdir(exist_ok=True)
    return SimpleNamespace(
        build=tmp_path/"actual_vitis_build",reports=reports,
        evidence=tmp_path/"next_fresh_run",
        dedicated_jtag_owner="YES",cpu_takeover_approved="YES",
        low_ddr_destructive_overwrite_approved="YES",
        firmware_coexistence_risk_acknowledged="YES",
        mailbox_overwrite_approved="YES",pl_program_approved="YES",
        reboot_recovery_approved="YES"
    )

def physical_width():
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
        "P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1"
    ])+"\n"

def mailbox():
    return struct.pack("<16I",
        0x50374249,1,0x600D600D,0,0,0x00000A00,
        0x4C543302,0x00010000,0x0001031F,0,0,1,0,
        0x43FF0000,0,0xC0DEF00D)

def test_old_b4i_exact_elf_map_and_memspan_accept():
    with patch.object(k.b4i,"preflight",return_value=candidate()):
        value=k.offline_manifest(Path("/offline"),Path("/reports"))
    assert value["loads"]==[(0,0x23A40)]
    assert k.PT_LOAD[0][1] < 0x40000000

@pytest.mark.parametrize("changed",[
    {"entry":4},{"loads":[(0,0x23A41)]},
    {"loads":[(0,0x44000000)]},
    {"sha256":{"elf":"0"*64,"map":k.MAP_SHA}},
    {"sha256":{"elf":k.ELF_SHA,"map":"0"*64}}
])
def test_reject_wrong_elf_and_low_ddr_layout(changed):
    altered=candidate()
    altered.update(changed)
    with patch.object(k.b4i,"preflight",return_value=altered):
        with pytest.raises(ValueError,match="NO-GO"):
            k.offline_manifest(Path("/offline"),Path("/reports"))

@pytest.mark.parametrize("flag",list(k.APPROVALS))
def test_every_separate_destructive_approval_is_required_before_hardware(tmp_path,flag):
    a=args(tmp_path)
    setattr(a,flag,"NO")
    with patch.object(k.b4i,"log_call",side_effect=AssertionError("hardware must not run")):
        with pytest.raises(ValueError,match=flag.replace("_","-")):
            k.run_physical(a,candidate())
    assert not a.evidence.exists()

def test_fresh_evidence_directory_must_not_exist(tmp_path):
    a=args(tmp_path)
    a.evidence.mkdir()
    with patch.object(k.b4i,"log_call",side_effect=AssertionError("hardware must not run")):
        with pytest.raises(ValueError,match="new absolute"):
            k.run_physical(a,candidate())

def test_missing_tools_fails_before_physical_contact(tmp_path):
    a=args(tmp_path)
    with patch.object(k.shutil,"which",return_value=None):
        with patch.object(k.b4i,"log_call",side_effect=AssertionError("hardware must not run")):
            with pytest.raises(ValueError,match="hardware tool"):
                k.run_physical(a,candidate())
    assert not a.evidence.exists()

def test_standalone_physical_stages_and_independent_mailbox(tmp_path,capsys):
    a=args(tmp_path)
    calls=[]
    def fake_hw(argv,destination):
        calls.append((argv,destination))
        if len(calls)==1:
            destination.write_text(physical_width())
        elif len(calls)==2:
            destination.write_text(k.b4j.PASS_MARKER+"\n")
        elif len(calls)==3:
            assert destination.name=="a53_run.log"
            # XTCL is simulated: identity-proven read-only firmware mailbox.
            (a.evidence/"p07_b4k_mailbox_64.bin").write_bytes(mailbox())
            destination.write_text("P07_B4I_MAILBOX_CAPTURED_64_BYTES=1\n")
        elif len(calls)==4:
            assert "p07_b4i_verify_mailbox.py" in argv
            assert "--mailbox" in argv
            destination.write_text(
                "P07_B4I_PHYSICAL_READONLY_ADMISSION_PASS=1\n"
                "P07_B4I_TRAINED_B2_INFERENCE_VERIFIED=0\n"
            )
        else: raise AssertionError("unexpected extra action")
    with patch.object(k.shutil,"which",return_value="/fake/tool"),(
            patch.object(k.b4i,"log_call",side_effect=fake_hw)):
        k.run_physical(a,candidate())
    assert len(calls)==4
    assert calls[0][0][1]==k.b4j.TAKEOVER_TCL
    assert calls[1][0][4]==k.b4j.PROGRAM_TCL
    assert calls[2][0][1]=="vivado/p07_b4i_xsdb_run.tcl"
    assert calls[3][0][1]=="scripts/p07_b4i_verify_mailbox.py"
    assert (a.evidence/"mailbox_zero_64.bin").read_bytes()==bytes(64)
    assert (a.evidence/"p07_b4k_mailbox_64.bin").read_bytes()==mailbox()
    assert (a.evidence/"stage.txt").read_text().strip()==(
        "P07_B4K_STANDALONE_ADMISSION_VERIFIED_REBOOT_REQUIRED")
    assert "P07_B4K_REAL_STANDALONE_A53_ADMISSION_PASS=1" in capsys.readouterr().out

def test_width_failure_prevents_pl_program_and_a53(tmp_path,capsys):
    a=args(tmp_path)
    calls=[]
    def fake_hw(argv,dest):
        calls.append(argv)
        if len(calls)>1: raise AssertionError("programming should not occur")
        dest.write_text(physical_width().replace("0x00000A00","0x00002560"))
    with patch.object(k.shutil,"which",return_value="/fake/tool"),(
            patch.object(k.b4i,"log_call",side_effect=fake_hw)):
        with pytest.raises(ValueError,match="FPD_AXIFS_RAW"):
            k.run_physical(a,candidate())
    assert len(calls)==1
    assert not (a.evidence/"a53_run.log").exists()
    assert "P07_B4K_REBOOT_REQUIRED=1" in capsys.readouterr().out

def test_program_failure_prevents_a53(tmp_path):
    a=args(tmp_path)
    calls=[]
    def fake_hw(argv,dest):
        calls.append(argv)
        if len(calls)==1:dest.write_text(physical_width())
        elif len(calls)==2:dest.write_text("no Vivado success marker\n")
        else:raise AssertionError("forbidden A53 launch")
    with patch.object(k.shutil,"which",return_value="/fake/tool"),(
            patch.object(k.b4i,"log_call",side_effect=fake_hw)):
        with pytest.raises(ValueError,match="program"):
            k.run_physical(a,candidate())
    assert len(calls)==2

@pytest.mark.parametrize("bad_receipt",[
    bytes(63),
    struct.pack("<16I",
        0x50374249,1,0xDEAD0000,0,0,0x00000A00,
        0x4C543302,0x00010000,0x0001031F,0,0,1,0,
        0x43FF0000,0,0xC0DEF00D)
])
def test_bad_mailbox_never_causes_success_receipt(tmp_path,bad_receipt):
    a=args(tmp_path)
    calls=[]
    def fake_hw(argv,dest):
        calls.append(argv)
        if len(calls)==1:dest.write_text(physical_width())
        elif len(calls)==2:dest.write_text(k.b4j.PASS_MARKER+"\n")
        elif len(calls)==3:
            (a.evidence/"p07_b4k_mailbox_64.bin").write_bytes(bad_receipt)
            dest.write_text("capture completed\n")
        else:raise AssertionError("should not verify malformed readback")
    with patch.object(k.shutil,"which",return_value="/fake/tool"),(
            patch.object(k.b4i,"log_call",side_effect=fake_hw)):
        if len(bad_receipt)!=64:
            with pytest.raises(ValueError,match="64-byte mailbox"):
                k.run_physical(a,candidate())
        else:
            # The real external verifier performs strict 16-word validation.
            import p07_b4i_verify_mailbox as verifier
            with pytest.raises(ValueError):
                verifier.verify(bad_receipt)

def test_no_operator_note_and_no_inference_in_runner():
    text=(V3/"scripts/p07_b4k_standalone_admission.py").read_text()
    assert "--recovery-note" not in text
    assert "operator_note" not in text
    assert "B2 inference" in text
    assert 'default="preflight"' in text
    assert "firmware_coexistence_risk_acknowledged" in k.APPROVALS
