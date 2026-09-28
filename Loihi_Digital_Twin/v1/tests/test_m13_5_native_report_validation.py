from __future__ import annotations

import json
from pathlib import Path

import pytest

from neuromorphic_twin.m13_hardware_audit import build_catalyst_hardware_result
from neuromorphic_twin.m13_native_report_validation import verify_native_report_regeneration


def _utilization(luts: int = 12345) -> str:
    return f"""
+----------------------------+-------+-------+-----------+-------+
| Site Type                  | Used  | Fixed | Available | Util% |
+----------------------------+-------+-------+-----------+-------+
| CLB LUTs                   | {luts:5d} |     0 |    117120 | 10.54 |
| CLB Registers              | 23456 |     0 |    234240 | 10.01 |
| Block RAM Tile             |  42.5 |     0 |       144 | 29.51 |
| DSPs                       |    17 |     0 |      1248 |  1.36 |
| URAM                       |     0 |     0 |        64 |  0.00 |
+----------------------------+-------+-------+-----------+-------+
"""


def _timing(wns: float = 0.001, whs: float = 0.013) -> str:
    return f"""
Design Timing Summary
---------------------
WNS(ns)      TNS(ns)  TNS Failing Endpoints  TNS Total Endpoints      WHS(ns)      THS(ns)  THS Failing Endpoints  THS Total Endpoints
-------      -------  ---------------------  -------------------      -------      -------  ---------------------  -------------------
 {wns:.3f}        0.000                      0                 1234        {whs:.3f}        0.000                      0                 1234
"""


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "evidence"
    native = root / "native_reports"
    native.mkdir(parents=True)
    utilization = native / "utilization.rpt"
    timing = native / "timing_summary.rpt"
    utilization.write_text(_utilization(), encoding="utf-8")
    timing.write_text(_timing(), encoding="utf-8")
    source_reports = {
        "utilization": str(utilization),
        "timing": str(timing),
    }
    result = build_catalyst_hardware_result(
        vivado_version="2025.2",
        utilization_text=utilization.read_text(encoding="utf-8"),
        timing_text=timing.read_text(encoding="utf-8"),
        source_reports=source_reports,
    )
    (root / "catalyst-hardware-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return root


def test_native_reports_exactly_regenerate_saved_result(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    result = verify_native_report_regeneration(root)
    assert result["timing"] == {"wns_ns": 0.001, "whs_ns": 0.013}
    assert result["resources"]["clb_luts"]["used"] == 12345


def test_native_timing_drift_is_rejected(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "native_reports" / "timing_summary.rpt").write_text(_timing(wns=0.101), encoding="utf-8")
    with pytest.raises(ValueError, match="does not exactly regenerate"):
        verify_native_report_regeneration(root)


def test_native_resource_drift_is_rejected(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "native_reports" / "utilization.rpt").write_text(_utilization(luts=12000), encoding="utf-8")
    with pytest.raises(ValueError, match="does not exactly regenerate"):
        verify_native_report_regeneration(root)


def test_missing_native_report_is_rejected(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "native_reports" / "timing_summary.rpt").unlink()
    with pytest.raises(ValueError, match="missing required file"):
        verify_native_report_regeneration(root)
