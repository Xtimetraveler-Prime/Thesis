"""A5 report compatibility and source-integrity tests: synthetic objects only."""
from __future__ import annotations
from copy import deepcopy
import hashlib
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from loihi_twin_v2 import p08_a5_cpu_benchmark as benchmark
from loihi_twin_v2.p08_a5_cpu_reference import CPUOutcome
from loihi_twin_v2.p08_a5_closeout import (
    make_draft,validate_cpu_report,validate_cross_provenance,
)
from loihi_twin_v2.p08_a3_2_repeats import AGG_SCHEMA

ROOT=Path(__file__).resolve().parents[1]


def _digest(label):
    return hashlib.sha256(label.encode()).hexdigest()


@pytest.fixture
def accepted_mock_reports(monkeypatch,tmp_path):
    reference=CPUOutcome(0,(0,)*10,((0,)*10,)*26,0,0,0,True)
    monkeypatch.setattr(benchmark,"image_event_schedule",lambda _: ((),)*26)
    monkeypatch.setattr(benchmark,"preloaded_compute",lambda *_:reference)
    monkeypatch.setattr(benchmark,"image_to_class",lambda *_:reference)
    row=SimpleNamespace(**{
        "predicted":reference.predicted,"counts":reference.counts,
        "output_spikes":reference.output_spikes,"routes":reference.routes,
        "discarded":reference.discarded,"external_events":reference.external_events,
        "all_silent":reference.all_silent,
    })
    cpu=benchmark.benchmark_cpu_two_endpoints(
        None,(bytes(784),)*1024,(row,)*1024,warmup=0,
        timer_environment={"machine":"SYNTHETIC", "implementation":"SYNTHETIC",
            "python_version":"0.0", "logical_cpu_count":1,
            "benchmark_language":"synthetic test only",
            "threading":"single fake", "timer":"fake host timer"}
    )
    physical_run=str(tmp_path/"pair1_a21")
    cpu["provenance"]={
        "original_p07_packed_independent_physical_oracle":"PASS_ALL_1024",
        "physical_capture_run_directory":physical_run,
        "source_sha256":{
            "stage_descriptor":_digest("desc"),
            "stage_pixels":_digest("pixels"),
            "stage_manifest":_digest("manifest"),
        },
    }
    physical={
        "schema":AGG_SCHEMA,
        "independent_firmware_sessions_per_variant":3,
        "independent_physical_pairs":3,
        "unique_train_validation_images":1024,
        "ordinary_images_per_pair":1023,
        "selected_full_trace_frame":1023,
        "frame_repeats_are_new_independent_images":False,
        "original_p07_neural_oracle":"passed for each source pair before aggregation",
        "power_energy":"DEFERRED","official_mnist_test":"NOT_RERUN",
        "measurement_scope":"instrumented A53 complete frame service, NOT pure FPGA neural compute",
        "immutable_stage_sha256":{
            "original_train_stage_descriptor":_digest("desc"),
            "original_train_stage_pixels":_digest("pixels"),
            "original_train_stage_manifest":_digest("manifest"),
        },
        "source_evidence":[
            {"a21_run_dir":str(tmp_path/f"pair{i}_a21"),
             "a22_run_dir":str(tmp_path/f"pair{i}_a22")} for i in range(1,4)
        ],
        "a21_ordinary_median_service_ms_by_run":[35.7023,35.6946,35.6696],
        "a22_ordinary_median_service_ms_by_run":[35.7234,35.7163,35.7220],
        "paired_ordinary_median_delta_ms_by_pair":[0.01684,0.0254,0.02971],
        "a21_ordinary_per_image_ms_by_run":[[35.0]*1023 for i in range(3)],
        "a22_ordinary_per_image_ms_by_run":[[35.03]*1023 for i in range(3)],
        "paired_ordinary_delta_ms_by_run":[[0.03]*1023 for i in range(3)],
        "between_pair_median_delta_ms":{
            "mean":(0.01684+0.0254+0.02971)/3,
            "sample_stdev":0.006551,
        },
    }
    return cpu,physical


def test_a5_closeout_candidate_same_stage_and_caveats(accepted_mock_reports):
    cpu,physical=accepted_mock_reports
    validate_cpu_report(cpu)
    validate_cross_provenance(cpu,physical)
    out=make_draft(cpu,physical,cpu_sha=_digest("cpu"),
                   physical_sha=_digest("physical"))
    assert "NOT YET ACCEPTED BY USER" in out
    assert "DO NOT LABEL THIS TABLE 'FPGA SPEEDUP'" in out
    assert "NOT scope-matched" not in out or "do not share identical" in out
    assert "35.7023" in out and "35.7234" in out
    assert "16.8400, 25.4000, 29.7100" in out
    assert "DEFERRED" in out


def test_rejects_cpu_from_different_train_stage(accepted_mock_reports):
    cpu,physical=accepted_mock_reports
    physical["immutable_stage_sha256"]["original_train_stage_pixels"]=_digest("wrong")
    with pytest.raises(ValueError,match="different TRAIN stage"):
        validate_cross_provenance(cpu,physical)


def test_rejects_forged_cpu_neural_results(accepted_mock_reports):
    cpu,physical=accepted_mock_reports
    cpu["all_1024_original_26tick_spike_traces_exact"]="SKIPPED"
    with pytest.raises(ValueError,match="not a validated"):
        validate_cpu_report(cpu)


def test_rejects_cpu_source_not_among_six_accepted_sessions(accepted_mock_reports):
    cpu,physical=accepted_mock_reports
    cpu["provenance"]["physical_capture_run_directory"]="/unrelated/run"
    with pytest.raises(ValueError,match="not tied to one accepted"):
        validate_cross_provenance(cpu,physical)


def test_rejects_mismatched_physical_scope(accepted_mock_reports):
    cpu,physical=accepted_mock_reports
    physical["measurement_scope"]="FPGA PURE ONLY"
    with pytest.raises(ValueError,match="metric scope"):
        validate_cross_provenance(cpu,physical)


def test_rejects_tampered_cpu_stats(accepted_mock_reports):
    cpu,_=accepted_mock_reports
    cpu["preloaded_core_endpoint"]["ordinary_1023_distributions_ms"][1]["median"]+=1
    with pytest.raises(ValueError,match="summary tampered"):
        validate_cpu_report(cpu)


def test_rejects_16_images_pretending_to_be_1024(accepted_mock_reports):
    cpu,_=accepted_mock_reports
    cpu["full_raw_image_to_class_endpoint"]["three_sequential_runs_ms"][0]=[1]*16
    with pytest.raises(ValueError,match="1024 positive"):
        validate_cpu_report(cpu)


def test_cli_syntax_and_offline_non_acceptance():
    cli=(ROOT/"scripts/p08_a5_closeout_report.py").read_text()
    assert "make_draft" in cli
    assert "P08_A5_FINAL_USER_ACCEPTANCE=PENDING" in cli
    assert "P08_A5_FPGA_SPEEDUP=NOT_CLAIMED_NON_EQUIVALENT_ENDPOINTS" in cli
    assert 'a.output_md.open("x"' in cli
    assert "xsdb " not in cli.lower()
    assert "vivado " not in cli.lower()
    check=subprocess.run(["python","-m","py_compile",
        str(ROOT/"scripts/p08_a5_closeout_report.py"),
        str(ROOT/"src/loihi_twin_v2/p08_a5_closeout.py")],
        capture_output=True,text=True)
    assert check.returncode==0,check.stderr
