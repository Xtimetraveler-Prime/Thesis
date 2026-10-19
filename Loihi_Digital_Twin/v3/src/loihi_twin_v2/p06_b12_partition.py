"""P06-B1.2 opt-in destination-neuron, synapse-pressure-aware mapper.

The accepted P06-A compile_network() is unchanged. This module reuses its
NetworkSpec / deployment data contracts and the accepted P03, P02 and P08
exporters, but does NOT reuse its compartment-first placement algorithm.

This is a host-side mapper: the scaled multi-core ingress/firmware streaming
protocol and physical KV260 execution remain separate B1.3 / P07-B gates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path

from .axon import InputAxonBinding, OutputRoute, OutputRouteEntry
from .compiler import (
    CompiledDeployment, IngressRoute, MappingError, NetworkSpec, PlacementRecord,
    P06_DEPLOYMENT_SCHEMA,
)
from .core import LogicalCoreConfig
from .hardware_p03 import P03_REQUIRED_ARITHMETIC
from .mapping import Deployment
from .p06_b1_contract import (
    B1CapacityError, CorePressure, MAX_AXONS, MAX_COMPARTMENTS,
    MAX_EVENTS_PER_BANK, MAX_LOGICAL_SYNAPSE_BYTES, MAX_ROUTES,
    MAX_SYN_WORDS, P05_DIAGNOSTIC_MAX_CORES, audit_compiled_candidate,
)
from .synapse import SynapseEntry, SynapseTemplate

B12_COMPILER_VERSION = "p06-b1.2-destination-synapse-fit-v1"
B12_SCHEMA = "p06-b1.2-synapse-aware-deployment-v1"
# A source group denotes a single external input or a single neural source;
# each has exactly one destination axon per destination core.
_Source = tuple[str, str, int]
_Destination = tuple[str, int]


def _hash(document: dict) -> str:
    return hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _positive_limit(name: str, value: int, bound: int) -> None:
    if type(value) is not int or not 1 <= value <= bound:
        raise ValueError(f"{name} must be an integer in [1, {bound}]")


@dataclass(frozen=True, slots=True)
class B12Options:
    """Strict, optionally smaller-than-hardware fit limits.

    The requested readout population is ALWAYS placed into separate terminal
    logical cores. Other populations are also separated to make source
    identity, traffic direction and later paging analysis unambiguous.
    """

    readout_population: str
    max_logical_cores: int = P05_DIAGNOSTIC_MAX_CORES
    compartments_per_core: int = MAX_COMPARTMENTS
    input_axons_per_core: int = MAX_AXONS
    route_words_per_core: int = MAX_ROUTES
    synapse_words_per_core: int = MAX_SYN_WORDS
    synapse_bytes_per_core: int = MAX_LOGICAL_SYNAPSE_BYTES
    event_bank_per_core: int = MAX_EVENTS_PER_BANK

    def __post_init__(self) -> None:
        if not isinstance(self.readout_population, str) or not self.readout_population:
            raise ValueError("readout_population must be a nonempty population name")
        for name, bound in (
            ("max_logical_cores", P05_DIAGNOSTIC_MAX_CORES),
            ("compartments_per_core", MAX_COMPARTMENTS),
            ("input_axons_per_core", MAX_AXONS),
            ("route_words_per_core", MAX_ROUTES),
            ("synapse_words_per_core", MAX_SYN_WORDS),
            ("synapse_bytes_per_core", MAX_LOGICAL_SYNAPSE_BYTES),
            ("event_bank_per_core", MAX_EVENTS_PER_BANK),
        ):
            _positive_limit(name, getattr(self, name), bound)


@dataclass(slots=True)
class _Draft:
    """Incremental destination core, not a serialized/accepted core image."""

    population: str
    members: list[_Destination] = field(default_factory=list)
    # Per source, an ordered list of (target compartment, signed integer weight).
    inbound: dict[_Source, list[tuple[int, int]]] = field(default_factory=dict)

    def push(self, destination: _Destination, edges: tuple[tuple[_Source, int], ...]) -> None:
        local = len(self.members)
        self.members.append(destination)
        for source, weight in edges:
            self.inbound.setdefault(source, []).append((local, weight))

    def pop(self, edges: tuple[tuple[_Source, int], ...]) -> None:
        self.members.pop()
        for source, _weight in edges:
            targets = self.inbound[source]
            targets.pop()
            if not targets:
                del self.inbound[source]


def _incoming(network: NetworkSpec) -> dict[_Destination, tuple[tuple[_Source, int], ...]]:
    by_dest: dict[_Destination, list[tuple[_Source, int]]] = {
        (population.name, neuron): []
        for population in network.populations
        for neuron in range(population.size)
    }
    for projection in sorted(network.input_projections, key=lambda item: item.name):
        for edge in sorted(projection.connections):
            by_dest[(projection.destination_population, edge.destination_index)].append((
                ("input", projection.source_input, edge.source_index), edge.weight,
            ))
    for projection in sorted(network.projections, key=lambda item: item.name):
        for edge in sorted(projection.connections):
            by_dest[(projection.destination_population, edge.destination_index)].append((
                ("neuron", projection.source_population, edge.source_index), edge.weight,
            ))
    result = {}
    for destination, sources in by_dest.items():
        ordered = sorted(sources, key=lambda item: item[0])
        if len({key for key, _weight in ordered}) != len(ordered):
            raise MappingError("b12_duplicate_source", "duplicate source for destination", destination=destination)
        result[destination] = tuple(ordered)
    return result


def _patterns(inbound: dict[_Source, list[tuple[int, int]]]) -> dict[_Source, tuple[int, tuple[tuple[int, int], ...]]]:
    """Same offset-relative template semantics as the original P06 compiler.

    No merge of distinct signed weight patterns. Sharing occurs ONLY when two
    complete normalized (target-offset, weight) tuples match exactly.
    """
    normalized = {}
    for key, entries in inbound.items():
        ordered = sorted(entries)
        if len({target for target, _ in ordered}) != len(ordered):
            raise MappingError("b12_duplicate_target", "source has duplicate destination compartment")
        base = ordered[0][0]
        normalized[key] = (base, tuple((target - base, weight) for target, weight in ordered))
    return normalized


def _pressure(draft: _Draft) -> CorePressure:
    signatures = _patterns(draft.inbound)
    unique = {pattern for _base, pattern in signatures.values()}
    return CorePressure(
        compartments=len(draft.members),
        input_axons=len(signatures),
        route_words=0,  # egress routes are checked separately once source placement resolves
        synapse_words=sum(len(pattern) for pattern in unique),
        template_headers=len(unique),
        external_events_per_tick=sum(key[0] == "input" for key in signatures),
        routed_events_per_tick=sum(key[0] == "neuron" for key in signatures),
        emitted_packets_per_tick=0,
    )


def _fit(draft: _Draft, options: B12Options) -> tuple[str, int, int] | None:
    pressure = _pressure(draft)
    # A user's smaller-than-physical budget may be used to force partitioning,
    # but no caller can relax the accepted hardware hard limits.
    for name, used, limit in (
        ("compartments", pressure.compartments, options.compartments_per_core),
        ("input_axons", pressure.input_axons, options.input_axons_per_core),
        ("synapse_words", pressure.synapse_words, options.synapse_words_per_core),
        ("synapse_bytes", pressure.synapse_bytes, options.synapse_bytes_per_core),
        ("current_event_bank_events", pressure.current_event_bank_events, options.event_bank_per_core),
    ):
        if used > limit:
            return name, used, limit
    try:
        pressure.validate()
    except B1CapacityError as exc:
        return exc.name, exc.used, exc.limit
    return None


def _place(network: NetworkSpec, options: B12Options) -> list[_Draft]:
    population_map = {population.name: population for population in network.populations}
    if options.readout_population not in population_map:
        raise MappingError("b12_readout_population", "readout population not in source graph",
                           readout_population=options.readout_population)
    # Alphabetical ordering for non-readout populations, terminal readout last.
    names = sorted(p for p in population_map if p != options.readout_population)
    names.append(options.readout_population)
    incoming = _incoming(network)
    drafts: list[_Draft] = []
    for name in names:
        current: _Draft | None = None
        for index in range(population_map[name].size):
            destination = (name, index)
            edges = incoming[destination]
            if current is None:
                if len(drafts) >= options.max_logical_cores:
                    raise MappingError("b12_core_count", "no logical core available for next population",
                                       required=len(drafts) + 1, limit=options.max_logical_cores)
                current = _Draft(population=name)
                drafts.append(current)
            current.push(destination, edges)
            problem = _fit(current, options)
            if problem is None:
                continue
            current.pop(edges)
            # A single destination neuron may be impossible to represent:
            # reject explicitly instead of silently dropping any synapse.
            if not current.members:
                resource, used, limit = problem
                raise MappingError("b12_unplaceable_neuron", "neuron cannot fit empty hardware core",
                                   population=name, neuron_index=index,
                                   resource=resource, used=used, limit=limit)
            if len(drafts) >= options.max_logical_cores:
                resource, used, limit = problem
                raise MappingError("b12_core_count", "synapse-aware split exceeds logical core budget",
                                   required=len(drafts) + 1, limit=options.max_logical_cores,
                                   resource=resource, used=used)
            current = _Draft(population=name)
            drafts.append(current)
            current.push(destination, edges)
            problem = _fit(current, options)
            if problem is not None:
                resource, used, limit = problem
                raise MappingError("b12_unplaceable_neuron", "neuron cannot fit empty hardware core",
                                   population=name, neuron_index=index,
                                   resource=resource, used=used, limit=limit)
    return drafts


def _emit_compiled(network: NetworkSpec, drafts: list[_Draft], options: B12Options) -> CompiledDeployment:
    populations = {population.name: population for population in network.populations}
    placement: list[PlacementRecord] = []
    locations: dict[_Destination, PlacementRecord] = {}
    for core_id, draft in enumerate(drafts):
        for compartment_id, (population, neuron_index) in enumerate(draft.members):
            record = PlacementRecord(population, neuron_index, core_id, compartment_id)
            placement.append(record)
            locations[(population, neuron_index)] = record

    routes_by_source: dict[int, dict[int, list[OutputRoute]]] = {
        core_id: {} for core_id in range(len(drafts))
    }
    ingress: list[IngressRoute] = []
    generated = []
    for core_id, draft in enumerate(drafts):
        normalized = _patterns(draft.inbound)
        unique_patterns = sorted({pattern for _base, pattern in normalized.values()})
        pattern_ids = {pattern: index for index, pattern in enumerate(unique_patterns)}
        templates = tuple(
            SynapseTemplate(
                template_id=pattern_ids[pattern],
                entries=tuple(SynapseEntry(offset, weight) for offset, weight in pattern),
            )
            for pattern in unique_patterns
        )
        bindings = []
        for axon_id, source in enumerate(sorted(normalized)):
            base, pattern = normalized[source]
            bindings.append(InputAxonBinding(axon_id, pattern_ids[pattern], base))
            kind, population, index = source
            if kind == "input":
                ingress.append(IngressRoute(population, index, core_id, axon_id))
            else:
                sender = locations[(population, index)]
                routes_by_source[sender.core_id].setdefault(sender.compartment_id, []).append(
                    OutputRoute(core_id, axon_id)
                )
        generated.append((draft, templates, tuple(bindings)))

    configs = []
    for core_id, (draft, templates, bindings) in enumerate(generated):
        outbound = routes_by_source[core_id]
        route_entries = tuple(
            OutputRouteEntry(source_compartment=source_compartment, routes=tuple(sorted(
                connections, key=lambda route: (route.destination_core, route.destination_axon)
            )))
            for source_compartment, connections in sorted(outbound.items())
        )
        num_routes = sum(len(entry.routes) for entry in route_entries)
        if num_routes > options.route_words_per_core:
            raise MappingError("b12_outgoing_route_capacity",
                               "source-core packet/route fanout exceeds configured capacity",
                               core_id=core_id, used=num_routes,
                               limit=options.route_words_per_core)
        pressure = _pressure(draft)
        candidate = CorePressure(
            compartments=pressure.compartments, input_axons=pressure.input_axons,
            route_words=num_routes, synapse_words=pressure.synapse_words,
            template_headers=pressure.template_headers,
            external_events_per_tick=pressure.external_events_per_tick,
            routed_events_per_tick=pressure.routed_events_per_tick,
            emitted_packets_per_tick=num_routes,
        )
        try:
            candidate.validate(core_id=core_id)
        except B1CapacityError as exc:
            raise MappingError("b12_final_capacity", "outgoing-route or event pressure exceeds hardware",
                               core_id=core_id, resource=exc.name, used=exc.used, limit=exc.limit) from exc
        try:
            configs.append(LogicalCoreConfig(
                core_id=core_id,
                compartments=tuple(populations[name].compartment for name, _ in draft.members),
                input_axons=bindings,
                synapse_templates=templates,
                output_routes=route_entries,
                arithmetic=P03_REQUIRED_ARITHMETIC,
            ))
        except (ValueError, TypeError) as exc:
            raise MappingError("b12_core_encoding", "invalid packed/logical configuration",
                               core_id=core_id, detail=str(exc)) from exc
    return CompiledDeployment(
        source_fingerprint=network.fingerprint,
        logical_deployment=Deployment(tuple(configs)),
        placement=tuple(sorted(placement)),
        ingress_routes=tuple(sorted(ingress)),
        compiler_version=B12_COMPILER_VERSION,
    )


@dataclass(frozen=True, slots=True)
class B12Result:
    compiled: CompiledDeployment
    options: B12Options
    capacity_audit: dict

    @property
    def fingerprint(self) -> str:
        return self.compiled.fingerprint

    def manifest(self) -> dict:
        """Versioned, deterministic and SHA-linked source / mapping / images."""
        core_roles = {}
        for item in self.compiled.placement:
            role = "readout" if item.population == self.options.readout_population else "non_readout"
            prior = core_roles.setdefault(item.core_id, (item.population, role))
            if prior != (item.population, role):
                raise ValueError("B1.2 core mixes readout and non-readout populations")
        return {
            "schema": B12_SCHEMA,
            "compiler_version": B12_COMPILER_VERSION,
            "source_fingerprint": self.compiled.source_fingerprint,
            "deployment_fingerprint": self.compiled.fingerprint,
            "options": asdict(self.options),
            "per_core_roles": [
                {"core_id": cid, "population": population, "role": role}
                for cid, (population, role) in sorted(core_roles.items())
            ],
            "placement": [asdict(item) for item in self.compiled.placement],
            "ingress_routes": [asdict(item) for item in self.compiled.ingress_routes],
            "capacity_audit": self.capacity_audit,
            "capacity_audit_basis": "B1.1 packed/DDR verifier reused by distinct B1.2 compiler",
            "physical_execution": "NOT_TESTED",
            "scaled_streaming_abi": "NOT_IMPLEMENTED_B1_2",
            "official_mnist_test_access": "NONE",
        }

    def to_dict(self) -> dict:
        payload = {
            "schema": B12_SCHEMA,
            "compiler_version": B12_COMPILER_VERSION,
            "options": asdict(self.options),
            # P06's serializer rejects non-legacy compiler versions on *read*.
            # B1.2 carries its own versioned reader instead of mislabeling this
            # deployment as P06-A first-fit to bypass that safety guard.
            "compiled": self.compiled._canonical_payload(),
            "manifest": self.manifest(),
        }
        payload["sha256"] = _hash(payload)
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2) + "\n"

    def write_json(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self.to_json(), encoding="utf-8")
        return output

    @classmethod
    def from_dict(cls, payload: dict) -> "B12Result":
        if not isinstance(payload, dict) or payload.get("schema") != B12_SCHEMA:
            raise ValueError("invalid B1.2 deployment schema")
        if payload.get("compiler_version") != B12_COMPILER_VERSION:
            raise ValueError("invalid B1.2 compiler version")
        checksum = payload.get("sha256")
        if not isinstance(checksum, str) or checksum != _hash({
            key: value for key, value in payload.items() if key != "sha256"
        }):
            raise ValueError("B1.2 deployment document SHA256 mismatch")
        options = B12Options(**payload["options"])
        saved = payload["compiled"]
        if saved.get("schema") != P06_DEPLOYMENT_SCHEMA:
            raise ValueError("unexpected underlying P06 structural schema")
        if saved.get("compiler_version") != B12_COMPILER_VERSION:
            raise ValueError("wrong serialized B1.2 mapping implementation")
        compiled = CompiledDeployment(
            source_fingerprint=saved["source_fingerprint"],
            logical_deployment=Deployment.from_dict(saved["logical_deployment"]),
            placement=tuple(PlacementRecord(**record) for record in saved["placement"]),
            ingress_routes=tuple(IngressRoute(**route) for route in saved["ingress_routes"]),
            compiler_version=B12_COMPILER_VERSION,
        )
        audit = audit_compiled_candidate(compiled)
        instance = cls(compiled, options, audit)
        if payload["manifest"] != instance.manifest():
            raise ValueError("B1.2 manifest, resource ledger or placement does not match deployment")
        return instance

    @classmethod
    def from_json(cls, raw: str) -> "B12Result":
        return cls.from_dict(json.loads(raw))


def compile_synapse_aware(network: NetworkSpec, options: B12Options) -> B12Result:
    """Greedy deterministic exact-template-pressure first-fit in population order.

    Each next destination neuron is tentatively added to the current core.
    Recompute actual offset-relative template sharing and source axon counts.
    On capacity exhaustion, start a new core; reject even one unplaceable
    neuron, core count overflow, oversized output fanout and invalid P03 words.
    """
    if not isinstance(network, NetworkSpec):
        raise TypeError("network must be a validated P06 NetworkSpec")
    if not isinstance(options, B12Options):
        raise TypeError("options must be B12Options")
    drafts = _place(network, options)
    compiled = _emit_compiled(network, drafts, options)
    try:
        audited = audit_compiled_candidate(compiled)
    except (ValueError, TypeError) as exc:
        raise MappingError("b12_packed_image", "accepted P03/P02 packer rejected B1.2 placement",
                           detail=str(exc)) from exc
    return B12Result(compiled, options, audited)
