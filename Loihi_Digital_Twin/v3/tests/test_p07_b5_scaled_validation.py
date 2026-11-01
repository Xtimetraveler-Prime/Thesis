"""P07-B.5 native safety/validation tests: NO BOARD, NO MNIST TEST."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b5_scaled_validation as b5

def test_b5_frozen_reference_requires_exact_real_signed_three_frames(tmp_path):
    with pytest.raises(b5.ValidationNoGo,match="ORDINAL"):
        b5.parse_run_spec("9:"+str(tmp_path))
    with pytest.raises(b5.ValidationNoGo,match="absolute"):
        b5.parse_run_spec("0:relative")
    with pytest.raises(b5.ValidationNoGo,match="ORDINAL"):
        b5.parse_run_spec(str(tmp_path))
    assert b5.parse_run_spec("2:"+str(tmp_path))==(2,tmp_path)

def test_b5_source_uses_actual_frozen_route_contract_not_test_or_mock():
    from loihi_twin_v2.compiler import IngressRoute
    route=IngressRoute(input_population="pixels",input_index=7,
                       destination_core=2,destination_axon=44)
    assert route.input_population=="pixels"
    assert route.input_index==7
    assert not hasattr(route,"source_input")
    assert b5.base.expected_counters is not None
    text=(ROOT/"scripts/p07_b5_scaled_validation.py").read_text()
    assert "simulate_monolithic" in text
    assert "base.expected_counters" in text
    assert "base.trace_fingerprint" in text
    assert "verify_physical_readback" in text
    assert "diag_v3_physical_mailbox_256.bin" in text
    assert "official_MNIST_TEST" in text
    assert "P07_B5_FULL_RAW_NEURON_PARITY_VERIFIED=0" in text
    # Diagnostics legitimately mention XSDB logs. Reject actual board tool
    # invocation rather than rejecting the word in an error message.
    assert 'subprocess.run(["xsdb"' not in text
    assert 'os.system("xsdb' not in text
    assert "subprocess.run(" not in text

def test_strict_original_run_identity_fail_closed(tmp_path):
    with pytest.raises(b5.ValidationNoGo,match="evidence"):
        b5.verify_run(tmp_path/"MISSING",0,{},tmp_path,tmp_path,{})
    directory=tmp_path/"actual"
    directory.mkdir()
    with pytest.raises(b5.ParityNoGo if hasattr(b5,"ParityNoGo") else ValueError):
        b5.verify_run(directory,0,{},tmp_path,tmp_path,{})

def fake_args(tmp_path,mode,ordinals):
    return argparse.Namespace(
        mode=mode,
        frozen_dir=tmp_path/"frozen",
        staged_dir=tmp_path/"stage",
        routes_dir=tmp_path/"routes",
        out=tmp_path/"never_write",
        run=[f"{n}:{tmp_path}/run_{n}_{i}" for i,n in enumerate(ordinals)]
    )

def fake_ref(i):
    return {
        "ordinal":i,
        "metrics":{"trained_readout_prediction":i},
        "trace_fingerprint_FNV64":f"0x{i+1:016X}",
    }

def fake_physical(path,i,ref,staged,routes,index):
    return {
        "schema":b5.SCHEMA,
        "evidence_dir":str(path),
        "original_train_validation_ordinal":i,
        "aggregate_and_full_26tick_FNV64_all_match":True,
        "physical":{"trained_readout_prediction":i,
                    "all_26_tick_trace_hash":ref["trace_fingerprint_FNV64"]},
        "strict_raw_neuron_by_neuron_trace_equality_proven":False,
    }

def mock_source():
    return SimpleNamespace(),SimpleNamespace(
        compiled=SimpleNamespace(fingerprint="pinned-candidate")
    ),{},[{"validation_ordinal":i} for i in range(3)]

@pytest.mark.parametrize("ordinals", [
    [0],[0,0,1,1],[0,1,2],[0,1,2,2],[0,1,2,0,0],
])
def test_consolidate_requires_three_distinct_validation_plus_train0_repeat(
    tmp_path,ordinals
):
    a=fake_args(tmp_path,"consolidate",ordinals)
    with patch.object(b5,"load_original",return_value=mock_source()):
        with pytest.raises(b5.ValidationNoGo,match="exact 0/1/2"):
            b5.run(a)

def test_consolidate_rejects_reused_evidence_folder(tmp_path):
    a=fake_args(tmp_path,"consolidate",[0,1,2,0])
    a.run[3]=a.run[0]
    with patch.object(b5,"load_original",return_value=mock_source()):
        with pytest.raises(b5.ValidationNoGo,match="DISTINCT"):
            b5.run(a)

def test_b5_multiframe_4_independent_sessions_and_explicit_raw_gate(tmp_path):
    a=fake_args(tmp_path,"consolidate",[0,1,2,0])
    with patch.object(b5,"load_original",return_value=mock_source()),(
         patch.object(b5,"make_reference",side_effect=lambda i,*args:fake_ref(i))),(
         patch.object(b5,"verify_run",side_effect=fake_physical)):
        receipt,code=b5.run(a)
    assert code==0
    assert receipt["genuine_independently_verified_sessions"]==4
    assert receipt["required_ordinal_sequence"]==[0,1,2,0]
    assert receipt["distinct_train_validation_frames"]==3
    assert receipt["train0_repeat_physical_metrics_and_FNV64_equal"] is True
    assert receipt["all_independent_fingerprint_gate_conditions_pass"] is True
    assert receipt["P07_B5_final_full_parity_and_acceptance"] is False
    assert receipt["full_raw_per_neuron_hardware_trace_directly_compared"] is False
    assert receipt["cold_reboot_between_runs_independently_proven"] is False
    assert receipt["official_MNIST_TEST"]=="SEALED_NOT_ACCESSED"

def test_b5_consolidate_repeat_neural_drift_never_accepted(tmp_path):
    a=fake_args(tmp_path,"consolidate",[0,1,2,0])
    def mismatch(path,i,ref,staged,routes,index):
        out=fake_physical(path,i,ref,staged,routes,index)
        if "run_0_3" in str(path):
            out["physical"]["all_26_tick_trace_hash"]="0xBADF00D"
        return out
    with patch.object(b5,"load_original",return_value=mock_source()),(
         patch.object(b5,"make_reference",side_effect=lambda i,*args:fake_ref(i))),(
         patch.object(b5,"verify_run",side_effect=mismatch)):
        receipt,code=b5.run(a)
    assert code==4
    assert receipt["train0_repeat_physical_metrics_and_FNV64_equal"] is False
    assert receipt["all_independent_fingerprint_gate_conditions_pass"] is False

def test_b5_consolidate_failed_independent_scalar_gate_rejected(tmp_path):
    a=fake_args(tmp_path,"consolidate",[0,1,2,0])
    def mismatch(path,i,ref,staged,routes,index):
        out=fake_physical(path,i,ref,staged,routes,index)
        if i==2:out["aggregate_and_full_26tick_FNV64_all_match"]=False
        return out
    with patch.object(b5,"load_original",return_value=mock_source()),(
         patch.object(b5,"make_reference",side_effect=lambda i,*args:fake_ref(i))),(
         patch.object(b5,"verify_run",side_effect=mismatch)):
        receipt,code=b5.run(a)
    assert code==4
    assert receipt["all_three_distinct_frames_scalar_vs_physical_equal"] is False
    assert receipt["P07_B5_final_full_parity_and_acceptance"] is False

def test_b5_one_real_run_verification_must_not_overstate_full_parity(tmp_path):
    a=fake_args(tmp_path,"verify",[1])
    with patch.object(b5,"load_original",return_value=mock_source()),(
         patch.object(b5,"make_reference",side_effect=lambda i,*args:fake_ref(i))),(
         patch.object(b5,"verify_run",side_effect=fake_physical)):
        report,code=b5.run(a)
    assert code==0
    assert report["aggregate_and_full_26tick_FNV64_all_match"] is True
    assert report["strict_raw_neuron_by_neuron_trace_equality_proven"] is False

def test_preview_original_signed_three_not_a_synthetic_physical_pass(tmp_path):
    a=fake_args(tmp_path,"preview",[])
    with patch.object(b5,"load_original",return_value=mock_source()),(
         patch.object(b5,"make_reference",side_effect=lambda i,*args:fake_ref(i))),(
         patch.object(b5,"verify_run",side_effect=AssertionError("must not access physical evidence"))):
        report,code=b5.run(a)
    assert code==0
    assert len(report["reference"])==3
    assert report["physical_run_executed"] is False
    assert report["physical_parity_proven"] is False

def test_no_overwrites_and_no_repo_writes(tmp_path):
    existing=tmp_path/"existing.json"
    existing.write_text("never rewrite")
    with pytest.raises(b5.ValidationNoGo,match="NEW"):
        b5.write_report(existing,{"new":True})
    assert existing.read_text()=="never rewrite"
    report=tmp_path/"new.json"
    b5.write_report(report,{"official_MNIST_TEST":"SEALED_NOT_ACCESSED"})
    assert json.loads(report.read_text())["official_MNIST_TEST"]=="SEALED_NOT_ACCESSED"
