"""Optional adapter for the external Brian2Loihi reference emulator."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from ..arithmetic import OverflowMode
from ..weights import WeightFormat, WeightSignMode
from .model import (
    BackendTick,
    BackendTrace,
    ComparisonScenario,
    describe_synapses,
)


class BackendUnavailableError(RuntimeError):
    """Raised when an optional comparison backend cannot be imported."""


class UnsupportedScenarioError(ValueError):
    """Raised when a scenario cannot be represented by this adapter."""


@dataclass(frozen=True, slots=True)
class Brian2LoihiMapping:
    threshold_scale: int = 64
    weight_scale: int = 64
    weight_exponent: int = 0
    num_weight_bits: int = 8


@dataclass(frozen=True, slots=True)
class Brian2LoihiSynapseGroup:
    """One deterministic set of connections sharing a Loihi weight format.

    Brian2Loihi stores exponent, configured precision, and sign mode on a
    ``LoihiSynapses`` object. Connections can therefore share one object only
    when all three fields match. ``scenario_indices`` preserves the original
    connection order so the backend can restore observed ``w_act`` values after
    executing format groups in any deterministic order.
    """

    exponent: int
    num_weight_bits: int
    sign_mode: WeightSignMode
    scenario_indices: tuple[int, ...]
    axon_ids: tuple[int, ...]
    target_neurons: tuple[int, ...]
    mantissas: tuple[int, ...]

    def __post_init__(self) -> None:
        lengths = {
            len(self.scenario_indices),
            len(self.axon_ids),
            len(self.target_neurons),
            len(self.mantissas),
        }
        if lengths != {len(self.scenario_indices)} or not self.scenario_indices:
            raise ValueError("synapse group fields must have one non-empty length")

    @property
    def weight_format(self) -> WeightFormat:
        return WeightFormat(
            exponent=self.exponent,
            num_weight_bits=self.num_weight_bits,
            sign_mode=self.sign_mode,
        )


@dataclass(frozen=True, slots=True)
class Brian2LoihiBackendRun:
    """Normalized trace plus Brian2Loihi effective weights in scenario order."""

    trace: BackendTrace
    effective_weights: tuple[int, ...]


def build_brian2loihi_synapse_groups(
    scenario: ComparisonScenario,
    mapping: Brian2LoihiMapping | None = None,
) -> tuple[Brian2LoihiSynapseGroup, ...]:
    """Translate scenario synapses into deterministic Brian2Loihi groups.

    Legacy integer synapses retain the original adapter contract: their
    mantissas are reconstructed through ``Brian2LoihiMapping`` and separated
    into excitatory and inhibitory exponent-zero groups. Encoded synapses use
    their original requested mantissa and immutable ``WeightFormat`` directly.
    Groups are returned in order of first appearance in the scenario.
    """

    mapping = mapping or Brian2LoihiMapping()
    grouped: dict[
        WeightFormat,
        list[tuple[int, int, int, int]],
    ] = {}

    for scenario_index, synapse in enumerate(scenario.synapses):
        if synapse.encoding is None:
            sign_mode = (
                WeightSignMode.EXCITATORY
                if synapse.weight >= 0
                else WeightSignMode.INHIBITORY
            )
            try:
                weight_format = WeightFormat(
                    exponent=mapping.weight_exponent,
                    num_weight_bits=mapping.num_weight_bits,
                    sign_mode=sign_mode,
                )
            except (TypeError, ValueError) as exc:
                raise UnsupportedScenarioError(
                    f"invalid legacy Brian2Loihi weight mapping: {exc}"
                ) from exc
            mantissa = effective_weight_to_mantissa(synapse.weight, mapping)
        else:
            weight_format = synapse.encoding.weight_format
            mantissa = synapse.encoding.requested_mantissa

        grouped.setdefault(weight_format, []).append(
            (
                scenario_index,
                synapse.axon_id,
                synapse.target_neuron,
                mantissa,
            )
        )

    return tuple(
        Brian2LoihiSynapseGroup(
            exponent=weight_format.exponent,
            num_weight_bits=weight_format.num_weight_bits,
            sign_mode=weight_format.sign_mode,
            scenario_indices=tuple(entry[0] for entry in entries),
            axon_ids=tuple(entry[1] for entry in entries),
            target_neurons=tuple(entry[2] for entry in entries),
            mantissas=tuple(entry[3] for entry in entries),
        )
        for weight_format, entries in grouped.items()
    )


def validate_brian2loihi_scenario(
    scenario: ComparisonScenario,
    mapping: Brian2LoihiMapping | None = None,
) -> None:
    mapping = mapping or Brian2LoihiMapping()
    configs = scenario.neuron_configs
    first = configs[0]

    if any(config != first for config in configs[1:]):
        raise UnsupportedScenarioError(
            "the first Brian2Loihi adapter requires one common neuron "
            "configuration for the whole neuron group"
        )
    if first.bias != 0:
        raise UnsupportedScenarioError(
            "Brian2Loihi LoihiNeuronGroup does not expose a bias parameter"
        )
    if first.reset_voltage != 0:
        raise UnsupportedScenarioError(
            "Brian2Loihi uses a fixed reset voltage of zero"
        )
    if not 1 <= first.refractory_ticks <= 64:
        raise UnsupportedScenarioError(
            "Brian2Loihi requires refractory_ticks in the range 1..64"
        )
    if first.threshold % mapping.threshold_scale != 0:
        raise UnsupportedScenarioError(
            f"threshold {first.threshold} is not divisible by "
            f"{mapping.threshold_scale}"
        )
    threshold_mantissa = first.threshold // mapping.threshold_scale
    if not 0 <= threshold_mantissa <= 131071:
        raise UnsupportedScenarioError(
            "threshold mantissa is outside Brian2Loihi's 0..131071 range"
        )

    if scenario.arithmetic.overflow is not OverflowMode.NONE:
        raise UnsupportedScenarioError(
            "the Brian2Loihi adapter currently compares only unbounded Python "
            "arithmetic; disable explicit saturation/wraparound"
        )

    # Building the groups validates every legacy mapping while preserving the
    # already-validated source format for encoded synapses.
    build_brian2loihi_synapse_groups(scenario, mapping)

    for tick, axons in enumerate(scenario.input_schedule):
        if len(axons) != len(set(axons)):
            raise UnsupportedScenarioError(
                f"tick {tick} repeats an axon ID; Brian SpikeGeneratorGroup "
                "does not represent two spikes from one source at one time"
            )


def effective_weight_to_mantissa(
    effective_weight: int,
    mapping: Brian2LoihiMapping | None = None,
) -> int:
    mapping = mapping or Brian2LoihiMapping()
    if effective_weight % mapping.weight_scale != 0:
        raise UnsupportedScenarioError(
            f"effective weight {effective_weight} is not divisible by "
            f"{mapping.weight_scale}"
        )
    mantissa = effective_weight // mapping.weight_scale
    if not -256 <= mantissa <= 255:
        raise UnsupportedScenarioError(
            f"weight mantissa {mantissa} is outside the supported -256..255 range"
        )
    return mantissa


def run_brian2loihi_backend(
    scenario: ComparisonScenario,
    *,
    mapping: Brian2LoihiMapping | None = None,
) -> BackendTrace:
    """Run one scenario and return its normalized trace."""

    return run_brian2loihi_backend_with_weights(
        scenario,
        mapping=mapping,
    ).trace


def run_brian2loihi_backend_with_weights(
    scenario: ComparisonScenario,
    *,
    mapping: Brian2LoihiMapping | None = None,
) -> Brian2LoihiBackendRun:
    """Run one scenario and retain Brian2Loihi ``w_act`` observations.

    The returned effective weights follow the original ``scenario.synapses``
    order even though Brian2Loihi connections are instantiated by shared format.
    """

    mapping = mapping or Brian2LoihiMapping()
    validate_brian2loihi_scenario(scenario, mapping)
    groups = build_brian2loihi_synapse_groups(scenario, mapping)

    try:
        import numpy as np
        from brian2 import prefs, start_scope
        from brian2_loihi import (
            LoihiNetwork,
            LoihiNeuronGroup,
            LoihiSpikeGeneratorGroup,
            LoihiSpikeMonitor,
            LoihiSynapses,
            synapse_sign_mode,
        )
    except Exception as exc:
        raise BackendUnavailableError(
            "Brian2Loihi could not be imported. Install the optional "
            "comparison dependencies with: "
            "python -m pip install -e '.[compare]'. "
            f"Original import error: {type(exc).__name__}: {exc}"
        ) from exc

    prefs.codegen.target = "numpy"
    start_scope()
    config = scenario.neuron_configs[0]
    neurons = LoihiNeuronGroup(
        len(scenario.neuron_configs),
        refractory=config.refractory_ticks,
        threshold_v_mant=config.threshold // mapping.threshold_scale,
        decay_v=config.voltage_decay,
        decay_I=config.current_decay,
    )

    event_indices: list[int] = []
    event_times: list[int] = []
    for tick, axons in enumerate(scenario.input_schedule):
        for axon_id in axons:
            event_indices.append(axon_id)
            event_times.append(tick)

    highest_input_axon = max(event_indices, default=0)
    highest_synapse_axon = max(
        (synapse.axon_id for synapse in scenario.synapses),
        default=0,
    )
    source_count = max(highest_input_axon, highest_synapse_axon) + 1
    generator = LoihiSpikeGeneratorGroup(
        source_count,
        event_indices,
        event_times,
    )

    objects: list[Any] = [neurons, generator]
    effective_weights = [0] * len(scenario.synapses)

    for group in groups:
        brian_synapses = LoihiSynapses(
            generator,
            neurons,
            w_exp=group.exponent,
            sign_mode=_brian_sign_mode(
                group.sign_mode,
                synapse_sign_mode,
            ),
            num_weight_bits=group.num_weight_bits,
        )
        brian_synapses.connect(
            i=list(group.axon_ids),
            j=list(group.target_neurons),
        )
        brian_synapses.w = np.asarray(group.mantissas, dtype=int)

        observed = _as_integer_tuple(
            brian_synapses.w_act,
            "Brian2Loihi actual weights",
        )
        if len(observed) != len(group.scenario_indices):
            raise RuntimeError(
                "Brian2Loihi returned an unexpected number of actual weights"
            )
        for scenario_index, actual_weight in zip(
            group.scenario_indices,
            observed,
            strict=True,
        ):
            effective_weights[scenario_index] = actual_weight

        objects.append(brian_synapses)

    spike_monitor = LoihiSpikeMonitor(neurons)
    objects.append(spike_monitor)
    network = LoihiNetwork(*objects)

    ticks: list[BackendTick] = []
    for tick in range(len(scenario.input_schedule)):
        current_before = _as_integer_tuple(neurons.I[:], "I before tick")
        voltage_before = _as_integer_tuple(neurons.v[:], "v before tick")
        spike_count_before = len(spike_monitor.i)

        network.run(1)

        current_after = _as_integer_tuple(neurons.I[:], "I after tick")
        voltage_after = _as_integer_tuple(neurons.v[:], "v after tick")
        new_spikes = tuple(
            sorted(
                int(neuron_id)
                for neuron_id in spike_monitor.i[spike_count_before:]
            )
        )
        ticks.append(
            BackendTick(
                tick=tick,
                current_before=current_before,
                voltage_before=voltage_before,
                current_after=current_after,
                voltage_after=voltage_after,
                spikes=new_spikes,
            )
        )

    trace = BackendTrace(
        backend="Brian2Loihi",
        scenario=scenario.name,
        ticks=tuple(ticks),
        metadata=(
            ("brian2", _package_version("brian2")),
            ("brian2-loihi", _package_version("brian2-loihi")),
            ("weight_scale", str(mapping.weight_scale)),
            ("threshold_scale", str(mapping.threshold_scale)),
            ("synapse_group_count", str(len(groups))),
        ),
        synapses=describe_synapses(scenario.synapses),
    )
    return Brian2LoihiBackendRun(
        trace=trace,
        effective_weights=tuple(effective_weights),
    )


def _brian_sign_mode(sign_mode: WeightSignMode, namespace: Any) -> int:
    if sign_mode is WeightSignMode.MIXED:
        return namespace.MIXED
    if sign_mode is WeightSignMode.EXCITATORY:
        return namespace.EXCITATORY
    if sign_mode is WeightSignMode.INHIBITORY:
        return namespace.INHIBITORY
    raise TypeError(f"unsupported WeightSignMode: {sign_mode!r}")


def _as_integer_tuple(values: Any, label: str) -> tuple[int, ...]:
    import numpy as np

    array = np.asarray(values, dtype=float)
    rounded = np.rint(array)
    if not np.allclose(array, rounded, atol=1e-9, rtol=0.0):
        raise RuntimeError(f"{label} contains non-integer values: {array!r}")
    return tuple(int(value) for value in rounded.tolist())


def _package_version(package: str) -> str:
    try:
        return version(package)
    except PackageNotFoundError:
        return "unknown"
