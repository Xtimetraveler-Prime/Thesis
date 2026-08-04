"""Data structures for backend-to-backend trace comparison.

The comparison layer deliberately uses a backend-neutral trace format. Today the
backends are the transparent Python model and Brian2Loihi. Later, an RTL
simulator or physical FPGA can emit the same format without changing the
comparison logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from ..arithmetic import ArithmeticConfig
from ..model import NeuronConfig, Synapse


@dataclass(frozen=True, slots=True)
class ComparisonScenario:
    """One deterministic network configuration and input-spike schedule."""

    name: str
    neuron_configs: tuple[NeuronConfig, ...]
    synapses: tuple[Synapse, ...]
    input_schedule: tuple[tuple[int, ...], ...]
    arithmetic: ArithmeticConfig = field(default_factory=ArithmeticConfig)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("scenario name cannot be empty")
        if not self.neuron_configs:
            raise ValueError("scenario must contain at least one neuron")
        if not self.input_schedule:
            raise ValueError("scenario must contain at least one tick")

        neuron_count = len(self.neuron_configs)
        for synapse in self.synapses:
            if synapse.target_neuron >= neuron_count:
                raise ValueError(
                    f"synapse target {synapse.target_neuron} is outside "
                    f"0..{neuron_count - 1}"
                )
        for tick, axons in enumerate(self.input_schedule):
            if any(axon_id < 0 for axon_id in axons):
                raise ValueError(f"tick {tick} contains a negative axon ID")

    @classmethod
    def build(
        cls,
        *,
        name: str,
        neuron_configs: list[NeuronConfig] | tuple[NeuronConfig, ...],
        synapses: list[Synapse] | tuple[Synapse, ...] = (),
        input_schedule: list[tuple[int, ...]] | tuple[tuple[int, ...], ...],
        arithmetic: ArithmeticConfig | None = None,
    ) -> "ComparisonScenario":
        """Construct a scenario while normalizing mutable inputs to tuples."""

        return cls(
            name=name,
            neuron_configs=tuple(neuron_configs),
            synapses=tuple(synapses),
            input_schedule=tuple(tuple(tick) for tick in input_schedule),
            arithmetic=arithmetic or ArithmeticConfig(),
        )


@dataclass(frozen=True, slots=True)
class BackendSynapse:
    """Portable description of one effective or encoded synapse.

    Integer-only legacy synapses populate only the routing fields and effective
    weight. Encoded synapses additionally retain every value needed to audit or
    reconstruct the Loihi-style initialization result.
    """

    axon_id: int
    target_neuron: int
    effective_weight: int
    requested_mantissa: int | None = None
    quantized_mantissa: int | None = None
    exponent: int | None = None
    num_weight_bits: int | None = None
    sign_mode: str | None = None
    effective_weight_before_clip: int | None = None
    clipped: bool | None = None

    def __post_init__(self) -> None:
        if self.axon_id < 0:
            raise ValueError("axon_id cannot be negative")
        if self.target_neuron < 0:
            raise ValueError("target_neuron cannot be negative")

        encoded_fields = (
            self.requested_mantissa,
            self.quantized_mantissa,
            self.exponent,
            self.num_weight_bits,
            self.sign_mode,
            self.effective_weight_before_clip,
            self.clipped,
        )
        if any(value is not None for value in encoded_fields) and not all(
            value is not None for value in encoded_fields
        ):
            raise ValueError(
                "encoded backend synapses must provide every encoding field"
            )

    @property
    def is_encoded(self) -> bool:
        return self.requested_mantissa is not None

    @classmethod
    def from_synapse(cls, synapse: Synapse) -> "BackendSynapse":
        """Create a portable descriptor from a production synapse."""

        encoding = synapse.encoding
        if encoding is None:
            return cls(
                axon_id=synapse.axon_id,
                target_neuron=synapse.target_neuron,
                effective_weight=synapse.weight,
            )

        fmt = encoding.weight_format
        return cls(
            axon_id=synapse.axon_id,
            target_neuron=synapse.target_neuron,
            effective_weight=encoding.effective_weight,
            requested_mantissa=encoding.requested_mantissa,
            quantized_mantissa=encoding.quantized_mantissa,
            exponent=fmt.exponent,
            num_weight_bits=fmt.num_weight_bits,
            sign_mode=fmt.sign_mode.value,
            effective_weight_before_clip=encoding.effective_weight_before_clip,
            clipped=encoding.clipped,
        )


def describe_synapses(synapses: Iterable[Synapse]) -> tuple[BackendSynapse, ...]:
    """Normalize scenario synapses into stable trace metadata."""

    return tuple(BackendSynapse.from_synapse(synapse) for synapse in synapses)


@dataclass(frozen=True, slots=True)
class BackendTick:
    """Backend-neutral state snapshot for one completed algorithmic tick."""

    tick: int
    current_before: tuple[int, ...]
    voltage_before: tuple[int, ...]
    current_after: tuple[int, ...]
    voltage_after: tuple[int, ...]
    spikes: tuple[int, ...]

    def __post_init__(self) -> None:
        lengths = {
            len(self.current_before),
            len(self.voltage_before),
            len(self.current_after),
            len(self.voltage_after),
        }
        if len(lengths) != 1:
            raise ValueError("all state vectors in a backend tick must match")
        if self.tick < 0:
            raise ValueError("tick cannot be negative")


@dataclass(frozen=True, slots=True)
class BackendTrace:
    """Complete trace produced by one simulation or hardware backend."""

    backend: str
    scenario: str
    ticks: tuple[BackendTick, ...]
    metadata: tuple[tuple[str, str], ...] = ()
    synapses: tuple[BackendSynapse, ...] = ()

    def __post_init__(self) -> None:
        if not self.backend.strip():
            raise ValueError("backend name cannot be empty")
        expected_ticks = tuple(range(len(self.ticks)))
        actual_ticks = tuple(tick.tick for tick in self.ticks)
        if actual_ticks != expected_ticks:
            raise ValueError(
                "backend traces must use contiguous zero-based tick indices"
            )

    @property
    def neuron_count(self) -> int:
        return len(self.ticks[0].current_after) if self.ticks else 0


@dataclass(frozen=True, slots=True)
class TraceMismatch:
    """One difference between the reference and candidate traces."""

    tick: int | None
    field: str
    neuron_id: int | None
    reference: Any
    candidate: Any


@dataclass(frozen=True, slots=True)
class ComparisonReport:
    """Result of comparing one candidate trace with one reference trace."""

    reference_backend: str
    candidate_backend: str
    scenario: str
    compared_ticks: int
    mismatches: tuple[TraceMismatch, ...]

    @property
    def passed(self) -> bool:
        return not self.mismatches
