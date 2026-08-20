"""Frozen M10 computational-core profile for FPGA implementation.

The generic Python model intentionally remains configurable so older validation
scenarios keep their original behavior.  This module names the exact profile
that M11 hardware and M12 hardware comparisons must use.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from .arithmetic import ArithmeticConfig, OverflowMode
from .model import NeuronConfig, SpikeRoute, Synapse

CORE_SPEC_SCHEMA = "neuromorphic-twin-core-spec-v1"

STATE_BITS = 24
STATE_MIN = -(1 << (STATE_BITS - 1))
STATE_MAX = (1 << (STATE_BITS - 1)) - 1

TICK_BITS = 32
ID_BITS = 16
ID_MAX = (1 << ID_BITS) - 1
REFRACTORY_BITS = 16
REFRACTORY_MAX = (1 << REFRACTORY_BITS) - 1
DECAY_BITS = 13
DECAY_MIN = 0
DECAY_MAX = 4096
DECAY_SCALE = 4096

FPGA_CORE_ARITHMETIC_V1 = ArithmeticConfig(
    state_bits=STATE_BITS,
    overflow=OverflowMode.SATURATE,
)


def validate_neuron_config_v1(config: NeuronConfig) -> None:
    """Reject neuron settings that cannot be represented by core profile v1."""

    if not isinstance(config, NeuronConfig):
        raise TypeError("config must be a NeuronConfig")

    for name, value in (
        ("threshold", config.threshold),
        ("bias", config.bias),
        ("reset_voltage", config.reset_voltage),
    ):
        if not STATE_MIN <= value <= STATE_MAX:
            raise ValueError(
                f"{name}={value} is outside signed {STATE_BITS}-bit state range"
            )

    for name, value in (
        ("current_decay", config.current_decay),
        ("voltage_decay", config.voltage_decay),
    ):
        if not DECAY_MIN <= value <= DECAY_MAX:
            raise ValueError(f"{name} must be in {DECAY_MIN}..{DECAY_MAX}")

    if not 0 <= config.refractory_ticks <= REFRACTORY_MAX:
        raise ValueError(
            "refractory_ticks must fit the unsigned "
            f"{REFRACTORY_BITS}-bit profile field"
        )


def validate_synapse_v1(synapse: Synapse, *, neuron_count: int) -> None:
    """Validate routing identifiers consumed by the v1 computational core."""

    if not isinstance(synapse, Synapse):
        raise TypeError("synapse must be a Synapse")
    if not 0 <= synapse.axon_id <= ID_MAX:
        raise ValueError(f"axon_id must fit unsigned {ID_BITS} bits")
    if not 0 <= synapse.target_neuron <= ID_MAX:
        raise ValueError(f"target_neuron must fit unsigned {ID_BITS} bits")
    if synapse.target_neuron >= neuron_count:
        raise ValueError(
            f"synapse target {synapse.target_neuron} is outside "
            f"0..{neuron_count - 1}"
        )


def validate_spike_route_v1(route: SpikeRoute, *, neuron_count: int) -> None:
    """Validate one recurrent route against v1 identifier widths."""

    if not isinstance(route, SpikeRoute):
        raise TypeError("route must be a SpikeRoute")
    if not 0 <= route.source_neuron <= ID_MAX:
        raise ValueError(f"source_neuron must fit unsigned {ID_BITS} bits")
    if route.source_neuron >= neuron_count:
        raise ValueError(
            f"route source {route.source_neuron} is outside 0..{neuron_count - 1}"
        )
    if not 0 <= route.target_axon <= ID_MAX:
        raise ValueError(f"target_axon must fit unsigned {ID_BITS} bits")


def validate_core_configuration_v1(
    neuron_configs: Sequence[NeuronConfig],
    synapses: Iterable[Synapse] = (),
    spike_routes: Iterable[SpikeRoute] = (),
) -> None:
    """Validate one complete static configuration for core profile v1.

    This function deliberately validates representability and deterministic
    routing only. Weight source-format validation remains owned by the frozen
    M08 FPGA weight-storage contract.
    """

    if not neuron_configs:
        raise ValueError("at least one neuron is required")
    if len(neuron_configs) > ID_MAX + 1:
        raise ValueError(f"neuron count cannot exceed {ID_MAX + 1}")

    for config in neuron_configs:
        validate_neuron_config_v1(config)

    neuron_count = len(neuron_configs)
    for synapse in synapses:
        validate_synapse_v1(synapse, neuron_count=neuron_count)

    seen_routes: set[tuple[int, int]] = set()
    for route in spike_routes:
        validate_spike_route_v1(route, neuron_count=neuron_count)
        key = (route.source_neuron, route.target_axon)
        if key in seen_routes:
            raise ValueError(
                "duplicate spike route from neuron "
                f"{route.source_neuron} to axon {route.target_axon}"
            )
        seen_routes.add(key)
