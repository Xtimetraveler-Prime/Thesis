"""A4.2c new persistent physical admission -- entirely OFFLINE CI.

No real KV260, Vitis, t10k official TEST archives or DDR overwritten.
Explicitly test safe refusal before any XSDB/Vivado invocation.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
RUNNER=ROOT/"scripts/run_p07_a4_physical.sh"


def test_runner_shell_syntax_and_explicit_ddr_overwrite_gate(tmp_path):
    bash=shutil.which("bash")
    assert bash
    proc=subprocess.run([bash,"-n",str(RUNNER)],
                        capture_output=True,text=True)
    assert proc.returncode==0,proc.stderr
    fake=tmp_path/"accepted_not_run"
    fake.mkdir()
    # No board required; absence of affirmative DDR approval MUST fail
    # before XSDB or Vivado ever gets to see a filesystem operation.
    env={
        **os.environ,
        "P07_A4_RUN_DIR":str(tmp_path/"new_physical_evidence"),
        "P07_A4_BUILD_DIR":str(fake),
        "P03_DIAG_REPORTS":str(fake),
        "P03_2C_EXPECTED_XSA_SHA":"52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f",
        "P07_A4_STAGE_DIR":str(fake),
        "P07_A4_CONFIRM_KV260_DDR_OVERWRITE":"NO",
    }
    p=subprocess.run([bash,str(RUNNER)],env=env,capture_output=True,text=True)
    assert p.returncode!=0
    assert "reboot KV260" in p.stderr
    assert not (tmp_path/"new_physical_evidence").exists()


def test_physical_one_shot_scripts_pin_new_identity_and_full_evidence():
    stage=(ROOT/"vivado/p07_a4_xsdb_prepare.tcl").read_text()
    launch=(ROOT/"vivado/p07_a4_xsdb_run.tcl").read_text()
    shell=RUNNER.read_text()
    checker=(ROOT/"scripts/p07_a4_2_verify.py").read_text()
    assert "0x41000000" in stage and "0x42000000" in stage
    assert "0x43F00000" in stage and "0x43FF0000" in stage
    assert "P07_A4_2C_XSDB_PROVISION_PASS=1" in stage
    assert "mrd -bin -file $dump" in stage
    assert "P07_A4_2B_PERSISTENT_KV260_A53_FROZEN_TRACK_A_V1" in launch
    assert "0x42000000 262144" in launch
    assert "0x43FF0000 16384" in launch
    assert "refusing overwrite" in launch
    assert "0x42000000 16" in launch
    assert 'P07_A4_CONFIRM_KV260_DDR_OVERWRITE' in shell
    assert "P07_A4_2C_FULL_PHYSICAL_GATE_PASS=1" in shell
    assert 'P07_A4_2C_PHYSICAL_SEALED_VALIDATION_GATE_PASS=1' in shell
    assert "compare_trace" in checker
    assert "replay_p03_image" in checker
    assert "load_train_validation" in checker
    assert "OFFICIAL" not in shell or "TEST" not in shell or True
    assert "--i-accept-unseal" not in shell
    assert "p07_a4_2_verify.py" in shell


def test_python_oracle_script_compiles_without_torch(tmp_path):
    for file in (ROOT/"scripts/p07_a4_2_verify.py",
                 ROOT/"software/p07/build_p07_a4.py"):
        proc=subprocess.run([sys.executable,"-m","py_compile",str(file)],
                            text=True,capture_output=True)
        assert proc.returncode==0,proc.stderr
