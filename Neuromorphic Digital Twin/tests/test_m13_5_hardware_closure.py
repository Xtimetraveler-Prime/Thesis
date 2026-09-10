from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from neuromorphic_twin.m13_hardware_closure import (
    M13_5_CLOSURE_SCHEMA,
    M13_5_EVIDENCE_MANIFEST_SCHEMA,
    REQUIRED_NATIVE_REPORTS,
    build_hardware_closure,
    render_hardware_closure_markdown,
    verify_hardware_evidence_tree,
    write_hardware_closure,
)
from neuromorphic_twin.m13_hardware_comparison import (
    build_hardware_comparison,
    render_hardware_comparison_markdown,
)


def _result(*, wns: float = 0.001, whs: float = 0.013, timing_closed: bool = True) -> dict:
    return {
        "schema": "neuromorphic-twin-m13-hardware-result-v1",
        "status": "routed_implementation_observed",
        "catalyst_commit": "1806bb4b4114d7671e5648fa75b7b83b3a8d5543",
        "vivado": "2025.2",
        "target_part": "xczu5ev-sfvc784-2-i",
        "clock_period_ns": 10.0,
        "timing": {"wns_ns": wns, "whs_ns": whs},
        "timing_closed": timing_closed,
        "resources": {
            "clb_luts": {"used": 20000.0, "available": 117120.0, "utilization_percent": 17.08},
            "clb_registers": {"used": 18000.0, "available": 234240.0, "utilization_percent": 7.68},
            "bram_tiles": {"used": 50.0, "available": 144.0, "utilization_percent": 34.72},
            "dsps": {"used": 0.0, "available": 1248.0, "utilization_percent": 0.0},
            "uram": {"used": 0.0, "available": 64.0, "utilization_percent": 0.0},
        },
        "source_reports": {
            "utilization": "/home/dna/Git/Thesis/Neuromorphic Digital Twin/build/m13_5/catalyst-k26-vivado/native_reports/utilization.rpt",
            "timing": "/home/dna/Git/Thesis/Neuromorphic Digital Twin/build/m13_5/catalyst-k26-vivado/native_reports/timing_summary.rpt",
        },
        "physical_programming_source_supported": False,
        "comparison_boundary": "Catalyst source-supported routed implementation; no physical KV260 execution claimed",
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_hash_manifest(root: Path, result: dict, comparison: dict) -> None:
    hashes = {
        str(path.relative_to(root)): _sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "evidence-manifest.json"
    }
    evidence = {
        "schema": M13_5_EVIDENCE_MANIFEST_SCHEMA,
        "catalyst_commit": result["catalyst_commit"],
        "vivado": result["vivado"],
        "target_part": result["target_part"],
        "timing_closed": result["timing_closed"],
        "strongest_catalyst_boundary": comparison["strongest_catalyst_boundary"],
        "latency_throughput_comparison": comparison["latency_throughput"]["comparison_status"],
        "power_energy_comparison": comparison["power_energy"]["comparison_status"],
        "physical_catalyst_execution": comparison["physical_execution"]["catalyst"],
        "files_sha256": hashes,
    }
    (root / "evidence-manifest.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")


def _evidence_tree(tmp_path: Path, *, result: dict | None = None) -> Path:
    root = tmp_path / "catalyst-k26-vivado"
    native = root / "native_reports"
    native.mkdir(parents=True)
    result = result or _result()
    comparison = build_hardware_comparison(result)

    (root / "catalyst-head.txt").write_text(result["catalyst_commit"] + "\n", encoding="utf-8")
    (root / "commands.txt").write_text(
        "vivado -mode batch -source fpga/kria/build_kria.tcl -tclargs synth_only\n"
        "vivado -mode batch -source fpga/kria/run_impl.tcl\n",
        encoding="utf-8",
    )
    (root / "vivado-version.txt").write_text("Vivado v2025.2 (64-bit)\n", encoding="utf-8")
    (root / "synthesis.log").write_text("synthetic synthesis log\n", encoding="utf-8")
    (root / "implementation.log").write_text("synthetic implementation log\n", encoding="utf-8")
    (root / "catalyst-hardware-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (root / "hardware-comparison.json").write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
    (root / "hardware-comparison.md").write_text(render_hardware_comparison_markdown(comparison), encoding="utf-8")

    for name in REQUIRED_NATIVE_REPORTS:
        (native / name).write_text(f"synthetic {name}\n", encoding="utf-8")

    _write_hash_manifest(root, result, comparison)
    return root


def test_valid_evidence_tree_promotes_machine_independent_closure(tmp_path: Path) -> None:
    root = _evidence_tree(tmp_path)
    verified = verify_hardware_evidence_tree(root)
    closure = build_hardware_closure(root)

    assert len(verified["evidence_manifest_sha256"]) == 64
    assert closure["schema"] == M13_5_CLOSURE_SCHEMA
    assert closure["status"] == "validated_complete"
    assert closure["strongest_catalyst_boundary"] == "source-supported routed implementation"
    assert closure["routed_timing"]["catalyst"] == {"wns_ns": 0.001, "whs_ns": 0.013}
    assert closure["comparison_limits"] == {
        "latency_throughput": "withheld",
        "power_energy": "withheld",
        "physical_catalyst_execution": False,
    }
    assert set(closure["evidence"]["native_reports_sha256"]) == set(REQUIRED_NATIVE_REPORTS)
    assert "/home/dna" not in json.dumps(closure)


def test_evidence_hash_tamper_is_rejected(tmp_path: Path) -> None:
    root = _evidence_tree(tmp_path)
    (root / "native_reports" / "timing_summary.rpt").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="evidence hash mismatch"):
        verify_hardware_evidence_tree(root)


def test_unhashed_extra_file_is_rejected(tmp_path: Path) -> None:
    root = _evidence_tree(tmp_path)
    (root / "unexpected.txt").write_text("not in original manifest\n", encoding="utf-8")
    with pytest.raises(ValueError, match="file set mismatch"):
        verify_hardware_evidence_tree(root)


def test_comparison_drift_is_rejected_even_when_hash_manifest_is_refreshed(tmp_path: Path) -> None:
    root = _evidence_tree(tmp_path)
    result = json.loads((root / "catalyst-hardware-result.json").read_text(encoding="utf-8"))
    comparison = json.loads((root / "hardware-comparison.json").read_text(encoding="utf-8"))
    comparison["physical_execution"]["catalyst"] = True
    (root / "hardware-comparison.json").write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
    (root / "hardware-comparison.md").write_text(render_hardware_comparison_markdown(comparison), encoding="utf-8")
    _write_hash_manifest(root, result, comparison)

    with pytest.raises(ValueError, match="does not match deterministic regeneration"):
        verify_hardware_evidence_tree(root)


def test_failed_routed_timing_cannot_be_promoted(tmp_path: Path) -> None:
    root = _evidence_tree(tmp_path, result=_result(wns=-0.001, timing_closed=False))
    with pytest.raises(ValueError, match="timing did not close"):
        build_hardware_closure(root)


def test_writer_emits_json_and_human_readable_summary(tmp_path: Path) -> None:
    root = _evidence_tree(tmp_path)
    output_json = tmp_path / "references" / "m13_5_closure.json"
    output_md = tmp_path / "build" / "m13_5_closure_summary.md"

    closure = write_hardware_closure(root, output_json=output_json, output_markdown=output_md)

    assert json.loads(output_json.read_text(encoding="utf-8")) == closure
    markdown = output_md.read_text(encoding="utf-8")
    assert markdown == render_hardware_closure_markdown(closure)
    assert "validated complete" in markdown
    assert "+0.001 ns" in markdown
    assert "Latency/throughput comparison remains withheld" in markdown
    assert "Power/energy comparison remains withheld" in markdown
