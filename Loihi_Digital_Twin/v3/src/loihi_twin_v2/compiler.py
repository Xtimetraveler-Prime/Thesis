"""P06 deterministic network mapper/compiler.

This module maps a project-defined population/projection graph onto the existing
validated :class:`LogicalCoreConfig` boundary.  The compiler is deliberately
architectural: it assigns logical cores, compartments, input axons, reusable
synapse templates, and output routes without exposing FPGA context slots or
physical execution-engine identity.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Iterable

from .arithmetic import ArithmeticConfig
from .axon import InputAxonBinding, OutputRoute, OutputRouteEntry
from .compartment import CompartmentConfig
from .core import LogicalCoreConfig
from .hardware_p03 import P03_REQUIRED_ARITHMETIC
from .mapping import Deployment
from .packet import SpikePacket
from .resources import (
    DEFAULT_CORE_CAPACITY,
    MAX_COMPARTMENTS_PER_CORE,
    MAX_LOGICAL_CORES,
    CoreCapacity,
    ResourceCapacityError,
)
from .synapse import SynapseEntry, SynapseTemplate

P06_NETWORK_SCHEMA = "p06-network-v1"
P06_DEPLOYMENT_SCHEMA = "v2.1-p06"
P06_COMPILER_VERSION = "p06-deterministic-first-fit-v1"


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
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    return value


def _canonical_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class MappingError(ValueError):
    """Explicit mapper failure with a stable diagnostic code."""

    def __init__(self, code: str, message: str, **context: object) -> None:
        self.code = code
        self.context = dict(context)
        detail = " ".join(f"{key}={value}" for key, value in sorted(self.context.items()))
        super().__init__(f"{code}: {message}" + (f" ({detail})" if detail else ""))


@dataclass(frozen=True, slots=True)
class PopulationSpec:
    name: str
    size: int
    compartment: CompartmentConfig

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("population name cannot be empty")
        if self.size <= 0:
            raise ValueError("population size must be positive")


@dataclass(frozen=True, slots=True)
class InputPopulationSpec:
    name: str
    size: int

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("input population name cannot be empty")
        if self.size <= 0:
            raise ValueError("input population size must be positive")


@dataclass(frozen=True, slots=True, order=True)
class ProjectionConnection:
    source_index: int
    destination_index: int
    weight: int
    delay: int = 0

    def __post_init__(self) -> None:
        if self.source_index < 0 or self.destination_index < 0:
            raise ValueError("projection indices cannot be negative")
        if self.delay != 0:
            raise ValueError("P06 execution currently supports synaptic delay 0 only")


@dataclass(frozen=True, slots=True)
class ProjectionSpec:
    name: str
    source_population: str
    destination_population: str
    connections: tuple[ProjectionConnection, ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("projection name cannot be empty")
        if not self.connections:
            raise ValueError("projection must contain at least one connection")
        pairs = [(c.source_index, c.destination_index) for c in self.connections]
        if len(pairs) != len(set(pairs)):
            raise ValueError(f"projection {self.name!r} contains duplicate source/destination pairs")


@dataclass(frozen=True, slots=True)
class InputProjectionSpec:
    name: str
    source_input: str
    destination_population: str
    connections: tuple[ProjectionConnection, ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("input projection name cannot be empty")
        if not self.connections:
            raise ValueError("input projection must contain at least one connection")
        pairs = [(c.source_index, c.destination_index) for c in self.connections]
        if len(pairs) != len(set(pairs)):
            raise ValueError(
                f"input projection {self.name!r} contains duplicate source/destination pairs"
            )


@dataclass(frozen=True, slots=True)
class NetworkSpec:
    populations: tuple[PopulationSpec, ...]
    projections: tuple[ProjectionSpec, ...] = ()
    input_populations: tuple[InputPopulationSpec, ...] = ()
    input_projections: tuple[InputProjectionSpec, ...] = ()

    def __post_init__(self) -> None:
        if not self.populations:
            raise ValueError("network must contain at least one neuron population")
        pop_names = [population.name for population in self.populations]
        input_names = [population.name for population in self.input_populations]
        projection_names = [projection.name for projection in self.projections]
        input_projection_names = [projection.name for projection in self.input_projections]
        if len(pop_names) != len(set(pop_names)):
            raise ValueError("neuron population names must be unique")
        if len(input_names) != len(set(input_names)):
            raise ValueError("input population names must be unique")
        if set(pop_names) & set(input_names):
            raise ValueError("neuron and input population names must be disjoint")
        all_projection_names = projection_names + input_projection_names
        if len(all_projection_names) != len(set(all_projection_names)):
            raise ValueError("projection names must be unique")

        pops = {population.name: population for population in self.populations}
        inputs = {population.name: population for population in self.input_populations}
        seen_neural_edges: set[tuple[str, int, str, int]] = set()
        seen_input_edges: set[tuple[str, int, str, int]] = set()
        for projection in self.projections:
            if projection.source_population not in pops:
                raise ValueError(f"projection {projection.name!r} references missing source population")
            if projection.destination_population not in pops:
                raise ValueError(
                    f"projection {projection.name!r} references missing destination population"
                )
            source = pops[projection.source_population]
            destination = pops[projection.destination_population]
            for connection in projection.connections:
                if connection.source_index >= source.size:
                    raise ValueError(f"projection {projection.name!r} source index is out of range")
                if connection.destination_index >= destination.size:
                    raise ValueError(
                        f"projection {projection.name!r} destination index is out of range"
                    )
                key = (
                    projection.source_population,
                    connection.source_index,
                    projection.destination_population,
                    connection.destination_index,
                )
                if key in seen_neural_edges:
                    raise ValueError(f"duplicate neural connection across projections: {key}")
                seen_neural_edges.add(key)

        for projection in self.input_projections:
            if projection.source_input not in inputs:
                raise ValueError(
                    f"input projection {projection.name!r} references missing input population"
                )
            if projection.destination_population not in pops:
                raise ValueError(
                    f"input projection {projection.name!r} references missing destination population"
                )
            source = inputs[projection.source_input]
            destination = pops[projection.destination_population]
            for connection in projection.connections:
                if connection.source_index >= source.size:
                    raise ValueError(
                        f"input projection {projection.name!r} source index is out of range"
                    )
                if connection.destination_index >= destination.size:
                    raise ValueError(
                        f"input projection {projection.name!r} destination index is out of range"
                    )
                key = (
                    projection.source_input,
                    connection.source_index,
                    projection.destination_population,
                    connection.destination_index,
                )
                if key in seen_input_edges:
                    raise ValueError(f"duplicate external connection across projections: {key}")
                seen_input_edges.add(key)

    @property
    def fingerprint(self) -> str:
        return _canonical_hash(self._canonical_payload())

    def _canonical_payload(self) -> dict:
        return {
            "schema": P06_NETWORK_SCHEMA,
            "populations": [
                _primitive(population)
                for population in sorted(self.populations, key=lambda item: item.name)
            ],
            "input_populations": [
                _primitive(population)
                for population in sorted(self.input_populations, key=lambda item: item.name)
            ],
            "projections": [
                {
                    "name": projection.name,
                    "source_population": projection.source_population,
                    "destination_population": projection.destination_population,
                    "connections": [
                        _primitive(connection)
                        for connection in sorted(projection.connections)
                    ],
                }
                for projection in sorted(self.projections, key=lambda item: item.name)
            ],
            "input_projections": [
                {
                    "name": projection.name,
                    "source_input": projection.source_input,
                    "destination_population": projection.destination_population,
                    "connections": [
                        _primitive(connection)
                        for connection in sorted(projection.connections)
                    ],
                }
                for projection in sorted(self.input_projections, key=lambda item: item.name)
            ],
        }

    def to_dict(self) -> dict:
        payload = self._canonical_payload()
        payload["fingerprint"] = self.fingerprint
        return payload

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent) + "\n"

    def write_json(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self.to_json(), encoding="utf-8")
        return output

    @classmethod
    def from_dict(cls, payload: dict) -> "NetworkSpec":
        if payload.get("schema") != P06_NETWORK_SCHEMA:
            raise ValueError(
                f"unsupported network schema {payload.get('schema')!r}; expected {P06_NETWORK_SCHEMA!r}"
            )
        populations = tuple(
            PopulationSpec(
                name=item["name"],
                size=item["size"],
                compartment=CompartmentConfig(**item["compartment"]),
            )
            for item in payload.get("populations", [])
        )
        input_populations = tuple(
            InputPopulationSpec(**item) for item in payload.get("input_populations", [])
        )
        projections = tuple(
            ProjectionSpec(
                name=item["name"],
                source_population=item["source_population"],
                destination_population=item["destination_population"],
                connections=tuple(
                    ProjectionConnection(**connection)
                    for connection in item.get("connections", [])
                ),
            )
            for item in payload.get("projections", [])
        )
        input_projections = tuple(
            InputProjectionSpec(
                name=item["name"],
                source_input=item["source_input"],
                destination_population=item["destination_population"],
                connections=tuple(
                    ProjectionConnection(**connection)
                    for connection in item.get("connections", [])
                ),
            )
            for item in payload.get("input_projections", [])
        )
        network = cls(populations, projections, input_populations, input_projections)
        recorded = payload.get("fingerprint")
        if recorded is not None and recorded != network.fingerprint:
            raise ValueError("network fingerprint does not match serialized contents")
        return network

    @classmethod
    def from_json(cls, text: str) -> "NetworkSpec":
        return cls.from_dict(json.loads(text))

    @classmethod
    def read_json(cls, path: str | Path) -> "NetworkSpec":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class MappingOptions:
    compartments_per_core: int = MAX_COMPARTMENTS_PER_CORE
    max_logical_cores: int = MAX_LOGICAL_CORES
    arithmetic: ArithmeticConfig = P03_REQUIRED_ARITHMETIC
    capacity: CoreCapacity = DEFAULT_CORE_CAPACITY

    def __post_init__(self) -> None:
        if not 1 <= self.compartments_per_core <= self.capacity.compartments:
            raise ValueError("compartments_per_core must be within the configured core capacity")
        if not 1 <= self.max_logical_cores <= MAX_LOGICAL_CORES:
            raise ValueError("max_logical_cores is outside the logical chip capacity")


@dataclass(frozen=True, slots=True, order=True)
class PlacementRecord:
    population: str
    neuron_index: int
    core_id: int
    compartment_id: int


@dataclass(frozen=True, slots=True, order=True)
class IngressRoute:
    input_population: str
    input_index: int
    destination_core: int
    destination_axon: int


@dataclass(frozen=True, slots=True)
class CompiledDeployment:
    source_fingerprint: str
    logical_deployment: Deployment
    placement: tuple[PlacementRecord, ...]
    ingress_routes: tuple[IngressRoute, ...]
    compiler_version: str = P06_COMPILER_VERSION

    @property
    def fingerprint(self) -> str:
        return _canonical_hash(self._canonical_payload())

    def _canonical_payload(self) -> dict:
        return {
            "schema": P06_DEPLOYMENT_SCHEMA,
            "compiler_version": self.compiler_version,
            "source_fingerprint": self.source_fingerprint,
            "logical_deployment": self.logical_deployment.to_dict(),
            "placement": [_primitive(item) for item in sorted(self.placement)],
            "ingress_routes": [_primitive(item) for item in sorted(self.ingress_routes)],
        }

    def to_dict(self) -> dict:
        payload = self._canonical_payload()
        payload["fingerprint"] = self.fingerprint
        payload["report"] = self.report()
        return payload

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent) + "\n"

    def write_json(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self.to_json(), encoding="utf-8")
        return output

    @classmethod
    def from_dict(cls, payload: dict) -> "CompiledDeployment":
        if payload.get("schema") != P06_DEPLOYMENT_SCHEMA:
            raise ValueError(
                f"unsupported compiled deployment schema {payload.get('schema')!r}; "
                f"expected {P06_DEPLOYMENT_SCHEMA!r}"
            )
        compiled = cls(
            source_fingerprint=payload["source_fingerprint"],
            logical_deployment=Deployment.from_dict(payload["logical_deployment"]),
            placement=tuple(PlacementRecord(**item) for item in payload.get("placement", [])),
            ingress_routes=tuple(
                IngressRoute(**item) for item in payload.get("ingress_routes", [])
            ),
            compiler_version=payload.get("compiler_version", ""),
        )
        if compiled.compiler_version != P06_COMPILER_VERSION:
            raise ValueError(
                f"unsupported compiler version {compiled.compiler_version!r}; "
                f"expected {P06_COMPILER_VERSION!r}"
            )
        recorded = payload.get("fingerprint")
        if recorded is not None and recorded != compiled.fingerprint:
            raise ValueError("compiled deployment fingerprint does not match serialized contents")
        return compiled

    @classmethod
    def from_json(cls, text: str) -> "CompiledDeployment":
        return cls.from_dict(json.loads(text))

    @classmethod
    def read_json(cls, path: str | Path) -> "CompiledDeployment":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    def build_chip(self):
        return self.logical_deployment.build_chip()

    def external_packets(
        self,
        input_population: str,
        active_indices: Iterable[int],
        *,
        target_timestep: int,
    ) -> tuple[SpikePacket, ...]:
        requested = set(active_indices)
        routes = [
            route
            for route in self.ingress_routes
            if route.input_population == input_population and route.input_index in requested
        ]
        known_indices = {
            route.input_index
            for route in self.ingress_routes
            if route.input_population == input_population
        }
        unknown = requested - known_indices
        if unknown:
            raise KeyError(
                f"input population {input_population!r} has no mapped routes for indices {sorted(unknown)}"
            )
        return tuple(
            SpikePacket(
                target_timestep=target_timestep,
                destination_core=route.destination_core,
                destination_axon=route.destination_axon,
            )
            for route in sorted(routes)
        )

    def report(self) -> dict:
        cores = []
        total_shared = 0
        total_expanded = 0
        total_routes = 0
        local_routes = 0
        remote_routes = 0
        for config in self.logical_deployment.core_configs:
            usage = config.resource_usage
            total_shared += usage.shared_parameters
            total_expanded += usage.expanded_connections
            total_routes += usage.output_routes
            core_local = 0
            core_remote = 0
            for entry in config.output_routes:
                for route in entry.routes:
                    if route.destination_core == config.core_id:
                        core_local += 1
                    else:
                        core_remote += 1
            local_routes += core_local
            remote_routes += core_remote
            cores.append(
                {
                    "core_id": config.core_id,
                    "usage": usage.as_dict(),
                    "headroom": {
                        "compartments": config.capacity.compartments - usage.compartments,
                        "input_axons": config.capacity.input_axons - usage.input_axons,
                        "output_routes": config.capacity.output_routes - usage.output_routes,
                        "synapse_bytes": config.capacity.synapse_bytes - usage.synapse_bytes,
                    },
                    "local_routes": core_local,
                    "remote_routes": core_remote,
                }
            )
        sharing_ratio = (
            float(total_expanded) / float(total_shared) if total_shared else 1.0
        )
        return {
            "schema": P06_DEPLOYMENT_SCHEMA,
            "compiler_version": self.compiler_version,
            "fingerprint": self.fingerprint,
            "source_fingerprint": self.source_fingerprint,
            "logical_core_count": len(self.logical_deployment.core_configs),
            "placement_count": len(self.placement),
            "ingress_route_count": len(self.ingress_routes),
            "static_route_estimate": {
                "total": total_routes,
                "local": local_routes,
                "remote": remote_routes,
            },
            "connection_sharing": {
                "expanded_connections": total_expanded,
                "stored_shared_parameters": total_shared,
                "expanded_per_stored_parameter": sharing_ratio,
            },
            "cores": cores,
        }


def _normalized_pattern(entries: list[tuple[int, int]]) -> tuple[int, tuple[tuple[int, int], ...]]:
    ordered = sorted(entries)
    targets = [target for target, _weight in ordered]
    if len(targets) != len(set(targets)):
        raise MappingError(
            "duplicate_target",
            "one source maps more than once to the same destination compartment",
        )
    base = min(targets)
    return base, tuple((target - base, weight) for target, weight in ordered)


def compile_network(
    network: NetworkSpec,
    options: MappingOptions = MappingOptions(),
) -> CompiledDeployment:
    """Deterministically map a high-level network into logical-core resources."""

    populations = sorted(network.populations, key=lambda item: item.name)
    placement: list[PlacementRecord] = []
    placement_lookup: dict[tuple[str, int], PlacementRecord] = {}
    core_compartments: list[list[CompartmentConfig]] = [[]]

    core_id = 0
    for population in populations:
        for neuron_index in range(population.size):
            if len(core_compartments[core_id]) >= options.compartments_per_core:
                core_id += 1
                if core_id >= options.max_logical_cores:
                    raise MappingError(
                        "logical_core_capacity",
                        "network requires more logical cores than mapper policy permits",
                        required=core_id + 1,
                        limit=options.max_logical_cores,
                    )
                core_compartments.append([])
            compartment_id = len(core_compartments[core_id])
            record = PlacementRecord(
                population=population.name,
                neuron_index=neuron_index,
                core_id=core_id,
                compartment_id=compartment_id,
            )
            placement.append(record)
            placement_lookup[(population.name, neuron_index)] = record
            core_compartments[core_id].append(population.compartment)

    # Each source -> destination-core group becomes one destination axon. The
    # group's relative weighted fanout becomes a reusable synapse template.
    neural_groups: dict[tuple[str, int, int], list[tuple[int, int]]] = {}
    input_groups: dict[tuple[str, int, int], list[tuple[int, int]]] = {}

    for projection in sorted(network.projections, key=lambda item: item.name):
        for connection in sorted(projection.connections):
            source = placement_lookup[(projection.source_population, connection.source_index)]
            destination = placement_lookup[
                (projection.destination_population, connection.destination_index)
            ]
            key = (projection.source_population, connection.source_index, destination.core_id)
            neural_groups.setdefault(key, []).append(
                (destination.compartment_id, connection.weight)
            )

    for projection in sorted(network.input_projections, key=lambda item: item.name):
        for connection in sorted(projection.connections):
            destination = placement_lookup[
                (projection.destination_population, connection.destination_index)
            ]
            key = (projection.source_input, connection.source_index, destination.core_id)
            input_groups.setdefault(key, []).append(
                (destination.compartment_id, connection.weight)
            )

    groups_by_destination: dict[
        int, list[tuple[tuple[str, str, int, int], int, tuple[tuple[int, int], ...]]]
    ] = {index: [] for index in range(len(core_compartments))}

    for (population, source_index, destination_core), entries in neural_groups.items():
        base, pattern = _normalized_pattern(entries)
        groups_by_destination[destination_core].append(
            (("neuron", population, source_index, destination_core), base, pattern)
        )
    for (input_name, source_index, destination_core), entries in input_groups.items():
        base, pattern = _normalized_pattern(entries)
        groups_by_destination[destination_core].append(
            (("input", input_name, source_index, destination_core), base, pattern)
        )

    templates_by_core: dict[int, tuple[SynapseTemplate, ...]] = {}
    axons_by_core: dict[int, tuple[InputAxonBinding, ...]] = {}
    routes_by_source: dict[int, dict[int, list[OutputRoute]]] = {
        index: {} for index in range(len(core_compartments))
    }
    ingress_routes: list[IngressRoute] = []

    for destination_core in range(len(core_compartments)):
        groups = sorted(groups_by_destination[destination_core], key=lambda item: item[0])
        patterns = sorted({pattern for _key, _base, pattern in groups})
        template_ids = {pattern: index for index, pattern in enumerate(patterns)}
        templates_by_core[destination_core] = tuple(
            SynapseTemplate(
                template_id=template_ids[pattern],
                entries=tuple(
                    SynapseEntry(target_compartment=offset, weight=weight)
                    for offset, weight in pattern
                ),
            )
            for pattern in patterns
        )

        bindings: list[InputAxonBinding] = []
        for axon_id, (key, base, pattern) in enumerate(groups):
            bindings.append(
                InputAxonBinding(
                    axon_id=axon_id,
                    template_id=template_ids[pattern],
                    target_offset=base,
                )
            )
            kind, source_name, source_index, _destination_core = key
            if kind == "neuron":
                source = placement_lookup[(source_name, source_index)]
                routes_by_source[source.core_id].setdefault(
                    source.compartment_id, []
                ).append(OutputRoute(destination_core, axon_id))
            else:
                ingress_routes.append(
                    IngressRoute(source_name, source_index, destination_core, axon_id)
                )
        axons_by_core[destination_core] = tuple(bindings)

    core_configs: list[LogicalCoreConfig] = []
    for current_core in range(len(core_compartments)):
        route_entries = tuple(
            OutputRouteEntry(
                source_compartment=source_compartment,
                routes=tuple(
                    sorted(
                        routes,
                        key=lambda route: (route.destination_core, route.destination_axon),
                    )
                ),
            )
            for source_compartment, routes in sorted(routes_by_source[current_core].items())
        )
        try:
            core_configs.append(
                LogicalCoreConfig(
                    core_id=current_core,
                    compartments=tuple(core_compartments[current_core]),
                    input_axons=axons_by_core[current_core],
                    synapse_templates=templates_by_core[current_core],
                    output_routes=route_entries,
                    arithmetic=options.arithmetic,
                    capacity=options.capacity,
                )
            )
        except ResourceCapacityError as exc:
            raise MappingError(
                "core_resource_capacity",
                "mapped logical core exceeds a hard resource limit",
                core_id=current_core,
                resource=exc.resource,
                used=exc.used,
                limit=exc.limit,
            ) from exc

    deployment = Deployment(tuple(core_configs))
    return CompiledDeployment(
        source_fingerprint=network.fingerprint,
        logical_deployment=deployment,
        placement=tuple(sorted(placement)),
        ingress_routes=tuple(sorted(ingress_routes)),
    )
