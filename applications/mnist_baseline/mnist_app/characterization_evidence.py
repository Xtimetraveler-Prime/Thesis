from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Iterable

ARCHIVE_SCHEMA = "neuromorphic-twin-mnist-10-physical-timing-evidence-v1"
TIMING_EXPECTATION_SCHEMA = "neuromorphic-twin-mnist-timing-expectation-v1"
RUNTIME_RESULT_SCHEMA = "neuromorphic-twin-mnist-runtime-result-v1"
DEFAULT_CASES: tuple[tuple[str, int], ...] = (
    ("cropped-dense", 3),
    ("native-sparse", 3),
    ("cropped-dense", 1),
    ("native-sparse", 1),
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _case_name(profile: str, index: int) -> str:
    return f"{profile}-index{index:05d}"


def _validate_case(source_dir: Path, *, profile: str, index: int) -> dict[str, Any]:
    paths = {
        "request": source_dir / "request.json",
        "events": source_dir / "events.tsv",
        "expectation": source_dir / "timing_expectation.json",
        "physical_result": source_dir / "physical_timing_result.json",
        "comparison": source_dir / "timing_comparison.json",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "MNIST-10 timing evidence is incomplete for "
            f"{profile} index {index}: {missing}"
        )

    request = _read_json(paths["request"])
    expectation = _read_json(paths["expectation"])
    physical = _read_json(paths["physical_result"])
    comparison = _read_json(paths["comparison"])

    if str(request.get("profile")) != profile or int(request.get("mnist_test_index", -1)) != index:
        raise ValueError("request identity does not match archive case")
    if int(request.get("presentation_ticks", -1)) != 16:
        raise ValueError("request does not use the frozen 16-tick presentation")
    if expectation.get("schema") != TIMING_EXPECTATION_SCHEMA:
        raise ValueError("unsupported timing-expectation schema")
    if str(expectation.get("profile")) != profile or int(expectation.get("mnist_test_index", -1)) != index:
        raise ValueError("timing expectation identity does not match archive case")
    if physical.get("schema") != RUNTIME_RESULT_SCHEMA:
        raise ValueError("unsupported physical runtime-result schema")
    if str(physical.get("profile")) != profile or int(physical.get("mnist_test_index", -1)) != index:
        raise ValueError("physical result identity does not match archive case")
    if str(comparison.get("profile")) != profile or int(comparison.get("mnist_test_index", -1)) != index:
        raise ValueError("timing comparison identity does not match archive case")
    if comparison.get("passed") is not True:
        raise ValueError("refusing to archive a failed MNIST-10 timing comparison")
    if list(comparison.get("mismatches", [])):
        raise ValueError("passed timing comparison contains mismatches")

    expected_ticks = tuple(int(value) for value in expectation["expected_tick_cycles"])
    physical_ticks = tuple(int(value) for value in physical["tick_cycles"])
    comparison_expected = tuple(int(value) for value in comparison["expected_tick_cycles"])
    comparison_physical = tuple(int(value) for value in comparison["physical_tick_cycles"])
    if not (expected_ticks == physical_ticks == comparison_expected == comparison_physical):
        raise ValueError("physical and expected 16-tick cycle vectors are not identical")
    if len(expected_ticks) != 16:
        raise ValueError("MNIST-10 timing evidence must contain exactly 16 tick measurements")

    expected_total = int(expectation["expected_total_cycles"])
    physical_total = int(comparison["physical_total_cycles"])
    comparison_expected_total = int(comparison["expected_total_cycles"])
    if sum(expected_ticks) != expected_total:
        raise ValueError("timing expectation total does not equal its tick vector")
    if expected_total != physical_total or expected_total != comparison_expected_total:
        raise ValueError("physical and expected total cycles differ")

    if int(physical.get("ticks", -1)) != 16:
        raise ValueError("physical result did not commit exactly 16 ticks")
    if int(physical.get("total_events", -1)) != int(request.get("total_events", -2)):
        raise ValueError("physical result event count does not match the host request")
    if int(physical.get("prediction", -1)) != int(comparison["golden_prediction"]):
        raise ValueError("physical prediction does not match the independent golden prediction")
    if tuple(int(v) for v in physical["spike_counts"]) != tuple(
        int(v) for v in comparison["golden_spike_counts"]
    ):
        raise ValueError("physical spike counts do not match independent golden spike counts")

    return {
        "profile": profile,
        "mnist_test_index": index,
        "label": int(request["label"]),
        "device": str(physical.get("device", "unknown")),
        "ticks": 16,
        "total_events": int(physical["total_events"]),
        "golden_prediction": int(comparison["golden_prediction"]),
        "physical_prediction": int(comparison["physical_prediction"]),
        "tick_cycles": list(expected_ticks),
        "total_cycles": expected_total,
        "latency_ms_at_100mhz": expected_total / 100_000.0,
        "passed": True,
        "files": {
            name: {
                "filename": path.name,
                "sha256": _sha256(path),
            }
            for name, path in paths.items()
        },
    }


def archive_physical_timing_evidence(
    build_dir: str | Path,
    output_dir: str | Path,
    *,
    cases: Iterable[tuple[str, int]] = DEFAULT_CASES,
) -> Path:
    """Validate and archive compact source-controlled evidence from local build outputs."""

    build_root = Path(build_dir)
    output_root = Path(output_dir)
    case_list = tuple(cases)
    if not case_list:
        raise ValueError("at least one timing case is required")
    if len(set(case_list)) != len(case_list):
        raise ValueError("timing archive cases must be unique")

    validated: list[tuple[dict[str, Any], Path]] = []
    for profile, index in case_list:
        source = build_root / "timing_requests" / _case_name(profile, index)
        validated.append((_validate_case(source, profile=profile, index=index), source))

    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    archived_cases: list[dict[str, Any]] = []
    for record, source in validated:
        case_dir = output_root / _case_name(record["profile"], record["mnist_test_index"])
        case_dir.mkdir(parents=True, exist_ok=True)
        for filename in (
            "request.json",
            "events.tsv",
            "timing_expectation.json",
            "physical_timing_result.json",
            "timing_comparison.json",
        ):
            shutil.copy2(source / filename, case_dir / filename)
        archived_cases.append(record)

    manifest = {
        "schema": ARCHIVE_SCHEMA,
        "clock_hz": 100_000_000,
        "timing_boundary": (
            "PL ap_clk cycles from accepted tick_start through outer-core tick_done; "
            "host/JTAG/VIO transport excluded"
        ),
        "validation_contract": (
            "physical prediction and spike-count vector match independent golden output, "
            "and every physical tick-cycle count exactly equals the M12.5-derived expectation"
        ),
        "case_count": len(archived_cases),
        "cases": archived_cases,
        "all_passed": all(bool(record["passed"]) for record in archived_cases),
    }
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path
