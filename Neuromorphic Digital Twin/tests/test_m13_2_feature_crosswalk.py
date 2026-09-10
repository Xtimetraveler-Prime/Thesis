from __future__ import annotations

from pathlib import Path

from neuromorphic_twin.m13_feature_crosswalk import (
    M13_2_COLUMNS,
    M13_2_REQUIRED_FEATURE_CLASSES,
    load_feature_crosswalk,
    render_feature_crosswalk_markdown,
)

ROOT = Path(__file__).resolve().parents[1]


def test_m13_2_covers_every_planned_feature_class_and_all_four_columns() -> None:
    data = load_feature_crosswalk()
    rows = data["rows"]
    assert len(rows) == 19
    assert M13_2_REQUIRED_FEATURE_CLASSES <= {row["feature_class"] for row in rows}
    for row in rows:
        for column in M13_2_COLUMNS:
            assert row[column]["summary"]
            assert row[column]["evidence"]


def test_m13_2_keeps_brian2loihi_separate_from_published_loihi() -> None:
    data = load_feature_crosswalk()
    for row in data["rows"]:
        assert row["published_loihi"] is not row["brian2loihi"]
        assert row["published_loihi"]["summary"] != row["brian2loihi"]["summary"]


def test_m13_2_links_prior_m03_m08_direct_brian2loihi_evidence() -> None:
    data = load_feature_crosswalk()
    source_id = "project_m03_m08_brian_evidence"
    source = data["source_registry"][source_id]
    assert source["evidence_type"] == "direct_observation"
    assert "M05" in source["role"] and "M07" in source["role"] and "M08.3" in source["role"]
    rows = {row["id"]: row for row in data["rows"]}
    for row_id in (
        "current-voltage-decay",
        "threshold-reset",
        "refractory-semantics",
        "weight-encoding",
        "synaptic-accumulation",
    ):
        assert source_id in rows[row_id]["brian2loihi"]["evidence"]


def test_m13_2_does_not_prematurely_assign_discrepancy_classes() -> None:
    data = load_feature_crosswalk()
    raw = (ROOT / "references" / "m13_2_feature_crosswalk.json").read_text(encoding="utf-8")
    assert '"discrepancy_class"' not in raw
    assert '"classification"' not in raw
    assert "M13.3" in data["purpose"]
    assert "M13.4" in data["purpose"]


def test_m13_2_captures_key_semantic_differences_without_calling_them_defects() -> None:
    data = load_feature_crosswalk()
    rows = {row["id"]: row for row in data["rows"]}

    threshold = rows["threshold-reset"]
    assert "strict" in threshold["project"]["summary"]
    assert ">=" in threshold["catalyst"]["summary"]
    assert threshold["overall_relationship"] == "comparable after a documented transform"

    decay = rows["current-voltage-decay"]
    assert "same-tick input" in decay["project"]["summary"]
    assert "old current" in decay["catalyst"]["summary"]
    assert decay["common_subset_candidate"] == "conditional"

    refractory = rows["refractory-semantics"]
    assert "next eligible" in refractory["m13_3_action"]


def test_m13_2_records_major_scope_gaps_explicitly() -> None:
    data = load_feature_crosswalk()
    rows = {row["id"]: row for row in data["rows"]}
    for row_id in (
        "dendritic-compartments",
        "synaptic-delay",
        "learning-plasticity",
        "routing-network",
        "multicore-noc",
        "async-execution",
    ):
        assert rows[row_id]["common_subset_candidate"] == "no"
        assert rows[row_id]["project"]["status"] == "out_of_scope"


def test_m13_2_preserves_catalyst_internal_boundary_differences() -> None:
    data = load_feature_crosswalk()
    rows = {row["id"]: row for row in data["rows"]}
    neuron = rows["neuron-state-model"]["catalyst"]["summary"]
    decay = rows["current-voltage-decay"]["catalyst"]["summary"]
    memory = rows["synapse-memory-organization"]["catalyst"]["summary"]
    assert "CPU reference" in neuron and "optional CUBA" in neuron
    assert "CPU simulator" in decay and "RTL" in decay
    assert "131072" in memory and "32768" in memory


def test_m13_2_renderer_is_deterministic_and_source_cited() -> None:
    data = load_feature_crosswalk()
    first = render_feature_crosswalk_markdown(data)
    second = render_feature_crosswalk_markdown(data)
    assert first == second
    assert "# M13.2 — Four-way Architectural Feature Crosswalk" in first
    assert "`loihi_davies_2018`" in first
    assert "`brian_neuron`" in first
    assert "`project_m03_m08_brian_evidence`" in first
    assert "`project_core_spec_m12`" in first
    assert "`catalyst_core_rtl`" in first
    assert "## M13.3 handoff by feature" in first


def test_m13_2_generated_document_matches_machine_readable_authority_when_present() -> None:
    data = load_feature_crosswalk()
    doc = ROOT / "docs" / "M13_2_ARCHITECTURAL_CROSSWALK.md"
    if doc.exists():
        assert doc.read_text(encoding="utf-8") == render_feature_crosswalk_markdown(data)
