"""A3.2.3 repeat aggregation tests: synthetic JSON ONLY; no KV260 access."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from loihi_twin_v2.p08_a3_2_analysis import (
    distribution,ELF_A21_SHA256,ELF_A22_SHA256,
)
from loihi_twin_v2.p08_a3_2_repeats import (
    aggregate_three_pairs,FRAME_COUNT,TRACE_FRAME,IMAGE_KEYS,
    SUMMARY_KEYS,STAGE_HASH_KEYS,CAPTURE_HASH_KEYS,
)

ROOT=Path(__file__).resolve().parents[1]


def _hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def fixture_reports(tmp_path):
    paths=[]
    for pair in range(3):
        a=[34.0+(i%17)*0.04+pair*0.02 for i in range(FRAME_COUNT)]
        delta=[0.008+0.01*pair+(i%13)*0.001 for i in range(FRAME_COUNT)]
        b=[x+y for x,y in zip(a,delta)]
        obj={
            "schema":"p08-a3-2-paired-1024-latency-v1",
            "sample_population":"TRAIN_DERIVED_VALIDATION_FIRST_1024",
            "distinct_images":1024,"ordinary_images":1023,
            "trace_frame":1023,"logical_timesteps_per_image":26,
            "a21_elf_sha256":ELF_A21_SHA256,
            "a22_elf_sha256":ELF_A22_SHA256,
            "both_independent_original_p07_oracles":"PASS",
            "detailed_tick_encoder_and_route_crosschecks":"PASS",
            "physical_pair_numerics_and_timing_integrity":"PASS_SINGLE_PAIR",
            "full_replicated_latency_baseline":"NOT_YET_ACCEPTED",
            "power_energy":"DEFERRED",
            "official_mnist_test":"NOT_RERUN",
            "a21_a53_cntfrq_el0_hz":99999001,
            "a22_a53_cntfrq_el0_hz":99999001,
            "a21_physical_run_directory":str(tmp_path/f"physical_a21_{pair}"),
            "a22_physical_run_directory":str(tmp_path/f"physical_a22_{pair}"),
            "input_evidence_sha256":{
                **{k:_hash("same frozen validation "+k) for k in STAGE_HASH_KEYS},
                **{k:_hash(f"{pair} unique physical {k}") for k in CAPTURE_HASH_KEYS},
            },
            IMAGE_KEYS[0]:a, IMAGE_KEYS[1]:b, IMAGE_KEYS[2]:delta,
            SUMMARY_KEYS[0]:distribution(a[:TRACE_FRAME]),
            SUMMARY_KEYS[1]:distribution(b[:TRACE_FRAME]),
            SUMMARY_KEYS[2]:distribution(delta[:TRACE_FRAME]),
        }
        path=tmp_path/f"pair_{pair}.json"
        path.write_text(json.dumps(obj),encoding="utf8")
        paths.append(path)
    return paths


def _mutate(path, fn):
    d=json.loads(path.read_text())
    fn(d)
    path.write_text(json.dumps(d))


def test_three_pairs_aggregate_fixed_image_repetition(tmp_path):
    files=fixture_reports(tmp_path)
    result=aggregate_three_pairs(files)
    assert result["independent_firmware_sessions_per_variant"]==3
    assert result["independent_physical_pairs"]==3
    assert result["unique_train_validation_images"]==1024
    assert result["ordinary_images_per_pair"]==1023
    assert result["frame_repeats_are_new_independent_images"] is False
    assert len(result["source_evidence"])==3
    assert len(result["paired_ordinary_delta_ms_by_run"])==3
    assert all(len(v)==1023 for v in result["paired_ordinary_delta_ms_by_run"])
    medians=result["paired_ordinary_median_delta_ms_by_pair"]
    assert medians[1]>medians[0] and medians[2]>medians[1]
    assert result["between_pair_median_delta_ms"]["n"]==3
    assert result["distribution_of_fixed_frame_mean_paired_delta_ms"]["n"]==1023
    assert result["distribution_of_fixed_frame_delta_range_across_3_runs_ms"]["n"]==1023
    assert result["power_energy"]=="DEFERRED"
    assert result["original_p07_neural_oracle"].startswith("passed for each")


def test_requires_three_distinct_pair_reports(tmp_path):
    a,b,c=fixture_reports(tmp_path)
    with pytest.raises(ValueError,match="exactly THREE"):
        aggregate_three_pairs([a,b])
    with pytest.raises(ValueError,match="exactly THREE"):
        aggregate_three_pairs([a,a,c])


def test_rejects_reused_firmware_capture_directory(tmp_path):
    a,b,c=fixture_reports(tmp_path)
    prior=json.loads(a.read_text())["a21_physical_run_directory"]
    _mutate(b,lambda d:d.update(a21_physical_run_directory=prior))
    with pytest.raises(ValueError,match="reused a physical session"):
        aggregate_three_pairs([a,b,c])


def test_rejects_reused_hardware_timing_sidecar_even_with_new_path(tmp_path):
    a,b,c=fixture_reports(tmp_path)
    same=json.loads(a.read_text())["input_evidence_sha256"]["A2_2_per_tick_timing"]
    def bad(d):
        d["input_evidence_sha256"]["A2_2_per_tick_timing"]=same
    _mutate(c,bad)
    with pytest.raises(ValueError,match="duplicate A2_2_per_tick_timing"):
        aggregate_three_pairs([a,b,c])


def test_rejects_forged_or_changed_validation_population(tmp_path):
    a,b,c=fixture_reports(tmp_path)
    _mutate(b,lambda d:d["input_evidence_sha256"].update(
        original_train_stage_pixels=_hash("different dataset")
    ))
    with pytest.raises(ValueError,match="original TRAIN stage differs"):
        aggregate_three_pairs([a,b,c])


def test_rejects_wrong_neural_oracle_status(tmp_path):
    a,b,c=fixture_reports(tmp_path)
    _mutate(c,lambda d:d.update(both_independent_original_p07_oracles="SKIPPED"))
    with pytest.raises(ValueError,match="invalid accepted single-pair"):
        aggregate_three_pairs([a,b,c])


def test_rejects_false_delta_tamper(tmp_path):
    a,b,c=fixture_reports(tmp_path)
    def bad(d):
        d[IMAGE_KEYS[2]][600]+=0.05
    _mutate(b,bad)
    with pytest.raises(ValueError,match="same-frame"):
        aggregate_three_pairs([a,b,c])


def test_rejects_mismatched_ordinary_summary(tmp_path):
    a,b,c=fixture_reports(tmp_path)
    def bad(d):
        d[SUMMARY_KEYS[2]]["median"]+=0.5
    _mutate(b,bad)
    with pytest.raises(ValueError,match="summary differs"):
        aggregate_three_pairs([a,b,c])


def test_rejects_nonfinite_and_missing_samples(tmp_path):
    a,b,c=fixture_reports(tmp_path)
    _mutate(b,lambda d:d[IMAGE_KEYS[0]].pop())
    with pytest.raises(ValueError,match="1024 finite"):
        aggregate_three_pairs([a,b,c])


def test_no_hardware_usage_and_cli_syntax():
    cli=(ROOT/"scripts/p08_a3_2_repeat_check.py").read_text()
    agg=(ROOT/"src/loihi_twin_v2/p08_a3_2_repeats.py").read_text()
    assert "aggregate_three_pairs" in cli
    assert 'args.report.open("x"' in cli
    assert "P08_A3_2_3_THREE_PAIRED_LATENCY_AGGREGATION_PASS=1" in cli
    assert "frame_repeats_are_new_independent_images" in agg
    assert "No physical calls" not in cli or "OFFLINE only" in cli
    assert "subprocess" not in cli
    compiled=subprocess.run(["python","-m","py_compile",
        str(ROOT/"scripts/p08_a3_2_repeat_check.py"),
        str(ROOT/"src/loihi_twin_v2/p08_a3_2_repeats.py")],
        capture_output=True,text=True)
    assert compiled.returncode==0,compiled.stderr
