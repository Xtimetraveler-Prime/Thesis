"""Machine-readable reporting helpers for P02 deployments and traces."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum

from .mapping import Deployment
from .resources import CoreCapacity
from .trace import ChipTrace


def _primitive(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _primitive(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [_primitive(item) for item in value]
    if isinstance(value, list):
        return [_primitive(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _primitive(item) for key, item in value.items()}
    return value


def deployment_report(deployment: Deployment) -> dict:
    report = deployment.manifest()
    for core_report, config in zip(report["cores"], deployment.core_configs, strict=True):
        capacity: CoreCapacity = config.capacity
        usage = config.resource_usage
        core_report["capacity"] = {
            "compartments": capacity.compartments,
            "input_axons": capacity.input_axons,
            "output_routes": capacity.output_routes,
            "synapse_bytes": capacity.synapse_bytes,
        }
        core_report["headroom"] = {
            "compartments": capacity.compartments - usage.compartments,
            "input_axons": capacity.input_axons - usage.input_axons,
            "output_routes": capacity.output_routes - usage.output_routes,
            "synapse_bytes": capacity.synapse_bytes - usage.synapse_bytes,
        }
    return report


def trace_report(trace: ChipTrace) -> dict:
    """Return a JSON-serializable normalized architecture trace."""

    return _primitive(trace)
