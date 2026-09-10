from __future__ import annotations

import json
from pathlib import Path


def _closure() -> dict:
    path = Path("references/m13_5_closure.json")
    return json.loads(path.read_text(encoding="utf-8"))


def test_tracked_m13_5_closure_freezes_observed_vendor_result() -> None:
    closure = _closure()

    assert closure["schema"] == "neuromorphic-twin-m13-hardware-closure-v1"
    assert closure["status"] == "validated_complete"
    assert closure["milestone"] == "M13.5"
    assert closure["strongest_catalyst_boundary"] == "source-supported routed implementation"
    assert closure["source_pins"]["catalyst_commit"] == "1806bb4b4114d7671e5648fa75b7b83b3a8d5543"
    assert closure["reproduction"] == {
        "vivado": "2025.2",
        "clock_hz": 100_000_000,
        "clock_period_ns": 10.0,
        "project_target_part": "xck26-sfvc784-2LV-c",
        "catalyst_target_part": "xczu5ev-sfvc784-2-i",
    }
    assert closure["routed_timing"]["project"] == {"wns_ns": 0.493, "whs_ns": 0.011}
    assert closure["routed_timing"]["catalyst"] == {"wns_ns": 0.001, "whs_ns": 0.013}
    assert closure["routed_timing"]["project_timing_closed"] is True
    assert closure["routed_timing"]["catalyst_timing_closed"] is True


def test_tracked_m13_5_closure_freezes_resource_context_without_ranking() -> None:
    closure = _closure()
    rows = {row["resource"]: row for row in closure["resources"]}

    assert rows["CLB LUTs"]["catalyst"] == {
        "used": 19891.0,
        "available": 117120.0,
        "utilization_percent": 16.98,
    }
    assert rows["CLB registers"]["catalyst"] == {
        "used": 30850.0,
        "available": 234240.0,
        "utilization_percent": 13.17,
    }
    assert rows["Block RAM tiles"]["catalyst"] == {
        "used": 52.5,
        "available": 144.0,
        "utilization_percent": 36.46,
    }
    assert rows["DSPs"]["catalyst"] == {
        "used": 14.0,
        "available": 1248.0,
        "utilization_percent": 1.12,
    }
    assert rows["URAM"]["catalyst"] == {
        "used": 0.0,
        "available": 64.0,
        "utilization_percent": 0.0,
    }
    assert all(row["comparison_status"] == "contextual_only" for row in rows.values())


def test_tracked_m13_5_closure_preserves_fairness_and_evidence_identity() -> None:
    closure = _closure()

    assert closure["comparison_limits"] == {
        "latency_throughput": "withheld",
        "power_energy": "withheld",
        "physical_catalyst_execution": False,
    }
    assert closure["behavioral_execution"]["project"] == {
        "cases": 22,
        "ticks": 166,
        "mismatches": 0,
    }
    assert closure["behavioral_execution"]["catalyst"] is None

    evidence = closure["evidence"]
    assert evidence["evidence_manifest_sha256"] == (
        "80a03e53f8775c6358654fa34e35176442f79b94b43de8e58ecf10920665b2bc"
    )
    assert len(evidence["native_reports_sha256"]) == 11
    assert all(len(digest) == 64 for digest in evidence["native_reports_sha256"].values())
    serialized = json.dumps(closure)
    assert "/home/dna" not in serialized
    assert "maximum Fmax" in closure["routed_timing"]["rule"]


def test_m13_5_documentation_records_closed_boundary() -> None:
    reproduction = Path("docs/M13_5_CATALYST_K26_REPRODUCTION.md").read_text(encoding="utf-8")
    closure_doc = Path("docs/M13_5_3_CLOSURE.md").read_text(encoding="utf-8")

    for text in (reproduction, closure_doc):
        assert "19,891" in text
        assert "30,850" in text
        assert "52.5" in text
        assert "+0.001 ns" in text
        assert "+0.013 ns" in text
        assert "80a03e53f8775c6358654fa34e35176442f79b94b43de8e58ecf10920665b2bc" in text
    assert "**Status: Complete**" in reproduction
    assert "**Status: Complete**" in closure_doc
