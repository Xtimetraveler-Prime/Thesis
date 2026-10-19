"""B1.4 differential check: independent monolithic source graph vs packed cores.

Expected spike/current/voltage/refractory and per-timestep integer synaptic
inputs come exclusively from p06_b14_monolithic (direct NetworkSpec + the
independent P06-A standalone scalar oracle). The production compiler, B1.2
placement, LogicalChip and B1.3 packet transport are ONLY test subjects.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json

from .compiler import NetworkSpec
from .p06_b12_partition import B12Result, B12_COMPILER_VERSION
from .p06_b14_monolithic import (
    B14OracleError, B14_TICKS, EventSchedule, MonolithicRun,
    simulate_monolithic,
)
from .p06_integer_oracle import wrap64
from .trace import ChipTrace

B14_COMPARE_SCHEMA = "p06-b1.4-monolithic-vs-partitioned-differential-v1"
_Neuron = tuple[str, int]
_External = tuple[str, int]


class B14Divergence(AssertionError):
    """First chronological/lexicographic semantic mismatch."""

    def __init__(self, tick: int, field: str, expected: object, actual: object,
                 neuron: _Neuron | None = None):
        self.tick, self.field, self.expected, self.actual, self.neuron = (
            tick, field, expected, actual, neuron)
        super().__init__(
            f"B1.4 first divergence tick={tick} neuron={neuron} field={field}: "
            f"expected={str(expected)[:240]!r} actual={str(actual)[:240]!r}"
        )


def _require_equal(tick: int, field: str, expected: object, actual: object,
                   neuron: _Neuron | None = None) -> None:
    if expected != actual:
        raise B14Divergence(tick, field, expected, actual, neuron)


@dataclass(frozen=True, slots=True)
class B14Comparison:
    reference: MonolithicRun
    deployment_sha256: str
    output_trace_sha256: str
    observed_core_spikes: int
    observed_routed_packets: int
    observed_external_packets: int
    readout_spike_counts: tuple[int, ...]
    predicted_class: int
    semantic_ticks_compared: int

    def report(self) -> dict:
        return {
            "schema": B14_COMPARE_SCHEMA,
            "reference_schema": self.reference.schema,
            "source_network_sha256": self.reference.source_fingerprint,
            "deployment_sha256": self.deployment_sha256,
            "monolithic_trace_sha256": self.reference.trace_sha256,
            "partitioned_trace_sha256": self.output_trace_sha256,
            "ticks": self.semantic_ticks_compared,
            "neurons_each_tick": len(self.reference.ticks[0].after),
            "independent_reference_spikes": self.reference.spike_count,
            "partitioned_spikes": self.observed_core_spikes,
            "partitioned_routed_packets": self.observed_routed_packets,
            "partitioned_external_packets": self.observed_external_packets,
            "readout_spike_counts": list(self.readout_spike_counts),
            "class": self.predicted_class,
            "all_neuron_states_and_inputs_equal": True,
            "all_spikes_and_NEXT_routes_equal": True,
            "physical_kv260_execution": "NOT_TESTED",
            "official_mnist_test_access": "NONE",
        }


@dataclass(frozen=True, slots=True)
class _Layout:
    by_id: dict[tuple[int, int], _Neuron]
    by_neuron: dict[_Neuron, tuple[int, int]]
    input_pairs: set[tuple[str, int, int]]
    external_cores_by_source: dict[_External, tuple[int, ...]]
    input_axon_owner: dict[tuple[int, int], _External]
    expected_outputs: dict[tuple[int, int], set[int]]
    output_axon_by_source_and_core: dict[tuple[int, int, int], int]
    known_external: dict[str, set[int]]


def _independent_layout(network: NetworkSpec, result: B12Result) -> _Layout:
    if not isinstance(result, B12Result) or result.compiled.compiler_version != B12_COMPILER_VERSION:
        raise B14OracleError("B1.4 requires an opt-in B1.2 compiled deployment")
    compiled = result.compiled
    _require_equal(-1, "source_fingerprint", network.fingerprint, compiled.source_fingerprint)
    _require_equal(-1, "audit_fingerprint", compiled.fingerprint,
                   result.capacity_audit.get("original_compiled_sha256"))
    original = {(pop.name, index) for pop in network.populations
                for index in range(pop.size)}
    placed = {(r.population, r.neuron_index) for r in compiled.placement}
    _require_equal(-1, "placement_coverage", original, placed)
    _require_equal(-1, "placement_uniqueness", len(original), len(compiled.placement))
    by_neuron = {(r.population, r.neuron_index): (r.core_id, r.compartment_id)
                 for r in compiled.placement}
    by_id = {location: neuron for neuron, location in by_neuron.items()}
    _require_equal(-1, "placement_address_uniqueness", len(original), len(by_id))
    actual_cores = {core.core_id: core for core in compiled.logical_deployment.core_configs}
    for core_id, compartment in by_id:
        if core_id not in actual_cores or not 0 <= compartment < len(actual_cores[core_id].compartments):
            raise B14Divergence(-1, "placement_address", "existing logical compartment",
                                (core_id, compartment))
    input_pairs = set()
    expected_outputs: dict[tuple[int, int], set[int]] = defaultdict(set)
    for projection in network.input_projections:
        for edge in projection.connections:
            core, _ = by_neuron[(projection.destination_population, edge.destination_index)]
            input_pairs.add((projection.source_input, edge.source_index, core))
    for projection in network.projections:
        for edge in projection.connections:
            source_addr = by_neuron[(projection.source_population, edge.source_index)]
            target_core, _ = by_neuron[(projection.destination_population, edge.destination_index)]
            expected_outputs[source_addr].add(target_core)

    external_groups: dict[_External, set[int]] = defaultdict(set)
    for pop, source_index, destination_core in input_pairs:
        external_groups[(pop, source_index)].add(destination_core)
    external_cores_by_source = {
        source: tuple(sorted(cores)) for source, cores in external_groups.items()
    }
    input_owner = {}
    observed_input_pairs = set()
    known_external: dict[str, set[int]] = defaultdict(set)
    for route in compiled.ingress_routes:
        addr = (route.destination_core, route.destination_axon)
        if addr in input_owner:
            raise B14Divergence(-1, "ingress_axons", "unique axon mapping", addr)
        input_owner[addr] = (route.input_population, route.input_index)
        observed_input_pairs.add((route.input_population, route.input_index,
                                  route.destination_core))
        known_external[route.input_population].add(route.input_index)
    _require_equal(-1, "ingress_source_core_fanout", input_pairs, observed_input_pairs)
    _require_equal(-1, "ingress_uniqueness", len(input_pairs), len(input_owner))

    observed_outputs: dict[tuple[int, int], set[int]] = defaultdict(set)
    output_axon_by_source_and_core: dict[tuple[int, int, int], int] = {}
    for core in compiled.logical_deployment.core_configs:
        for entry in core.output_routes:
            origin = (core.core_id, entry.source_compartment)
            for route in entry.routes:
                destination_core = route.destination_core
                if destination_core in observed_outputs[origin]:
                    raise B14Divergence(-1, "output_route_uniqueness",
                                        "one route per source/destination-core pair", origin)
                observed_outputs[origin].add(destination_core)
                output_axon_by_source_and_core[(
                    core.core_id, entry.source_compartment, destination_core,
                )] = route.destination_axon
    _require_equal(-1, "neural_source_core_fanout",
                   {k: frozenset(v) for k, v in expected_outputs.items()},
                   {k: frozenset(v) for k, v in observed_outputs.items()})
    return _Layout(by_id, by_neuron, input_pairs, external_cores_by_source,
                   input_owner, dict(expected_outputs),
                   output_axon_by_source_and_core, dict(known_external))


def _incoming_oracle(
    tick: int, schedule: EventSchedule, previous_spikes: tuple[_Neuron, ...],
    layout: _Layout,
) -> Counter:
    expected = Counter()
    for population, rows in schedule.items():
        for source in rows[tick]:
            for destination_core in layout.external_cores_by_source.get(
                    (population, source), ()):
                expected[("external", population, source, destination_core)] += 1
    for origin in previous_spikes:
        core, compartment = layout.by_neuron[origin]
        for destination_core in layout.expected_outputs.get((core, compartment), ()):
            expected[("neural", origin[0], origin[1], destination_core)] += 1
    return expected


def _observed_packets_in(tick: int, trace: ChipTrace, layout: _Layout) -> Counter:
    observed = Counter()
    for core in trace.cores:
        for packet in core.packet_in:
            _require_equal(tick, "incoming_packet_target_tick", tick, packet.target_timestep)
            _require_equal(tick, "incoming_packet_destination_core", core.logical_core_id,
                           packet.destination_core)
            if packet.source_core is None:
                addr = (packet.destination_core, packet.destination_axon)
                if addr not in layout.input_axon_owner:
                    raise B14Divergence(tick, "input_packet_registered_axon",
                                        "registered source pixel/axon", addr)
                pop, index = layout.input_axon_owner[addr]
                observed[("external", pop, index, packet.destination_core)] += 1
            else:
                if packet.source_compartment is None:
                    raise B14Divergence(tick, "routed_packet_source", "source compartment", None)
                addr = (packet.source_core, packet.source_compartment)
                if addr not in layout.by_id:
                    raise B14Divergence(tick, "routed_packet_source", "placed source neuron", addr)
                _require_equal(tick, "routed_packet_source_epoch", tick - 1,
                               packet.source_timestep, layout.by_id[addr])
                mapped_axon = layout.output_axon_by_source_and_core.get((
                    packet.source_core, packet.source_compartment, packet.destination_core))
                _require_equal(tick, "routed_packet_destination_axon",
                               mapped_axon, packet.destination_axon, layout.by_id[addr])
                neuron = layout.by_id[addr]
                observed[("neural", neuron[0], neuron[1], packet.destination_core)] += 1
    return observed


def _outgoing_oracle(tick: int, spikes: tuple[_Neuron, ...], layout: _Layout) -> Counter:
    expected = Counter()
    for origin in spikes:
        address = layout.by_neuron[origin]
        for destination_core in layout.expected_outputs.get(address, ()):
            expected[(tick + 1, origin, destination_core)] += 1
    return expected


def _actual_outgoing(tick: int, trace: ChipTrace, layout: _Layout) -> Counter:
    counts = Counter()
    for core in trace.cores:
        for packet in core.packets_out:
            addr = (packet.source_core, packet.source_compartment)
            if addr not in layout.by_id:
                raise B14Divergence(tick, "packet_source", "known neuron", addr)
            neuron = layout.by_id[addr]
            _require_equal(tick, "NEXT_packet_target", tick + 1, packet.target_timestep, neuron)
            _require_equal(tick, "packet_source_tick", tick, packet.source_timestep, neuron)
            _require_equal(tick, "packet_source_core", core.logical_core_id,
                           packet.source_core, neuron)
            expected_axon = layout.output_axon_by_source_and_core.get((
                packet.source_core, packet.source_compartment, packet.destination_core))
            _require_equal(tick, "packet_destination_axon",
                           expected_axon, packet.destination_axon, neuron)
            counts[(packet.target_timestep, neuron, packet.destination_core)] += 1
    return counts


def compare_monolithic_to_traces(
    network: NetworkSpec, result: B12Result, schedule: EventSchedule,
    traces: tuple[ChipTrace, ...], *,
    readout_population: str,
    reference: MonolithicRun | None = None,
) -> B14Comparison:
    """Compare EVERY tick, neuron, synaptic sum, spike and routed NEXT group.

    Accept external genuine chip traces for targeted mutation/first-divergence
    regression; no pass can be inferred from only comparing aggregate spikes.
    """
    layout = _independent_layout(network, result)
    oracle = reference or simulate_monolithic(
        network, schedule, readout_population=readout_population)
    _require_equal(-1, "reference_source_sha", network.fingerprint, oracle.source_fingerprint)
    _require_equal(-1, "reference_readout", readout_population, oracle.readout_population)
    _require_equal(-1, "trace_tick_count", B14_TICKS, len(traces))
    observed_counts = [0] * len(oracle.readout_spike_counts)
    trace_hash = hashlib.sha256()
    spike_total, output_total, input_total = 0, 0, 0
    for tick, (expect, actual) in enumerate(zip(oracle.ticks, traces, strict=True)):
        _require_equal(tick, "chip_epoch", tick, actual.algorithmic_timestep)
        core_traces = {core.logical_core_id: core for core in actual.cores}
        if len(core_traces) != len(result.compiled.logical_deployment.core_configs):
            raise B14Divergence(tick, "core_trace_count",
                                len(result.compiled.logical_deployment.core_configs), len(core_traces))
        _require_equal(tick, "core_epoch", {tick},
                       {core.algorithmic_timestep for core in actual.cores})
        observed_before, observed_after, observed_input, observed_spikes = {}, {}, {}, []
        for core in actual.cores:
            for before in core.compartment_state_before:
                neuron = layout.by_id[(core.logical_core_id, before.compartment_id)]
                observed_before[neuron] = before.state
            for after in core.compartment_state_after:
                neuron = layout.by_id[(core.logical_core_id, after.compartment_id)]
                observed_after[neuron] = after.state
            delivered: dict[int, int] = defaultdict(int)
            for contrib in core.synaptic_contributions:
                delivered[contrib.target_compartment] = wrap64(
                    delivered[contrib.target_compartment] + contrib.weight)
            for compartment in range(len(core.compartment_state_after)):
                neuron = layout.by_id[(core.logical_core_id, compartment)]
                observed_input[neuron] = delivered.get(compartment, 0)
            observed_spikes.extend(layout.by_id[(core.logical_core_id, i)]
                                   for i in core.spikes_out)

        oracle_before = dict(expect.before)
        oracle_after = dict(expect.after)
        oracle_in = dict(expect.synaptic_inputs)
        # Chronological THEN sorted source-neuron order => stable first divergence.
        for neuron in oracle_before:
            if neuron not in observed_before or neuron not in observed_after or neuron not in observed_input:
                raise B14Divergence(tick, "neuron_trace_coverage", "present", neuron, neuron)
            for label, expected_state, measured_state in (
                ("state_before", oracle_before[neuron], observed_before[neuron]),
                ("state_after", oracle_after[neuron], observed_after[neuron]),
            ):
                for field in ("current", "voltage", "refractory_remaining"):
                    _require_equal(tick, f"{label}.{field}",
                                   getattr(expected_state, field),
                                   getattr(measured_state, field), neuron)
            _require_equal(tick, "synaptic_input", oracle_in[neuron],
                           observed_input[neuron], neuron)
            _require_equal(tick, "neuron_spiked", neuron in expect.spikes,
                           neuron in observed_spikes, neuron)
        _require_equal(tick, "neuron_trace_coverage_total", len(oracle_before),
                       len(observed_before))
        _require_equal(tick, "spike_total", len(expect.spikes), len(observed_spikes))

        previous = () if tick == 0 else oracle.ticks[tick - 1].spikes
        ingress_expect = _incoming_oracle(tick, schedule, previous, layout)
        ingress_actual = _observed_packets_in(tick, actual, layout)
        _require_equal(tick, "ingress_SOURCE/NEXT_fanout", ingress_expect, ingress_actual)
        outgoing_expect = _outgoing_oracle(tick, expect.spikes, layout)
        outgoing_actual = _actual_outgoing(tick, actual, layout)
        _require_equal(tick, "routed_NEXT_packet_fanout", outgoing_expect, outgoing_actual)
        if tick == B14_TICKS - 1:
            _require_equal(tick, "final_drain_egress", 0, sum(outgoing_actual.values()))

        for neuron in observed_spikes:
            if neuron[0] == readout_population:
                observed_counts[neuron[1]] += 1
        _require_equal(tick, "readout_spike_counts", expect.readout_counts,
                       tuple(observed_counts))

        # Source-index normalization avoids differences in legal physical
        # service order and packet-drain order.
        row = {
            "tick": tick,
            "states": [(p, i, s.current, s.voltage, s.refractory_remaining)
                       for (p, i), s in sorted(observed_after.items())],
            "input": [(p, i, v) for (p, i), v in sorted(observed_input.items())],
            "spikes": sorted(observed_spikes),
            "routed": sorted((target, pop, idx, dest, count)
                             for (target, (pop, idx), dest), count in outgoing_actual.items()),
        }
        trace_hash.update(json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        spike_total += len(observed_spikes)
        output_total += sum(outgoing_actual.values())
        input_total += sum(v for (kind, *_), v in ingress_actual.items() if kind == "external")

    winner = max(range(len(observed_counts)), key=lambda n: observed_counts[n])
    _require_equal(B14_TICKS, "final_class", oracle.predicted_class, winner)
    _require_equal(B14_TICKS, "final_readout", oracle.readout_spike_counts,
                   tuple(observed_counts))
    return B14Comparison(
        reference=oracle,
        deployment_sha256=result.compiled.fingerprint,
        output_trace_sha256=trace_hash.hexdigest(),
        observed_core_spikes=spike_total,
        observed_routed_packets=output_total,
        observed_external_packets=input_total,
        readout_spike_counts=tuple(observed_counts),
        predicted_class=winner,
        semantic_ticks_compared=B14_TICKS,
    )


def run_and_compare(
    network: NetworkSpec, result: B12Result, schedule: EventSchedule, *,
    readout_population: str,
    service_order: tuple[int, ...] | None = None,
    reverse_packet_drain: bool = False,
) -> B14Comparison:
    """Generate 26 production LogicalChip traces; independently check all."""
    oracle = simulate_monolithic(
        network, schedule, readout_population=readout_population)
    layout = _independent_layout(network, result)
    core_ids = tuple(sorted(core.core_id
                            for core in result.compiled.logical_deployment.core_configs))
    if service_order is not None and tuple(sorted(service_order)) != core_ids:
        raise B14OracleError("service_order must enumerate all configured logical core IDs")
    chip = result.compiled.build_chip()
    traces = []
    for tick in range(B14_TICKS):
        injected = []
        for input_population, rows in sorted(schedule.items()):
            used = layout.known_external.get(input_population, set())
            active = tuple(index for index in rows[tick] if index in used)
            if active:
                injected.extend(result.compiled.external_packets(
                    input_population, active, target_timestep=tick))
        # A source can be disconnected and still have a valid scheduled event.
        traces.append(chip.step(
            tuple(injected), service_order=service_order,
            reverse_packet_drain=reverse_packet_drain))
    return compare_monolithic_to_traces(
        network, result, schedule, tuple(traces),
        readout_population=readout_population, reference=oracle)
