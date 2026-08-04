"""Directed conformance checks for Loihi-style static weight encoding.

This module deliberately keeps encoded weights outside the production ``Synapse``
schema. The Python candidate consumes the encoder's derived effective integer,
while the Brian2Loihi reference receives the original mantissa and shared format.
That isolates M08.3 arithmetic validation from the M08.4 schema integration.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Callable, Sequence

from ..model import NeuronConfig, Synapse
from ..weights import (
    StaticWeightEncoding,
    WeightFormat,
    WeightSignMode,
    encode_static_weight,
)
from .brian2loihi_backend import BackendUnavailableError
from .compare import compare_traces
from .model import (
    BackendTick,
    BackendTrace,
    ComparisonReport,
    ComparisonScenario,
    TraceMismatch,
)
from .python_backend import run_python_backend


@dataclass(frozen=True, slots=True)
class WeightConformanceCase:
    """One encoded-weight question with a one-synapse observable scenario."""

    name: str
    description: str
    encoding: StaticWeightEncoding
    scenario: ComparisonScenario
    fields: tuple[str, ...] = (
        "current_after",
        "voltage_after",
        "spikes",
    )

    def __post_init__(self) -> None:
        if self.scenario.name != self.name:
            raise ValueError("case name and scenario name must match")
        if len(self.scenario.synapses) != 1:
            raise ValueError("weight conformance cases require exactly one synapse")
        synapse = self.scenario.synapses[0]
        if synapse.weight != self.encoding.effective_weight:
            raise ValueError(
                "Python scenario weight must equal the encoder effective weight"
            )


@dataclass(frozen=True, slots=True)
class WeightBackendRun:
    """Trace plus the backend's directly observable effective weight."""

    trace: BackendTrace
    effective_weight: int


WeightRunner = Callable[[WeightConformanceCase], WeightBackendRun]


@dataclass(frozen=True, slots=True)
class WeightConformanceCaseResult:
    case: WeightConformanceCase
    reference: WeightBackendRun | None
    candidate: WeightBackendRun | None
    report: ComparisonReport | None
    error: str | None = None

    @property
    def status(self) -> str:
        if self.error is not None:
            return "ERROR"
        assert self.report is not None
        return "PASS" if self.report.passed else "FAIL"


@dataclass(frozen=True, slots=True)
class WeightConformanceSuiteReport:
    results: tuple[WeightConformanceCaseResult, ...]

    @property
    def passed(self) -> bool:
        return bool(self.results) and all(
            result.status == "PASS" for result in self.results
        )

    @property
    def pass_count(self) -> int:
        return sum(result.status == "PASS" for result in self.results)

    @property
    def fail_count(self) -> int:
        return sum(result.status == "FAIL" for result in self.results)

    @property
    def error_count(self) -> int:
        return sum(result.status == "ERROR" for result in self.results)

    @property
    def total_ticks(self) -> int:
        return sum(
            result.report.compared_ticks
            for result in self.results
            if result.report is not None
        )

    @property
    def mismatch_count(self) -> int:
        return sum(
            len(result.report.mismatches)
            for result in self.results
            if result.report is not None
        )


