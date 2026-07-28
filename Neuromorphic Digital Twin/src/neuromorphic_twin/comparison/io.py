"""Stable JSON interchange for software, RTL, and FPGA traces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import BackendTick, BackendTrace, ComparisonReport

_TRACE_SCHEMA = "neuromorphic-twin-trace-v1"
_REPORT_SCHEMA = "neuromorphic-twin-comparison-v1"


def write_trace_json(trace: BackendTrace, path: str | Path) -> Path:
    """Write one backend trace as a portable, deterministic JSON artifact."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": _TRACE_SCHEMA,
        "backend": trace.backend,
        "scenario": trace.scenario,
        "metadata": dict(trace.metadata),
        "ticks": [
            {
                "tick": tick.tick,
                "current_before": list(tick.current_before),
                "voltage_before": list(tick.voltage_before),
                "current_after": list(tick.current_after),
                "voltage_after": list(tick.voltage_after),
                "spikes": list(tick.spikes),
            }
            for tick in trace.ticks
        ],
    }
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output


def read_trace_json(path: str | Path) -> BackendTrace:
    """Load a trace written by :func:`write_trace_json`."""

    payload: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != _TRACE_SCHEMA:
        raise ValueError(
            f"unsupported trace schema {payload.get('schema')!r}; "
            f"expected {_TRACE_SCHEMA!r}"
        )

    ticks = tuple(
        BackendTick(
            tick=int(item["tick"]),
            current_before=tuple(int(v) for v in item["current_before"]),
            voltage_before=tuple(int(v) for v in item["voltage_before"]),
            current_after=tuple(int(v) for v in item["current_after"]),
            voltage_after=tuple(int(v) for v in item["voltage_after"]),
            spikes=tuple(int(v) for v in item["spikes"]),
        )
        for item in payload["ticks"]
    )
    metadata = tuple(
        (str(key), str(value))
        for key, value in sorted(payload.get("metadata", {}).items())
    )
    return BackendTrace(
        backend=str(payload["backend"]),
        scenario=str(payload["scenario"]),
        ticks=ticks,
        metadata=metadata,
    )


def write_report_json(report: ComparisonReport, path: str | Path) -> Path:
    """Write machine-readable mismatch information for regression tests."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": _REPORT_SCHEMA,
        "passed": report.passed,
        "reference_backend": report.reference_backend,
        "candidate_backend": report.candidate_backend,
        "scenario": report.scenario,
        "compared_ticks": report.compared_ticks,
        "mismatches": [
            {
                "tick": mismatch.tick,
                "field": mismatch.field,
                "neuron_id": mismatch.neuron_id,
                "reference": mismatch.reference,
                "candidate": mismatch.candidate,
            }
            for mismatch in report.mismatches
        ],
    }
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output
