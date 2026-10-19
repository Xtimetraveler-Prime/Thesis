"""A3.2.2 physical capture gate; tests NEVER contact the KV260.

Synthetic verifier fixtures are UNIT ONLY: cannot establish hardware results.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p08_a3_2_single_check as single

RUNNER=ROOT/"scripts/run_p08_a3_2_1024.sh"


def env_for(tmp_path,mode="A2_1"):
    """Use sibling stage/build/route/evidence paths, like a valid real run.

    The physical runner intentionally rejects an evidence directory inside
    its immutable stage. Never weaken that protection to satisfy a fixture.
    """
    stage=tmp_path/"stage"
    stage.mkdir(exist_ok=True)
    return {
        **os.environ,
        "P08_A3_2_VARIANT":mode,
        "P08_A3_2_RUN_DIR":str(tmp_path/"not-created"),
        "P08_A3_2_STAGE_DIR":str(stage),
        "P08_A2_BUILD_DIR":str(tmp_path/"no-a21-build"),
        "P08_A2_2_BUILD_DIR":str(tmp_path/"no-a22-build"),
        "P03_DIAG_REPORTS":str(tmp_path/"no-p03-reports"),
    }


def call_runner(env):
    return subprocess.run(["bash",str(RUNNER)],cwd=ROOT,env=env,
                          capture_output=True,text=True)


def test_invalid_variant_blocks_without_hardware_or_output(tmp_path):
    env=env_for(tmp_path,"NO_SUCH_VARIANT")
    out=call_runner(env)
    assert out.returncode!=0 and "must be A2_1 or A2_2" in out.stderr
    assert not (tmp_path/"not-created").exists()


@pytest.mark.parametrize("mode",["A2_1","A2_2"])
def test_missing_explicit_three_consents_blocks_before_jtag(tmp_path,mode):
    env=env_for(tmp_path,mode)
    env.update({
        "P08_A3_2_CONFIRM_JTAG_ONLY":"YES",
        "P08_A3_2_CONFIRM_DDR_OVERWRITE":"YES",
    })
    env.pop("P08_A3_2_CONFIRM_TRAIN_VALIDATION_ONLY",None)
    env.pop("P08_A3_2_PREFLIGHT_ONLY",None)
    out=call_runner(env)
    assert out.returncode!=0 and "JTAG-only bare-metal" in out.stderr
    assert not (tmp_path/"not-created").exists()


@pytest.mark.parametrize("mode",["A2_1","A2_2"])
def test_offline_preflight_can_only_fail_closed_with_missing_artifacts(tmp_path,mode):
    env=env_for(tmp_path,mode)
    env["P08_A3_2_PREFLIGHT_ONLY"]="YES"
    for key in ("P08_A3_2_CONFIRM_JTAG_ONLY","P08_A3_2_CONFIRM_DDR_OVERWRITE",
                "P08_A3_2_CONFIRM_TRAIN_VALIDATION_ONLY"):
        env.pop(key,None)
    out=call_runner(env)
    assert out.returncode!=0 and "physical dependency missing" in out.stderr
    assert not (tmp_path/"not-created").exists()


@pytest.mark.parametrize("mode",["A2_1","A2_2"])
@pytest.mark.parametrize("source",["stage","build","route"])
def test_rejects_evidence_inside_immutable_source_before_hardware(tmp_path,mode,source):
    """Isolation is a real safety property, not a fixture false positive."""
    env=env_for(tmp_path,mode)
    parent={
        "stage":Path(env["P08_A3_2_STAGE_DIR"]),
        "build":Path(env["P08_A2_BUILD_DIR"] if mode=="A2_1" else env["P08_A2_2_BUILD_DIR"]),
        "route":Path(env["P03_DIAG_REPORTS"]),
    }[source]
    forbidden=parent/"nested-physical-run"
    env["P08_A3_2_RUN_DIR"]=str(forbidden)
    # Real physical consent flags must not override source/evidence isolation.
    env.pop("P08_A3_2_PREFLIGHT_ONLY",None)
    env.update({
        "P08_A3_2_CONFIRM_JTAG_ONLY":"YES",
        "P08_A3_2_CONFIRM_DDR_OVERWRITE":"YES",
        "P08_A3_2_CONFIRM_TRAIN_VALIDATION_ONLY":"YES",
    })
    result=call_runner(env)
    assert result.returncode!=0
    assert "must not overlap or live inside stage/build/route artifacts" in result.stderr
    assert not forbidden.exists()


def test_refuses_preexisting_output_before_jtag(tmp_path):
    run=tmp_path/"not-created"
    run.mkdir()
    got=call_runner(env_for(tmp_path))
    assert got.returncode!=0 and "never overwritten" in got.stderr
    assert list(run.iterdir())==[]


def test_a3_2_capture_requires_original_oracle_before_timing(monkeypatch,tmp_path):
    stream=SimpleNamespace(image_count=1024,trace_index=1023)
    monkeypatch.setattr(single,"sha",lambda _:single.ELF_A21_SHA256)
    monkeypatch.setattr(single,"validate_staging",lambda _:
        ({"scope":"TRAIN_DERIVED_VALIDATION_FIRST_1024"},stream))
    fake=[tmp_path/x for x in ("journal","trace","image")]
    monkeypatch.setattr(single,"verified_source",lambda *a:tuple(fake))
    called=[]
    def reject(*args):
        called.append("P07_original_oracle")
        raise ValueError("fake original packed-oracle failed")
    monkeypatch.setattr(single,"require_original_p07_oracle",reject)
    monkeypatch.setattr(single,"parse_journal",lambda *args:
        pytest.fail("timing/neural parsing invoked before P07 independent oracle"))
    with pytest.raises(ValueError,match="original packed-oracle"):
        single.check_single(tmp_path,tmp_path/"run","A2_1",tmp_path/"fake.elf")
    assert called==["P07_original_oracle"]


def test_rejects_non1024_validation_stage_before_p07_oracle(monkeypatch,tmp_path):
    monkeypatch.setattr(single,"sha",lambda _:single.ELF_A21_SHA256)
    monkeypatch.setattr(single,"validate_staging",lambda _:
        ({"scope":"TRAIN_DERIVED_VALIDATION_FIRST_16"},
         SimpleNamespace(image_count=16,trace_index=0)))
    monkeypatch.setattr(single,"require_original_p07_oracle",
                        lambda *a:pytest.fail("oracle ran on wrong stage"))
    with pytest.raises(ValueError,match="only frozen original TRAIN first1024"):
        single.check_single(tmp_path,tmp_path/"run","A2_1",tmp_path/"fake.elf")


def test_rejects_variant_sha_substitution(monkeypatch,tmp_path):
    monkeypatch.setattr(single,"sha",lambda _:single.ELF_A21_SHA256)
    with pytest.raises(ValueError,match="ELF SHA256 mismatch"):
        single.check_single(tmp_path,tmp_path/"run","A2_2",tmp_path/"fake.elf")
    with pytest.raises(ValueError,match="variant A2_1 or A2_2"):
        single.check_single(tmp_path,tmp_path/"run","BAD",tmp_path/"fake.elf")


@pytest.mark.parametrize("mode",["A2_1","A2_2"])
def test_single_run_offline_gate_returns_correct_scope_without_false_pair(monkeypatch,tmp_path,mode):
    stage=tmp_path/"stage"
    run=tmp_path/"run"
    stage.mkdir()
    run.mkdir()
    for file in ("p07_a4_descriptor_256.bin","p07_a4_mapping_1568.bin",
                 "p07_a4_pixels_raw.bin",
                 "p07_a4_2a_validation_labels_HOST_ONLY.json",
                 "p07_a4_2a_stage_manifest.json"):
        (stage/file).write_bytes(b"synthetic-unit-only")
    paths=[run/x for x in ("journal.bin","trace.bin","images.bin")]
    for f in paths:f.write_bytes(b"synthetic-unit-only")
    if mode=="A2_2":
        (run/"p08_a2_2_ticks_3m.bin").write_bytes(b"synthetic-unit-only")
    (run/"physical_identity.txt").write_text("synthetic unit only")
    (run/"a53_run.log").write_text("synthetic unit only")
    stream=SimpleNamespace(image_count=1024,trace_index=1023,
                           header=bytes(252)+bytes([1,2,3,4]))
    monkeypatch.setattr(single,"sha",lambda p:
        (single.ELF_A21_SHA256 if mode=="A2_1" else single.ELF_A22_SHA256)
        if p==tmp_path/"elf" else "fake-crc")
    monkeypatch.setattr(single,"validate_staging",lambda _:(
        {"scope":"TRAIN_DERIVED_VALIDATION_FIRST_1024"},stream))
    monkeypatch.setattr(single,"verified_source",lambda *a:tuple(paths))
    monkeypatch.setattr(single,"require_original_p07_oracle",lambda *a:None)
    monkeypatch.setattr(single,"parse_journal",lambda *a:tuple([0]*1024))
    timings=SimpleNamespace(count=1024,trace_index=1023,cntfrq_hz=99999001,
        records=tuple(SimpleNamespace(service_ticks=100000,
                                      pl_dispatch_cycles=1234) for _ in range(1024)))
    monkeypatch.setattr(single,"parse_timing",lambda *a,**k:timings)
    monkeypatch.setattr(single,"parse_ticks",lambda *a,**k:SimpleNamespace(ticks=(1,)))
    tested=[]
    monkeypatch.setattr(single,"validate_detailed_telemetry",
                        lambda *a:tested.append("A2_2_checked"))
    report=single.check_single(stage,run,mode,tmp_path/"elf")
    assert report["frame_count"]==1024
    assert report["original_independent_p07_oracle"]=="PASS_ALL_1024"
    assert report["physical_capture_single_run"]=="PASS"
    assert report["repeated_baseline"]=="NOT_ACCEPTED"
    assert report["paired_overhead"]=="NOT_YET_MEASURED"
    assert len(report["per_image_a53_service_ms"])==1024
    assert tested==(["A2_2_checked"] if mode=="A2_2" else [])


def test_physical_runner_contract_and_static_syntax():
    code=RUNNER.read_text()
    assert "PINNED_ELF_SHA=fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0" in code
    assert "PINNED_ELF_SHA=87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361" in code
    assert "P08_A3_2_2_OFFLINE_PREFLIGHT_PASS=1" in code
    assert "P08_A3_2_CONFIRM_JTAG_ONLY" in code
    assert "P08_A3_2_CONFIRM_DDR_OVERWRITE" in code
    assert "P08_A3_2_CONFIRM_TRAIN_VALIDATION_ONLY" in code
    assert "p07_a4_xsdb_prepare.tcl" in code
    assert "P08_A3_2_2_SINGLE_1024_FULL_PHYSICAL_GATE_PASS=1" in code
    assert "select_validation_prefix(split,1024)" in code
    assert "stream.trace_index!=1023" in code
    assert "P08_A3_2_2_POWER=DEFERRED" in (ROOT/"scripts/p08_a3_2_single_check.py").read_text()
    assert "official_TEST_population=NOT_USED" in code
    assert "P08_A3_2_2_PAIRED_BASELINE=NOT_YET_RUN" in code
    assert "P08_A2_1_KV260_STATUS=TERMINAL_BOTH_SUCCESS_UNVERIFIED_NUMERICS" in code
    assert "P08_A2_2_KV260_STATUS=TERMINAL_ALL_THREE_SUCCESS_UNVERIFIED_NUMERICS" in code
    assert "p08_a3_2_single_check.py" in code
    assert "RUN_REAL" in code and "STAGE_REAL" in code
    assert "BUILD_REAL" in code and "REPORTS_REAL" in code
    assert code.index("P08_A3_2_2_OFFLINE_PREFLIGHT_PASS=1") < code.index(
        "xsdb vivado/p03_2c_xsdb_ps_axi_width_diag.tcl"
    )
    assert "physical_identity.txt" in code
    assert "firmware_variant=$MODE" in code
    assert "p08_a3_1" not in code
    syntax=subprocess.run(["bash","-n",str(RUNNER)],
        capture_output=True,text=True)
    assert syntax.returncode==0,syntax.stderr