def build_weight_conformance_cases() -> tuple[WeightConformanceCase, ...]:
    """Return directed static-weight cases covering M08.3 boundaries."""

    cases = (
        _case(
            "weight-baseline-excitatory",
            "Baseline exponent-zero, eight-bit excitatory expansion.",
            124,
            WeightFormat(),
        ),
        _case(
            "weight-positive-exponent",
            "Positive exponent increases the aligned effective weight.",
            3,
            WeightFormat(exponent=3),
        ),
        _case(
            "weight-negative-exponent-exact",
            "Negative exponent with an exactly representable aligned result.",
            128,
            WeightFormat(exponent=-2),
        ),
        _case(
            "weight-negative-exponent-positive-floor",
            "Small positive value with a negative exponent aligns down to zero.",
            1,
            WeightFormat(exponent=-1),
        ),
        _case(
            "weight-negative-exponent-negative-floor",
            "Small negative value floors to the next lower aligned weight.",
            -1,
            WeightFormat(
                exponent=-1,
                sign_mode=WeightSignMode.INHIBITORY,
            ),
        ),
        _case(
            "weight-reduced-precision-excitatory",
            "Reduced precision truncates a positive mantissa toward zero.",
            127,
            WeightFormat(num_weight_bits=6),
        ),
        _case(
            "weight-reduced-precision-inhibitory",
            "Reduced precision truncates a negative mantissa toward zero.",
            -127,
            WeightFormat(
                num_weight_bits=6,
                sign_mode=WeightSignMode.INHIBITORY,
            ),
        ),
        _case(
            "weight-mixed-positive-quantization",
            "Mixed mode consumes one precision bit for a positive mantissa.",
            253,
            WeightFormat(sign_mode=WeightSignMode.MIXED),
        ),
        _case(
            "weight-mixed-negative-quantization",
            "Mixed mode consumes one precision bit for a negative mantissa.",
            -255,
            WeightFormat(sign_mode=WeightSignMode.MIXED),
        ),
        _case(
            "weight-excitatory-maximum",
            "Maximum excitatory mantissa at maximum exponent remains in range.",
            255,
            WeightFormat(exponent=7),
        ),
        _case(
            "weight-inhibitory-minimum",
            "Minimum inhibitory mantissa is accepted at exponent zero.",
            -256,
            WeightFormat(sign_mode=WeightSignMode.INHIBITORY),
        ),
        _case(
            "weight-negative-clipping",
            "Extreme negative mixed weight clips to the aligned 21-bit limit.",
            -256,
            WeightFormat(
                exponent=7,
                sign_mode=WeightSignMode.MIXED,
            ),
        ),
        _case(
            "weight-zero-bits-excitatory",
            "Zero configured bits quantize the largest excitatory mantissa to zero.",
            255,
            WeightFormat(num_weight_bits=0),
        ),
        _case(
            "weight-zero-bits-inhibitory",
            "Zero configured bits preserve the minimum inhibitory mantissa.",
            -256,
            WeightFormat(
                num_weight_bits=0,
                sign_mode=WeightSignMode.INHIBITORY,
            ),
        ),
        _case(
            "weight-zero-bits-mixed",
            "Zero configured bits quantize the minimum mixed mantissa to zero.",
            -256,
            WeightFormat(
                num_weight_bits=0,
                sign_mode=WeightSignMode.MIXED,
            ),
        ),
    )
    names = tuple(case.name for case in cases)
    if len(names) != len(set(names)):
        raise RuntimeError("weight conformance case names must be unique")
    return cases


def run_python_weight_backend(
    case: WeightConformanceCase,
) -> WeightBackendRun:
    """Run the effective integer weight through the transparent Python core."""

    return WeightBackendRun(
        trace=run_python_backend(case.scenario),
        effective_weight=case.encoding.effective_weight,
    )


