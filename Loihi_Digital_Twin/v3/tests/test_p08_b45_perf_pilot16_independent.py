"""P08-B4.5 independent pilot16 reviewer fail-closed host-only negative gates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p08_b45_perf_pilot16_independent_verify as review


@pytest.fixture
def setup(tmp_path, monkeypatch):
    evidence=tmp_path/"physical"
    evidence.mkdir()
    out=tmp_path/"independent.json"
    args=argparse.Namespace(
        evidence=evidence, out=out, experiment="once", stage=tmp_path/"stage",
        first16=tmp_path/"oracle.json",b3_report=tmp_path/"b3.json",
        build=tmp_path/"build",original_elf=tmp_path/"b2.elf",
        reset_pins=tmp_path/"pins",reports=tmp_path/"reports",
    )
    offline={
        "schema":"p08-b45-unprotected-pilot16-offline-pc-preflight-v1",
        "experiment":"once",
        "new_performance_pilot16_ELF_sha256":"a"*64,
    }
    monkeypatch.setattr(review.pilot,"admission",lambda *_:dict(offline))
    return args, offline


def test_missing_preflight_cannot_report_success(setup):
    args,_=setup
    with pytest.raises(OSError):
        review.review(args)
    assert not args.out.exists()


@pytest.mark.parametrize("fault",(
    "missing_approvals","wrong_sha","invented_protection",
    "wrong_mode", "not_unproven",
))
def test_read_only_prior_report_falsification_fails(setup,fault):
    args,offline=setup
    prior=dict(offline)
    prior["all_ten_independent_operator_approvals_recorded"]=True
    prior["physical_JTAG_session_started"]=False
    if fault=="missing_approvals":
        prior["all_ten_independent_operator_approvals_recorded"]=False
    if fault=="wrong_sha":
        prior["new_performance_pilot16_ELF_sha256"]="b"*64
    if fault=="invented_protection":
        prior["backup_protection_verified"]=True
        # actual review must not accept positive physical security claims
        # even if injected as an extraneous host receipt field.
        prior["schema"]="fabricated"
    if fault=="wrong_mode":prior["experiment"]="unchecked"
    if fault=="not_unproven":prior["physical_JTAG_session_started"]=True
    (args.evidence/"preflight.json").write_text(json.dumps(prior))
    with pytest.raises((review.IndependentNoGo,OSError)):
        review.review(args)
    assert not args.out.exists()


def test_independent_script_only_parses_existing_files_and_no_hardware():
    s=(ROOT/"scripts"/"p08_b45_perf_pilot16_independent_verify.py").read_text()
    assert "subprocess" not in s
    assert "Xil_Out32" not in s
    assert "xsdb " not in s
    assert "mwr " not in s
    for k in ("pilot.admission(args)","pilot.b3.readback_original(",
              "pilot.check_post_backup(","neural.verify(","sidecar.audit(",
              "require_protection=False","backup_protection_verified",
              "physical_1024"):
        if k=="physical_1024":continue
        assert k in s,k
