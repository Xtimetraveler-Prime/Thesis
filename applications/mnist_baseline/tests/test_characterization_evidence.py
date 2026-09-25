from __future__ import annotations

import json
from pathlib import Path

import pytest

from mnist_app.characterization_evidence import (
    ARCHIVE_SCHEMA,
    DEFAULT_CASES,
    archive_physical_timing_evidence,
)


def _write_case(root: Path, profile: str, index: int) -> None:
    case_dir = root / "timing_requests" / f"{profile}-index{index:05d}"
    case_dir.mkdir(parents=True, exist_ok=True)
    tick_cycles = [170 + tick for tick in range(16)]
    total_cycles = sum(tick_cycles)
    spike_counts = [0] * 10
    spike_counts[index % 10] = 3
    prediction = index % 10

    request = {
        "schema": "neuromorphic-twin-mnist-runtime-request-v1",
        "profile": profile,
        "profile_id": 0 if profile == "cropped-dense" else 1,
        "mnist_test_index": index,
        "label": prediction,
        "presentation_ticks": 16,
        "total_events": 12,
        "events_per_tick": [0] * 16,
        "golden_prediction": prediction,
        "golden_spike_counts": spike_counts,
    }
    expectation = {
        "schema": "neuromorphic-twin-mnist-timing-expectation-v1",
        "profile": profile,
        "mnist_test_index": index,
        "label": prediction,
        "events_per_tick": [0] * 16,
        "synapse_visits_per_tick": [0] * 16,
        "expected_tick_cycles": tick_cycles,
        "expected_total_cycles": total_cycles,
        "expected_latency_ms_at_100mhz": total_cycles / 100_000.0,
    }
    physical = {
        "schema": "neuromorphic-twin-mnist-runtime-result-v1",
        "profile": profile,
        "profile_id": request["profile_id"],
        "mnist_test_index": index,
        "device": "xck26_0",
        "ticks": 16,
        "total_events": 12,
        "spike_counts": spike_counts,
        "tick_cycles": tick_cycles,
        "prediction": prediction,
    }
    comparison = {
        "passed": True,
        "mismatches": [],
        "profile": profile,
        "mnist_test_index": index,
        "label": prediction,
        "golden_prediction": prediction,
        "physical_prediction": prediction,
        "golden_spike_counts": spike_counts,
        "physical_spike_counts": spike_counts,
        "expected_tick_cycles": tick_cycles,
        "physical_tick_cycles": tick_cycles,
        "expected_total_cycles": total_cycles,
        "physical_total_cycles": total_cycles,
        "clock_hz": 100_000_000,
    }

    (case_dir / "request.json").write_text(json.dumps(request), encoding="utf-8")
    (case_dir / "events.tsv").write_text(
        "tick\tevents\n" + "\n".join(f"{tick}\t" for tick in range(16)) + "\n",
        encoding="utf-8",
    )
    (case_dir / "timing_expectation.json").write_text(
        json.dumps(expectation), encoding="utf-8"
    )
    (case_dir / "physical_timing_result.json").write_text(
        json.dumps(physical), encoding="utf-8"
    )
    (case_dir / "timing_comparison.json").write_text(
        json.dumps(comparison), encoding="utf-8"
    )


def test_archive_physical_timing_evidence(tmp_path: Path) -> None:
    build_dir = tmp_path / "build"
    for profile, index in DEFAULT_CASES:
        _write_case(build_dir, profile, index)

    output = tmp_path / "evidence"
    manifest_path = archive_physical_timing_evidence(build_dir, output)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["schema"] == ARCHIVE_SCHEMA
    assert manifest["case_count"] == 4
    assert manifest["all_passed"] is True
    assert {(case["profile"], case["mnist_test_index"]) for case in manifest["cases"]} == set(DEFAULT_CASES)
    for case in manifest["cases"]:
        case_dir = output / f"{case['profile']}-index{case['mnist_test_index']:05d}"
        assert (case_dir / "physical_timing_result.json").is_file()
        assert len(case["tick_cycles"]) == 16
        assert case["passed"] is True
        assert len(case["files"]["physical_result"]["sha256"]) == 64


def test_archive_rejects_cycle_mismatch(tmp_path: Path) -> None:
    build_dir = tmp_path / "build"
    profile, index = DEFAULT_CASES[0]
    _write_case(build_dir, profile, index)
    case_dir = build_dir / "timing_requests" / f"{profile}-index{index:05d}"
    physical_path = case_dir / "physical_timing_result.json"
    physical = json.loads(physical_path.read_text(encoding="utf-8"))
    physical["tick_cycles"][0] += 1
    physical_path.write_text(json.dumps(physical), encoding="utf-8")

    with pytest.raises(ValueError, match="cycle vectors"):
        archive_physical_timing_evidence(
            build_dir,
            tmp_path / "evidence",
            cases=((profile, index),),
        )


def test_archive_rejects_failed_comparison(tmp_path: Path) -> None:
    build_dir = tmp_path / "build"
    profile, index = DEFAULT_CASES[0]
    _write_case(build_dir, profile, index)
    case_dir = build_dir / "timing_requests" / f"{profile}-index{index:05d}"
    comparison_path = case_dir / "timing_comparison.json"
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    comparison["passed"] = False
    comparison["mismatches"] = ["tick_cycles"]
    comparison_path.write_text(json.dumps(comparison), encoding="utf-8")

    with pytest.raises(ValueError, match="failed"):
        archive_physical_timing_evidence(
            build_dir,
            tmp_path / "evidence",
            cases=((profile, index),),
        )
