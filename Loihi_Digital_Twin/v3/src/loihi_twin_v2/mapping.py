"""Deterministic deployment representation and serialization for P02.

Full graph partitioning/optimization belongs to P06. P02 defines the stable,
machine-readable object consumed by the golden model and validates it.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path

from .arithmetic import ArithmeticConfig, OverflowMode
from .axon import InputAxonBinding, OutputRoute, OutputRouteEntry
from .chip import LogicalChip
from .compartment import CompartmentConfig
from .core import LogicalCoreConfig
from .resources import CoreCapacity, SynapseCostModel
from .synapse import SynapseEntry, SynapseTemplate


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
        return {
            str(key): _primitive(item)
            for key, item in sorted(value.items(), key=lambda x: str(x[0]))
        }
    return value


def _core_from_dict(payload: dict) -> LogicalCoreConfig:
    arithmetic_payload = payload.get("arithmetic", {})
    capacity_payload = payload.get("capacity", {})
    cost_payload = payload.get("synapse_cost_model", {})

    compartments = tuple(
        CompartmentConfig(**item) for item in payload.get("compartments", [])
    )
    input_axons = tuple(
        InputAxonBinding(**item) for item in payload.get("input_axons", [])
    )
    templates = tuple(
        SynapseTemplate(
            template_id=item["template_id"],
            entries=tuple(SynapseEntry(**entry) for entry in item.get("entries", [])),
            encoding_profile=item.get(
                "encoding_profile", "effective-integer-v1-compatible"
            ),
        )
        for item in payload.get("synapse_templates", [])
    )
    output_routes = tuple(
        OutputRouteEntry(
            source_compartment=item["source_compartment"],
            routes=tuple(OutputRoute(**route) for route in item.get("routes", [])),
        )
        for item in payload.get("output_routes", [])
    )

    arithmetic = ArithmeticConfig(
        state_bits=arithmetic_payload.get("state_bits"),
        overflow=OverflowMode(arithmetic_payload.get("overflow", OverflowMode.NONE.value)),
    )
    capacity = CoreCapacity(
        compartments=capacity_payload.get("compartments", CoreCapacity().compartments),
        input_axons=capacity_payload.get("input_axons", CoreCapacity().input_axons),
        output_routes=capacity_payload.get("output_routes", CoreCapacity().output_routes),
        synapse_bytes=capacity_payload.get("synapse_bytes", CoreCapacity().synapse_bytes),
    )
    cost_model = SynapseCostModel(
        name=cost_payload.get("name", SynapseCostModel().name),
        bytes_per_template_header=cost_payload.get(
            "bytes_per_template_header", SynapseCostModel().bytes_per_template_header
        ),
        bytes_per_template_entry=cost_payload.get(
            "bytes_per_template_entry", SynapseCostModel().bytes_per_template_entry
        ),
        bytes_per_axon_binding=cost_payload.get(
            "bytes_per_axon_binding", SynapseCostModel().bytes_per_axon_binding
        ),
    )

    return LogicalCoreConfig(
        core_id=payload["core_id"],
        compartments=compartments,
        input_axons=input_axons,
        synapse_templates=templates,
        output_routes=output_routes,
        arithmetic=arithmetic,
        capacity=capacity,
        synapse_cost_model=cost_model,
    )


class Deployment:
    """Validated logical-core configuration shared by Python and later FPGA paths."""

    version = "v2.0-p02"

    def __init__(self, core_configs: tuple[LogicalCoreConfig, ...]) -> None:
        self.core_configs = tuple(sorted(core_configs, key=lambda config: config.core_id))
        LogicalChip(self.core_configs)

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
                for config in self.core_configs
            ],
        }

    def to_dict(self) -> dict:
        """Return the full deterministic deployment document."""

        return {
            "version": self.version,
            "fingerprint": self.fingerprint,
            "cores": _primitive(self.core_configs),
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent) + "\n"

    def write_json(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self.to_json(), encoding="utf-8")
        return output

    @classmethod
    def from_dict(cls, payload: dict) -> "Deployment":
        if not isinstance(payload, dict):
            raise TypeError("deployment document must be a mapping")
        version = payload.get("version")
        if version != cls.version:
            raise ValueError(
                f"unsupported deployment version {version!r}; expected {cls.version!r}"
            )
        cores_payload = payload.get("cores")
        if not isinstance(cores_payload, list) or not cores_payload:
            raise ValueError("deployment must contain a non-empty cores list")

        deployment = cls(tuple(_core_from_dict(item) for item in cores_payload))
        recorded = payload.get("fingerprint")
        if recorded is not None and recorded != deployment.fingerprint:
            raise ValueError("deployment fingerprint does not match serialized contents")
        return deployment

    @classmethod
    def from_json(cls, text: str) -> "Deployment":
        return cls.from_dict(json.loads(text))

    @classmethod
    def read_json(cls, path: str | Path) -> "Deployment":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    def build_chip(self) -> LogicalChip:
        return LogicalChip(self.core_configs)