def run_brian2loihi_weight_backend(
    case: WeightConformanceCase,
) -> WeightBackendRun:
    """Run the original mantissa and format through Brian2Loihi."""

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

    scenario = case.scenario
    config = scenario.neuron_configs[0]
    neurons = LoihiNeuronGroup(
        len(scenario.neuron_configs),
        refractory=config.refractory_ticks,
        threshold_v_mant=config.threshold // 64,
        decay_v=config.voltage_decay,
        decay_I=config.current_decay,
    )

    event_indices: list[int] = []
    event_times: list[int] = []
    for tick, axons in enumerate(scenario.input_schedule):
        for axon_id in axons:
            event_indices.append(axon_id)
            event_times.append(tick)

    synapse = scenario.synapses[0]
    source_count = max(
        max(event_indices, default=0),
        synapse.axon_id,
    ) + 1
    generator = LoihiSpikeGeneratorGroup(
        source_count,
        event_indices,
        event_times,
    )

    fmt = case.encoding.weight_format
    encoded_synapse = LoihiSynapses(
        generator,
        neurons,
        w_exp=fmt.exponent,
        sign_mode=_brian_sign_mode(fmt.sign_mode, synapse_sign_mode),
        num_weight_bits=fmt.num_weight_bits,
    )
    encoded_synapse.connect(
        i=[synapse.axon_id],
        j=[synapse.target_neuron],
    )
    encoded_synapse.w = np.asarray(
        [case.encoding.requested_mantissa],
        dtype=int,
    )

    reference_weights = _as_integer_tuple(
        encoded_synapse.w_act,
        "Brian2Loihi actual weight",
    )
    if len(reference_weights) != 1:
        raise RuntimeError(
            "weight conformance case expected exactly one Brian2Loihi weight"
        )
    reference_effective_weight = reference_weights[0]

    spike_monitor = LoihiSpikeMonitor(neurons)
    network = LoihiNetwork(
        neurons,
        generator,
        encoded_synapse,
        spike_monitor,
    )

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
        backend="Brian2Loihi-encoded-weight",
        scenario=scenario.name,
        ticks=tuple(ticks),
        metadata=(
            ("brian2", _package_version("brian2")),
            ("brian2-loihi", _package_version("brian2-loihi")),
            ("requested_mantissa", str(case.encoding.requested_mantissa)),
            ("weight_exponent", str(fmt.exponent)),
            ("num_weight_bits", str(fmt.num_weight_bits)),
            ("sign_mode", fmt.sign_mode.value),
            ("effective_weight", str(reference_effective_weight)),
        ),
    )
    return WeightBackendRun(
        trace=trace,
        effective_weight=reference_effective_weight,
    )


def run_weight_conformance_suite(
    cases: Sequence[WeightConformanceCase] | None = None,
    *,
    reference_runner: WeightRunner = run_brian2loihi_weight_backend,
    candidate_runner: WeightRunner = run_python_weight_backend,
    stop_on_failure: bool = False,
) -> WeightConformanceSuiteReport:
    """Run selected encoded-weight cases and compare direct values plus traces."""

    selected = (
        tuple(cases)
        if cases is not None
        else build_weight_conformance_cases()
    )
    results: list[WeightConformanceCaseResult] = []

    for case in selected:
        reference: WeightBackendRun | None = None
        candidate: WeightBackendRun | None = None
        try:
            candidate = candidate_runner(case)
            reference = reference_runner(case)
            report = compare_traces(
                reference.trace,
                candidate.trace,
                fields=case.fields,
            )
            if reference.effective_weight != candidate.effective_weight:
                report = replace(
                    report,
                    mismatches=(
                        TraceMismatch(
                            tick=None,
                            field="effective_weight",
                            neuron_id=None,
                            reference=reference.effective_weight,
                            candidate=candidate.effective_weight,
                        ),
                        *report.mismatches,
                    ),
                )
            result = WeightConformanceCaseResult(
                case=case,
                reference=reference,
                candidate=candidate,
                report=report,
            )
        except BackendUnavailableError:
            raise
        except Exception as exc:
            result = WeightConformanceCaseResult(
                case=case,
                reference=reference,
                candidate=candidate,
                report=None,
                error=f"{type(exc).__name__}: {exc}",
            )

        results.append(result)
        if stop_on_failure and result.status != "PASS":
            break

    return WeightConformanceSuiteReport(results=tuple(results))


