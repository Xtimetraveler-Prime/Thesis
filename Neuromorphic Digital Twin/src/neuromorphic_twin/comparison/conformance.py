"""Directed Loihi conformance scenarios and suite reporting.

Each case asks one narrow architectural question. Keeping cases small makes the
first mismatch interpretable and prevents one error from contaminating several
behaviors at once.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from ..model import NeuronConfig, Synapse
from .brian2loihi_backend import (
    BackendUnavailableError,
    run_brian2loihi_backend,
)
from .compare import compare_traces
from .model import BackendTrace, ComparisonReport, ComparisonScenario
from .python_backend import run_python_backend

TraceRunner = Callable[[ComparisonScenario], BackendTrace]


@dataclass(frozen=True, slots=True)
class DirectedCase:
    """One deliberately isolated conformance experiment."""

    name: str
    category: str
    description: str
    scenario: ComparisonScenario
    fields: tuple[str, ...] = (
        "current_after",
        "voltage_after",
        "spikes",
    )

    def __post_init__(self) -> None:
        if self.scenario.name != self.name:
            raise ValueError("case name and scenario name must match")


@dataclass(frozen=True, slots=True)
class ConformanceCaseResult:
    """Outcome for one directed case."""

    case: DirectedCase
    reference: BackendTrace | None
    candidate: BackendTrace | None
    report: ComparisonReport | None
    error: str | None = None

    @property
    def status(self) -> str:
        if self.error is not None:
            return "ERROR"
        assert self.report is not None
        return "PASS" if self.report.passed else "FAIL"


@dataclass(frozen=True, slots=True)
class ConformanceSuiteReport:
    """Aggregate result for a collection of directed cases."""

    results: tuple[ConformanceCaseResult, ...]

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


def build_directed_cases() -> tuple[DirectedCase, ...]:
    """Return the deterministic Phase-1 conformance suite."""

    cases = (
        _smoke_no_decay(),
        _current_decay_order(),
        _voltage_decay(),
        _negative_current_rounding(),
        _inhibitory_synapse(),
        _threshold_boundary(),
        _refractory_one_tick(),
        _refractory_three_ticks(),
        _simultaneous_fan_in(),
        _fan_out(),
        _mixed_excitation_inhibition(),
        _multiple_simultaneous_spikes(),
    )
    names = tuple(case.name for case in cases)
    if len(names) != len(set(names)):
        raise RuntimeError("directed conformance case names must be unique")
    return cases


def run_directed_suite(
    cases: Sequence[DirectedCase] | None = None,
    *,
    reference_runner: TraceRunner = run_brian2loihi_backend,
    candidate_runner: TraceRunner = run_python_backend,
    stop_on_failure: bool = False,
) -> ConformanceSuiteReport:
    """Run all selected cases and continue after ordinary mismatches."""

    selected = tuple(cases) if cases is not None else build_directed_cases()
    results: list[ConformanceCaseResult] = []

    for case in selected:
        reference: BackendTrace | None = None
        candidate: BackendTrace | None = None
        try:
            candidate = candidate_runner(case.scenario)
            reference = reference_runner(case.scenario)
            report = compare_traces(
                reference,
                candidate,
                fields=case.fields,
            )
            result = ConformanceCaseResult(
                case=case,
                reference=reference,
                candidate=candidate,
                report=report,
            )
        except BackendUnavailableError:
            raise
        except Exception as exc:
            result = ConformanceCaseResult(
                case=case,
                reference=reference,
                candidate=candidate,
                report=None,
                error=f"{type(exc).__name__}: {exc}",
            )

        results.append(result)
        if stop_on_failure and result.status != "PASS":
            break

    return ConformanceSuiteReport(results=tuple(results))


def format_suite_report(
    suite: ConformanceSuiteReport,
    *,
    max_mismatches_per_case: int = 5,
) -> str:
    """Render a compact table followed by first-mismatch details."""

    if max_mismatches_per_case < 1:
        raise ValueError("max_mismatches_per_case must be positive")

    lines = [
        "Directed Loihi conformance suite",
        "=" * 86,
        f"{'STATUS':<7} {'CASE':<34} {'TICKS':>7} {'MISMATCHES':>12}  CATEGORY",
        "-" * 86,
    ]

    for result in suite.results:
        ticks = result.report.compared_ticks if result.report else 0
        mismatches = len(result.report.mismatches) if result.report else 0
        lines.append(
            f"{result.status:<7} {result.case.name:<34} "
            f"{ticks:>7} {mismatches:>12}  {result.case.category}"
        )

    lines.extend(
        [
            "-" * 86,
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
            f"{result.status}: {result.case.name} — {result.case.description}"
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


def write_suite_report_json(
    suite: ConformanceSuiteReport,
    path: str | Path,
) -> Path:
    """Write an aggregate machine-readable conformance report."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "neuromorphic-twin-conformance-v1",
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
            {
                "name": result.case.name,
                "category": result.case.category,
                "description": result.case.description,
                "status": result.status,
                "error": result.error,
                "compared_ticks": (
                    result.report.compared_ticks if result.report else 0
                ),
                "mismatch_count": (
                    len(result.report.mismatches) if result.report else 0
                ),
            }
            for result in suite.results
        ],
    }
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output


def case_output_name(case_name: str) -> str:
    """Return a stable filesystem-safe case directory name."""

    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", case_name).strip("-")


