"""A3.1 pre-hardware gate tests. Never connect to KV260 or use official TEST.

Mocked timing input is UNIT-ONLY; this suite must never claim physical PASS.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts import p08_a3_1_verify as verifier

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("approval", [None,"NO",""])
def test_physical_runner_denies_without_three_explicit_approvals(tmp_path,approval):
    run=tmp_path/"unused-physical-run"
    stage=tmp_path/"stage"
    stage.mkdir()
    env={
        **os.environ,
        "P08_A3_1_RUN_DIR":str(run),
        "P08_A2_2_BUILD_DIR":str(tmp_path/"fake-build"),
        "P03_DIAG_REPORTS":str(tmp_path/"fake-reports"),
        "P08_A3_1_STAGE_DIR":str(stage),
        "P08_A3_1_EXPECTED_ELF_SHA256":"0"*64,
    }
    # Even two approvals must never permit a hardware probe.
    env["P08_A3_1_CONFIRM_JTAG_ONLY"]="YES"
    env["P08_A3_1_CONFIRM_DDR_OVERWRITE"]="YES"
    if approval is None:
        env.pop("P08_A3_1_CONFIRM_TRAIN_VALIDATION_ONLY",None)
    else:
        env["P08_A3_1_CONFIRM_TRAIN_VALIDATION_ONLY"]=approval
    got=subprocess.run(["bash",str(ROOT/"scripts/run_p08_a3_1_pilot.sh")],
                       cwd=ROOT,env=env,text=True,capture_output=True)
    assert got.returncode!=0
    assert "bare-metal JTAG-only" in got.stderr
    assert not run.exists()


def test_a3_1_invalid_population_refused_before_oracle(monkeypatch,tmp_path):
    called=[]
    stream=SimpleNamespace(image_count=128)
    monkeypatch.setattr(verifier,"validate_staging",
        lambda _stage:({"scope":"TRAIN_DERIVED_VALIDATION_FIRST_128"},stream))
    monkeypatch.setattr(verifier.subprocess,"run",
        lambda *a,**k:called.append(True))
    with pytest.raises(ValueError,match="first-16"):
        verifier.validate_evidence(tmp_path,tmp_path/"journal",
                                  tmp_path/"trace",tmp_path/"images",
                                  tmp_path/"ticks")
    assert not called


@dataclass(frozen=True)
class FakeTick:
    frame:int
    tick:int
    external_events:int=0
    emitted_packets:int=1
    acknowledged_packets:int=1


def test_a3_1_crosscheck_when_raw_is_already_parsed(monkeypatch,tmp_path):
    # A pure mocked unit test: does NOT run the P07 packed oracle and
    # must explicitly report physical acceptance FALSE.
    class Stream:
        image_count=16
        trace_index=0
        header=bytes(252)+bytes.fromhex("78563412")
        def image(self,index):
            return bytes(784)
    stage=tmp_path/"stage"
    stage.mkdir()
    for file in ("p07_a4_descriptor_256.bin","p07_a4_mapping_1568.bin",
                 "p07_a4_pixels_raw.bin","p07_a4_2a_stage_manifest.json"):
        (stage/file).write_bytes(b"unit-only")
    datafiles=[tmp_path/n for n in ("journal","trace","image","tick")]
    for f in datafiles:f.write_bytes(b"unit-only")
    orig=[SimpleNamespace(routes=25,discarded=2,external_events=0)
          for _ in range(16)]
    image=SimpleNamespace(
        count=16, trace_index=0, cntfrq_hz=100000000,
        dataset_start=1,dataset_stop=10000,
        records=[SimpleNamespace(index=i,service_ticks=100,pl_dispatch_cycles=200)
                 for i in range(16)])
    tickrecords=[
        SimpleNamespace(frame=i,tick=t,external_events=0,
                        emitted_packets=2 if t==25 else 1,
                        acknowledged_packets=2 if t==25 else 1,
                        source_ticks=1,bank_ticks=2,dispatch_wrapper_ticks=3,
                        trace_ticks=4,route_ticks=5,barrier_ticks=6)
        for i in range(16) for t in range(26)
    ]
    timed=SimpleNamespace(count=16,ticks=tuple(tickrecords))
    monkeypatch.setattr(verifier,"validate_staging",
                        lambda s:({"scope":"TRAIN_DERIVED_VALIDATION_FIRST_16"},Stream()))
    monkeypatch.setattr(verifier,"parse_journal",lambda a,b:tuple(orig))
    monkeypatch.setattr(verifier,"parse_timing",
                        lambda *a,**k:image)
    monkeypatch.setattr(verifier,"parse_ticks",
                        lambda *a,**k:timed)
    summary=verifier.validate_evidence(stage,*datafiles,oracle_proof=False)
    assert summary["completed_frames"]==16
    assert summary["physical_latency_accepted"] is False
    assert summary["p07_independent_oracle_parity"]=="NOT_RUN_UNIT_TEST_ONLY"
    assert summary["tick_input_route_drain_crosschecks"]=="PASS"
    assert summary["pl_counter_vs_26tick_sum"]=="PASS"

    # Change just one per-tick route acknowledgment to force a hard failure.
    tickrecords[0].acknowledged_packets=0
    with pytest.raises(ValueError,match="packet acknowledgement"):
        verifier.validate_evidence(stage,*datafiles,oracle_proof=False)


def test_a3_1_explicit_original_oracle_failure_refuses_latency(monkeypatch,tmp_path):
    stream=SimpleNamespace(image_count=16)
    monkeypatch.setattr(verifier,"validate_staging",
                        lambda s:({"scope":"TRAIN_DERIVED_VALIDATION_FIRST_16"},stream))
    monkeypatch.setattr(verifier.subprocess,"run",
                        lambda *a,**k:SimpleNamespace(returncode=1,
                            stdout="NOT_A_PHYSICAL_PASS\n",stderr="neural mismatch"))
    with pytest.raises(ValueError,match="independent packed replay"):
        verifier.validate_evidence(tmp_path,tmp_path/"journal",tmp_path/"trace",
                                  tmp_path/"image",tmp_path/"tick")


def test_a3_1_contract_keeps_power_deferred_and_never_runs_official_test():
    shell=(ROOT/"scripts/run_p08_a3_1_pilot.sh").read_text()
    assert "TRAIN_DERIVED_VALIDATION_FIRST_16" in shell
    assert "P08_A3_1_CONFIRM_JTAG_ONLY" in shell
    assert "P08_A3_1_CONFIRM_DDR_OVERWRITE" in shell
    assert "P08_A3_1_CONFIRM_TRAIN_VALIDATION_ONLY" in shell
    assert "P08_A3_1_EXPECTED_ELF_SHA256" in shell
    assert "P08_A2_2_ELF_SHA256=" in shell
    assert "p08_a3_1_verify.py" in shell
    assert "p07_a4_xsdb_prepare.tcl" in shell
    assert "p08_a2_2_xsdb_run.tcl" in shell
    assert "P08_A3_1_POWER=DEFERRED" in (ROOT/"scripts/p08_a3_1_verify.py").read_text()
    parsed=subprocess.run(["bash","-n",str(ROOT/"scripts/run_p08_a3_1_pilot.sh")],
                          text=True,capture_output=True)
    assert parsed.returncode==0,parsed.stderr
