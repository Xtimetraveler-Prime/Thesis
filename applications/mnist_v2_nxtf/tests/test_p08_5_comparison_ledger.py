from __future__ import annotations

import json

import pytest

from mnist_v2_nxtf.comparison_ledger import (
    ACCEPTED_IDENTITIES,
    COMPARABLE_WITH_RECONSTRUCTION_CAVEAT,
    CONTEXT_ONLY,
    DIRECTLY_COMPARABLE,
    LEDGER_JSON,
    LEDGER_MARKDOWN,
    NOT_COMPARABLE,
    PROJECT_SPECIFIC,
    build_ledger,
    validate_ledger,
    write_ledger,
)


def _rows_by_id(ledger):
    return {row["id"]: row for row in ledger["rows"]}


def test_p08_5_ledger_is_deterministic_and_bound_to_accepted_identities():
    first = build_ledger()
    second = build_ledger()
    assert first == second
    assert first["accepted_identities"] == ACCEPTED_IDENTITIES
    assert first["ledger_fingerprint"] == second["ledger_fingerprint"]
    assert len(first["ledger_fingerprint"]) == 64


def test_p08_5_ledger_classifications_and_values_are_frozen():
    ledger = build_ledger()
    rows = _rows_by_id(ledger)
    assert len(rows) == 24

    counts = {}
    for row in rows.values():
        counts[row["comparison_class"]] = counts.get(row["comparison_class"], 0) + 1
    assert counts == {
        DIRECTLY_COMPARABLE: 3,
        COMPARABLE_WITH_RECONSTRUCTION_CAVEAT: 7,
        CONTEXT_ONLY: 2,
        PROJECT_SPECIFIC: 10,
        NOT_COMPARABLE: 2,
    }

    assert rows["algorithmic_timesteps"]["nxtf"]["value"] == 100
    assert rows["algorithmic_timesteps"]["project"]["value"] == 100
    assert rows["ann_test_error"]["nxtf"]["value"] == pytest.approx(0.0074)
    assert rows["ann_test_error"]["project"]["value"] == pytest.approx(0.0126)
    assert rows["snn_test_error"]["nxtf"]["value"] == pytest.approx(0.0079)
    assert rows["snn_test_error"]["project"]["value"] == pytest.approx(0.0176)
    assert rows["neuron_count"]["project"]["value"] == 4218
    assert rows["trainable_parameters"]["project"]["value"] == 7006
    assert rows["expanded_connections"]["project"]["value"] == 338880


def test_p08_5_unsafe_cross_system_ratios_are_forbidden():
    rows = _rows_by_id(build_ledger())

    assert rows["shared_weight_accounting"]["comparison_class"] == CONTEXT_ONLY
    assert rows["shared_weight_accounting"]["allow_numeric_delta"] is False
    assert rows["mapped_core_count"]["comparison_class"] == CONTEXT_ONLY
    assert rows["mapped_core_count"]["allow_numeric_delta"] is False

    for metric_id in ("native_loihi_energy", "native_loihi_latency"):
        assert rows[metric_id]["comparison_class"] == NOT_COMPARABLE
        assert rows[metric_id]["project"]["value"] is None
        assert rows[metric_id]["allow_numeric_delta"] is False

    assert rows["representative_physical_dispatch_cycles"]["comparison_class"] == PROJECT_SPECIFIC
    assert rows["representative_physical_dispatch_cycles"]["allow_numeric_delta"] is False
    assert rows["representative_physical_dispatch_time"]["project"]["value"] == pytest.approx(38.65)


def test_p08_5_overclaim_guardrails_all_remain_false():
    ledger = build_ledger()
    assert ledger["guardrails"]
    assert set(ledger["guardrails"].values()) == {False}


def test_p08_5_validation_rejects_energy_overclaim():
    ledger = build_ledger()
    ledger.pop("ledger_fingerprint")
    rows = _rows_by_id(ledger)
    rows["native_loihi_energy"]["comparison_class"] = DIRECTLY_COMPARABLE
    rows["native_loihi_energy"]["project"]["value"] = 0.1
    with pytest.raises(ValueError):
        validate_ledger(ledger)


def test_p08_5_write_outputs_revalidate(tmp_path):
    ledger = write_ledger(tmp_path)
    json_path = tmp_path / LEDGER_JSON
    markdown_path = tmp_path / LEDGER_MARKDOWN
    assert json_path.is_file()
    assert markdown_path.is_file()

    saved = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved == ledger
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "Native-Loihi energy and latency remain published context only" in markdown
    assert ledger["ledger_fingerprint"] in markdown