def format_weight_suite_report(
    suite: WeightConformanceSuiteReport,
    *,
    max_mismatches_per_case: int = 5,
) -> str:
    """Render a compact encoded-weight suite report."""

    if max_mismatches_per_case < 1:
        raise ValueError("max_mismatches_per_case must be positive")

    lines = [
        "Directed encoded-weight conformance suite",
        "=" * 106,
        (
            f"{'STATUS':<7} {'CASE':<42} {'MANT':>6} {'EXP':>4} "
            f"{'BITS':>4} {'MODE':<11} {'TICKS':>5} {'MISMATCHES':>10}"
        ),
        "-" * 106,
    ]

    for result in suite.results:
        encoding = result.case.encoding
        fmt = encoding.weight_format
        ticks = result.report.compared_ticks if result.report else 0
        mismatches = len(result.report.mismatches) if result.report else 0
        lines.append(
            f"{result.status:<7} {result.case.name:<42} "
            f"{encoding.requested_mantissa:>6} {fmt.exponent:>4} "
            f"{fmt.num_weight_bits:>4} {fmt.sign_mode.value:<11} "
            f"{ticks:>5} {mismatches:>10}"
        )

    lines.extend(
        [
            "-" * 106,
            f"cases={len(suite.results)}, pass={suite.pass_count}, "
            f"fail={suite.fail_count}, error={suite.error_count}, "
            f"ticks={suite.total_ticks}, mismatches={suite.mismatch_count}",
        ]
    )

    for result in suite.results:
        if result.status == "PASS":
            continue
        lines.append("")
        lines.append(
            f"{result.status}: {result.case.name} — "
            f"{result.case.description}"
        )
        if result.error is not None:
            lines.append(f"  {result.error}")
            continue

        assert result.report is not None
        for mismatch in result.report.mismatches[:max_mismatches_per_case]:
            location = (
                "global" if mismatch.tick is None else f"tick {mismatch.tick}"
            )
            if mismatch.neuron_id is not None:
                location += f", neuron {mismatch.neuron_id}"
            lines.append(
                f"  - {location}, {mismatch.field}: "
                f"reference={mismatch.reference!r}, "
                f"candidate={mismatch.candidate!r}"
            )
        hidden = (
            len(result.report.mismatches) - max_mismatches_per_case
        )
        if hidden > 0:
            lines.append(f"  ... {hidden} additional mismatches omitted")

    return "\n".join(lines)


def write_weight_suite_report_json(
    suite: WeightConformanceSuiteReport,
    path: str | Path,
) -> Path:
    """Write a machine-readable encoded-weight conformance report."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "neuromorphic-twin-weight-conformance-v1",
        "passed": suite.passed,
        "summary": {
            "cases": len(suite.results),
            "pass": suite.pass_count,
            "fail": suite.fail_count,
            "error": suite.error_count,
            "ticks": suite.total_ticks,
            "mismatches": suite.mismatch_count,
        },
        "results": [
            _result_payload(result)
            for result in suite.results
        ],
    }
    output.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    return output


def weight_case_output_name(case_name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", case_name).strip("-")


def _case(
    name: str,
    description: str,
    mantissa: int,
    weight_format: WeightFormat,
) -> WeightConformanceCase:
    encoding = encode_static_weight(mantissa, weight_format)
    scenario = ComparisonScenario.build(
        name=name,
        neuron_configs=[
            NeuronConfig(
                current_decay=0,
                voltage_decay=0,
                threshold=8_388_544,
                reset_voltage=0,
                refractory_ticks=1,
            )
        ],
        synapses=[
            Synapse(
                axon_id=0,
                target_neuron=0,
                weight=encoding.effective_weight,
            )
        ],
        input_schedule=[(0,)],
    )
    return WeightConformanceCase(
        name=name,
        description=description,
        encoding=encoding,
        scenario=scenario,
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


def _result_payload(
    result: WeightConformanceCaseResult,
) -> dict[str, object]:
    encoding = result.case.encoding
    fmt = encoding.weight_format
    return {
        "name": result.case.name,
        "description": result.case.description,
        "status": result.status,
        "error": result.error,
        "encoding": {
            "requested_mantissa": encoding.requested_mantissa,
            "quantized_mantissa": encoding.quantized_mantissa,
            "exponent": fmt.exponent,
            "num_weight_bits": fmt.num_weight_bits,
            "sign_mode": fmt.sign_mode.value,
            "effective_weight_before_clip": (
                encoding.effective_weight_before_clip
            ),
            "candidate_effective_weight": encoding.effective_weight,
            "clipped": encoding.clipped,
        },
        "reference_effective_weight": (
            result.reference.effective_weight
            if result.reference is not None
            else None
        ),
        "compared_ticks": (
            result.report.compared_ticks if result.report else 0
        ),
        "mismatch_count": (
            len(result.report.mismatches) if result.report else 0
        ),
    }
