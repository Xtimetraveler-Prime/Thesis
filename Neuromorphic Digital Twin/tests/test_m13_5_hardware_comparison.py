from __future__ import annotations

from neuromorphic_twin.m13_hardware_comparison import (
    M13_5_COMPARISON_SCHEMA,
    build_hardware_comparison,
    render_hardware_comparison_markdown,
)


def _result() -> dict:
    return {
        "schema": "neuromorphic-twin-m13-hardware-result-v1",
        "status": "routed_implementation_observed",
        "catalyst_commit": "1806bb4b4114d7671e5648fa75b7b83b3a8d5543",
        "vivado": "2025.2",
        "target_part": "xczu5ev-sfvc784-2-i",
        "clock_period_ns": 10.0,
        "timing": {"wns_ns": 0.250, "whs_ns": 0.020},
        "timing_closed": True,
        "resources": {
            "clb_luts": {"used": 20000.0, "available": 117120.0, "utilization_percent": 17.08},
            "clb_registers": {"used": 18000.0, "available": 234240.0, "utilization_percent": 7.68},
            "bram_tiles": {"used": 50.0, "available": 144.0, "utilization_percent": 34.72},
            "dsps": {"used": 0.0, "available": 1248.0, "utilization_percent": 0.0},
            "uram": {"used": 0.0, "available": 64.0, "utilization_percent": 0.0},
        },
        "source_reports": {},
        "physical_programming_source_supported": False,
        "comparison_boundary": "Catalyst source-supported routed implementation; no physical KV260 execution claimed",
    }


def test_comparison_keeps_part_strings_and_evidence_strength_distinct() -> None:
    comparison = build_hardware_comparison(_result())
    assert comparison["schema"] == M13_5_COMPARISON_SCHEMA
    assert comparison["targets"]["project"] == "xck26-sfvc784-2LV-c"
    assert comparison["targets"]["catalyst"] == "xczu5ev-sfvc784-2-i"
    assert comparison["physical_execution"]["project"] is True
    assert comparison["physical_execution"]["catalyst"] is False


def test_comparison_withholds_latency_power_and_efficiency_ranking() -> None:
    comparison = build_hardware_comparison(_result())
    assert comparison["latency_throughput"]["comparison_status"] == "withheld"
    assert comparison["latency_throughput"]["catalyst"] is None
    assert comparison["power_energy"]["comparison_status"] == "withheld"
    assert all(row["comparison_status"] == "contextual_only" for row in comparison["resources"])


def test_comparison_retains_both_10ns_timing_margins_without_fmax_claim() -> None:
    comparison = build_hardware_comparison(_result())
    timing = comparison["routed_timing"]
    assert timing["project"] == {"wns_ns": 0.493, "whs_ns": 0.011}
    assert timing["catalyst"] == {"wns_ns": 0.250, "whs_ns": 0.020}
    assert "maximum Fmax" in timing["rule"]


def test_markdown_renderer_states_the_withheld_comparisons() -> None:
    markdown = render_hardware_comparison_markdown(build_hardware_comparison(_result()))
    assert "contextual evidence, not an efficiency ranking" in markdown
    assert "Latency/throughput" in markdown
    assert "Power/energy" in markdown
    assert "no physical KV260 execution claimed" in markdown
    assert "xck26-sfvc784-2LV-c" in markdown
    assert "xczu5ev-sfvc784-2-i" in markdown
