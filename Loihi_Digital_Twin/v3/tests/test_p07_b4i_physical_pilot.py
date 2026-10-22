"""P07-B.4i: native safety and mailbox contract; no real board tools."""
from __future__ import annotations
from pathlib import Path
import importlib.util
import shutil
import struct
from types import SimpleNamespace
from unittest.mock import patch
import pytest

ROOT=Path(__file__).resolve().parents[1]

def module(name:str,path:str):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    assert spec and spec.loader
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

verify=module("b4i_verifier","scripts/p07_b4i_verify_mailbox.py")
pilot=module("b4i_pilot","scripts/p07_b4i_physical_pilot.py")
build=module("b4i_build","software/p07/build_p07_b4i.py")

def mailbox():
    return struct.pack("<16I",0x50374249,1,0x600D600D,0,0,0x00000A00,
                       0x4C543302,0x00010000,0x0001031F,0,0,1,0,
                       0x43FF0000,0,0xC0DEF00D)

def test_real_mailbox_contract_strict_16_words():
    v=verify.verify(mailbox())
    assert v["fpd"]==0xA00
    assert v["inference_authorized"]==0

@pytest.mark.parametrize("index,value",[
    (0,0),(1,2),(2,0xDEAD0000),(3,1),(4,0xFFFFFFFF),
    (5,0x2560),(6,0),(7,0),(8,0),(9,1),(10,1),
    (11,0),(12,1),(13,0x42000000),(14,1),(15,0),
])
def test_bad_mailbox_word_never_accepted(index,value):
    words=list(struct.unpack("<16I",mailbox()))
    words[index]=value
    with pytest.raises(ValueError):
        verify.verify(struct.pack("<16I",*words))

def test_truncated_mailbox_never_accepted():
    with pytest.raises(ValueError,match="64"):
        verify.verify(mailbox()[:-1])

READ_ELF="""ELF Header:
  Entry point address:               0x0
Program Headers:
  Type           Offset   VirtAddr           PhysAddr           FileSiz  MemSiz   Flg Align
  LOAD           0x000000 0x0000000000000000 0x0000000000000000 0x000100 0x000200 RWE 0x10000
"""
def test_entry_zero_is_risk_not_automatically_safe():
    entry,spans=pilot.parse_layout(READ_ELF)
    assert entry==0 and spans==[(0,0x200)]

def test_p02_intersect_is_no_go():
    text=READ_ELF.replace("0x0000000000000000 0x000100",
                          "0x0000000040000000 0x000100")
    # Force entry into the protected segment rather than reject only entry.
    text=text.replace("0x0\nProgram","0x40000000\nProgram")
    with pytest.raises(ValueError):
        pilot.parse_layout(text)

def test_wrong_entry_is_no_go():
    with pytest.raises(ValueError,match="entry not"):
        pilot.parse_layout(READ_ELF.replace("0x0\nProgram","0x2000\nProgram"))

def test_execution_missing_consent_performs_no_hardware(tmp_path):
    args=SimpleNamespace(
        dedicated_jtag_owner="NO",cpu_takeover_approved="NO",
        low_ddr_exclusive="NO",mailbox_overwrite_approved="NO",
        pl_program_approved="NO",reboot_recovery_approved="NO",
        evidence=tmp_path/"NEVER_CREATE")
    with patch.object(pilot,"log_call",side_effect=AssertionError("hardware called")):
        with pytest.raises(ValueError,match="six distinct"):
            pilot.run_physical(args,{"sha256":{},"entry":0,"loads":[(0,0x200)],"low_ddr_risk":True})
    assert not args.evidence.exists()

