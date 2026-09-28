"""Pure trace-comparison logic and human-readable reporting."""

from __future__ import annotations

from collections.abc import Sequence

from .model import BackendTrace, ComparisonReport, TraceMismatch

_VECTOR_FIELDS = (
    "current_before",
    "voltage_before",
    "current_after",
    "voltage_after",
)


def compare_traces(
    reference: BackendTrace,
    candidate: BackendTrace,
    *,
    fields: Sequence[str] = ("current_after", "voltage_after", "spikes"),
) -> ComparisonReport:
    """Compare selected fields exactly, tick by tick.

    Exact comparison is intentional. These deterministic integer traces are
    intended to become bit-accurate verification artifacts, not approximate
    numerical simulations.
    """

    unknown = set(fields) - {*_VECTOR_FIELDS, "spikes"}
    if unknown:
        raise ValueError(f"unknown comparison fields: {sorted(unknown)}")

    mismatches: list[TraceMismatch] = []

    if reference.scenario != candidate.scenario:
        mismatches.append(
            TraceMismatch(
                tick=None,
                field="scenario",
                neuron_id=None,
                reference=reference.scenario,
                candidate=candidate.scenario,
            )
        )

    if len(reference.ticks) != len(candidate.ticks):
        mismatches.append(
            TraceMismatch(
                tick=None,
                field="tick_count",
                neuron_id=None,
                reference=len(reference.ticks),
                candidate=len(candidate.ticks),
            )
        )

    common_ticks = min(len(reference.ticks), len(candidate.ticks))
    for tick_id in range(common_ticks):
        ref_tick = reference.ticks[tick_id]
        cand_tick = candidate.ticks[tick_id]

        for field in fields:
            reference_value = getattr(ref_tick, field)
            candidate_value = getattr(cand_tick, field)

            if field == "spikes":
                ref_spikes = tuple(sorted(reference_value))
                cand_spikes = tuple(sorted(candidate_value))
                if ref_spikes != cand_spikes:
                    mismatches.append(
                        TraceMismatch(
                            tick=tick_id,
                            field=field,
                            neuron_id=None,
                            reference=ref_spikes,
                            candidate=cand_spikes,
                        )
                    )
                continue

            if len(reference_value) != len(candidate_value):
                mismatches.append(
                    TraceMismatch(
                        tick=tick_id,
                        field=f"{field}.length",
                        neuron_id=None,
                        reference=len(reference_value),
                        candidate=len(candidate_value),
                    )
                )
                continue

            for neuron_id, (ref_item, cand_item) in enumerate(
                zip(reference_value, candidate_value, strict=True)
            ):
                if ref_item != cand_item:
                    mismatches.append(
                        TraceMismatch(
                            tick=tick_id,
                            field=field,
                            neuron_id=neuron_id,
                            reference=ref_item,
                            candidate=cand_item,
                        )
                    )

    return ComparisonReport(
        reference_backend=reference.backend,
        candidate_backend=candidate.backend,
        scenario=reference.scenario,
        compared_ticks=common_ticks,
        mismatches=tuple(mismatches),
    )


def format_report(report: ComparisonReport, *, max_mismatches: int = 20) -> str:
    """Render a compact console report with the earliest mismatches first."""

    if max_mismatches < 1:
        raise ValueError("max_mismatches must be positive")

    status = "PASS" if report.passed else "FAIL"
    lines = [
        f"{status}: {report.candidate_backend} vs {report.reference_backend}",
        f"scenario={report.scenario!r}, compared_ticks={report.compared_ticks}, "
        f"mismatches={len(report.mismatches)}",
    ]

    for mismatch in report.mismatches[:max_mismatches]:
        location = "global" if mismatch.tick is None else f"tick {mismatch.tick}"
        if mismatch.neuron_id is not None:
            location += f", neuron {mismatch.neuron_id}"
        lines.append(
            f"  - {location}, {mismatch.field}: "
            f"reference={mismatch.reference!r}, "
            f"candidate={mismatch.candidate!r}"
        )

    hidden = len(report.mismatches) - max_mismatches
    if hidden > 0:
        lines.append(f"  ... {hidden} additional mismatches omitted")

    return "\n".join(lines)
