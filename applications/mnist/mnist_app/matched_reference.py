"""Shared frozen-workload contract for MNIST-11/12 matched comparisons.

The matched-reference experiments deliberately reuse the accepted native-sparse
MNIST deployment without retraining or parameter retuning.  This module owns the
application-level audit boundary shared by Brian2Loihi and Catalyst adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
from typing import Iterable, Sequence


PROFILE = "native-sparse"
PRESENTATION_TICKS = 16
INPUT_AXONS = 784
OUTPUT_NEURONS = 10
STORED_SYNAPSES = 4086
EXPECTED_THRESHOLD = 8384
EXPECTED_CURRENT_DECAY = 4096
EXPECTED_VOLTAGE_DECAY = 0
EXPECTED_REFRACTORY = 0
REFERENCE_REFRACTORY = 1
SAT24_MAX = (1 << 23) - 1

SEMANTIC_CLASSES = {
    "EXACT",
    "EQUIVALENT",
    "TRANSLATED",
    "UNREPRESENTABLE",
    "NOT_USED",
}


@dataclass(frozen=True, slots=True)
class FrozenMatchedWorkload:
    deployment_path: Path
    profile: str
    configs: tuple[object, ...]
    synapses: tuple[object, ...]
    input_axons: int
    output_neurons: int
    presentation_ticks: int
    conservative_abs_voltage_bound: float


@dataclass(frozen=True, slots=True)
class SemanticAuditRow:
    field: str
    brian2loihi: str
    catalyst: str
    rationale: str

    def __post_init__(self) -> None:
        if self.brian2loihi not in SEMANTIC_CLASSES:
            raise ValueError(f"invalid Brian2Loihi semantic class: {self.brian2loihi}")
        if self.catalyst not in SEMANTIC_CLASSES:
            raise ValueError(f"invalid Catalyst semantic class: {self.catalyst}")


def native_deployment_path(frozen_root: str | Path) -> Path:
    return Path(frozen_root) / "deployments" / PROFILE / "deployment.json"


def load_frozen_matched_workload(frozen_root: str | Path) -> FrozenMatchedWorkload:
    """Load and validate the exact native-sparse deployment used by MNIST-11/12."""

    from neuromorphic_twin import NeuronConfig, read_weight_storage_json

    deployment = native_deployment_path(frozen_root)
    payload = json.loads(deployment.read_text(encoding="utf-8"))
    architecture = payload["architecture"]
    if payload.get("schema") != "neuromorphic-twin-mnist-deployment-v2":
        raise ValueError("unsupported frozen MNIST deployment schema")
    if payload.get("profile") != PROFILE:
        raise ValueError("matched comparison must use frozen native-sparse profile")
    expected_architecture = {
        "input_axons": INPUT_AXONS,
        "output_neurons": OUTPUT_NEURONS,
        "presentation_ticks": PRESENTATION_TICKS,
        "stored_synapses": STORED_SYNAPSES,
        "routes": 0,
    }
    for key, expected in expected_architecture.items():
        if int(architecture[key]) != expected:
            raise ValueError(f"frozen architecture changed: {key}={architecture[key]!r}")

    configs = tuple(NeuronConfig(**row) for row in payload["neuron_configs"])
    if len(configs) != OUTPUT_NEURONS or any(config != configs[0] for config in configs[1:]):
        raise ValueError("matched reference requires ten identical frozen output configs")
    config = configs[0]
    expected_config = (
        EXPECTED_CURRENT_DECAY,
        EXPECTED_VOLTAGE_DECAY,
        EXPECTED_THRESHOLD,
        0,
        0,
        EXPECTED_REFRACTORY,
    )
    actual_config = (
        config.current_decay,
        config.voltage_decay,
        config.threshold,
        config.bias,
        config.reset_voltage,
        config.refractory_ticks,
    )
    if actual_config != expected_config:
        raise ValueError(f"frozen native-sparse neuron contract changed: {actual_config!r}")

    storage = read_weight_storage_json(deployment.parent / payload["weight_storage"])
    if storage.axon_count != INPUT_AXONS or storage.synapse_count != STORED_SYNAPSES:
        raise ValueError("frozen native-sparse weight-storage counts changed")
    synapses = storage.decode_synapses()
    if len(synapses) != STORED_SYNAPSES or any(s.encoding is None for s in synapses):
        raise ValueError("matched comparison requires all stored synapses to retain encoding metadata")
    if any(s.weight % 64 for s in synapses):
        raise ValueError("frozen effective weights must remain aligned to 64")

    bound = float(payload["quantization"]["conservative_abs_voltage_bound"])
    if bound >= SAT24_MAX:
        raise ValueError("frozen conservative voltage bound no longer proves SAT24 is inactive")

    return FrozenMatchedWorkload(
        deployment_path=deployment,
        profile=PROFILE,
        configs=configs,
        synapses=synapses,
        input_axons=INPUT_AXONS,
        output_neurons=OUTPUT_NEURONS,
        presentation_ticks=PRESENTATION_TICKS,
        conservative_abs_voltage_bound=bound,
    )


def reference_configs(workload: FrozenMatchedWorkload) -> tuple[object, ...]:
    """Return the R=1 reference surrogate for the frozen project's R=0 config.

    FPGA-v1 stores ``max(R-1, 0)`` future blocked ticks after a spike.  Therefore
    R=0 and R=1 both store zero and are behaviorally identical under the frozen
    one-update-per-neuron-per-tick execution contract.  Brian2Loihi requires
    refractory>=1 and Catalyst's frozen transform maps canonical R to native
    R-1, so R=1 is the explicit common representation.
    """

    return tuple(replace(config, refractory_ticks=REFERENCE_REFRACTORY) for config in workload.configs)


def validate_schedule(schedule: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    if len(schedule) != PRESENTATION_TICKS:
        raise ValueError("matched MNIST schedule must contain exactly 16 ticks")
    normalized: list[tuple[int, ...]] = []
    for tick, events in enumerate(schedule):
        row = tuple(int(axon) for axon in events)
        if any(axon < 0 or axon >= INPUT_AXONS for axon in row):
            raise ValueError(f"tick {tick} contains an axon outside 0..783")
        if len(row) != len(set(row)):
            raise ValueError(
                f"tick {tick} repeats a source axon; this is outside the exact Brian2Loihi input subset"
            )
        normalized.append(row)
    return tuple(normalized)


def build_comparison_scenario(
    workload: FrozenMatchedWorkload,
    schedule: Sequence[Sequence[int]],
    *,
    name: str,
    reference_refractory: bool = False,
    unbounded_arithmetic: bool = False,
):
    """Build one backend-neutral frozen MNIST scenario without changing weights."""

    from neuromorphic_twin import ArithmeticConfig, FPGA_CORE_ARITHMETIC_V1
    from neuromorphic_twin.comparison.model import ComparisonScenario

    configs = reference_configs(workload) if reference_refractory else workload.configs
    arithmetic = ArithmeticConfig() if unbounded_arithmetic else FPGA_CORE_ARITHMETIC_V1
    return ComparisonScenario.build(
        name=name,
        neuron_configs=configs,
        synapses=workload.synapses,
        input_schedule=validate_schedule(schedule),
        arithmetic=arithmetic,
        spike_routes=(),
    )


def spike_counts_from_trace(trace: object, *, neurons: int = OUTPUT_NEURONS) -> tuple[int, ...]:
    counts = [0] * neurons
    for tick in trace.ticks:
        for neuron_id in tick.spikes:
            counts[int(neuron_id)] += 1
    return tuple(counts)


def decode_spike_counts(counts: Sequence[int]) -> int:
    if len(counts) != OUTPUT_NEURONS:
        raise ValueError("MNIST decoder requires ten output spike counts")
    # Python's max with a key returns the first maximum, matching np.argmax's
    # accepted lowest-ID tie break.
    return max(range(OUTPUT_NEURONS), key=lambda neuron: int(counts[neuron]))


def frozen_corpus_indices(frozen_root: str | Path) -> tuple[int, ...]:
    payload = json.loads(
        (Path(frozen_root) / "fpga_validation_corpus.json").read_text(encoding="utf-8")
    )
    if int(payload.get("count", -1)) != 30 or len(payload.get("entries", [])) != 30:
        raise ValueError("frozen validation corpus must contain exactly 30 entries")
    indices = tuple(int(entry["mnist_test_index"]) for entry in payload["entries"])
    if len(set(indices)) != 30:
        raise ValueError("frozen validation corpus indices must be unique")
    return indices


def semantic_audit(workload: FrozenMatchedWorkload) -> tuple[SemanticAuditRow, ...]:
    """Application-level semantic classification frozen before matched execution."""

    return (
        SemanticAuditRow(
            "input_schedule",
            "EXACT",
            "TRANSLATED",
            "Brian receives the same 16 tick/axon spike list; Catalyst compares both graph-preserving source spikes and a separately labeled delivered-drive collapse.",
        ),
        SemanticAuditRow(
            "synaptic_graph",
            "EXACT",
            "TRANSLATED",
            "Brian preserves all 4,086 encoded axon->output edges; Catalyst CPU graph mode preserves the effective 4,086-edge matrix but not Loihi source encoding fields.",
        ),
        SemanticAuditRow(
            "effective_weights",
            "EXACT",
            "EXACT",
            "All frozen weights are effective integer multiples of 64 and fit both Brian2Loihi's accepted format mapping and Catalyst signed-int16 weight boundary.",
        ),
        SemanticAuditRow(
            "threshold",
            "TRANSLATED",
            "TRANSLATED",
            "8384 maps to Brian threshold_v_mant=131; Catalyst uses native T+1 to reproduce the project's strict V>T comparison.",
        ),
        SemanticAuditRow(
            "current_decay",
            "EXACT",
            "TRANSLATED",
            "Brian uses decay_I=4096 directly. Catalyst simple-LIF has no independent current state; the delivered-drive experiment is valid because project current fully decays each tick.",
        ),
        SemanticAuditRow(
            "voltage_decay",
            "EXACT",
            "EQUIVALENT",
            "Frozen voltage_decay=0 is directly represented by Brian and by zero Catalyst leak in the simple-LIF comparison.",
        ),
        SemanticAuditRow(
            "reset_voltage_bias",
            "EXACT",
            "EQUIVALENT",
            "All are zero; Brian uses fixed zero reset and Catalyst resting/leak settings preserve zero-reset behavior on the common subset.",
        ),
        SemanticAuditRow(
            "refractory",
            "EQUIVALENT",
            "EQUIVALENT",
            "Project R=0 and R=1 both store zero future blocked ticks; the matched reference uses R=1, which Brian accepts and Catalyst maps to native refractory=0.",
        ),
        SemanticAuditRow(
            "finite_width_saturation",
            "EQUIVALENT",
            "UNREPRESENTABLE",
            f"Brian runs unbounded, but the frozen conservative voltage bound {workload.conservative_abs_voltage_bound:.1f} is below SAT24 max {SAT24_MAX}; Catalyst state-width behavior is not declared identical.",
        ),
        SemanticAuditRow(
            "online_learning_recurrence",
            "NOT_USED",
            "NOT_USED",
            "The accepted MNIST deployment has fixed weights, no routes, and no online learning.",
        ),
    )


def semantic_audit_payload(workload: FrozenMatchedWorkload) -> dict[str, object]:
    rows = semantic_audit(workload)
    return {
        "schema": "neuromorphic-twin-mnist-matched-semantic-audit-v1",
        "profile": workload.profile,
        "rows": [
            {
                "field": row.field,
                "brian2loihi": row.brian2loihi,
                "catalyst": row.catalyst,
                "rationale": row.rationale,
            }
            for row in rows
        ],
        "allowed_classes": sorted(SEMANTIC_CLASSES),
    }
