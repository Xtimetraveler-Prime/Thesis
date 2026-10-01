from __future__ import annotations

from copy import deepcopy

import pytest

from mnist_v2_nxtf.comparison_ledger import build_ledger
from mnist_v2_nxtf.final_comparison import (
    ACCEPTED_LEDGER_FINGERPRINT,
    AUTHORIZED_NUMERIC_CROSS_SYSTEM,
    FORBIDDEN_DERIVED_CROSS_SYSTEM,
    REPORT_SCHEMA,
    REPORT_STATUS,
    build_report,
    render_markdown,
    validate_report,
)


def test_report_is_bound_to_independently_accepted_ledger() -> None:
    ledger = build_ledger()
    report = build_report()

    assert ledger["ledger_fingerprint"] == ACCEPTED_LEDGER_FINGERPRINT
    assert report["schema"] == REPORT_SCHEMA
    assert report["status"] == REPORT_STATUS
    assert report["accepted_ledger_fingerprint"] == ACCEPTED_LEDGER_FINGERPRINT
    assert report["accepted_identities"] == ledger["accepted_identities"]


def test_only_frozen_accuracy_metrics_drive_cross_system_numeric_interpretation() -> None:
    report = build_report()

    assert report["authorized_numeric_cross_system_metric_ids"] == AUTHORIZED_NUMERIC_CROSS_SYSTEM
    assert report["forbidden_derived_cross_system_metric_ids"] == FORBIDDEN_DERIVED_CROSS_SYSTEM
    numeric = report["numeric_comparisons"]
    assert numeric["ann_test_error_gap_fraction"] == pytest.approx(0.0052)
    assert numeric["ann_test_error_gap_percentage_points"] == pytest.approx(0.52)
    assert numeric["snn_test_error_gap_fraction"] == pytest.approx(0.0097)
    assert numeric["snn_test_error_gap_percentage_points"] == pytest.approx(0.97)
    assert numeric["ann_to_snn_error_increase_gap_fraction"] == pytest.approx(0.0045)
    assert numeric["ann_to_snn_error_increase_gap_percentage_points"] == pytest.approx(0.45)


def test_forbidden_contextual_metric_cannot_be_promoted_to_numeric_delta() -> None:
    report = build_report()
    unsafe = deepcopy(report)
    unsafe.pop("report_fingerprint")
    unsafe["bounded_findings"].append(
        {
            "id": "unsafe_core_ratio",
            "basis": "CONTEXT_ONLY",
            "metric_ids": ["mapped_core_count"],
            "numeric_delta_metric_id": "mapped_core_count",
            "text": "unsafe",
        }
    )

    with pytest.raises(ValueError, match="unauthorized numeric cross-system delta"):
        validate_report(unsafe)


def test_report_rejects_ledger_identity_drift() -> None:
    report = build_report()
    unsafe = deepcopy(report)
    unsafe.pop("report_fingerprint")
    unsafe["accepted_ledger_fingerprint"] = "0" * 64

    with pytest.raises(ValueError, match="not bound to accepted P08.5.1 ledger"):
        validate_report(unsafe)


def test_report_guardrails_remain_all_false() -> None:
    report = build_report()
    assert report["guardrails"]
    assert set(report["guardrails"].values()) == {False}
    assert len(report["explicit_nonclaims"]) >= 8


def test_rendered_report_contains_bounded_numbers_and_nonclaims() -> None:
    report = build_report()
    markdown = render_markdown(report)

    assert "0.52 percentage points" in markdown
    assert "0.97 percentage points" in markdown
    assert "0.45 percentage points" in markdown
    assert "4,218 neurons" in markdown
    assert "7,006 trainable parameters" in markdown
    assert "338,880 expanded connections" in markdown
    assert "no efficiency ratio is derived" in markdown
    assert "one deep-core dispatch, not full-sample latency" in markdown
    assert "no FPGA-versus-Loihi energy or latency conclusion is drawn" in markdown
    assert "does not claim that the entire 100-timestep representative inference was physically replayed end-to-end over JTAG" in markdown


def test_report_generation_is_deterministic() -> None:
    first = build_report()
    second = build_report()
    assert first == second
    assert first["report_fingerprint"] == second["report_fingerprint"]
