"""Stable JSON interchange for software, RTL, and FPGA traces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import BackendSynapse, BackendTick, BackendTrace, ComparisonReport

_TRACE_SCHEMA_V1 = "neuromorphic-twin-trace-v1"
_TRACE_SCHEMA_V2 = "neuromorphic-twin-trace-v2"
_TRACE_SCHEMA = _TRACE_SCHEMA_V2
_SUPPORTED_TRACE_SCHEMAS = {_TRACE_SCHEMA_V1, _TRACE_SCHEMA_V2}
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
        "synapses": [_synapse_to_payload(synapse) for synapse in trace.synapses],
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
    """Load a v1 or v2 trace written by :func:`write_trace_json`.

    Version 1 traces remain readable and simply contain no structured synapse
    metadata. Version 2 adds the optional ``synapses`` collection.
    """

    payload: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    schema = payload.get("schema")
    if schema not in _SUPPORTED_TRACE_SCHEMAS:
        raise ValueError(
            f"unsupported trace schema {schema!r}; expected one of "
            f"{sorted(_SUPPORTED_TRACE_SCHEMAS)!r}"
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
    synapses = tuple(
        _synapse_from_payload(item) for item in payload.get("synapses", [])
    )
    return BackendTrace(
        backend=str(payload["backend"]),
        scenario=str(payload["scenario"]),
        ticks=ticks,
        metadata=metadata,
        synapses=synapses,
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


def _synapse_to_payload(synapse: BackendSynapse) -> dict[str, Any]:
    encoding: dict[str, Any] | None = None
    if synapse.is_encoded:
        encoding = {
            "requested_mantissa": synapse.requested_mantissa,
            "quantized_mantissa": synapse.quantized_mantissa,
            "exponent": synapse.exponent,
            "num_weight_bits": synapse.num_weight_bits,
            "sign_mode": synapse.sign_mode,
            "effective_weight_before_clip": synapse.effective_weight_before_clip,
            "clipped": synapse.clipped,
        }

    return {
        "axon_id": synapse.axon_id,
        "target_neuron": synapse.target_neuron,
        "effective_weight": synapse.effective_weight,
        "encoding": encoding,
    }


def _synapse_from_payload(payload: dict[str, Any]) -> BackendSynapse:
    encoding = payload.get("encoding")
    if encoding is None:
        return BackendSynapse(
            axon_id=int(payload["axon_id"]),
            target_neuron=int(payload["target_neuron"]),
            effective_weight=int(payload["effective_weight"]),
        )

    return BackendSynapse(
        axon_id=int(payload["axon_id"]),
        target_neuron=int(payload["target_neuron"]),
        effective_weight=int(payload["effective_weight"]),
        requested_mantissa=int(encoding["requested_mantissa"]),
        quantized_mantissa=int(encoding["quantized_mantissa"]),
        exponent=int(encoding["exponent"]),
        num_weight_bits=int(encoding["num_weight_bits"]),
        sign_mode=str(encoding["sign_mode"]),
        effective_weight_before_clip=int(
            encoding["effective_weight_before_clip"]
        ),
        clipped=bool(encoding["clipped"]),
    )
