"""M12.2 directed single-tick Python/physical-FPGA conformance corpus.

The corpus is generated from the frozen FPGA-v1 software contracts rather than
from FPGA output.  Each case contains the complete packed load image needed by
hardware plus an independently computed expected physical tick.  Later M12.2
board tooling may serialize these inputs into RTL memories, but it must never
embed the expected result in the FPGA implementation under test.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

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
from .specification import STATE_MAX, STATE_MIN
from .weights import WeightFormat, WeightSignMode


M12_SINGLE_TICK_CORPUS_SCHEMA = "neuromorphic-twin-m12-single-tick-corpus-v1"
M12_SINGLE_TICK_REPORT_SCHEMA = "neuromorphic-twin-m12-single-tick-report-v1"


@dataclass(frozen=True, slots=True)
class FpgaSingleTickCase:
    """One independently generated, physically loadable M12.2 case."""

    case_id: int
    name: str
    category: str
    coverage: tuple[str, ...]
    storage: FrozenWeightStorage
    routes: FrozenRouteStorage
    config_words: tuple[int, ...]
    initial_state_words: tuple[int, ...]
    external_axons: tuple[int, ...]
    expected: PhysicalFpgaTickCapture

    def __post_init__(self) -> None:
        if isinstance(self.case_id, bool) or not isinstance(self.case_id, int):
            raise TypeError("case_id must be int")
        if not 0 <= self.case_id < 256:
            raise ValueError("case_id must fit unsigned 8 bits")
        if not self.name:
            raise ValueError("case name must not be empty")
        if not self.category:
            raise ValueError("case category must not be empty")
        if not self.coverage:
            raise ValueError("case coverage must not be empty")
        if len(self.config_words) != len(self.initial_state_words):
            raise ValueError("config/state word counts must match")
        if len(self.config_words) != self.routes.neuron_count:
            raise ValueError("route neuron_count must match configured neurons")
        if self.expected.snapshot.neuron_count != len(self.config_words):
            raise ValueError("expected neuron_count must match load image")
        if self.expected.snapshot.external_input_axons != self.external_axons:
            raise ValueError("expected external events must match load image")
        if self.expected.snapshot.committed_tick != 1:
            raise ValueError("M12.2 single-tick expected capture must commit tick 1")

    @property
    def neuron_count(self) -> int:
        return len(self.config_words)

    def to_dict(self) -> dict[str, Any]:
        expected_artifact = PhysicalFpgaTraceArtifact(
            scenario_id=self.name,
            transport="python-golden",
            device="python-golden",
            ticks=(self.expected,),
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
                "external_events": len(self.external_axons),
            },
            "load_image": {
                "format_words": [_hex(word, 16) for word in self.storage.format_words],
                "synapse_words": [_hex(word, 32) for word in self.storage.synapse_words],
                "weight_rows": [_hex(word, 32) for word in self.storage.axon_row_pointers],
                "route_rows": [_hex(word, 32) for word in self.routes.row_pointers],
                "route_targets": [_hex(word, 16) for word in self.routes.target_axons],
                "config_words": [_hex(word, 128) for word in self.config_words],
                "initial_state_words": [_hex(word, 64) for word in self.initial_state_words],
                "external_axons": list(self.external_axons),
            },
            "expected_tick": expected_artifact.to_dict()["ticks"][0],
        }


@dataclass(frozen=True, slots=True)
class SingleTickMismatch:
    field: str
    expected: Any
    actual: Any


@dataclass(frozen=True, slots=True)
class SingleTickDifferentialReport:
    case_id: int
    case_name: str
    device: str
    mismatches: tuple[SingleTickMismatch, ...]

    @property
    def passed(self) -> bool:
        return not self.mismatches

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": M12_SINGLE_TICK_REPORT_SCHEMA,
            "case_id": self.case_id,
            "case_name": self.case_name,
            "device": self.device,
            "passed": self.passed,
            "mismatch_count": len(self.mismatches),
            "mismatches": [
                {
                    "field": mismatch.field,
                    "expected": mismatch.expected,
                    "actual": mismatch.actual,
                }
                for mismatch in self.mismatches
            ],
        }


def build_m12_single_tick_cases() -> tuple[FpgaSingleTickCase, ...]:
    """Return the frozen directed M12.2 corpus.

    The cases intentionally overlap some features so physical run count stays
    modest while every planned M12.2 feature class has an explicit coverage tag.
    """

    exc = WeightFormat(0, 8, WeightSignMode.EXCITATORY)
    inh = WeightFormat(0, 8, WeightSignMode.INHIBITORY)
    mixed_reduced = WeightFormat(0, 6, WeightSignMode.MIXED)
    exc_exp2 = WeightFormat(2, 8, WeightSignMode.EXCITATORY)
    inh_exp_neg1 = WeightFormat(-1, 8, WeightSignMode.INHIBITORY)

    quiet = _config(threshold=STATE_MAX)
    cases = (
        _make_case(
            0,
            "positive-synaptic-input",
            "synaptic",
            ("positive_synaptic_input", "encoded_excitatory"),
            configs=(quiet,),
            states=(NeuronState(),),
            formats=(exc,),
            rows=(((0, 2, 0),),),
            external=(0,),
        ),
        _make_case(
            1,
            "negative-synaptic-rounding",
            "synaptic",
            ("negative_synaptic_input", "encoded_inhibitory", "current_decay", "negative_rounding"),
            configs=(_config(current_decay=2048, threshold=STATE_MAX),),
            states=(NeuronState(current=-1),),
            formats=(inh,),
            rows=(((0, -1, 0),),),
            external=(0,),
        ),
        _make_case(
            2,
            "mixed-excitation-inhibition",
            "synaptic",
            ("mixed_excitation_inhibition", "multiple_axons"),
            configs=(quiet,),
            states=(NeuronState(),),
            formats=(exc, inh),
            rows=(((0, 3, 0),), ((0, -1, 1),)),
            external=(0, 1),
        ),
        _make_case(
            3,
            "voltage-decay-rounding",
            "voltage",
            ("voltage_decay", "decay_rounding"),
            configs=(_config(voltage_decay=2048, threshold=STATE_MAX),),
            states=(NeuronState(voltage=101),),
            formats=(exc,),
            rows=(((0, 1, 0),),),
            external=(),
        ),
        _make_case(
            4,
            "positive-state-saturation",
            "arithmetic",
            ("positive_state_saturation",),
            configs=(quiet,),
            states=(NeuronState(current=STATE_MAX - 32, voltage=STATE_MAX - 32),),
            formats=(exc,),
            rows=(((0, 1, 0),),),
            external=(0,),
        ),
        _make_case(
            5,
            "negative-state-saturation",
            "arithmetic",
            ("negative_state_saturation",),
            configs=(quiet,),
            states=(NeuronState(current=STATE_MIN + 32, voltage=STATE_MIN + 32),),
            formats=(inh,),
            rows=(((0, -1, 0),),),
            external=(0,),
        ),
        _make_case(
            6,
            "threshold-equality",
            "threshold",
            ("threshold_equality", "strict_greater_than"),
            configs=(_config(threshold=64),),
            states=(NeuronState(voltage=64),),
            formats=(exc,),
            rows=(((0, 1, 0),),),
            external=(),
        ),
        _make_case(
            7,
            "threshold-over-refractory-entry",
            "threshold",
            ("threshold_just_over", "reset", "refractory_entry", "single_tick_routing"),
            configs=(_config(threshold=64, reset_voltage=-7, refractory_ticks=3),),
            states=(NeuronState(voltage=65),),
            formats=(exc,),
            rows=(((0, 1, 0),), ()),
            external=(),
            routes=(SpikeRoute(0, 1),),
        ),
        _make_case(
            8,
            "refractory-hold",
            "refractory",
            ("refractory_hold", "refractory_countdown", "current_updates_while_refractory"),
            configs=(_config(current_decay=2048, threshold=64, reset_voltage=-9, refractory_ticks=3),),
            states=(NeuronState(current=100, voltage=777, refractory_remaining=2),),
            formats=(exc,),
            rows=(((0, 1, 0),),),
            external=(),
        ),
        _make_case(
            9,
            "refractory-release-boundary",
            "refractory",
            ("refractory_release",),
            configs=(_config(threshold=64, refractory_ticks=2),),
            states=(NeuronState(voltage=65, refractory_remaining=0),),
            formats=(exc,),
            rows=(((0, 1, 0),),),
            external=(),
        ),
        _make_case(
            10,
            "multi-neuron-multi-axon",
            "integration",
            ("multiple_neurons", "multiple_axons", "fanout", "fanin"),
            configs=(quiet, quiet, quiet),
            states=(NeuronState(), NeuronState(), NeuronState()),
            formats=(exc, inh),
            rows=(
                ((0, 2, 0), (1, 1, 0)),
                ((1, 2, 0), (2, -1, 1)),
                ((2, 3, 0),),
            ),
            external=(0, 1, 2),
        ),
        _make_case(
            11,
            "repeated-event-multiplicity",
            "routing",
            ("event_multiplicity",),
            configs=(quiet,),
            states=(NeuronState(),),
            formats=(exc,),
            rows=(((0, 1, 0),),),
            external=(0, 0, 0),
        ),
        _make_case(
            12,
            "empty-csr-row",
            "routing",
            ("empty_csr_row",),
            configs=(quiet,),
            states=(NeuronState(),),
            formats=(exc,),
            rows=(((0, 1, 0),), ()),
            external=(1,),
        ),
        _make_case(
            13,
            "encoded-positive-exponent",
            "weight-format",
            ("encoded_positive_exponent",),
            configs=(quiet,),
            states=(NeuronState(),),
            formats=(exc_exp2,),
            rows=(((0, 3, 0),),),
            external=(0,),
        ),
        _make_case(
            14,
            "encoded-negative-exponent",
            "weight-format",
            ("encoded_negative_exponent", "negative_fractional_alignment"),
            configs=(quiet,),
            states=(NeuronState(),),
            formats=(inh_exp_neg1,),
            rows=(((0, -3, 0),),),
            external=(0,),
        ),
        _make_case(
            15,
            "encoded-reduced-precision-mixed",
            "weight-format",
            ("encoded_reduced_precision", "encoded_mixed_sign_mode"),
            configs=(quiet,),
            states=(NeuronState(),),
            formats=(mixed_reduced,),
            rows=(((0, 15, 0),),),
            external=(0,),
        ),
    )
    ids = tuple(case.case_id for case in cases)
    names = tuple(case.name for case in cases)
    if ids != tuple(range(len(cases))):
        raise RuntimeError("M12.2 case IDs must remain dense and zero-based")
    if len(names) != len(set(names)):
        raise RuntimeError("M12.2 case names must be unique")
    return cases


def compare_m12_single_tick_capture(
    case: FpgaSingleTickCase,
    actual: PhysicalFpgaTraceArtifact,
) -> SingleTickDifferentialReport:
    """Compare one physical artifact exactly against its Python-golden case."""

    if not isinstance(case, FpgaSingleTickCase):
        raise TypeError("case must be FpgaSingleTickCase")
    if not isinstance(actual, PhysicalFpgaTraceArtifact):
        raise TypeError("actual must be PhysicalFpgaTraceArtifact")

    mismatches: list[SingleTickMismatch] = []

    def check(field: str, expected: Any, observed: Any) -> None:
        if expected != observed:
            mismatches.append(SingleTickMismatch(field, expected, observed))

    check("scenario_id", case.name, actual.scenario_id)
    check("transport", FPGA_PHYSICAL_TRACE_TRANSPORT_JTAG_VIO, actual.transport)
    check("tick_count", 1, len(actual.ticks))
    if len(actual.ticks) == 1:
        expected = case.expected
        observed = actual.ticks[0]
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
            check(field, getattr(expected, field), getattr(observed, field))

    return SingleTickDifferentialReport(
        case_id=case.case_id,
        case_name=case.name,
        device=actual.device,
        mismatches=tuple(mismatches),
    )


def write_m12_single_tick_corpus(
    output_dir: str | Path,
    cases: Sequence[FpgaSingleTickCase] | None = None,
) -> Path:
    """Write deterministic case/golden artifacts and return manifest path."""

    selected = tuple(cases) if cases is not None else build_m12_single_tick_cases()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    manifest_cases = []
    for case in selected:
        payload = {
            "schema": M12_SINGLE_TICK_CORPUS_SCHEMA,
            **case.to_dict(),
        }
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
        "schema": M12_SINGLE_TICK_CORPUS_SCHEMA,
        "case_count": len(selected),
        "cases": manifest_cases,
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def write_m12_single_tick_report(
    report: SingleTickDifferentialReport,
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
    external: Iterable[int],
    routes: Sequence[SpikeRoute] = (),
) -> FpgaSingleTickCase:
    if len(configs) != len(states):
        raise ValueError("configs/states lengths must match")
    neuron_count = len(configs)
    storage = _make_storage(formats, rows)
    frozen_routes = freeze_spike_routes_v1(routes, neuron_count=neuron_count)
    config_words = tuple(pack_neuron_config_word(config) for config in configs)
    initial_state_words = tuple(pack_neuron_state_word(state) for state in states)
    external_axons = tuple(external)

    queue = DoubleBufferedRecurrentQueue.empty()
    phase_b = accumulate_frozen_weight_image_v1(
        storage,
        neuron_count=neuron_count,
        external_axons=external_axons,
        recurrent_axons=queue.current_events,
    )
    stepped = step_packed_neuron_array_v1(
        initial_state_words,
        config_words,
        phase_b.accumulators,
    )
    routed = route_and_commit_recurrent_v1(
        queue,
        frozen_routes,
        stepped.spikes,
    )

    snapshot = FpgaTickTraceSnapshot(
        committed_tick=1,
        external_input_axons=external_axons,
        recurrent_input_axons=routed.consumed_recurrent_axons,
        synaptic_input=phase_b.accumulators,
        state_before_words=initial_state_words,
        state_after_words=stepped.state_words,
        spikes=stepped.spikes,
        routed_output_axons=routed.routed_output_axons,
    )
    after = routed.queue_after_commit
    expected = PhysicalFpgaTickCapture(
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
    return FpgaSingleTickCase(
        case_id=case_id,
        name=name,
        category=category,
        coverage=coverage,
        storage=storage,
        routes=frozen_routes,
        config_words=config_words,
        initial_state_words=initial_state_words,
        external_axons=external_axons,
        expected=expected,
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