def _config(
    *,
    current_decay: int = 0,
    voltage_decay: int = 0,
    threshold: int = 4096,
    refractory_ticks: int = 1,
) -> NeuronConfig:
    return NeuronConfig(
        current_decay=current_decay,
        voltage_decay=voltage_decay,
        threshold=threshold,
        reset_voltage=0,
        refractory_ticks=refractory_ticks,
    )


def _case(
    *,
    name: str,
    category: str,
    description: str,
    config: NeuronConfig,
    neuron_count: int = 1,
    synapses: Sequence[Synapse],
    schedule: Sequence[tuple[int, ...]],
) -> DirectedCase:
    scenario = ComparisonScenario.build(
        name=name,
        neuron_configs=[config] * neuron_count,
        synapses=list(synapses),
        input_schedule=list(schedule),
    )
    return DirectedCase(
        name=name,
        category=category,
        description=description,
        scenario=scenario,
    )


def _smoke_no_decay() -> DirectedCase:
    return _case(
        name="smoke-no-decay",
        category="integration",
        description="Basic current/voltage integration, threshold, spike, and reset.",
        config=_config(threshold=256),
        synapses=[Synapse(0, 0, 128)],
        schedule=[(0,), (0,)],
    )


def _current_decay_order() -> DirectedCase:
    return _case(
        name="current-decay-order",
        category="current",
        description="Input is visible before current decay and voltage sees pre-decay current.",
        config=_config(current_decay=2048),
        synapses=[Synapse(0, 0, 128)],
        schedule=[(0,), (), ()],
    )


def _voltage_decay() -> DirectedCase:
    return _case(
        name="voltage-decay",
        category="voltage",
        description="Voltage persists and decays after a one-tick current impulse.",
        config=_config(current_decay=4096, voltage_decay=2048),
        synapses=[Synapse(0, 0, 128)],
        schedule=[(0,), (), ()],
    )


def _negative_current_rounding() -> DirectedCase:
    return _case(
        name="negative-current-rounding",
        category="arithmetic",
        description="Negative fractional current decay rounds away from zero.",
        config=_config(current_decay=1025),
        synapses=[Synapse(0, 0, -64)],
        schedule=[(0,), (), ()],
    )


def _inhibitory_synapse() -> DirectedCase:
    return _case(
        name="inhibitory-synapse",
        category="synapse",
        description="A purely inhibitory connection drives negative current and voltage.",
        config=_config(),
        synapses=[Synapse(0, 0, -128)],
        schedule=[(0,), ()],
    )


def _threshold_boundary() -> DirectedCase:
    return _case(
        name="threshold-boundary",
        category="threshold",
        description="Equality does not spike; the next representable step above threshold does.",
        config=_config(current_decay=4096, threshold=256),
        synapses=[
            Synapse(0, 0, 256),
            Synapse(1, 0, 64),
        ],
        schedule=[(0,), (1,)],
    )


def _refractory_one_tick() -> DirectedCase:
    return _case(
        name="refractory-one-tick",
        category="refractory",
        description="Repeated suprathreshold input probes one-tick refractory release timing.",
        config=_config(
            current_decay=4096,
            threshold=256,
            refractory_ticks=1,
        ),
        synapses=[Synapse(0, 0, 320)],
        schedule=[(0,), (0,), (0,), ()],
    )


def _refractory_three_ticks() -> DirectedCase:
    return _case(
        name="refractory-three-ticks",
        category="refractory",
        description="Repeated input probes a multi-tick refractory counter and release tick.",
        config=_config(
            current_decay=4096,
            threshold=256,
            refractory_ticks=3,
        ),
        synapses=[Synapse(0, 0, 320)],
        schedule=[(0,), (0,), (0,), (0,), (0,), (0,), ()],
    )


def _simultaneous_fan_in() -> DirectedCase:
    return _case(
        name="simultaneous-fan-in",
        category="connectivity",
        description="Two distinct input axons sum into one destination before update.",
        config=_config(),
        synapses=[
            Synapse(0, 0, 128),
            Synapse(1, 0, 64),
        ],
        schedule=[(0, 1), ()],
    )


def _fan_out() -> DirectedCase:
    return _case(
        name="fan-out",
        category="connectivity",
        description="One axon fans out to three neurons with independent weights.",
        config=_config(),
        neuron_count=3,
        synapses=[
            Synapse(0, 0, 64),
            Synapse(0, 1, 128),
            Synapse(0, 2, 192),
        ],
        schedule=[(0,), ()],
    )


def _mixed_excitation_inhibition() -> DirectedCase:
    return _case(
        name="mixed-excitation-inhibition",
        category="synapse",
        description="Excitatory and inhibitory groups sum into one net input.",
        config=_config(),
        synapses=[
            Synapse(0, 0, 192),
            Synapse(1, 0, -64),
        ],
        schedule=[(0, 1), ()],
    )


def _multiple_simultaneous_spikes() -> DirectedCase:
    return _case(
        name="multiple-simultaneous-spikes",
        category="spike",
        description="Three independent neurons cross threshold in the same tick.",
        config=_config(current_decay=4096, threshold=256),
        neuron_count=3,
        synapses=[
            Synapse(0, 0, 320),
            Synapse(1, 1, 384),
            Synapse(2, 2, 448),
        ],
        schedule=[(0, 1, 2), ()],
    )
