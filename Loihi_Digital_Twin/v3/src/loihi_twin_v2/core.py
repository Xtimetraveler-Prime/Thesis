"""One explicit logical Loihi-like core for the v2 Python golden model."""

from __future__ import annotations

from dataclasses import dataclass

from .arithmetic import ArithmeticConfig
from .axon import InputAxonBinding, OutputRouteEntry
from .compartment import CompartmentConfig, CompartmentState, step_compartment
from .packet import SpikePacket
from .resources import (
    DEFAULT_CORE_CAPACITY,
    DEFAULT_SYNAPSE_COST_MODEL,
    MAX_INPUT_AXONS_PER_CORE,
    MAX_LOGICAL_CORES,
    CoreCapacity,
    ResourceUsage,
    SynapseCostModel,
    validate_resource_usage,
)
from .synapse import SynapseTemplate
from .trace import (
    AxonExpansionTrace,
    CompartmentSnapshot,
    CoreTrace,
    SynapticContributionTrace,
)


@dataclass(frozen=True, slots=True)
class LogicalCoreConfig:
    core_id: int
    compartments: tuple[CompartmentConfig, ...]
    input_axons: tuple[InputAxonBinding, ...] = ()
    synapse_templates: tuple[SynapseTemplate, ...] = ()
    output_routes: tuple[OutputRouteEntry, ...] = ()
    arithmetic: ArithmeticConfig = ArithmeticConfig()
    capacity: CoreCapacity = DEFAULT_CORE_CAPACITY
    synapse_cost_model: SynapseCostModel = DEFAULT_SYNAPSE_COST_MODEL

    def __post_init__(self) -> None:
        if not 0 <= self.core_id < MAX_LOGICAL_CORES:
            raise ValueError(f"core_id must be in [0, {MAX_LOGICAL_CORES})")

        template_ids = [template.template_id for template in self.synapse_templates]
        if len(set(template_ids)) != len(template_ids):
            raise ValueError("synapse template IDs must be unique within a core")
        axon_ids = [binding.axon_id for binding in self.input_axons]
        if len(set(axon_ids)) != len(axon_ids):
            raise ValueError("input axon IDs must be unique within a core")

        usage = self.resource_usage
        validate_resource_usage(usage, self.capacity)

        templates = {template.template_id: template for template in self.synapse_templates}
        for binding in self.input_axons:
            if not 0 <= binding.axon_id < MAX_INPUT_AXONS_PER_CORE:
                raise ValueError(f"axon_id {binding.axon_id} is outside the logical core ID space")
            if binding.template_id not in templates:
                raise ValueError(f"axon {binding.axon_id} references missing template {binding.template_id}")
            for entry in templates[binding.template_id].entries:
                if entry.delay != 0:
                    raise ValueError("v2.0 execution currently supports synaptic delay 0 only")
                target = binding.target_offset + entry.target_compartment
                if not 0 <= target < len(self.compartments):
                    raise ValueError(
                        f"axon {binding.axon_id} expands to invalid compartment {target}"
                    )

        for route_entry in self.output_routes:
            if not 0 <= route_entry.source_compartment < len(self.compartments):
                raise ValueError("output route references invalid source compartment")
            for route in route_entry.routes:
                if not 0 <= route.destination_core < MAX_LOGICAL_CORES:
                    raise ValueError("output route destination core is outside the logical chip ID space")
                if not 0 <= route.destination_axon < MAX_INPUT_AXONS_PER_CORE:
                    raise ValueError("output route destination axon is outside the logical core ID space")

    @property
    def resource_usage(self) -> ResourceUsage:
        template_bytes = sum(
            self.synapse_cost_model.template_bytes(len(template.entries))
            for template in self.synapse_templates
        )
        binding_bytes = self.synapse_cost_model.bindings_bytes(len(self.input_axons))
        templates = {template.template_id: template for template in self.synapse_templates}
        expanded = sum(len(templates[b.template_id].entries) for b in self.input_axons if b.template_id in templates)
        return ResourceUsage(
            compartments=len(self.compartments),
            input_axons=len(self.input_axons),
            output_routes=sum(len(entry.routes) for entry in self.output_routes),
            synapse_bytes=template_bytes + binding_bytes,
            shared_parameters=sum(len(template.entries) for template in self.synapse_templates),
            expanded_connections=expanded,
        )


