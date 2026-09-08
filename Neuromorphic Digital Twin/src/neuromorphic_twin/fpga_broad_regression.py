"""M12.4 broad deterministic physical-regression corpus.

The M12.2/M12.3 directed suites remain retained regression anchors. This module
adds a wider deterministic physical corpus made of seeded generated networks and
selected finite-capacity stress cases. Every case carries stable generator
metadata and a SHA-256 hash over its FPGA-visible input image. Expected outputs
remain host-side and are computed from the frozen Python FPGA-v1 contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from .fpga_core_capacity import pack_neuron_config_word, pack_neuron_state_word
from .fpga_multitick_conformance import (
    FpgaMultiTickCase,
    compare_m12_multitick_capture,
    write_m12_multitick_report,
)
from .fpga_physical_trace import PhysicalFpgaTickCapture, PhysicalFpgaTraceArtifact
from .fpga_recurrent_routing import (
    DoubleBufferedRecurrentQueue,
    freeze_spike_routes_v1,
    route_and_commit_recurrent_v1,
)
from .fpga_synapse_reference import accumulate_frozen_weight_image_v1
from .fpga_trace_snapshot import FpgaTickTraceSnapshot
from .fpga_weight_storage import FrozenWeightStorage, pack_synapse_word, pack_weight_format
from .model import NeuronConfig, NeuronState, SpikeRoute
from .neuron_array_reference import step_packed_neuron_array_v1
from .weights import WeightFormat, WeightSignMode


M12_BROAD_CORPUS_SCHEMA = "neuromorphic-twin-m12-broad-corpus-v1"
M12_BROAD_GENERATOR_VERSION = "m12.4-generator-v1"
M12_BROAD_MASTER_SEED = 0x4D31323456310001
M12_BROAD_SEEDED_CASES = 16
M12_BROAD_STRESS_CASES = 6
M12_BROAD_CASE_COUNT = M12_BROAD_SEEDED_CASES + M12_BROAD_STRESS_CASES


@dataclass(frozen=True, slots=True)
class BroadRegressionCase:
    """One reproducible M12.4 physical case plus provenance metadata."""

    workload: FpgaMultiTickCase
    source_kind: str
    seed: int
    generator_version: str
    configuration_sha256: str

    def __post_init__(self) -> None:
        if self.source_kind not in {"seeded", "stress"}:
            raise ValueError("source_kind must be seeded or stress")
        if not 0 <= self.seed < (1 << 64):
            raise ValueError("seed must fit unsigned 64 bits")
        if self.generator_version != M12_BROAD_GENERATOR_VERSION:
            raise ValueError("unexpected M12.4 generator version")
        if self.configuration_sha256 != configuration_sha256(self.workload):
            raise ValueError("configuration_sha256 does not match workload input image")

    @property
    def case_id(self) -> int:
        return self.workload.case_id

    @property
    def name(self) -> str:
        return self.workload.name

    @property
    def tick_count(self) -> int:
        return self.workload.tick_count

    def to_dict(self) -> dict[str, Any]:
        workload = self.workload.to_dict()
        return {
            "schema": M12_BROAD_CORPUS_SCHEMA,
            "generator_version": self.generator_version,
            "source_kind": self.source_kind,
            "seed": f"0x{self.seed:016x}",
            "configuration_sha256": self.configuration_sha256,
            **workload,
        }


def configuration_sha256(workload: FpgaMultiTickCase) -> str:
    """Hash only the reproducible FPGA input/configuration payload."""

    payload = workload.to_dict()
    input_only = {
        "case_id": payload["case_id"],
        "name": payload["name"],
        "category": payload["category"],
        "coverage": payload["coverage"],
        "counts": payload["counts"],
        "load_image": payload["load_image"],
    }
    encoded = json.dumps(input_only, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_m12_broad_cases() -> tuple[BroadRegressionCase, ...]:
    """Return the frozen 22-case M12.4 broad physical corpus."""

    seed_rng = _SplitMix64(M12_BROAD_MASTER_SEED)
    seeded: list[BroadRegressionCase] = []
    for case_id in range(M12_BROAD_SEEDED_CASES):
        seed = seed_rng.next_u64()
        workload = _make_generated_case(case_id, seed)
        seeded.append(_wrap(workload, "seeded", seed))

    stress_start = M12_BROAD_SEEDED_CASES
    stress_workloads = (
        _stress_external_multiplicity(stress_start + 0),
        _stress_dense_synaptic_fanin(stress_start + 1),
        _stress_recurrent_fanout(stress_start + 2),
        _stress_neuron_population(stress_start + 3),
        _stress_long_recurrent_ring(stress_start + 4),
        _stress_mixed_dense_history(stress_start + 5),
    )
    stress_seeds = (
        0x4D31323453545230,
        0x4D31323453545231,
        0x4D31323453545232,
        0x4D31323453545233,
        0x4D31323453545234,
        0x4D31323453545235,
    )
    stress = [
        _wrap(workload, "stress", seed)
        for workload, seed in zip(stress_workloads, stress_seeds)
    ]

    result = tuple(seeded + stress)
    if len(result) != M12_BROAD_CASE_COUNT:
        raise AssertionError("M12.4 case-count contract changed")
    if tuple(case.case_id for case in result) != tuple(range(M12_BROAD_CASE_COUNT)):
        raise AssertionError("M12.4 case IDs must remain dense")
    return result


def write_m12_broad_corpus(output_dir: str | Path) -> Path:
    """Write deterministic per-case golden artifacts and top-level manifest."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    cases = build_m12_broad_cases()
    manifest_cases: list[dict[str, Any]] = []

    for case in cases:
        filename = f"{case.case_id:02d}-{case.name}.golden.json"
        path = output / filename
        path.write_text(json.dumps(case.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest_cases.append(
            {
                "case_id": case.case_id,
                "name": case.name,
                "source_kind": case.source_kind,
                "seed": f"0x{case.seed:016x}",
                "generator_version": case.generator_version,
                "configuration_sha256": case.configuration_sha256,
                "ticks": case.tick_count,
                "golden_file": filename,
            }
        )

    manifest = {
        "schema": M12_BROAD_CORPUS_SCHEMA,
        "generator_version": M12_BROAD_GENERATOR_VERSION,
        "master_seed": f"0x{M12_BROAD_MASTER_SEED:016x}",
        "case_count": len(cases),
        "seeded_case_count": M12_BROAD_SEEDED_CASES,
        "stress_case_count": M12_BROAD_STRESS_CASES,
        "total_ticks": sum(case.tick_count for case in cases),
        "retained_regression_anchors": {
            "m12_2_directed_single_tick_cases": 16,
            "m12_3_directed_multitick_cases": 10,
            "m12_3_directed_multitick_ticks": 40,
        },
        "cases": manifest_cases,
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def compare_m12_broad_capture(case: BroadRegressionCase, artifact: PhysicalFpgaTraceArtifact):
    return compare_m12_multitick_capture(case.workload, artifact)


def write_m12_broad_report(report, path: str | Path) -> Path:
    return write_m12_multitick_report(report, path)


def _wrap(workload: FpgaMultiTickCase, source_kind: str, seed: int) -> BroadRegressionCase:
    return BroadRegressionCase(
        workload=workload,
        source_kind=source_kind,
        seed=seed,
        generator_version=M12_BROAD_GENERATOR_VERSION,
        configuration_sha256=configuration_sha256(workload),
    )


def _make_generated_case(case_id: int, seed: int) -> FpgaMultiTickCase:
    rng = _SplitMix64(seed)
    neuron_count = 4 + rng.randbelow(9)  # 4..12
    axon_count = max(neuron_count, 8 + rng.randbelow(17))  # 8..24
    tick_count = 5 + rng.randbelow(5)  # 5..9

    formats = (
        WeightFormat(0, 8, WeightSignMode.MIXED),
        WeightFormat(-1, 7, WeightSignMode.MIXED),
        WeightFormat(1, 6, WeightSignMode.MIXED),
    )
    mantissas = (-64, -32, -16, -8, 8, 16, 32, 64)

    rows: list[tuple[tuple[int, int, int], ...]] = []
    for _axon in range(axon_count):
        fanout = 1 + rng.randbelow(3)
        row = tuple(
            (
                rng.randbelow(neuron_count),
                rng.choice(mantissas),
                rng.randbelow(len(formats)),
            )
            for _ in range(fanout)
        )
        rows.append(row)

    decays = (0, 512, 1024, 2048, 3072, 4096)
    thresholds = (512, 1024, 2048, 4096, 8192)
    biases = (-64, 0, 64)
    configs: list[NeuronConfig] = []
    states: list[NeuronState] = []
    for _ in range(neuron_count):
        refractory_ticks = rng.randbelow(4)
        configs.append(
            NeuronConfig(
                current_decay=rng.choice(decays),
                voltage_decay=rng.choice(decays),
                threshold=rng.choice(thresholds),
                bias=rng.choice(biases),
                reset_voltage=0,
                refractory_ticks=refractory_ticks,
            )
        )
        states.append(
            NeuronState(
                current=rng.choice((-512, -128, 0, 128, 512)),
                voltage=rng.choice((-256, -64, 0, 64, 256)),
                refractory_remaining=(rng.randbelow(refractory_ticks + 1) if refractory_ticks else 0),
            )
        )

    routes: list[SpikeRoute] = []
    for source in range(neuron_count):
        targets: set[int] = set()
        for _ in range(rng.randbelow(3)):
            target = rng.randbelow(axon_count)
            if target not in targets:
                targets.add(target)
                routes.append(SpikeRoute(source, target))
    if not routes:
        routes.append(SpikeRoute(0, 0))

    external_schedule: list[tuple[int, ...]] = []
    for tick in range(tick_count):
        count = 1 + rng.randbelow(4) if tick == 0 else rng.randbelow(5)
        external_schedule.append(tuple(rng.randbelow(axon_count) for _ in range(count)))

    return _make_case(
        case_id,
        f"seeded-{case_id:02d}",
        "seeded-generated",
        (
            "seeded_topology",
            "mixed_weight_formats",
            "initial_state_variation",
            "decay_threshold_refractory_variation",
            "external_schedule_variation",
            "recurrent_history",
        ),
        configs=configs,
        states=states,
        formats=formats,
        rows=rows,
        routes=routes,
        external_schedule=external_schedule,
    )


def _stress_external_multiplicity(case_id: int) -> FpgaMultiTickCase:
    fmt = WeightFormat(0, 8, WeightSignMode.EXCITATORY)
    return _make_case(
        case_id,
        "stress-external-multiplicity-1024",
        "finite-capacity-stress",
        ("external_event_multiplicity", "event_buffer_stress", "wide_accumulation"),
        configs=(NeuronConfig(4096, 4096, 4_000_000),),
        states=(NeuronState(),),
        formats=(fmt,),
        rows=(((0, 1, 0),),),
        routes=(),
        external_schedule=((0,) * 1024, ()),
    )


def _stress_dense_synaptic_fanin(case_id: int) -> FpgaMultiTickCase:
    fmt = WeightFormat(0, 8, WeightSignMode.EXCITATORY)
    neuron_count = 32
    axon_count = 32
    rows = tuple(
        tuple(((axon + j) % neuron_count, 1, 0) for j in range(8))
        for axon in range(axon_count)
    )
    configs = tuple(NeuronConfig(4096, 4096, 1_000_000) for _ in range(neuron_count))
    return _make_case(
        case_id,
        "stress-dense-fanin-256-synapses",
        "finite-capacity-stress",
        ("dense_synaptic_fanin", "synapse_traversal", "parallel_neuron_accumulators"),
        configs=configs,
        states=tuple(NeuronState() for _ in range(neuron_count)),
        formats=(fmt,),
        rows=rows,
        routes=(),
        external_schedule=(tuple(range(axon_count)), ()),
    )


def _stress_recurrent_fanout(case_id: int) -> FpgaMultiTickCase:
    fmt = WeightFormat(0, 8, WeightSignMode.EXCITATORY)
    axon_count = 257
    rows = [((0, 1, 0),)]
    rows.extend(((1, 1, 0),) for _ in range(256))
    routes = tuple(SpikeRoute(0, axon) for axon in range(1, 257))
    return _make_case(
        case_id,
        "stress-recurrent-fanout-256",
        "finite-capacity-stress",
        ("route_fanout", "recurrent_event_count", "double_buffer_queue"),
        configs=(NeuronConfig(4096, 4096, 32), NeuronConfig(4096, 4096, 1_000_000)),
        states=(NeuronState(), NeuronState()),
        formats=(fmt,),
        rows=tuple(rows),
        routes=routes,
        external_schedule=((0,), (), ()),
    )


def _stress_neuron_population(case_id: int) -> FpgaMultiTickCase:
    fmt = WeightFormat(0, 8, WeightSignMode.EXCITATORY)
    neuron_count = 128
    rows = tuple(((neuron, 1, 0),) for neuron in range(neuron_count))
    return _make_case(
        case_id,
        "stress-neuron-population-128",
        "finite-capacity-stress",
        ("neuron_population", "wide_spike_vector", "state_memory_traversal"),
        configs=tuple(NeuronConfig(4096, 4096, 32) for _ in range(neuron_count)),
        states=tuple(NeuronState() for _ in range(neuron_count)),
        formats=(fmt,),
        rows=rows,
        routes=(),
        external_schedule=(tuple(range(neuron_count)), ()),
    )


def _stress_long_recurrent_ring(case_id: int) -> FpgaMultiTickCase:
    fmt = WeightFormat(0, 8, WeightSignMode.EXCITATORY)
    count = 16
    return _make_case(
        case_id,
        "stress-recurrent-ring-32-ticks",
        "finite-capacity-stress",
        ("long_recurrent_history", "repeated_queue_swaps", "ring_topology"),
        configs=tuple(NeuronConfig(4096, 4096, 32) for _ in range(count)),
        states=tuple(NeuronState() for _ in range(count)),
        formats=(fmt,),
        rows=tuple(((neuron, 1, 0),) for neuron in range(count)),
        routes=tuple(SpikeRoute(neuron, (neuron + 1) % count) for neuron in range(count)),
        external_schedule=((0,),) + ((),) * 31,
    )


def _stress_mixed_dense_history(case_id: int) -> FpgaMultiTickCase:
    rng = _SplitMix64(0x4D3132344D495845)
    neuron_count = 32
    axon_count = 64
    formats = (
        WeightFormat(0, 8, WeightSignMode.MIXED),
        WeightFormat(-1, 7, WeightSignMode.MIXED),
        WeightFormat(1, 7, WeightSignMode.MIXED),
    )
    mantissas = (-32, -16, -8, 8, 16, 32)
    rows = tuple(
        tuple(
            (rng.randbelow(neuron_count), rng.choice(mantissas), rng.randbelow(3))
            for _ in range(4)
        )
        for _ in range(axon_count)
    )
    configs = tuple(
        NeuronConfig(
            current_decay=rng.choice((512, 1024, 2048, 3072)),
            voltage_decay=rng.choice((512, 1024, 2048, 3072)),
            threshold=rng.choice((1024, 2048, 4096)),
            bias=rng.choice((-32, 0, 32)),
            refractory_ticks=rng.randbelow(4),
        )
        for _ in range(neuron_count)
    )
    routes: list[SpikeRoute] = []
    for source in range(neuron_count):
        targets: set[int] = set()
        while len(targets) < 4:
            targets.add(rng.randbelow(axon_count))
        routes.extend(SpikeRoute(source, target) for target in sorted(targets))
    schedule = tuple(
        tuple(rng.randbelow(axon_count) for _ in range(8 + rng.randbelow(9)))
        for _ in range(12)
    )
    return _make_case(
        case_id,
        "stress-mixed-dense-history",
        "finite-capacity-stress",
        ("mixed_dense_workload", "multi_format_weights", "route_density", "state_history"),
        configs=configs,
        states=tuple(NeuronState() for _ in range(neuron_count)),
        formats=formats,
        rows=rows,
        routes=routes,
        external_schedule=schedule,
    )


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
        phase_b = accumulate_frozen_weight_image_v1(
            storage,
            neuron_count=neuron_count,
            external_axons=external_axons,
            recurrent_axons=queue.current_events,
        )
        stepped = step_packed_neuron_array_v1(
            state_words,
            config_words,
            phase_b.accumulators,
        )
        routed = route_and_commit_recurrent_v1(queue, frozen_routes, stepped.spikes)
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


class _SplitMix64:
    def __init__(self, seed: int) -> None:
        self.state = seed & 0xFFFFFFFFFFFFFFFF

    def next_u64(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        return (z ^ (z >> 31)) & 0xFFFFFFFFFFFFFFFF

    def randbelow(self, bound: int) -> int:
        if bound <= 0:
            raise ValueError("bound must be positive")
        return self.next_u64() % bound

    def choice(self, values: Sequence[int]):
        if not values:
            raise ValueError("choice requires a nonempty sequence")
        return values[self.randbelow(len(values))]
