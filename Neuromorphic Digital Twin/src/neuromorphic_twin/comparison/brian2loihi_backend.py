"""Optional adapter for the external Brian2Loihi reference emulator."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from .model import (
    BackendTick,
    BackendTrace,
    ComparisonScenario,
    describe_synapses,
)
from ..arithmetic import OverflowMode


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

    for synapse in scenario.synapses:
        if synapse.encoding is not None:
            raise UnsupportedScenarioError(
                "the generic Brian2Loihi adapter does not yet group encoded "
                "synapses by exponent, precision, and sign mode; use the M08.3 "
                "weight-conformance runner until that M08.4 refactor lands"
            )
        effective_weight_to_mantissa(synapse.weight, mapping)

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
    mapping = mapping or Brian2LoihiMapping()
    validate_brian2loihi_scenario(scenario, mapping)

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
        (synapse.axon_id for synapse in scenario.synapses), default=0
    )
    source_count = max(highest_input_axon, highest_synapse_axon) + 1
    generator = LoihiSpikeGeneratorGroup(
        source_count,
        event_indices,
        event_times,
    )

    objects: list[Any] = [neurons, generator]
    positive = [synapse for synapse in scenario.synapses if synapse.weight >= 0]
    negative = [synapse for synapse in scenario.synapses if synapse.weight < 0]

    if positive:
        synapses_ex = LoihiSynapses(
            generator,
            neurons,
            w_exp=mapping.weight_exponent,
            sign_mode=synapse_sign_mode.EXCITATORY,
            num_weight_bits=mapping.num_weight_bits,
        )
        synapses_ex.connect(
            i=[synapse.axon_id for synapse in positive],
            j=[synapse.target_neuron for synapse in positive],
        )
        synapses_ex.w = np.asarray(
            [effective_weight_to_mantissa(s.weight, mapping) for s in positive],
            dtype=int,
        )
        objects.append(synapses_ex)

    if negative:
        synapses_in = LoihiSynapses(
            generator,
            neurons,
            w_exp=mapping.weight_exponent,
            sign_mode=synapse_sign_mode.INHIBITORY,
            num_weight_bits=mapping.num_weight_bits,
        )
        synapses_in.connect(
            i=[synapse.axon_id for synapse in negative],
            j=[synapse.target_neuron for synapse in negative],
        )
        synapses_in.w = np.asarray(
            [effective_weight_to_mantissa(s.weight, mapping) for s in negative],
            dtype=int,
        )
        objects.append(synapses_in)

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

    return BackendTrace(
        backend="Brian2Loihi",
        scenario=scenario.name,
        ticks=tuple(ticks),
        metadata=(
            ("brian2", _package_version("brian2")),
            ("brian2-loihi", _package_version("brian2-loihi")),
            ("weight_scale", str(mapping.weight_scale)),
            ("threshold_scale", str(mapping.threshold_scale)),
        ),
        synapses=describe_synapses(scenario.synapses),
    )


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