def test_no_operator_note_required_while_six_flags_remain_mandatory(tmp_path):
    evidence=tmp_path/"new_evidence"
    args=SimpleNamespace(
        dedicated_jtag_owner="YES",cpu_takeover_approved="YES",
        low_ddr_exclusive="YES",mailbox_overwrite_approved="YES",
        pl_program_approved="YES",reboot_recovery_approved="YES",
        evidence=evidence)
    manifest={"sha256":{"elf":"host-only-test"},
              "entry":0,"loads":[(0,145984)],"low_ddr_risk":True}
    with patch.object(pilot.subprocess,"run",return_value=SimpleNamespace(returncode=0)):
        with patch.object(pilot,"log_call",side_effect=RuntimeError("mock stop; no hardware called")):
            with pytest.raises(RuntimeError,match="mock stop"):
                pilot.run_physical(args,manifest)
    assert evidence.is_dir()
    assert "host-only-test" in (evidence/"manifest.txt").read_text()
    assert "--recovery-note" not in (ROOT/"scripts/p07_b4i_physical_pilot.py").read_text()

def test_distinct_stage_identity_negative(tmp_path):
    for name in build.SOURCES+build.HEADERS:
        (tmp_path/name).write_text(build.IDENTITY if name==build.SOURCES[0] else "fixture")
    build.check_stage(tmp_path)
    (tmp_path/"p07_b4i_readonly_mailbox_board.c").write_text("stale")
    with pytest.raises(ValueError,match="identity"):
        build.check_stage(tmp_path)
    (tmp_path/"p07_b4i_readonly_mailbox_board.c").write_text(build.IDENTITY)
    (tmp_path/"rogue.c").write_text("extra")
    with pytest.raises(ValueError,match="mismatch"):
        build.check_stage(tmp_path)

def test_tcl_only_runs_with_dedicated_owner_marker():
    tcl=(ROOT/"vivado/p07_b4i_xsdb_run.tcl").read_text()
    assert "DEDICATED_A53_DDR_OWNER_VERIFIED" in tcl
    assert "0x43FF0000" in tcl and "dow -data" in tcl
    assert "rst -processor" in tcl and "dow $elf" in tcl
    assert "mrd -bin -file" in tcl
    assert "P07_B4I_REBOOT_REQUIRED=1" in tcl

def test_preflight_source_stage_drift_detected(tmp_path):
    stage=tmp_path/"source"
    stage.mkdir()
    for file,original in pilot.REQUIRED_SOURCE.items():
        shutil.copy(ROOT/original,stage/file)
    (stage/"p03_hw_adapter.c").write_text("tampered")
    assert pilot.sha256(stage/"p03_hw_adapter.c")!=pilot.sha256(
        ROOT/pilot.REQUIRED_SOURCE["p03_hw_adapter.c"])

def test_run_mode_defaults_to_preflight():
    text=(ROOT/"scripts/p07_b4i_physical_pilot.py").read_text()
    assert 'default="preflight"' in text
    assert "P07_B4I_OFFLINE_ONLY_NO_BOARD_ACCESS=1" in text
    assert "P07_B4I_PHYSICAL_A53_LAUNCH_AUTHORIZED=0" in text


def test_build_shell_parses_without_vitis_or_board():
    import subprocess
    run=subprocess.run(["bash","-n",str(ROOT/"scripts/build_p07_b4i.sh")],
                       capture_output=True,text=True)
    assert run.returncode==0,run.stderr

def test_xsdb_tcl_without_dedicated_owner_never_connects():
    import subprocess
    import shutil
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh unavailable")
    tcl=ROOT/"vivado/p07_b4i_xsdb_run.tcl"
    run=subprocess.run(["tclsh",str(tcl)],capture_output=True,text=True)
    assert run.returncode!=0
    assert "DEDICATED_A53_DDR_OWNER_VERIFIED" in run.stderr

