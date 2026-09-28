"""Independent native-report regeneration gate for M13.5.3 closure.

This module intentionally re-parses the preserved routed Vivado utilization and
timing reports instead of trusting the already-normalized JSON result.  The
reparsed result must match the saved result exactly before evidence promotion is
allowed to continue.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .m13_hardware_audit import build_catalyst_hardware_result


def verify_native_report_regeneration(evidence_dir: str | Path) -> dict[str, Any]:
    root = Path(evidence_dir).resolve()
    result_path = root / "catalyst-hardware-result.json"
    utilization_path = root / "native_reports" / "utilization.rpt"
    timing_path = root / "native_reports" / "timing_summary.rpt"

    for path in (result_path, utilization_path, timing_path):
        if not path.is_file():
            raise ValueError(f"M13.5 native-report regeneration missing required file: {path}")

    result = json.loads(result_path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError("M13.5 normalized hardware result must be a JSON object")

    source_reports = result.get("source_reports")
    if not isinstance(source_reports, dict):
        raise ValueError("M13.5 normalized result source_reports must be an object")

    reparsed = build_catalyst_hardware_result(
        vivado_version=str(result.get("vivado", "")),
        utilization_text=utilization_path.read_text(encoding="utf-8", errors="replace"),
        timing_text=timing_path.read_text(encoding="utf-8", errors="replace"),
        source_reports=source_reports,
    )
    if reparsed != result:
        raise ValueError(
            "M13.5 normalized hardware result does not exactly regenerate from the preserved native Vivado reports"
        )
    return reparsed
