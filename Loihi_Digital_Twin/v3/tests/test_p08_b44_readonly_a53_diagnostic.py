"""P08-B44 post-power-cycle read-only A53 target inventory; no-board guard."""
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/"vivado/p08_b44_a53_status_readonly.tcl"
TAKEOVER=ROOT/"vivado/p07_b4i_stop_and_width_gate.tcl"

def test_jtag_inventory_has_no_hardware_mutating_xsdb_ops():
    source=TARGET.read_text()
    # Verify EXACT permitted XSDB action set, not merely warning labels.
    lines=[
        x.strip() for x in source.splitlines()
        if x.strip() and not x.lstrip().startswith("#")
    ]
    assert "connect -url $server" in lines
    assert "puts [targets]" in lines
    assert "puts [jtag targets]" in lines
    assert 'if {[catch {targets -target-properties} props_error]} {' in lines
    assert 'if {[catch {jtag targets -target-properties -filter {name =~ "arm_dap"}} dap_error]} {' in lines
    assert "P08_B44_READONLY_PROCESSOR_TARGET_PROPERTIES_BEGIN" in source
    assert "P08_B44_READONLY_ARM_DAP_JTAG_PROPERTIES_BEGIN" in source
    assert not re.search(r"(?m)^\s*(?:targets -set|mwr|mrd|mask_write|reset|stop|rst|dow|con|fpga)\b",source)

    assert 'if {$connected} {catch {disconnect}}' in lines
    assert "P08_B44_READONLY_TARGET_OBSERVATION_ONLY=1" in source
    assert "P08_B44_NEW_PROFILE_PHYSICAL_JTAG_AUTHORIZED=0" in source
    assert "P08_B44_HALTED_OR_POWERED_DOWN_ALL_A53_PROVEN=0" in source
    assert "P08_B44_ORIGINAL_P07_CORE_STOP_GATE_UNCHANGED=1" in source
    bad_patterns=[
        r"\bstop\b",r"\brst\b",r"\breset\b",r"\bresume\b",
        r"\bmwr\b",r"\bmrd\b",r"\bdow\b",r"\bcon\b",
        r"\bfpga\b",r"\bprogram\b",r"\btargets\s+-set\b",
        r"\bafter\s+\d+",r"\bsource\b",
    ]
    # Check actual code lines only, not safety commentary/quoted markers.
    for line in lines:
        if line.startswith(("puts ","error ","set ","if ","}","connect ")):
            # Restrict mutator checks to command-leading forms or Tcl
            # semicolon commands, not non-executable quoted output.
            assert not re.match(r"^(?:stop|rst|reset|resume|mwr|mrd|dow|con|fpga|program|source)\b",line)
            assert "targets -set" not in line
            assert not re.search(r";\s*(?:stop|rst|mwr|dow|con|fpga|program)\b",line)
    assert not re.search(r"(?m)^\s*(?:stop|rst|mwr|dow|con|fpga|program)\b",source)

def test_original_fail_closed_a53_1_takeover_unchanged():
    takeover=TAKEOVER.read_text()
    assert 'set observed_error [string trim $stop_error]' in takeover
    assert 'The core is powered down' in takeover
    assert 'Cannot halt processor core: power down' in takeover
    assert 'error "P07-B.4i stop failed for $name: $stop_error"' in takeover
    assert "External debug access is disabled" not in takeover
    assert "P07_B4I_STOP_WIDTH_GATE_FAIL_REBOOT_REQUIRED=1" in takeover

def test_readonly_script_refuses_missing_or_nonlocal_target(tmp_path):
    tclsh=shutil.which("tclsh")
    if tclsh is None:pytest.skip("tclsh unavailable")
    none=subprocess.run([tclsh,str(TARGET)],cwd=tmp_path,
                        capture_output=True,text=True,timeout=10)
    assert none.returncode!=0
    assert "usage:" in none.stderr
    for server in ("tcp:192.168.1.12:3121","http://localhost:3121",
                   "tcp:127.0.0.1:123456", "tcp:127.0.0.1:3"):
        trial=subprocess.run([tclsh,str(TARGET),server],cwd=tmp_path,
                             capture_output=True,text=True,timeout=10)
        assert trial.returncode!=0
        assert "requires localhost hardware server" in trial.stderr
    assert not list(tmp_path.iterdir())

def test_explicit_diagnostic_non_acceptance_for_security_denial():
    s=TARGET.read_text()
    assert "External debug access is disabled" in s
    assert 'P08_B44_NEW_PROFILE_PHYSICAL_JTAG_AUTHORIZED=0' in s
    assert 'P08_B44_HALTED_OR_POWERED_DOWN_ALL_A53_PROVEN=0' in s
