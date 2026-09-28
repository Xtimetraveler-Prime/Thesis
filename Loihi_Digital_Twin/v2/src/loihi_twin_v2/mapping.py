"""Minimal deterministic deployment representation for P02.

Full graph partitioning/optimization belongs to P06. P02 only defines the
machine-readable object consumed by the golden model and validates it.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
import hashlib
import json

from .chip import LogicalChip
from .core import LogicalCoreConfig


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
        return {str(key): _primitive(item) for key, item in sorted(value.items(), key=lambda x: str(x[0]))}
    return value


class Deployment:
    version = "v2.0-p02"

    def __init__(self, core_configs: tuple[LogicalCoreConfig, ...]) -> None:
        self.core_configs = core_configs
        LogicalChip(core_configs)

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(
            {"version": self.version, "cores": _primitive(self.core_configs)},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def manifest(self) -> dict:
        return {
            "version": self.version,
            "fingerprint": self.fingerprint,
            "logical_core_count": len(self.core_configs),
            "cores": [
                {
                    "core_id": config.core_id,
                    "resource_usage": config.resource_usage.as_dict(),
                    "synapse_cost_model": config.synapse_cost_model.name,
                }
                for config in sorted(self.core_configs, key=lambda x: x.core_id)
            ],
        }

    def build_chip(self) -> LogicalChip:
        return LogicalChip(self.core_configs)
