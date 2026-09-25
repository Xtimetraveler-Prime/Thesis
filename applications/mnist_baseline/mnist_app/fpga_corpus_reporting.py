"""Console reporting helpers for the MNIST-08 physical corpus suite."""

from __future__ import annotations

from typing import Mapping


def format_suite_summary(suite: Mapping[str, object]) -> tuple[str, ...]:
    """Format the stable suite keys emitted by ``validate_physical_corpus_suite``."""

    profiles = suite["profiles"]
    reasons = suite["selection_reasons"]
    if not isinstance(profiles, Mapping) or not isinstance(reasons, Mapping):
        raise TypeError("MNIST-08 suite summaries must be mappings")

    lines = [
        "MNIST-08 suite: "
        f"passed={suite['passed']} cases={suite['case_count']} "
        f"ticks={suite['tick_count']} mismatches={suite['mismatch_count']}"
    ]
    for profile, summary in profiles.items():
        if not isinstance(summary, Mapping):
            raise TypeError("MNIST-08 profile summary must be a mapping")
        lines.append(
            f"profile={profile} cases={summary['cases']} "
            f"passed={summary['passed']} mismatches={summary['mismatches']}"
        )
    for reason, summary in reasons.items():
        if not isinstance(summary, Mapping):
            raise TypeError("MNIST-08 selection-reason summary must be a mapping")
        lines.append(
            f"reason={reason} cases={summary['cases']} "
            f"passed={summary['passed']} mismatches={summary['mismatches']}"
        )
    return tuple(lines)
