from __future__ import annotations

import json
from pathlib import Path

import pytest

from neuromorphic_twin.m13_hardware_audit import (
    EXPECTED_VIVADO_VERSION,
    M13_5_HARDWARE_SCHEMA,
    M13_5_RESULT_SCHEMA,
    build_catalyst_hardware_result,
    load_hardware_manifest,
    parse_timing_summary,
    parse_utilization_report,
    parse_vivado_version,
    require_vivado_2025_2,
)


def _utilization() -> str:
    return """
+----------------------------+-------+-------+-----------+-------+
| Site Type                  | Used  | Fixed | Available | Util% |
+----------------------------+-------+-------+-----------+-------+
| CLB LUTs                   | 12345 |     0 |    117120 | 10.54 |
| CLB Registers              | 23456 |     0 |    234240 | 10.01 |
| Block RAM Tile             |  42.5 |     0 |       144 | 29.51 |
| DSPs                       |    17 |     0 |      1248 |  1.36 |
| URAM                       |     0 |     0 |        64 |  0.00 |
+----------------------------+-------+-------+-----------+-------+
"""


def _timing(wns: float = 0.321, whs: float = 0.014) -> str:
    return f"""
Design Timing Summary
---------------------
WNS(ns)      TNS(ns)  TNS Failing Endpoints  TNS Total Endpoints      WHS(ns)      THS(ns)  THS Failing Endpoints  THS Total Endpoints
-------      -------  ---------------------  -------------------      -------      -------  ---------------------  -------------------
 {wns:.3f}        0.000                      0                 1234        {whs:.3f}        0.000                      0                 1234
"""


def test_m13_5_manifest_freezes_hardware_and_fairness_boundary() -> None:
    data = load_hardware_manifest()
    assert data["schema"] == M13_5_HARDWARE_SCHEMA
    assert data["status"] == "preflight_frozen_pending_vivado_reproduction"
    assert data["baseline"]["m13_4_main_merge"] == "54c7840dff765d585e7ff236845b085007405c05"
    assert data["catalyst_k26"]["upstream_target_part"] == "xczu5ev-sfvc784-2-i"
    assert data["project_m12_physical"]["target_part"] == "xck26-sfvc784-2LV-c"
    assert data["catalyst_k26"]["physical_programming_boundary"]["source_supported"] is False
    assert data["project_m12_physical"]["behavioral_validation"] == {
        "cases": 22,
        "ticks": 166,
        "mismatches": 0,
    }


def test_m13_5_manifest_records_readme_flow_caveat_and_exact_commands() -> None:
    data = load_hardware_manifest()["catalyst_k26"]
    assert data["readme_command"].endswith("fpga/kria/build_kria.tcl")
    assert data["source_supported_synthesis_command"].endswith("-tclargs synth_only")
    assert data["source_supported_implementation_command"].endswith("fpga/kria/run_impl.tcl")
    assert "default mode=full" in data["readme_flow_caveat"]


def test_vivado_version_parser_and_gate() -> None:
    text = "Vivado v2025.2 (64-bit)\nSW Build 123456"
    assert parse_vivado_version(text) == EXPECTED_VIVADO_VERSION
    assert require_vivado_2025_2(text) == EXPECTED_VIVADO_VERSION
    with pytest.raises(ValueError, match="requires Vivado 2025.2"):
        require_vivado_2025_2("Vivado v2025.1 (64-bit)")


def test_utilization_parser_reads_used_available_and_percent() -> None:
    parsed = parse_utilization_report(_utilization())
    assert parsed["clb_luts"].used == 12345
    assert parsed["clb_luts"].available == 117120
    assert parsed["clb_luts"].utilization_percent == pytest.approx(10.54)
    assert parsed["clb_registers"].used == 23456
    assert parsed["bram_tiles"].used == pytest.approx(42.5)
    assert parsed["dsps"].used == 17
    assert parsed["uram"].used == 0


def test_utilization_parser_fails_closed_if_major_resource_row_is_missing() -> None:
    with pytest.raises(ValueError, match="missing required rows"):
        parse_utilization_report(_utilization().replace("| DSPs", "| NOT_DSP"))


def test_timing_parser_uses_numeric_summary_positions_not_header_word_count() -> None:
    parsed = parse_timing_summary(_timing())
    assert parsed == {"wns_ns": pytest.approx(0.321), "whs_ns": pytest.approx(0.014)}


def test_hardware_result_records_timing_closure_and_no_physical_claim() -> None:
    result = build_catalyst_hardware_result(
        vivado_version="2025.2",
        utilization_text=_utilization(),
        timing_text=_timing(),
        source_reports={"utilization": "utilization.rpt", "timing": "timing_summary.rpt"},
    )
    assert result["schema"] == M13_5_RESULT_SCHEMA
    assert result["target_part"] == "xczu5ev-sfvc784-2-i"
    assert result["timing_closed"] is True
    assert result["physical_programming_source_supported"] is False
    assert result["resources"]["clb_luts"]["used"] == 12345


def test_hardware_result_preserves_negative_timing_as_failed_closure() -> None:
    result = build_catalyst_hardware_result(
        vivado_version="2025.2",
        utilization_text=_utilization(),
        timing_text=_timing(wns=-0.123, whs=0.005),
    )
    assert result["timing_closed"] is False
    assert result["timing"]["wns_ns"] == pytest.approx(-0.123)


def test_manifest_is_plain_json_and_round_trips() -> None:
    path = Path("references/m13_5_hardware_manifest.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert json.loads(json.dumps(data))["schema"] == M13_5_HARDWARE_SCHEMA
