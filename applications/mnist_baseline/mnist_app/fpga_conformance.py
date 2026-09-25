"""MNIST-07 single-image FPGA conformance generation and comparison.

The physical FPGA receives only the frozen static deployment image and the
per-tick external event schedule. Golden states, synaptic accumulators, spikes,
and the final prediction remain host-side evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .dataset import load_mnist
from .encoding import encode_event_schedule
from .inference import load_deployment

MNIST_FPGA_CONFORMANCE_SCHEMA = "neuromorphic-twin-mnist-fpga-conformance-v1"
MNIST_FPGA_CONFORMANCE_REPORT_SCHEMA = (
    "neuromorphic-twin-mnist-fpga-conformance-report-v1"
)
PROFILE_ORDER = ("cropped-dense", "native-sparse")


@dataclass(frozen=True, slots=True)
class MnistFpgaConformanceCase:
    case_id: int
    name: str
    profile: str
    mnist_test_index: int
    label: int
    expected_prediction: int
    config_words: tuple[int, ...]
    initial_state_words: tuple[int, ...]
    format_words: tuple[int, ...]
    synapse_words: tuple[int, ...]
    weight_rows: tuple[int, ...]
    route_rows: tuple[int, ...]
    route_targets: tuple[int, ...]
    external_schedule: tuple[tuple[int, ...], ...]
    golden_trace: object

    @property
    def neuron_count(self) -> int:
        return len(self.config_words)

    @property
    def axon_count(self) -> int:
        return len(self.weight_rows) - 1

    @property
    def synapse_count(self) -> int:
        return len(self.synapse_words)

    @property
    def format_count(self) -> int:
        return len(self.format_words)

    @property
    def route_count(self) -> int:
        return len(self.route_targets)

    @property
    def tick_count(self) -> int:
        return len(self.external_schedule)


def select_single_image_anchor(corpus: dict[str, object]) -> dict[str, object]:
    """Return the first frozen case both accepted profiles classify correctly."""

    if corpus.get("schema") != "neuromorphic-twin-mnist-fpga-corpus-v1":
        raise ValueError("unsupported frozen FPGA corpus schema")
    entries = corpus.get("entries")
    if not isinstance(entries, list):
        raise TypeError("frozen FPGA corpus entries must be a list")
    for entry in entries:
        if not isinstance(entry, dict):
            raise TypeError("frozen FPGA corpus entry must be an object")
        if (
            entry.get("selection_reason") == "both-correct"
            and entry.get("cropped_dense_correct") is True
            and entry.get("native_sparse_correct") is True
        ):
            return entry
    raise ValueError("frozen FPGA corpus contains no both-correct anchor")


def build_single_image_cases(
    frozen_root: str | Path,
) -> tuple[MnistFpgaConformanceCase, ...]:
    """Build the two frozen MNIST-07 cases and independent golden timelines."""

    from neuromorphic_twin import NeuronConfig, NeuronState, read_weight_storage_json
    from neuromorphic_twin.fpga_core_capacity import (
        pack_neuron_config_word,
        pack_neuron_state_word,
    )
    from neuromorphic_twin.fpga_physical_trace import (
        PhysicalFpgaTickCapture,
        PhysicalFpgaTraceArtifact,
    )
    from neuromorphic_twin.fpga_trace_snapshot import FpgaTickTraceSnapshot

    root = Path(frozen_root)
    corpus_path = root / "fpga_validation_corpus.json"
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    anchor = select_single_image_anchor(corpus)
    source_index = int(anchor["mnist_test_index"])
    expected_label = int(anchor["label"])

    dataset = load_mnist()
    image = np.asarray(dataset.x_test[source_index])
    actual_label = int(dataset.y_test[source_index])
    if actual_label != expected_label:
        raise ValueError(
            f"frozen corpus label mismatch at test index {source_index}: "
            f"{expected_label} != {actual_label}"
        )

    cases: list[MnistFpgaConformanceCase] = []
    for case_id, profile_name in enumerate(PROFILE_ORDER):
        deployment_path = root / "deployments" / profile_name / "deployment.json"
        runtime = load_deployment(deployment_path)
        if runtime.profile.name != profile_name:
            raise ValueError("frozen deployment profile mismatch")

        storage_path = deployment_path.parent / runtime.manifest["weight_storage"]
        storage = read_weight_storage_json(storage_path)
        configs = tuple(
            NeuronConfig(**row) for row in runtime.manifest["neuron_configs"]
        )
        config_words = tuple(pack_neuron_config_word(config) for config in configs)
        initial_state_words = tuple(
            pack_neuron_state_word(NeuronState()) for _ in configs
        )
        schedule = encode_event_schedule(image, profile=runtime.profile)

        runtime.core.reset()
        captures: list[PhysicalFpgaTickCapture] = []
        spike_counts = np.zeros(len(configs), dtype=np.int64)
        refractory_before = tuple(0 for _ in configs)
        for committed_tick, external_events in enumerate(schedule, start=1):
            trace = runtime.core.step(external_events)
            state_before_words = tuple(
                pack_neuron_state_word(
                    NeuronState(
                        current=current,
                        voltage=voltage,
                        refractory_remaining=refractory,
                    )
                )
                for current, voltage, refractory in zip(
                    trace.current_before,
                    trace.voltage_before,
                    refractory_before,
                    strict=True,
                )
            )
            state_after_words = tuple(
                pack_neuron_state_word(
                    NeuronState(
                        current=current,
                        voltage=voltage,
                        refractory_remaining=refractory,
                    )
                )
                for current, voltage, refractory in zip(
                    trace.current_after,
                    trace.voltage_after,
                    trace.refractory_after,
                    strict=True,
                )
            )
            spiked_ids = {spike.neuron_id for spike in trace.spikes}
            spike_flags = tuple(i in spiked_ids for i in range(len(configs)))
            for neuron_id in spiked_ids:
                spike_counts[neuron_id] += 1

            snapshot = FpgaTickTraceSnapshot(
                committed_tick=committed_tick,
                external_input_axons=tuple(trace.external_input_axons),
                recurrent_input_axons=tuple(trace.recurrent_input_axons),
                synaptic_input=tuple(trace.synaptic_input),
                state_before_words=state_before_words,
                state_after_words=state_after_words,
                spikes=spike_flags,
                routed_output_axons=tuple(trace.routed_output_axons),
            )
            captures.append(
                PhysicalFpgaTickCapture(
                    snapshot=snapshot,
                    core_fault=False,
                    core_fault_code=0,
                    recurrent_current_bank=False,
                    recurrent_current_count=0,
                    recurrent_bank0_count=0,
                    recurrent_bank1_count=0,
                    consumed_recurrent_count=0,
                    routed_recurrent_count=0,
                    external_event_count=len(external_events),
                )
            )
            refractory_before = tuple(trace.refractory_after)

        prediction = int(np.argmax(spike_counts))
        expected_prediction = int(
            anchor[
                "cropped_dense_golden_prediction"
                if profile_name == "cropped-dense"
                else "native_sparse_golden_prediction"
            ]
        )
        if prediction != expected_prediction:
            raise ValueError(
                f"{profile_name} regenerated golden prediction {prediction} "
                f"does not match frozen corpus prediction {expected_prediction}"
            )

        name = f"mnist07-{profile_name}-index{source_index:05d}"
        golden = PhysicalFpgaTraceArtifact(
            scenario_id=name,
            transport="python-golden",
            device="python-golden",
            ticks=tuple(captures),
        )
        cases.append(
            MnistFpgaConformanceCase(
                case_id=case_id,
                name=name,
                profile=profile_name,
                mnist_test_index=source_index,
                label=actual_label,
                expected_prediction=expected_prediction,
                config_words=config_words,
                initial_state_words=initial_state_words,
                format_words=tuple(storage.format_words),
                synapse_words=tuple(storage.synapse_words),
                weight_rows=tuple(storage.axon_row_pointers),
                route_rows=tuple(0 for _ in range(len(configs) + 1)),
                route_targets=(),
                external_schedule=tuple(tuple(events) for events in schedule),
                golden_trace=golden,
            )
        )

    if cases[0].mnist_test_index != cases[1].mnist_test_index:
        raise AssertionError("MNIST-07 profiles must use the same source test image")
    return tuple(cases)


def _hex(value: int, width: int) -> str:
    return f"{value & ((1 << width) - 1):0{(width + 3) // 4}x}"


def _pad(values: Sequence[int], count: int) -> tuple[int, ...]:
    values = tuple(int(value) for value in values)
    if len(values) > count:
        raise ValueError("MNIST-07 generated row exceeds include stride")
    return values + (0,) * (count - len(values))


def write_systemverilog_include(
    cases: Sequence[MnistFpgaConformanceCase],
    output: str | Path,
) -> Path:
    """Write M12.3-compatible FPGA inputs, never golden outputs."""

    selected = tuple(cases)
    if not selected:
        raise ValueError("at least one MNIST-07 case is required")
    max_neurons = max(case.neuron_count for case in selected)
    max_axons = max(case.axon_count for case in selected)
    max_synapses = max(case.synapse_count for case in selected)
    max_formats = max(case.format_count for case in selected)
    max_routes = max(1, max(case.route_count for case in selected))
    max_ticks = max(case.tick_count for case in selected)
    max_external = max(
        1,
        max(len(events) for case in selected for events in case.external_schedule),
    )

    lines = [
        "// Generated by applications/mnist/scripts/generate_fpga_conformance.py; do not edit.",
        "// MNIST-07 INPUTS ONLY: expected state/spike/prediction data is host-side only.",
        f"localparam int M12_3_CASE_COUNT = {len(selected)};",
        f"localparam int M12_3_MAX_NEURONS = {max_neurons};",
        f"localparam int M12_3_MAX_AXONS = {max_axons};",
        f"localparam int M12_3_MAX_SYNAPSES = {max_synapses};",
        f"localparam int M12_3_MAX_FORMATS = {max_formats};",
        f"localparam int M12_3_MAX_ROUTES = {max_routes};",
        f"localparam int M12_3_MAX_TICKS = {max_ticks};",
        f"localparam int M12_3_MAX_EXTERNAL_EVENTS = {max_external};",
        "",
    ]

    def emit(name: str, width: int, words: Sequence[int]) -> None:
        words = tuple(words)
        lines.append(
            f"localparam logic [{width - 1}:0] {name} [0:{len(words) - 1}] = '{{"
        )
        for index, word in enumerate(words):
            comma = "," if index + 1 != len(words) else ""
            lines.append(f"    {width}'h{_hex(int(word), width)}{comma}")
        lines.append("};")
        lines.append("")

    emit("M12_3_NEURON_COUNTS", 9, tuple(c.neuron_count for c in selected))
    emit("M12_3_AXON_COUNTS", 11, tuple(c.axon_count for c in selected))
    emit("M12_3_SYNAPSE_COUNTS", 13, tuple(c.synapse_count for c in selected))
    emit("M12_3_FORMAT_COUNTS", 5, tuple(c.format_count for c in selected))
    emit("M12_3_ROUTE_COUNTS", 13, tuple(c.route_count for c in selected))
    emit("M12_3_TICK_COUNTS", 8, tuple(c.tick_count for c in selected))
    emit(
        "M12_3_CONFIG_WORDS",
        128,
        tuple(word for c in selected for word in _pad(c.config_words, max_neurons)),
    )
    emit(
        "M12_3_INITIAL_STATE_WORDS",
        64,
        tuple(
            word for c in selected for word in _pad(c.initial_state_words, max_neurons)
        ),
    )
    emit(
        "M12_3_FORMAT_WORDS",
        16,
        tuple(word for c in selected for word in _pad(c.format_words, max_formats)),
    )
    emit(
        "M12_3_SYNAPSE_WORDS",
        32,
        tuple(word for c in selected for word in _pad(c.synapse_words, max_synapses)),
    )
    emit(
        "M12_3_WEIGHT_ROWS",
        32,
        tuple(word for c in selected for word in _pad(c.weight_rows, max_axons + 1)),
    )
    emit(
        "M12_3_ROUTE_ROWS",
        32,
        tuple(word for c in selected for word in _pad(c.route_rows, max_neurons + 1)),
    )
    emit(
        "M12_3_ROUTE_TARGETS",
        16,
        tuple(word for c in selected for word in _pad(c.route_targets, max_routes)),
    )

    external_counts: list[int] = []
    external_words: list[int] = []
    for case in selected:
        padded_ticks = case.external_schedule + ((),) * (max_ticks - case.tick_count)
        for events in padded_ticks:
            external_counts.append(len(events))
            external_words.extend(_pad(events, max_external))
    emit("M12_3_EXTERNAL_COUNTS", 13, external_counts)
    emit("M12_3_EXTERNAL_EVENTS", 16, external_words)

    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def write_conformance_bundle(
    cases: Sequence[MnistFpgaConformanceCase],
    output_dir: str | Path,
    sv_output: str | Path,
) -> Path:
    """Write golden traces, hardware metadata, manifest, and FPGA input include."""

    from neuromorphic_twin.fpga_physical_trace import write_physical_fpga_trace_json

    selected = tuple(cases)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    write_systemverilog_include(selected, sv_output)

    metadata_lines = ["case_id\tcase_name\tneuron_count\ttick_count"]
    records: list[dict[str, Any]] = []
    for case in selected:
        golden_name = f"{case.case_id:02d}-{case.name}.golden.json"
        golden_path = output / golden_name
        write_physical_fpga_trace_json(case.golden_trace, golden_path)
        metadata_lines.append(
            f"{case.case_id}\t{case.name}\t{case.neuron_count}\t{case.tick_count}"
        )
        records.append(
            {
                "case_id": case.case_id,
                "name": case.name,
                "profile": case.profile,
                "mnist_test_index": case.mnist_test_index,
                "label": case.label,
                "expected_prediction": case.expected_prediction,
                "golden_trace": golden_name,
                "counts": {
                    "neurons": case.neuron_count,
                    "axons": case.axon_count,
                    "synapses": case.synapse_count,
                    "formats": case.format_count,
                    "routes": case.route_count,
                    "ticks": case.tick_count,
                    "max_external_events_per_tick": max(
                        len(events) for events in case.external_schedule
                    ),
                },
            }
        )

    (output / "hardware_cases.tsv").write_text(
        "\n".join(metadata_lines) + "\n", encoding="utf-8"
    )
    manifest = output / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": MNIST_FPGA_CONFORMANCE_SCHEMA,
                "fpga_input_contract": (
                    "static-load-image-plus-external-events-only; "
                    "golden outputs remain host-side"
                ),
                "cases": records,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


def prediction_from_trace(artifact: object) -> tuple[int, tuple[int, ...]]:
    counts: list[int] | None = None
    for tick in artifact.ticks:
        if counts is None:
            counts = [0] * tick.snapshot.neuron_count
        for neuron_id, spiked in enumerate(tick.snapshot.spikes):
            counts[neuron_id] += int(spiked)
    if counts is None:
        raise ValueError("trace contains no ticks")
    prediction = int(np.argmax(np.asarray(counts, dtype=np.int64)))
    return prediction, tuple(counts)


def compare_physical_to_golden(
    golden: object,
    physical: object,
    *,
    expected_prediction: int,
) -> dict[str, object]:
    """Compare exact architectural fields for one MNIST-07 physical capture."""

    mismatches: list[dict[str, object]] = []

    def check(tick: int | None, field: str, expected: object, actual: object) -> None:
        if expected != actual:
            mismatches.append(
                {"tick": tick, "field": field, "expected": expected, "actual": actual}
            )

    check(None, "scenario_id", golden.scenario_id, physical.scenario_id)
    check(None, "transport", "jtag-vio", physical.transport)
    check(None, "tick_count", len(golden.ticks), len(physical.ticks))

    fields = (
        "committed_tick",
        "external_input_axons",
        "recurrent_input_axons",
        "synaptic_input",
        "state_before_words",
        "state_after_words",
        "spikes",
        "routed_output_axons",
    )
    for expected_tick, actual_tick in zip(golden.ticks, physical.ticks):
        tick = expected_tick.snapshot.committed_tick
        for field in fields:
            check(
                tick,
                f"snapshot.{field}",
                getattr(expected_tick.snapshot, field),
                getattr(actual_tick.snapshot, field),
            )
        check(tick, "core_fault", False, actual_tick.core_fault)
        check(tick, "core_fault_code", 0, actual_tick.core_fault_code)
        check(
            tick,
            "external_event_count",
            expected_tick.external_event_count,
            actual_tick.external_event_count,
        )
        check(tick, "consumed_recurrent_count", 0, actual_tick.consumed_recurrent_count)
        check(tick, "routed_recurrent_count", 0, actual_tick.routed_recurrent_count)

    golden_prediction, golden_counts = prediction_from_trace(golden)
    physical_prediction, physical_counts = prediction_from_trace(physical)
    check(None, "golden_prediction", expected_prediction, golden_prediction)
    check(None, "physical_prediction", expected_prediction, physical_prediction)
    check(None, "output_spike_counts", golden_counts, physical_counts)

    return {
        "schema": MNIST_FPGA_CONFORMANCE_REPORT_SCHEMA,
        "scenario_id": golden.scenario_id,
        "passed": not mismatches,
        "mismatch_count": len(mismatches),
        "expected_prediction": expected_prediction,
        "golden_prediction": golden_prediction,
        "physical_prediction": physical_prediction,
        "golden_spike_counts": list(golden_counts),
        "physical_spike_counts": list(physical_counts),
        "mismatches": mismatches,
    }
