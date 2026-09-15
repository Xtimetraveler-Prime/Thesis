"""MNIST-08 frozen-corpus FPGA generation and exact physical validation.

MNIST-08 expands the proven MNIST-07 physical correctness boundary to all 30
source images in the frozen ``mnist-v1`` corpus and both deployment profiles.
The FPGA still receives inputs only: two shared static deployment images plus
per-case external-event schedules. Golden states/spikes/predictions remain
host-side evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .dataset import load_mnist
from .encoding import encode_event_schedule
from .fpga_conformance import compare_physical_to_golden
from .inference import load_deployment

MNIST_FPGA_CORPUS_SCHEMA = "neuromorphic-twin-mnist-fpga-corpus-conformance-v1"
MNIST_FPGA_CORPUS_SUITE_SCHEMA = (
    "neuromorphic-twin-mnist-fpga-corpus-conformance-suite-v1"
)
PROFILE_ORDER = ("cropped-dense", "native-sparse")
PROFILE_ID = {name: index for index, name in enumerate(PROFILE_ORDER)}
EXPECTED_SOURCE_CASES = 30
EXPECTED_PHYSICAL_CASES = EXPECTED_SOURCE_CASES * len(PROFILE_ORDER)
# Vivado synthesis rejects a single packed variable above 1,000,000 bits.
# MNIST-08 therefore stores external events in one 16-bit bank per profile and
# enforces this ceiling before writing the generated include.
VIVADO_MAX_VARIABLE_BITS = 1_000_000
EXTERNAL_EVENT_WORD_BITS = 16


@dataclass(frozen=True, slots=True)
class MnistFpgaCorpusCase:
    case_id: int
    name: str
    profile: str
    profile_id: int
    source_ordinal: int
    selection_reason: str
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


@dataclass(frozen=True, slots=True)
class MnistFpgaStaticProfile:
    profile: str
    profile_id: int
    config_words: tuple[int, ...]
    initial_state_words: tuple[int, ...]
    format_words: tuple[int, ...]
    synapse_words: tuple[int, ...]
    weight_rows: tuple[int, ...]
    route_rows: tuple[int, ...]
    route_targets: tuple[int, ...]

    @classmethod
    def from_case(cls, case: MnistFpgaCorpusCase) -> "MnistFpgaStaticProfile":
        return cls(
            profile=case.profile,
            profile_id=case.profile_id,
            config_words=case.config_words,
            initial_state_words=case.initial_state_words,
            format_words=case.format_words,
            synapse_words=case.synapse_words,
            weight_rows=case.weight_rows,
            route_rows=case.route_rows,
            route_targets=case.route_targets,
        )

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


def load_frozen_corpus_entries(frozen_root: str | Path) -> tuple[dict[str, object], ...]:
    root = Path(frozen_root)
    payload = json.loads((root / "fpga_validation_corpus.json").read_text(encoding="utf-8"))
    if payload.get("schema") != "neuromorphic-twin-mnist-fpga-corpus-v1":
        raise ValueError("unsupported frozen FPGA corpus schema")
    entries = payload.get("entries")
    if not isinstance(entries, list) or len(entries) != EXPECTED_SOURCE_CASES:
        raise ValueError("frozen FPGA corpus must contain exactly 30 source entries")

    result: list[dict[str, object]] = []
    seen_indices: set[int] = set()
    class_counts = {digit: 0 for digit in range(10)}
    for raw in entries:
        if not isinstance(raw, dict):
            raise TypeError("frozen FPGA corpus entries must be JSON objects")
        index = int(raw["mnist_test_index"])
        label = int(raw["label"])
        reason = str(raw["selection_reason"])
        if index in seen_indices:
            raise ValueError(f"duplicate frozen MNIST test index: {index}")
        if label not in class_counts:
            raise ValueError(f"frozen corpus label outside 0..9: {label}")
        if reason not in {"both-correct", "profile-divergent", "both-wrong"}:
            raise ValueError(f"unexpected frozen selection_reason: {reason}")
        seen_indices.add(index)
        class_counts[label] += 1
        result.append(raw)

    if any(count != 3 for count in class_counts.values()):
        raise ValueError("frozen FPGA corpus must contain exactly three entries per digit")
    return tuple(result)


def build_corpus_cases(frozen_root: str | Path) -> tuple[MnistFpgaCorpusCase, ...]:
    """Build all 60 profile/image cases with independent 16-tick golden traces."""

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
    entries = load_frozen_corpus_entries(root)
    dataset = load_mnist()

    profile_data: dict[str, dict[str, object]] = {}
    for profile_name in PROFILE_ORDER:
        deployment_path = root / "deployments" / profile_name / "deployment.json"
        runtime = load_deployment(deployment_path)
        if runtime.profile.name != profile_name:
            raise ValueError("frozen deployment profile mismatch")
        storage_path = deployment_path.parent / runtime.manifest["weight_storage"]
        storage = read_weight_storage_json(storage_path)
        configs = tuple(
            NeuronConfig(**row) for row in runtime.manifest["neuron_configs"]
        )
        profile_data[profile_name] = {
            "runtime": runtime,
            "storage": storage,
            "configs": configs,
            "config_words": tuple(pack_neuron_config_word(config) for config in configs),
            "initial_state_words": tuple(
                pack_neuron_state_word(NeuronState()) for _ in configs
            ),
        }

    cases: list[MnistFpgaCorpusCase] = []
    for source_ordinal, entry in enumerate(entries):
        source_index = int(entry["mnist_test_index"])
        expected_label = int(entry["label"])
        selection_reason = str(entry["selection_reason"])
        image = np.asarray(dataset.x_test[source_index])
        actual_label = int(dataset.y_test[source_index])
        if actual_label != expected_label:
            raise ValueError(
                f"frozen corpus label mismatch at test index {source_index}: "
                f"{expected_label} != {actual_label}"
            )

        for profile_name in PROFILE_ORDER:
            values = profile_data[profile_name]
            runtime = values["runtime"]
            storage = values["storage"]
            configs = values["configs"]
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
            prediction_key = (
                "cropped_dense_golden_prediction"
                if profile_name == "cropped-dense"
                else "native_sparse_golden_prediction"
            )
            expected_prediction = int(entry[prediction_key])
            if prediction != expected_prediction:
                raise ValueError(
                    f"{profile_name} regenerated prediction {prediction} at test index "
                    f"{source_index} does not match frozen prediction {expected_prediction}"
                )

            case_id = len(cases)
            safe_reason = selection_reason.replace("-", "_")
            name = f"mnist08-{profile_name}-index{source_index:05d}-{safe_reason}"
            golden = PhysicalFpgaTraceArtifact(
                scenario_id=name,
                transport="python-golden",
                device="python-golden",
                ticks=tuple(captures),
            )
            cases.append(
                MnistFpgaCorpusCase(
                    case_id=case_id,
                    name=name,
                    profile=profile_name,
                    profile_id=PROFILE_ID[profile_name],
                    source_ordinal=source_ordinal,
                    selection_reason=selection_reason,
                    mnist_test_index=source_index,
                    label=actual_label,
                    expected_prediction=expected_prediction,
                    config_words=values["config_words"],
                    initial_state_words=values["initial_state_words"],
                    format_words=tuple(storage.format_words),
                    synapse_words=tuple(storage.synapse_words),
                    weight_rows=tuple(storage.axon_row_pointers),
                    route_rows=tuple(0 for _ in range(len(configs) + 1)),
                    route_targets=(),
                    external_schedule=tuple(tuple(events) for events in schedule),
                    golden_trace=golden,
                )
            )

    validate_corpus_case_contract(cases)
    return tuple(cases)


def validate_corpus_case_contract(cases: Sequence[MnistFpgaCorpusCase]) -> None:
    selected = tuple(cases)
    if len(selected) != EXPECTED_PHYSICAL_CASES:
        raise ValueError("MNIST-08 must contain exactly 60 physical cases")
    if tuple(case.case_id for case in selected) != tuple(range(EXPECTED_PHYSICAL_CASES)):
        raise ValueError("MNIST-08 case IDs must be dense and zero-based")

    by_source: dict[int, list[MnistFpgaCorpusCase]] = {}
    for case in selected:
        by_source.setdefault(case.source_ordinal, []).append(case)
    if len(by_source) != EXPECTED_SOURCE_CASES:
        raise ValueError("MNIST-08 must cover exactly 30 source images")
    for source_ordinal, group in by_source.items():
        if {case.profile for case in group} != set(PROFILE_ORDER):
            raise ValueError(f"source ordinal {source_ordinal} does not contain both profiles")
        indices = {case.mnist_test_index for case in group}
        labels = {case.label for case in group}
        reasons = {case.selection_reason for case in group}
        if len(indices) != 1 or len(labels) != 1 or len(reasons) != 1:
            raise ValueError("paired profile cases must share source index/label/reason")

    for profile_name in PROFILE_ORDER:
        profile_cases = [case for case in selected if case.profile == profile_name]
        if len(profile_cases) != EXPECTED_SOURCE_CASES:
            raise ValueError(f"{profile_name} must contain 30 cases")
        anchor = MnistFpgaStaticProfile.from_case(profile_cases[0])
        for case in profile_cases[1:]:
            if MnistFpgaStaticProfile.from_case(case) != anchor:
                raise ValueError(f"{profile_name} static deployment changed between cases")


def _static_profiles(cases: Sequence[MnistFpgaCorpusCase]) -> tuple[MnistFpgaStaticProfile, ...]:
    selected = tuple(cases)
    return tuple(
        MnistFpgaStaticProfile.from_case(next(case for case in selected if case.profile == name))
        for name in PROFILE_ORDER
    )


def _hex(value: int, width: int) -> str:
    return f"{value & ((1 << width) - 1):0{(width + 3) // 4}x}"


def _pad(values: Sequence[int], count: int) -> tuple[int, ...]:
    values = tuple(int(value) for value in values)
    if len(values) > count:
        raise ValueError("MNIST-08 generated row exceeds include stride")
    return values + (0,) * (count - len(values))


def write_corpus_systemverilog_include(
    cases: Sequence[MnistFpgaCorpusCase],
    output: str | Path,
) -> Path:
    """Write shared static profiles plus profile-banked external schedules."""

    selected = tuple(cases)
    validate_corpus_case_contract(selected)
    profiles = _static_profiles(selected)

    max_neurons = max(profile.neuron_count for profile in profiles)
    max_axons = max(profile.axon_count for profile in profiles)
    max_synapses = max(profile.synapse_count for profile in profiles)
    max_formats = max(profile.format_count for profile in profiles)
    max_routes = max(1, max(profile.route_count for profile in profiles))
    max_ticks = max(case.tick_count for case in selected)
    max_external = max(1, max(len(events) for case in selected for events in case.external_schedule))

    lines = [
        "// Generated by applications/mnist/scripts/generate_fpga_corpus.py; do not edit.",
        "// MNIST-08 INPUTS ONLY: golden state/spike/prediction data stays host-side.",
        "// Static deployment images are stored once per profile.",
        "// External-event words are also banked by profile to stay below Vivado's",
        "// per-variable synthesis-size limit while preserving exact event order/multiplicity.",
        f"localparam int M12_3_CASE_COUNT = {len(selected)};",
        f"localparam int M12_3_PROFILE_COUNT = {len(profiles)};",
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
        values = tuple(int(word) for word in words)
        if not values:
            raise ValueError(f"cannot emit empty array: {name}")
        lines.append(f"localparam logic [{width - 1}:0] {name} [0:{len(values) - 1}] = '{{")
        for index, word in enumerate(values):
            comma = "," if index + 1 != len(values) else ""
            lines.append(f"    {width}'h{_hex(word, width)}{comma}")
        lines.append("};")
        lines.append("")

    emit("M12_3_CASE_PROFILE_IDS", 8, tuple(case.profile_id for case in selected))
    emit("M12_3_NEURON_COUNTS", 9, tuple(case.neuron_count for case in selected))
    emit("M12_3_AXON_COUNTS", 11, tuple(case.axon_count for case in selected))
    emit("M12_3_SYNAPSE_COUNTS", 13, tuple(case.synapse_count for case in selected))
    emit("M12_3_FORMAT_COUNTS", 5, tuple(case.format_count for case in selected))
    emit("M12_3_ROUTE_COUNTS", 13, tuple(case.route_count for case in selected))
    emit("M12_3_TICK_COUNTS", 8, tuple(case.tick_count for case in selected))

    emit("M12_3_CONFIG_WORDS", 128, tuple(word for p in profiles for word in _pad(p.config_words, max_neurons)))
    emit("M12_3_INITIAL_STATE_WORDS", 64, tuple(word for p in profiles for word in _pad(p.initial_state_words, max_neurons)))
    emit("M12_3_FORMAT_WORDS", 16, tuple(word for p in profiles for word in _pad(p.format_words, max_formats)))
    emit("M12_3_SYNAPSE_WORDS", 32, tuple(word for p in profiles for word in _pad(p.synapse_words, max_synapses)))
    emit("M12_3_WEIGHT_ROWS", 32, tuple(word for p in profiles for word in _pad(p.weight_rows, max_axons + 1)))
    emit("M12_3_ROUTE_ROWS", 32, tuple(word for p in profiles for word in _pad(p.route_rows, max_neurons + 1)))
    emit("M12_3_ROUTE_TARGETS", 16, tuple(word for p in profiles for word in _pad(p.route_targets, max_routes)))

    # Each tick stores a start offset relative to its profile-specific event bank.
    # The controller already has the case profile ID, so no second case table is needed.
    external_counts: list[int] = []
    external_rows: list[int] = []
    external_banks: list[list[int]] = [[] for _ in PROFILE_ORDER]
    for case in selected:
        bank = external_banks[case.profile_id]
        padded_ticks = case.external_schedule + ((),) * (max_ticks - case.tick_count)
        for events in padded_ticks:
            external_counts.append(len(events))
            external_rows.append(len(bank))
            bank.extend(int(event) for event in events)

    for profile_id, words in enumerate(external_banks):
        if not words:
            words.append(0)
        bit_size = len(words) * EXTERNAL_EVENT_WORD_BITS
        if bit_size >= VIVADO_MAX_VARIABLE_BITS:
            raise ValueError(
                f"profile {PROFILE_ORDER[profile_id]} external-event bank is {bit_size} bits; "
                f"must remain below Vivado limit {VIVADO_MAX_VARIABLE_BITS}"
            )

    emit("M12_3_EXTERNAL_COUNTS", 13, external_counts)
    emit("M12_3_EXTERNAL_ROWS", 32, external_rows)
    emit("M12_3_EXTERNAL_EVENTS_PROFILE0", 16, external_banks[0])
    emit("M12_3_EXTERNAL_EVENTS_PROFILE1", 16, external_banks[1])

    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def write_corpus_bundle(
    cases: Sequence[MnistFpgaCorpusCase], output_dir: str | Path, sv_output: str | Path
) -> Path:
    from neuromorphic_twin.fpga_physical_trace import write_physical_fpga_trace_json

    selected = tuple(cases)
    validate_corpus_case_contract(selected)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    write_corpus_systemverilog_include(selected, sv_output)

    metadata_lines = ["case_id\tcase_name\tneuron_count\ttick_count"]
    records: list[dict[str, Any]] = []
    for case in selected:
        golden_name = f"{case.case_id:02d}-{case.name}.golden.json"
        write_physical_fpga_trace_json(case.golden_trace, output / golden_name)
        metadata_lines.append(f"{case.case_id}\t{case.name}\t{case.neuron_count}\t{case.tick_count}")
        records.append(
            {
                "case_id": case.case_id,
                "name": case.name,
                "profile": case.profile,
                "profile_id": case.profile_id,
                "source_ordinal": case.source_ordinal,
                "selection_reason": case.selection_reason,
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
                    "external_events": sum(map(len, case.external_schedule)),
                    "max_external_events_per_tick": max(map(len, case.external_schedule)),
                },
            }
        )

    (output / "hardware_cases.tsv").write_text("\n".join(metadata_lines) + "\n", encoding="utf-8")
    manifest = output / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": MNIST_FPGA_CORPUS_SCHEMA,
                "source_corpus": "applications/mnist/frozen/mnist-v1/fpga_validation_corpus.json",
                "source_image_count": EXPECTED_SOURCE_CASES,
                "physical_case_count": EXPECTED_PHYSICAL_CASES,
                "profiles": list(PROFILE_ORDER),
                "presentation_ticks": selected[0].tick_count,
                "fpga_input_contract": (
                    "two-shared-static-profile-images-plus-profile-banked-packed-case-external-events; "
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


def validate_physical_corpus_suite(
    manifest_path: str | Path, physical_dir: str | Path, report_dir: str | Path
) -> dict[str, object]:
    """Validate all 60 physical cases against their independent golden traces."""

    from neuromorphic_twin.fpga_physical_trace import read_physical_fpga_trace_json

    manifest_path = Path(manifest_path)
    physical_dir = Path(physical_dir)
    report_dir = Path(report_dir)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema") != MNIST_FPGA_CORPUS_SCHEMA:
        raise ValueError("unsupported MNIST-08 manifest schema")
    records = payload.get("cases")
    if not isinstance(records, list) or len(records) != EXPECTED_PHYSICAL_CASES:
        raise ValueError("MNIST-08 manifest must contain exactly 60 cases")

    report_dir.mkdir(parents=True, exist_ok=True)
    reports: list[dict[str, object]] = []
    for record in records:
        case_id = int(record["case_id"])
        name = str(record["name"])
        golden = read_physical_fpga_trace_json(manifest_path.parent / str(record["golden_trace"]))
        physical = read_physical_fpga_trace_json(physical_dir / f"{case_id:02d}-{name}.physical.json")
        report = compare_physical_to_golden(
            golden, physical, expected_prediction=int(record["expected_prediction"])
        )
        report.update(
            {
                "case_id": case_id,
                "profile": record["profile"],
                "selection_reason": record["selection_reason"],
                "mnist_test_index": record["mnist_test_index"],
                "label": record["label"],
            }
        )
        (report_dir / f"{case_id:02d}-{name}.report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        reports.append(report)

    passed = all(bool(report["passed"]) for report in reports)
    profile_summary = {}
    for profile in PROFILE_ORDER:
        subset = [report for report in reports if report["profile"] == profile]
        profile_summary[profile] = {
            "cases": len(subset),
            "passed": sum(bool(report["passed"]) for report in subset),
            "mismatches": sum(int(report["mismatch_count"]) for report in subset),
        }
    reason_summary = {}
    for reason in ("both-correct", "profile-divergent", "both-wrong"):
        subset = [report for report in reports if report["selection_reason"] == reason]
        reason_summary[reason] = {
            "cases": len(subset),
            "passed": sum(bool(report["passed"]) for report in subset),
            "mismatches": sum(int(report["mismatch_count"]) for report in subset),
        }

    suite = {
        "schema": MNIST_FPGA_CORPUS_SUITE_SCHEMA,
        "passed": passed,
        "case_count": len(reports),
        "tick_count": sum(len(read_physical_fpga_trace_json(physical_dir / f"{int(record['case_id']):02d}-{record['name']}.physical.json").ticks) for record in records),
        "mismatch_count": sum(int(report["mismatch_count"]) for report in reports),
        "profiles": profile_summary,
        "selection_reasons": reason_summary,
        "cases": reports,
    }
    (report_dir / "suite_report.json").write_text(
        json.dumps(suite, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return suite
