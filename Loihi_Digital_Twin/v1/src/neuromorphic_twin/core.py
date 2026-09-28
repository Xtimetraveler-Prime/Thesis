"""A small programmable neuromorphic core with fixed-weight synapses."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence

from .arithmetic import ArithmeticConfig
from .model import (
    NeuronConfig,
    NeuronState,
    Spike,
    SpikeRoute,
    Synapse,
    TickTrace,
)
from .neuron import step_neuron


class NeuromorphicCore:
    """Single-core, tick-driven neuromorphic processor model.

    The model uses a structure-of-arrays state layout (`currents`, `voltages`,
    and refractory counters). Separate arrays map naturally to independent FPGA
    memories and make every mutable state element directly observable.
    """

    def __init__(
        self,
        neuron_configs: Sequence[NeuronConfig],
        synapses: Iterable[Synapse] = (),
        *,
        spike_routes: Iterable[SpikeRoute] = (),
        arithmetic: ArithmeticConfig | None = None,
    ) -> None:
        if not neuron_configs:
            raise ValueError("at least one neuron is required")

        self._configs = tuple(neuron_configs)
        self._arithmetic = arithmetic or ArithmeticConfig()
        self._tick = 0

        neuron_count = len(self._configs)
        self._currents = [0] * neuron_count
        self._voltages = [cfg.reset_voltage for cfg in self._configs]
        self._refractory = [0] * neuron_count

        # axon_id -> immutable tuple of (target_neuron, weight)
        mutable_map: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for synapse in synapses:
            if synapse.target_neuron >= neuron_count:
                raise ValueError(
                    f"synapse target {synapse.target_neuron} is outside "
                    f"0..{neuron_count - 1}"
                )
            mutable_map[synapse.axon_id].append(
                (synapse.target_neuron, synapse.weight)
            )
        self._axon_map = {
            axon_id: tuple(connections)
            for axon_id, connections in mutable_map.items()
        }

        # source_neuron -> routes in declaration order. Output events are
        # queued after a tick and become inputs only at the next tick boundary.
        mutable_routes: dict[int, list[int]] = defaultdict(list)
        seen_routes: set[tuple[int, int]] = set()
        for route in spike_routes:
            if route.source_neuron >= neuron_count:
                raise ValueError(
                    f"route source {route.source_neuron} is outside "
                    f"0..{neuron_count - 1}"
                )
            key = (route.source_neuron, route.target_axon)
            if key in seen_routes:
                raise ValueError(
                    "duplicate spike route from neuron "
                    f"{route.source_neuron} to axon {route.target_axon}"
                )
            seen_routes.add(key)
            mutable_routes[route.source_neuron].append(route.target_axon)
        self._spike_routes = {
            neuron_id: tuple(axons)
            for neuron_id, axons in mutable_routes.items()
        }
        self._pending_recurrent_axons: tuple[int, ...] = ()

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def neuron_count(self) -> int:
        return len(self._configs)

    def state(self, neuron_id: int) -> NeuronState:
        """Return an immutable snapshot of one neuron state."""

        self._validate_neuron_id(neuron_id)
        return NeuronState(
            current=self._currents[neuron_id],
            voltage=self._voltages[neuron_id],
            refractory_remaining=self._refractory[neuron_id],
        )

    def set_state(self, neuron_id: int, state: NeuronState) -> None:
        """Set one state explicitly for deterministic tests and replay."""

        self._validate_neuron_id(neuron_id)
        self._currents[neuron_id] = self._arithmetic.apply(state.current)
        self._voltages[neuron_id] = self._arithmetic.apply(state.voltage)
        self._refractory[neuron_id] = state.refractory_remaining

    def reset(self) -> None:
        """Return the core to its power-on state."""

        self._tick = 0
        self._pending_recurrent_axons = ()
        for neuron_id, config in enumerate(self._configs):
            self._currents[neuron_id] = 0
            self._voltages[neuron_id] = config.reset_voltage
            self._refractory[neuron_id] = 0

    def step(self, input_axons: Iterable[int] = ()) -> TickTrace:
        """Process one complete algorithmic tick and return a full trace."""

        external_axons = tuple(int(axon_id) for axon_id in input_axons)
        if any(axon_id < 0 for axon_id in external_axons):
            raise ValueError("input axon IDs cannot be negative")
        recurrent_axons = self._pending_recurrent_axons
        axons = external_axons + recurrent_axons

        synaptic_input = [0] * self.neuron_count
        for axon_id in axons:
            for target_neuron, weight in self._axon_map.get(axon_id, ()):
                synaptic_input[target_neuron] += weight

        current_before = tuple(self._currents)
        voltage_before = tuple(self._voltages)
        spikes: list[Spike] = []

        for neuron_id, config in enumerate(self._configs):
            result = step_neuron(
                NeuronState(
                    current=self._currents[neuron_id],
                    voltage=self._voltages[neuron_id],
                    refractory_remaining=self._refractory[neuron_id],
                ),
                config,
                synaptic_input[neuron_id],
                self._arithmetic,
            )
            self._currents[neuron_id] = result.state.current
            self._voltages[neuron_id] = result.state.voltage
            self._refractory[neuron_id] = result.state.refractory_remaining
            if result.spiked:
                spikes.append(Spike(tick=self._tick, neuron_id=neuron_id))

        routed_axons = tuple(
            axon_id
            for spike in spikes
            for axon_id in self._spike_routes.get(spike.neuron_id, ())
        )
        self._pending_recurrent_axons = routed_axons

        trace = TickTrace(
            tick=self._tick,
            input_axons=axons,
            synaptic_input=tuple(synaptic_input),
            current_before=current_before,
            voltage_before=voltage_before,
            current_after=tuple(self._currents),
            voltage_after=tuple(self._voltages),
            refractory_after=tuple(self._refractory),
            spikes=tuple(spikes),
            external_input_axons=external_axons,
            recurrent_input_axons=recurrent_axons,
            routed_output_axons=routed_axons,
        )
        self._tick += 1
        return trace

    def _validate_neuron_id(self, neuron_id: int) -> None:
        if not 0 <= neuron_id < self.neuron_count:
            raise IndexError(
                f"neuron_id must be in 0..{self.neuron_count - 1}"
            )
