"""Loihi-1 logical resource limits and versioned v2 accounting policy."""

from __future__ import annotations

from dataclasses import dataclass


MAX_LOGICAL_CORES = 128
MAX_COMPARTMENTS_PER_CORE = 1024
MAX_INPUT_AXONS_PER_CORE = 4096
MAX_OUTPUT_ROUTES_PER_CORE = 4096
MAX_SYNAPSE_MEMORY_BYTES_PER_CORE = 128 * 1024


class ResourceCapacityError(ValueError):
    def __init__(self, resource: str, used: int, limit: int) -> None:
        self.resource = resource
        self.used = used
        self.limit = limit
        super().__init__(f"{resource} capacity exceeded: used={used} limit={limit}")


@dataclass(frozen=True, slots=True)
class CoreCapacity:
    compartments: int = MAX_COMPARTMENTS_PER_CORE
    input_axons: int = MAX_INPUT_AXONS_PER_CORE
    output_routes: int = MAX_OUTPUT_ROUTES_PER_CORE
    synapse_bytes: int = MAX_SYNAPSE_MEMORY_BYTES_PER_CORE


DEFAULT_CORE_CAPACITY = CoreCapacity()


@dataclass(frozen=True, slots=True)
class SynapseCostModel:
    """Project-defined conservative v2.0 storage model, not native SRAM packing.

    The model is deliberately isolated so later sparse/dense/run-length Loihi
    encodings can replace it without changing logical connectivity semantics.
    """

    name: str = "v2-simple-32bit-entry"
    bytes_per_template_header: int = 4
    bytes_per_template_entry: int = 4
    bytes_per_axon_binding: int = 4

    def __post_init__(self) -> None:
        for name, value in (
            ("bytes_per_template_header", self.bytes_per_template_header),
            ("bytes_per_template_entry", self.bytes_per_template_entry),
            ("bytes_per_axon_binding", self.bytes_per_axon_binding),
        ):
            if value < 0:
                raise ValueError(f"{name} cannot be negative")

    def template_bytes(self, entry_count: int) -> int:
        return self.bytes_per_template_header + entry_count * self.bytes_per_template_entry

    def bindings_bytes(self, binding_count: int) -> int:
        return binding_count * self.bytes_per_axon_binding


DEFAULT_SYNAPSE_COST_MODEL = SynapseCostModel()


@dataclass(frozen=True, slots=True)
class ResourceUsage:
    compartments: int
    input_axons: int
    output_routes: int
    synapse_bytes: int
    shared_parameters: int
    expanded_connections: int

    def as_dict(self) -> dict[str, int]:
        return {
            "compartments": self.compartments,
            "input_axons": self.input_axons,
            "output_routes": self.output_routes,
            "synapse_bytes": self.synapse_bytes,
            "shared_parameters": self.shared_parameters,
            "expanded_connections": self.expanded_connections,
        }


def validate_resource_usage(
    usage: ResourceUsage,
    capacity: CoreCapacity = DEFAULT_CORE_CAPACITY,
) -> None:
    for resource in ("compartments", "input_axons", "output_routes", "synapse_bytes"):
        used = getattr(usage, resource)
        limit = getattr(capacity, resource)
        if used > limit:
            raise ResourceCapacityError(resource, used, limit)