def test_b4i_c_builds_with_standalone_bsp_interface_stubs(tmp_path):
    import subprocess
    import shutil
    if shutil.which("gcc") is None:
        pytest.skip("GCC unavailable")
    (tmp_path/"xil_cache.h").write_text(
        "typedef unsigned long INTPTR;\n"
        "void Xil_DCacheFlushRange(INTPTR, unsigned);\n"
    )
    (tmp_path/"xil_printf.h").write_text(
        "int xil_printf(const char*, ...);\n"
    )
    command=[
        "gcc","-std=c11","-fsyntax-only","-Wall","-Wextra","-Werror",
        "-I",str(tmp_path),"-I",str(ROOT/"software/p07/include"),
        "-I",str(ROOT/"software/p03/include"),
        str(ROOT/"software/p07/p07_b4i_readonly_mailbox_board.c")
    ]
    result=subprocess.run(command,capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_b4i_takeover_gate_success_with_fake_xsdb(tmp_path):
    import subprocess
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh unavailable")
    gate=ROOT/"vivado/p07_b4i_stop_and_width_gate.tcl"
    wrapper=tmp_path/"good.tcl"
    wrapper.write_text(
        "proc connect {args} {return ok}\n"
        "proc disconnect {} {return ok}\n"
        "proc targets {args} {return ok}\n"
        "proc stop {} {return ok}\n"
        'proc mrd {args} {if {[lsearch $args 0xFD615000] >= 0} {return "FD615000: 00000A00"}; return "FF419000: 00000200"}\n'
        "set argc 2\nset argv {DEDICATED_DISCARD_LINUX_APPROVED tcp:127.0.0.1:3121}\n"
        f"source {{{gate}}}\n"
    )
    proc=subprocess.run(["tclsh",str(wrapper)],text=True,capture_output=True)
    assert proc.returncode==0,proc.stderr
    for i in range(4):
        assert f"P07_B4I_A53_{i}_STOP_COMMAND_PASS=1" in proc.stdout
    assert "P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1" in proc.stdout

def test_b4i_takeover_gate_refuses_failed_core_stop(tmp_path):
    import subprocess
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh unavailable")
    gate=ROOT/"vivado/p07_b4i_stop_and_width_gate.tcl"
    wrapper=tmp_path/"bad_stop.tcl"
    wrapper.write_text(
        "proc connect {args} {return ok}\n"
        "proc disconnect {} {return ok}\n"
        "proc targets {args} {return ok}\n"
        'proc stop {} {error "CPU halt refused"}\n'
        'proc mrd {args} {error "MUST NOT READ WHEN CPU STOP FAILED"}\n'
        "set argc 2\nset argv {DEDICATED_DISCARD_LINUX_APPROVED tcp:127.0.0.1:3121}\n"
        f"source {{{gate}}}\n"
    )
    proc=subprocess.run(["tclsh",str(wrapper)],text=True,capture_output=True)
    assert proc.returncode!=0
    assert "stop failed" in proc.stderr
    assert "P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1" not in proc.stdout

def test_b4i_takeover_script_is_used_before_bitstream_programming():
    physical=(ROOT/"scripts/p07_b4i_physical_pilot.py").read_text()
    assert "vivado/p07_b4i_stop_and_width_gate.tcl" in physical
    assert "vivado/p03_2c_xsdb_ps_axi_width_diag.tcl" not in physical
    assert physical.index("vivado/p07_b4i_stop_and_width_gate.tcl") < (
        physical.index("vivado/p03_2c_program_bitstream.tcl"))



def b4i_fake_tcl_stop(tmp_path, name, fail_core, fail_message):
    """Host Tcl simulation only; never invokes XSDB or KV260."""
    import subprocess
    gate=ROOT/"vivado/p07_b4i_stop_and_width_gate.tcl"
    wrapper=tmp_path/(name+".tcl")
    wrapper.write_text(
        "set ::selected \"\"\n"
        "proc connect {args} {return ok}\n"
        "proc disconnect {} {return ok}\n"
        "proc targets {args} {set ::selected [lindex $args end]; return ok}\n"
        "proc stop {} {\n"
        f"  if {{[string first \"Cortex-A53 #{fail_core}\" $::selected] >= 0}} {{error {{{fail_message}}}}}\n"
        "  return ok\n"
        "}\n"
        'proc mrd {args} {if {[lsearch $args 0xFD615000] >= 0} {return "FD615000: 00000A00"}; return "FF419000: 00000200"}\n'
        "set argc 2\n"
        "set argv {DEDICATED_DISCARD_LINUX_APPROVED tcp:127.0.0.1:3121}\n"
        f"source {{{gate}}}\n"
    )
    return subprocess.run(["tclsh",str(wrapper)],text=True,capture_output=True)

def test_secondary_explicit_power_down_is_not_fatal(tmp_path):
    import shutil
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh unavailable")
    run=b4i_fake_tcl_stop(tmp_path,"core1_down",1,"The core is powered down")
    assert run.returncode==0,run.stderr
    assert "P07_B4I_A53_1_POWERED_DOWN_OBSERVED=1" in run.stdout
    assert "P07_B4I_A53_1_STOP_COMMAND_PASS=1" not in run.stdout
    assert pilot.verify_takeover_log(run.stdout)=={
        0:"halted",1:"powered_down",2:"halted",3:"halted"
    }

def test_primary_power_down_is_always_fatal(tmp_path):
    import shutil
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh unavailable")
    run=b4i_fake_tcl_stop(tmp_path,"core0_down",0,"The core is powered down")
    assert run.returncode!=0
    assert "stop failed for Cortex-A53 #0" in run.stderr
    assert "P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1" not in run.stdout

@pytest.mark.parametrize("message",[
    "The core is powered down; but transport broke",
    "The core is powered down\nUnexpected failure",
    "The core is powered down on multiple cores",
    "JTAG timeout",
])
def test_secondary_unrecognized_errors_still_fatal(tmp_path,message):
    import shutil
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh unavailable")
    run=b4i_fake_tcl_stop(tmp_path,"unrecognized",1,message)
    assert run.returncode!=0
    assert "stop failed for Cortex-A53 #1" in run.stderr
    assert "P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1" not in run.stdout

def valid_b4i_takeover_log():
    return "\n".join([
        "P07_B4I_A53_0_STOP_COMMAND_PASS=1",
        "P07_B4I_A53_1_POWERED_DOWN_OBSERVED=1",
        "P07_B4I_A53_2_STOP_COMMAND_PASS=1",
        "P07_B4I_A53_3_POWERED_DOWN_OBSERVED=1",
        "P03_2C_PS_FPD_AXIFS_RAW=0x00000A00",
        "P03_2C_PS_FPD_HPM0_WIDTH_BITS=128",
        "P03_2C_PS_LPD_AXIFS_RAW=0x00000200",
        "P03_2C_PS_LPD_HPM0_WIDTH_BITS=128",
        "P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1",
    ])

def test_takeover_receipt_validates_mixed_states():
    assert pilot.verify_takeover_log(valid_b4i_takeover_log())=={
        0:"halted",1:"powered_down",2:"halted",3:"powered_down"
    }

@pytest.mark.parametrize("mutation",[
    lambda lines:[line for line in lines if "A53_1_POWERED" not in line],
    lambda lines:lines+["P07_B4I_A53_1_STOP_COMMAND_PASS=1"],
    lambda lines:lines+["P07_B4I_A53_0_POWERED_DOWN_OBSERVED=1"],
    lambda lines:lines+["P07_B4I_A53_2_STOP_COMMAND_PASS=1"],
    lambda lines:[line for line in lines if not line.endswith("PSWIDTH128_GATE_PASS=1")],
    lambda lines:lines+["P07_B4I_STOP_WIDTH_GATE_FAIL_REBOOT_REQUIRED=1"],
    lambda lines:[line.replace("0x00000A00","0x00002560") for line in lines],
])
def test_takeover_receipt_rejects_missing_contradictory_or_wrong_states(mutation):
    with pytest.raises(ValueError):
        pilot.verify_takeover_log("\n".join(mutation(valid_b4i_takeover_log().splitlines())))
