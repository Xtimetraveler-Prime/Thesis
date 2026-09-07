"""M12.3 directed multi-tick Python/physical-FPGA conformance corpus.

Python independently constructs each stateful workload and computes every
committed tick from the frozen FPGA-v1 software contracts. FPGA-visible sources
receive only static load images and per-tick *external* event schedules. Recurrent
inputs are never injected from the golden model: they must be produced by the
physical FPGA's own previous-tick routing and double-buffered queues.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Sequence

from .fpga_core_capacity import pack_neuron_config_word, pack_neuron_state_word
from .fpga_physical_trace import (
    FPGA_PHYSICAL_TRACE_TRANSPORT_JTAG_VIO,
    PhysicalFpgaTickCapture,
    PhysicalFpgaTraceArtifact,
)
from .fpga_recurrent_routing import (
    DoubleBufferedRecurrentQueue,
    FrozenRouteStorage,
    freeze_spike_routes_v1,
    route_and_commit_recurrent_v1,
)
from .fpga_synapse_reference import accumulate_frozen_weight_image_v1
from .fpga_trace_snapshot import FpgaTickTraceSnapshot
from .fpga_weight_storage import FrozenWeightStorage, pack_synapse_word, pack_weight_format
from .model import NeuronConfig, NeuronState, SpikeRoute
from .neuron_array_reference import step_packed_neuron_array_v1
from .weights import WeightFormat, WeightSignMode


M12_MULTITICK_CORPUS_SCHEMA = "neuromorphic-twin-m12-multitick-corpus-v1"
M12_MULTITICK_REPORT_SCHEMA = "neuromorphic-twin-m12-multitick-report-v1"


@dataclass(frozen=True, slots=True)
class FpgaMultiTickCase:
    """One stateful M12.3 workload with an independent Python-golden timeline."""

    case_id: int
    name: str
    category: str
    coverage: tuple[str, ...]
    storage: FrozenWeightStorage
    routes: FrozenRouteStorage
    config_words: tuple[int, ...]
    initial_state_words: tuple[int, ...]
    external_schedule: tuple[tuple[int, ...], ...]
    expected_ticks: tuple[PhysicalFpgaTickCapture, ...]

    def __post_init__(self) -> None:
        if isinstance(self.case_id, bool) or not isinstance(self.case_id, int):
            raise TypeError("case_id must be int")
        if not 0 <= self.case_id < 256:
            raise ValueError("case_id must fit unsigned 8 bits")
        if not self.name or not self.category or not self.coverage:
            raise ValueError("name, category, and coverage must be nonempty")
        if not self.external_schedule:
            raise ValueError("multi-tick case must contain at least one tick")
        if len(self.config_words) != len(self.initial_state_words):
            raise ValueError("config/state word counts must match")
        if len(self.config_words) != self.routes.neuron_count:
            raise ValueError("route neuron_count must match configured neurons")
        if len(self.expected_ticks) != len(self.external_schedule):
            raise ValueError("expected timeline length must match external schedule")
        for index, capture in enumerate(self.expected_ticks, start=1):
            if capture.snapshot.committed_tick != index:
                raise ValueError("expected committed ticks must be dense and one-based")
            if capture.snapshot.neuron_count != self.neuron_count:
                raise ValueError("expected neuron_count must match load image")
            if capture.snapshot.external_input_axons != self.external_schedule[index - 1]:
                raise ValueError("expected external events must match schedule")

    @property
    def neuron_count(self) -> int:
        return len(self.config_words)

    @property
    def tick_count(self) -> int:
        return len(self.external_schedule)

    def to_dict(self) -> dict[str, Any]:
        expected_artifact = PhysicalFpgaTraceArtifact(
            scenario_id=self.name,
            transport="python-golden",
            device="python-golden",
            ticks=self.expected_ticks,
        )
        return {
            "case_id": self.case_id,
            "name": self.name,
            "category": self.category,
            "coverage": list(self.coverage),
            "counts": {
                "neurons": self.neuron_count,
                "axons": self.storage.axon_count,
                "synapses": self.storage.synapse_count,
                "formats": self.storage.format_count,
                "routes": self.routes.route_count,
                "ticks": self.tick_count,
                "max_external_events_per_tick": max(map(len, self.external_schedule)),
            },
            "load_image": {
                "format_words": [_hex(word, 16) for word in self.storage.format_words],
                "synapse_words": [_hex(word, 32) for word in self.storage.synapse_words],
                "weight_rows": [_hex(word, 32) for word in self.storage.axon_row_pointers],
                "route_rows": [_hex(word, 32) for word in self.routes.row_pointers],
                "route_targets": [_hex(word, 16) for word in self.routes.target_axons],
                "config_words": [_hex(word, 128) for word in self.config_words],
                "initial_state_words": [_hex(word, 64) for word in self.initial_state_words],
                "external_schedule": [list(events) for events in self.external_schedule],
            },
            "expected_ticks": expected_artifact.to_dict()["ticks"],
        }


@dataclass(frozen=True, slots=True)
class MultiTickMismatch:
    tick: int | None
    field: str
    expected: Any
    actual: Any


@dataclass(frozen=True, slots=True)
class MultiTickDifferentialReport:
    case_id: int
    case_name: str
    device: str
    mismatches: tuple[MultiTickMismatch, ...]

    @property
    def passed(self) -> bool:
        return not self.mismatches

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": M12_MULTITICK_REPORT_SCHEMA,
            "case_id": self.case_id,
            "case_name": self.case_name,
            "device": self.device,
            "passed": self.passed,
            "mismatch_count": len(self.mismatches),
            "mismatches": [
                {
                    "tick": mismatch.tick,
                    "field": mismatch.field,
                    "expected": mismatch.expected,
                    "actual": mismatch.actual,
                }
                for mismatch in self.mismatches
            ],
        }


def build_m12_multitick_cases() -> tuple[FpgaMultiTickCase, ...]:
    """Return the frozen directed M12.3 stateful/recurrent corpus."""

    exc = WeightFormat(0, 8, WeightSignMode.EXCITATORY)
    spike = _config(current_decay=4096, voltage_decay=4096, threshold=32)
    double_required = _config(current_decay=4096, voltage_decay=4096, threshold=96)

    cases = (
        _make_case(
            0,
            "feedforward-recurrent-chain",
            "chain",
            ("feedforward_chain", "next_tick_recurrence", "queue_swaps", "quiescence"),
            configs=(spike, spike, spike),
            states=(NeuronState(), NeuronState(), NeuronState()),
            formats=(exc,),
            rows=(
                ((0, 1, 0),),
                ((1, 1, 0),),
                ((2, 1, 0),),
            ),
            routes=(SpikeRoute(0, 1), SpikeRoute(1, 2)),
            external_schedule=((0,), (), (), ()),
        ),
        _make_case(
            1,
            "self-recurrent-oscillator",
            "self-recurrent",
            ("self_recurrent", "next_tick_recurrence", "repeated_bank_swaps"),
            configs=(spike,),
            states=(NeuronState(),),
            formats=(exc,),
            rows=(((0, 1, 0),),),
            routes=(SpikeRoute(0, 0),),
            external_schedule=((0,), (), (), ()),
        ),
        _make_case(
            2,
            "two-neuron-recurrent-loop",
            "loop",
            ("recurrent_loop", "state_history", "repeated_bank_swaps", "reset_replay_anchor"),
            configs=(spike, spike),
            states=(NeuronState(), NeuronState()),
            formats=(exc,),
            rows=(((0, 1, 0),), ((1, 1, 0),)),
            routes=(SpikeRoute(0, 1), SpikeRoute(1, 0)),
            external_schedule=((0,), (), (), (), (), ()),
        ),
        _make_case(
            3,
            "recurrent-fanout",
            "fanout",
            ("recurrent_fanout", "simultaneous_spikes"),
            configs=(spike, spike, spike),
            states=(NeuronState(), NeuronState(), NeuronState()),
            formats=(exc,),
            rows=(
                ((0, 1, 0),),
                ((1, 1, 0),),
                ((2, 1, 0),),
            ),
            routes=(SpikeRoute(0, 1), SpikeRoute(0, 2)),
            external_schedule=((0,), (), ()),
        ),
        _make_case(
            4,
            "recurrent-fanin",
            "fanin",
            ("recurrent_fanin", "simultaneous_sources", "multiple_recurrent_axons"),
            configs=(spike, spike, double_required),
            states=(NeuronState(), NeuronState(), NeuronState()),
            formats=(exc,),
            rows=(
                ((0, 1, 0),),
                ((1, 1, 0),),
                ((2, 1, 0),),
                ((2, 1, 0),),
            ),
            routes=(SpikeRoute(0, 2), SpikeRoute(1, 3)),
            external_schedule=((0, 1), (), ()),
        ),
        _make_case(
            5,
            "same-target-recurrent-multiplicity",
            "multiplicity",
            ("same_target_multiplicity", "cross_source_duplicates", "double_accumulation"),
            configs=(spike, spike, double_required),
            states=(NeuronState(), NeuronState(), NeuronState()),
            formats=(exc,),
            rows=(
                ((0, 1, 0),),
                ((1, 1, 0),),
                ((2, 1, 0),),
            ),
            routes=(SpikeRoute(0, 2), SpikeRoute(1, 2)),
            external_schedule=((0, 1), (), ()),
        ),
        _make_case(
            6,
            "external-plus-recurrent-same-tick",
            "mixed-input",
            ("external_plus_recurrent", "external_before_recurrent", "combined_accumulation"),
            configs=(spike, double_required),
            states=(NeuronState(), NeuronState()),
            formats=(exc,),
            rows=(
                ((0, 1, 0),),
                ((1, 1, 0),),
                ((1, 1, 0),),
            ),
            routes=(SpikeRoute(0, 1),),
            external_schedule=((0,), (2,), ()),
        ),
        _make_case(
            7,
            "simultaneous-routing-order",
            "ordering",
            ("simultaneous_spikes", "source_order", "route_declaration_order"),
            configs=(spike, spike),
            states=(NeuronState(), NeuronState()),
            formats=(exc,),
            rows=(
                ((0, 1, 0),),
                ((1, 1, 0),),
                (),
                (),
                (),
            ),
            routes=(
                SpikeRoute(0, 3),
                SpikeRoute(0, 2),
                SpikeRoute(1, 4),
            ),
            external_schedule=((0, 1), (), ()),
        ),
        _make_case(
            8,
            "quiescence-then-renewed-input",
            "quiescence",
            ("quiescent_period", "renewed_external_input", "state_persistence"),
            configs=(spike,),
            states=(NeuronState(),),
            formats=(exc,),
            rows=(((0, 1, 0),),),
            routes=(),
            external_schedule=((0,), (), (), (0,), ()),
        ),
        _make_case(
            9,
            "decay-refractory-history",
            "state-history",
            ("multi_tick_decay", "refractory_entry_hold_release", "input_during_refractory"),
            configs=(
                _config(
                    current_decay=2048,
                    voltage_decay=2048,
                    threshold=96,
                    reset_voltage=-16,
                    refractory_ticks=3,
                ),
            ),
            states=(NeuronState(),),
            formats=(exc,),
            rows=(((0, 2, 0),),),
            routes=(),
            external_schedule=((0,), (), (0,), (), (), ()),
        ),
    )

    ids = tuple(case.case_id for case in cases)
    names = tuple(case.name for case in cases)
    if ids != tuple(range(len(cases))):
        raise RuntimeError("M12.3 case IDs must remain dense and zero-based")
    if len(names) != len(set(names)):
        raise RuntimeError("M12.3 case names must be unique")
    return cases


def compare_m12_multitick_capture(
    case: FpgaMultiTickCase,
    actual: PhysicalFpgaTraceArtifact,
) -> MultiTickDifferentialReport:
    """Compare every committed physical tick against one Python-golden case."""

    if not isinstance(case, FpgaMultiTickCase):
        raise TypeError("case must be FpgaMultiTickCase")
    if not isinstance(actual, PhysicalFpgaTraceArtifact):
        raise TypeError("actual must be PhysicalFpgaTraceArtifact")

    mismatches: list[MultiTickMismatch] = []

    def check(tick: int | None, field: str, expected: Any, observed: Any) -> None:
        if expected != observed:
            mismatches.append(MultiTickMismatch(tick, field, expected, observed))

    check(None, "scenario_id", case.name, actual.scenario_id)
    check(None, "transport", FPGA_PHYSICAL_TRACE_TRANSPORT_JTAG_VIO, actual.transport)
    check(None, "tick_count", case.tick_count, len(actual.ticks))

    for expected, observed in zip(case.expected_ticks, actual.ticks):
        tick = expected.snapshot.committed_tick
        for field in (
            "committed_tick",
            "external_input_axons",
            "recurrent_input_axons",
            "synaptic_input",
            "state_before_words",
            "state_after_words",
            "spikes",
            "routed_output_axons",
        ):
            check(
                tick,
                f"snapshot.{field}",
                getattr(expected.snapshot, field),
                getattr(observed.snapshot, field),
            )
        for field in (
            "core_fault",
            "core_fault_code",
            "recurrent_current_bank",
            "recurrent_current_count",
            "recurrent_bank0_count",
            "recurrent_bank1_count",
            "consumed_recurrent_count",
            "routed_recurrent_count",
            "external_event_count",
        ):
            check(tick, field, getattr(expected, field), getattr(observed, field))

    return MultiTickDifferentialReport(
        case_id=case.case_id,
        case_name=case.name,
        device=actual.device,
        mismatches=tuple(mismatches),
    )


def write_m12_multitick_corpus(
    output_dir: str | Path,
    cases: Sequence[FpgaMultiTickCase] | None = None,
) -> Path:
    selected = tuple(cases) if cases is not None else build_m12_multitick_cases()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    manifest_cases: list[dict[str, Any]] = []
    for case in selected:
        payload = {"schema": M12_MULTITICK_CORPUS_SCHEMA, **case.to_dict()}
        filename = f"{case.case_id:02d}-{case.name}.golden.json"
        (output / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifest_cases.append(
            {
                "case_id": case.case_id,
                "name": case.name,
                "category": case.category,
                "coverage": list(case.coverage),
                "golden_file": filename,
                "counts": payload["counts"],
            }
        )
    manifest = {
        "schema": M12_MULTITICK_CORPUS_SCHEMA,
        "case_count": len(selected),
        "total_ticks": sum(case.tick_count for case in selected),
        "cases": manifest_cases,
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def write_m12_multitick_report(
    report: MultiTickDifferentialReport,
    path: str | Path,
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output


def _make_case(
    case_id: int,
    name: str,
    category: str,
    coverage: tuple[str, ...],
    *,
    configs: Sequence[NeuronConfig],
    states: Sequence[NeuronState],
    formats: Sequence[WeightFormat],
    rows: Sequence[Sequence[tuple[int, int, int]]],
    routes: Sequence[SpikeRoute],
    external_schedule: Sequence[Sequence[int]],
) -> FpgaMultiTickCase:
    if len(configs) != len(states):
        raise ValueError("configs/states lengths must match")
    neuron_count = len(configs)
    storage = _make_storage(formats, rows)
    frozen_routes = freeze_spike_routes_v1(routes, neuron_count=neuron_count)
    config_words = tuple(pack_neuron_config_word(config) for config in configs)
    initial_state_words = tuple(pack_neuron_state_word(state) for state in states)
    external_ticks = tuple(tuple(events) for events in external_schedule)

    queue = DoubleBufferedRecurrentQueue.empty()
    state_words = initial_state_words
    expected: list[PhysicalFpgaTickCapture] = []

    for tick_index, external_axons in enumerate(external_ticks, start=1):
        recurrent_before = queue.current_events
        phase_b = accumulate_frozen_weight_image_v1(
            storage,
            neuron_count=neuron_count,
            external_axons=external_axons,
            recurrent_axons=recurrent_before,
        )
        stepped = step_packed_neuron_array_v1(
            state_words,
            config_words,
            phase_b.accumulators,
        )
        routed = route_and_commit_recurrent_v1(
            queue,
            frozen_routes,
            stepped.spikes,
        )
        after = routed.queue_after_commit
        snapshot = FpgaTickTraceSnapshot(
            committed_tick=tick_index,
            external_input_axons=external_axons,
            recurrent_input_axons=routed.consumed_recurrent_axons,
            synaptic_input=phase_b.accumulators,
            state_before_words=state_words,
            state_after_words=stepped.state_words,
            spikes=stepped.spikes,
            routed_output_axons=routed.routed_output_axons,
        )
        expected.append(
            PhysicalFpgaTickCapture(
                snapshot=snapshot,
                core_fault=False,
                core_fault_code=0,
                recurrent_current_bank=bool(after.current_bank),
                recurrent_current_count=len(after.current_events),
                recurrent_bank0_count=len(after.bank0),
                recurrent_bank1_count=len(after.bank1),
                consumed_recurrent_count=len(routed.consumed_recurrent_axons),
                routed_recurrent_count=len(routed.routed_output_axons),
                external_event_count=len(external_axons),
            )
        )
        state_words = stepped.state_words
        queue = after

    return FpgaMultiTickCase(
        case_id=case_id,
        name=name,
        category=category,
        coverage=coverage,
        storage=storage,
        routes=frozen_routes,
        config_words=config_words,
        initial_state_words=initial_state_words,
        external_schedule=external_ticks,
        expected_ticks=tuple(expected),
    )


def _make_storage(
    formats: Sequence[WeightFormat],
    rows: Sequence[Sequence[tuple[int, int, int]]],
) -> FrozenWeightStorage:
    format_words = tuple(pack_weight_format(fmt) for fmt in formats)
    synapse_words: list[int] = []
    pointers = [0]
    for row in rows:
        for target, mantissa, format_index in row:
            synapse_words.append(
                pack_synapse_word(
                    target_neuron=target,
                    requested_mantissa=mantissa,
                    format_index=format_index,
                )
            )
        pointers.append(len(synapse_words))
    return FrozenWeightStorage(
        format_words=format_words,
        synapse_words=tuple(synapse_words),
        axon_row_pointers=tuple(pointers),
    )


def _config(
    *,
    current_decay: int = 0,
    voltage_decay: int = 0,
    threshold: int = 4096,
    bias: int = 0,
    reset_voltage: int = 0,
    refractory_ticks: int = 0,
) -> NeuronConfig:
    return NeuronConfig(
        current_decay=current_decay,
        voltage_decay=voltage_decay,
        threshold=threshold,
        bias=bias,
        reset_voltage=reset_voltage,
        refractory_ticks=refractory_ticks,
    )


def _hex(value: int, bits: int) -> str:
    return f"0x{value & ((1 << bits) - 1):0{(bits + 3) // 4}x}"
