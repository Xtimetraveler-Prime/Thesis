from __future__ import annotations

from copy import deepcopy

import pytest

from mnist_v2_nxtf.final_closure import (
    ACCEPTED_LEDGER_FINGERPRINT,
    ACCEPTED_MERGES,
    ACCEPTED_REPORT_FINGERPRINT,
    CLOSURE_SCHEMA,
    CLOSURE_STATUS,
    EXPECTED_RESULTS,
    REQUIRED_NONCLAIMS,
    build_closure,
    render_markdown,
    validate_closure,
)


def test_closure_binds_accepted_p08_5_1_and_p08_5_2() -> None:
    closure = build_closure()
    assert closure["schema"] == CLOSURE_SCHEMA
    assert closure["status"] == CLOSURE_STATUS
    assert closure["accepted_ledger_fingerprint"] == ACCEPTED_LEDGER_FINGERPRINT
    assert closure["accepted_report_fingerprint"] == ACCEPTED_REPORT_FINGERPRINT
    assert closure["accepted_merge_commits"] == ACCEPTED_MERGES


def test_closure_freezes_final_metrics_and_architecture() -> None:
    closure = build_closure()
    assert closure["results"] == EXPECTED_RESULTS
    assert closure["results"]["ann_test_accuracy"] == pytest.approx(0.9874)
    assert closure["results"]["snn_test_accuracy"] == pytest.approx(0.9824)
    assert closure["results"]["logical_cores"] == 5
    assert closure["results"]["resident_contexts"] == 3
    assert closure["results"]["physical_engines"] == 1


def test_closure_keeps_completion_pending_until_independent_reproduction() -> None:
    closure = build_closure()
    assert closure["p08_complete"] is False
    assert closure["subphases"]["P08.5.3"] == "REVIEW_PENDING"
    assert closure["completion_condition"] == "independent reproduction of P08.5.3 closure gate"


def test_closure_rejects_overclaim_guardrail_mutation() -> None:
    closure = build_closure()
    unsafe = deepcopy(closure)
    unsafe.pop("closure_fingerprint")
    unsafe["guardrails"]["claim_direct_energy_comparison"] = True
    with pytest.raises(ValueError, match="overclaim guardrails"):
        validate_closure(unsafe)


def test_closure_preserves_explicit_nonclaims_and_physical_scope() -> None:
    closure = build_closure()
    assert tuple(closure["explicit_nonclaims"]) == REQUIRED_NONCLAIMS
    markdown = render_markdown(closure)
    assert "98.74%" in markdown
    assert "98.24%" in markdown
    assert "4,218 neurons" in markdown
    assert "5 logical cores / 3 resident contexts / 1 physical engine" in markdown
    assert "3,865 cycles" in markdown
    assert "one dispatch, not full-sample latency" in markdown
    assert "full 100-timestep representative inference physically replayed end-to-end over JTAG" in markdown
    assert "P08 completion remains pending independent reproduction" in markdown


def test_closure_generation_is_deterministic() -> None:
    first = build_closure()
    second = build_closure()
    assert first == second
    assert first["closure_fingerprint"] == second["closure_fingerprint"]