class LogicalCore:
    def __init__(self, config: LogicalCoreConfig) -> None:
        self.config = config
        self.states = [CompartmentState() for _ in config.compartments]
        self._templates = {template.template_id: template for template in config.synapse_templates}
        self._axons = {binding.axon_id: binding for binding in config.input_axons}
        self._routes = {
            entry.source_compartment: entry.routes for entry in config.output_routes
        }
        self._pending_inputs: dict[int, list[int]] = {}
        self._ingress_packets: dict[int, list[SpikePacket]] = {}
        self._expansions: dict[int, list[AxonExpansionTrace]] = {}
        self._contributions: dict[int, list[SynapticContributionTrace]] = {}
        self._last_evaluated = -1

    def ingest_packet(self, packet: SpikePacket) -> None:
        if packet.destination_core != self.config.core_id:
            raise ValueError("packet delivered to the wrong logical core")
        binding = self._axons.get(packet.destination_axon)
        if binding is None:
            raise KeyError(
                f"core {self.config.core_id} has no input axon {packet.destination_axon}"
            )
        template = self._templates[binding.template_id]
        accum = self._pending_inputs.setdefault(
            packet.target_timestep, [0] * len(self.config.compartments)
        )
        self._ingress_packets.setdefault(packet.target_timestep, []).append(packet)
        self._expansions.setdefault(packet.target_timestep, []).append(
            AxonExpansionTrace(packet.destination_axon, template.template_id, len(template.entries))
        )
        contribution_log = self._contributions.setdefault(packet.target_timestep, [])
        for entry in template.entries:
            target = binding.target_offset + entry.target_compartment
            accum[target] += entry.weight
            contribution_log.append(
                SynapticContributionTrace(
                    source_axon=packet.destination_axon,
                    template_id=template.template_id,
                    target_compartment=target,
                    weight=entry.weight,
                )
            )

    def evaluate(self, timestep: int) -> CoreTrace:
        if timestep != self._last_evaluated + 1:
            raise RuntimeError(
                f"core {self.config.core_id} expected timestep {self._last_evaluated + 1}, got {timestep}"
            )
        synaptic_input = self._pending_inputs.pop(
            timestep, [0] * len(self.config.compartments)
        )
        packets_in = tuple(sorted(self._ingress_packets.pop(timestep, []), key=lambda p: p.logical_key))
        expansions = tuple(
            sorted(
                self._expansions.pop(timestep, []),
                key=lambda x: (x.axon_id, x.template_id, x.expanded_count),
            )
        )
        contributions = tuple(
            sorted(
                self._contributions.pop(timestep, []),
                key=lambda x: (x.source_axon, x.template_id, x.target_compartment, x.weight),
            )
        )
        before = tuple(
            CompartmentSnapshot(compartment_id=i, state=state)
            for i, state in enumerate(self.states)
        )

        spikes: list[int] = []
        next_states: list[CompartmentState] = []
        for compartment_id, (state, config, delivered) in enumerate(
            zip(self.states, self.config.compartments, synaptic_input, strict=True)
        ):
            result = step_compartment(state, config, delivered, self.config.arithmetic)
            next_states.append(result.state)
            if result.spiked:
                spikes.append(compartment_id)
        self.states = next_states

        packets_out: list[SpikePacket] = []
        for compartment_id in spikes:
            for route in self._routes.get(compartment_id, ()):
                packets_out.append(
                    SpikePacket(
                        target_timestep=timestep + 1,
                        destination_core=route.destination_core,
                        destination_axon=route.destination_axon,
                        source_core=self.config.core_id,
                        source_compartment=compartment_id,
                        source_timestep=timestep,
                    )
                )

        after = tuple(
            CompartmentSnapshot(compartment_id=i, state=state)
            for i, state in enumerate(self.states)
        )
        self._last_evaluated = timestep
        return CoreTrace(
            algorithmic_timestep=timestep,
            logical_core_id=self.config.core_id,
            phase="compartment-update/egress",
            packet_in=packets_in,
            axon_expansions=expansions,
            synaptic_contributions=contributions,
            compartment_state_before=before,
            compartment_state_after=after,
            spikes_out=tuple(spikes),
            packets_out=tuple(sorted(packets_out, key=lambda p: p.logical_key)),
            local_done=True,
        )
