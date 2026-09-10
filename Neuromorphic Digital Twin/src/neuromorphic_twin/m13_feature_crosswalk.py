from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


M13_2_SCHEMA = "neuromorphic-twin-m13-feature-crosswalk-v1"
M13_2_PROJECT_BASELINE = "80a502ec6dfc4c8d61372089b08c9a584ad65f85"
M13_2_M13_1_MERGE = "fab362cebdff133e71367c186d8689e332a99a10"
M13_2_CATALYST_COMMIT = "1806bb4b4114d7671e5648fa75b7b83b3a8d5543"
M13_2_BRIAN2LOIHI_COMMIT = "d54676cb113e48dc886615a0b589bb0e4bccbca4"

M13_2_COLUMNS = ("published_loihi", "brian2loihi", "project", "catalyst")
M13_2_REQUIRED_FEATURE_CLASSES = {
    "neuron model/state variables",
    "current and voltage decay semantics",
    "update ordering and algorithmic tick boundaries",
    "threshold, reset, and refractory behavior",
    "weight representation, sign modes, exponent/precision behavior, quantization, and clipping",
    "synaptic accumulation and fan-in/fan-out",
    "fixed-point widths, rounding, saturation/overflow behavior",
    "event ordering and multiplicity",
    "recurrent delivery timing",
    "synapse/routing memory organization at the architectural level",
    "routing/network organization",
    "learning/plasticity support",
    "management/host-control architecture",
    "multicore/network-on-chip features",
    "observability/debug mechanisms relevant to experimental validation",
}
M13_2_RELATIONSHIPS = {
    "exactly comparable",
    "comparable after a documented transform",
    "similar but architecturally different",
    "unsupported by one implementation",
    "not observable through the available interface",
    "ambiguous in available Loihi evidence",
    "out of project scope",
}
M13_2_CELL_STATUSES = {
    "documented",
    "implemented",
    "physically_validated",
    "directly_observed",
    "partial",
    "unsupported",
    "not_observable",
    "ambiguous",
    "out_of_scope",
}
M13_2_COMMON_SUBSET = {"yes", "conditional", "no"}
M13_2_EVIDENCE_TYPES = {
    "published_documentation",
    "direct_observation",
    "implementation_inference",
    "project_interpretation",
}


def default_crosswalk_path() -> Path:
    return Path(__file__).resolve().parents[2] / "references" / "m13_2_feature_crosswalk.json"


def load_feature_crosswalk(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path is not None else default_crosswalk_path()
    with target.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    validate_feature_crosswalk(data)
    return data


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def validate_feature_crosswalk(data: Mapping[str, Any]) -> None:
    if data.get("schema") != M13_2_SCHEMA:
        raise ValueError("unexpected M13.2 crosswalk schema")
    pins = {
        "project_baseline_commit": M13_2_PROJECT_BASELINE,
        "m13_1_merge_commit": M13_2_M13_1_MERGE,
        "catalyst_commit": M13_2_CATALYST_COMMIT,
        "brian2loihi_commit": M13_2_BRIAN2LOIHI_COMMIT,
    }
    for key, expected in pins.items():
        if data.get(key) != expected:
            raise ValueError(f"M13.2 pin changed: {key}")

    if set(data.get("relationship_vocabulary", [])) != M13_2_RELATIONSHIPS:
        raise ValueError("M13.2 relationship vocabulary differs from milestone contract")
    if set(data.get("cell_status_vocabulary", [])) != M13_2_CELL_STATUSES:
        raise ValueError("M13.2 cell-status vocabulary changed")

    sources = _mapping(data.get("source_registry"), "source_registry")
    if len(sources) < 12:
        raise ValueError("M13.2 source registry is unexpectedly small")
    for source_id, source in sources.items():
        source = _mapping(source, f"source_registry.{source_id}")
        if source.get("evidence_type") not in M13_2_EVIDENCE_TYPES:
            raise ValueError(f"invalid evidence type for source {source_id}")
        if not source.get("role"):
            raise ValueError(f"source {source_id} lacks a role")
        if "repository" in source and not source.get("commit"):
            raise ValueError(f"repository source {source_id} is not commit-pinned")

    rows = data.get("rows")
    if not isinstance(rows, list) or len(rows) < 15:
        raise ValueError("M13.2 requires at least 15 feature rows")
    row_ids: set[str] = set()
    covered_classes: set[str] = set()
    for index, row_value in enumerate(rows):
        row = _mapping(row_value, f"rows[{index}]")
        row_id = str(row.get("id", ""))
        if not row_id or row_id in row_ids:
            raise ValueError(f"missing/duplicate row id: {row_id!r}")
        row_ids.add(row_id)
        feature_class = str(row.get("feature_class", ""))
        covered_classes.add(feature_class)
        if not row.get("feature") or not row.get("m13_3_action"):
            raise ValueError(f"row {row_id} lacks feature/action text")
        if row.get("overall_relationship") not in M13_2_RELATIONSHIPS:
            raise ValueError(f"row {row_id} has invalid relationship")
        if row.get("common_subset_candidate") not in M13_2_COMMON_SUBSET:
            raise ValueError(f"row {row_id} has invalid common-subset flag")
        if any(key in row for key in ("discrepancy_class", "classification", "A", "B", "C", "D", "E", "F", "G", "H")):
            raise ValueError(f"row {row_id} prematurely assigns an M13 discrepancy class")

        for column in M13_2_COLUMNS:
            cell = _mapping(row.get(column), f"{row_id}.{column}")
            if cell.get("status") not in M13_2_CELL_STATUSES:
                raise ValueError(f"row {row_id} column {column} has invalid status")
            if not str(cell.get("summary", "")).strip():
                raise ValueError(f"row {row_id} column {column} lacks summary")
            evidence = cell.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                raise ValueError(f"row {row_id} column {column} lacks evidence")
            unknown = set(evidence) - set(sources)
            if unknown:
                raise ValueError(f"row {row_id} column {column} cites unknown sources: {sorted(unknown)}")

    missing = M13_2_REQUIRED_FEATURE_CLASSES - covered_classes
    if missing:
        raise ValueError(f"M13.2 misses milestone feature classes: {sorted(missing)}")

    summary = _mapping(data.get("summary"), "summary")
    if summary.get("row_count") != len(rows):
        raise ValueError(f"summary row_count={summary.get('row_count')} but actual={len(rows)}")
    if summary.get("minimum_milestone_feature_classes_covered") != len(M13_2_REQUIRED_FEATURE_CLASSES):
        raise ValueError("summary feature-class count is inconsistent")
    grouped = {
        "yes": set(summary.get("common_subset_yes", [])),
        "conditional": set(summary.get("common_subset_conditional", [])),
        "no": set(summary.get("common_subset_no", [])),
    }
    if set().union(*grouped.values()) != row_ids:
        raise ValueError("summary common-subset lists do not cover every row exactly")
    if sum(len(group) for group in grouped.values()) != len(row_ids):
        raise ValueError("summary common-subset lists contain duplicate row IDs")
    for row in rows:
        rid = row["id"]
        expected_group = row["common_subset_candidate"]
        if rid not in grouped[expected_group]:
            raise ValueError(f"row {rid} is in the wrong common-subset summary group")


def _source_label(source_id: str, source: Mapping[str, Any]) -> str:
    if "doi" in source:
        return f"{source_id}: DOI {source['doi']}"
    return f"{source_id}: `{source.get('repository', '')}@{source.get('commit', '')}` `{source.get('path', '')}`"


def render_feature_crosswalk_markdown(data: Mapping[str, Any]) -> str:
    validate_feature_crosswalk(data)
    sources = _mapping(data["source_registry"], "source_registry")
    rows = data["rows"]
    out: list[str] = []
    out += [
        "# M13.2 — Four-way Architectural Feature Crosswalk",
        "",
        "**Status:** Complete crosswalk candidate; M13.2 only. No A–H discrepancy adjudication is performed here.",
        "",
        "This document compares four deliberately separate evidence columns: **published Loihi information**, **Brian2Loihi 0.5.2**, **the M12-validated project digital twin**, and **Catalyst N1 at the M13.1 pin**. Agreement is evidence of a shared interpretation, not proof of undocumented Intel microarchitecture. Architectural differences are preserved rather than forced into equality.",
        "",
        "The machine-readable authority for this document is `references/m13_2_feature_crosswalk.json`. M13.3 may define transforms only after this matrix is reviewed; M13.4 may classify observed differences only after directed probes exist.",
        "",
        "## Frozen reference boundary",
        "",
        f"- Project computational baseline: `{data['project_baseline_commit']}` (M12 complete)",
        f"- M13.1 merge: `{data['m13_1_merge_commit']}`",
        f"- Brian2Loihi: `{data['brian2loihi_commit']}` / package 0.5.2",
        f"- Catalyst N1: `{data['catalyst_commit']}` / `v2.3-paper` = `n1-final`",
        "",
        "## Relationship vocabulary",
        "",
    ]
    for relation in data["relationship_vocabulary"]:
        out.append(f"- `{relation}`")
    out += [
        "",
        "These are **comparability labels**, not the M13 A–H discrepancy classes. In particular, a row marked `similar but architecturally different` is not a Class-C finding until a later directed comparison establishes a concrete discrepancy.",
        "",
        "## Crosswalk summary",
        "",
        "| ID | Feature | Published Loihi | Brian2Loihi | Project | Catalyst N1 | Relationship | Common subset? |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        cells = []
        for column in M13_2_COLUMNS:
            cell = row[column]
            refs = ", ".join(f"`{ref}`" for ref in cell["evidence"])
            cells.append(f"**{cell['status']}** — {cell['summary']} ({refs})")
        out.append(
            "| {id} | {feature} | {loihi} | {brian} | {project} | {catalyst} | {relation} | {common} |".format(
                id=f"`{row['id']}`",
                feature=str(row["feature"]).replace("|", "\\|"),
                loihi=cells[0].replace("|", "\\|"),
                brian=cells[1].replace("|", "\\|"),
                project=cells[2].replace("|", "\\|"),
                catalyst=cells[3].replace("|", "\\|"),
                relation=f"`{row['overall_relationship']}`",
                common=f"`{row['common_subset_candidate']}`",
            )
        )

    out += ["", "## Major findings before normalization", ""]
    for finding in data["summary"]["major_crosswalk_findings"]:
        out.append(f"- {finding}")

    out += [
        "",
        "## M13.3 handoff by feature",
        "",
        "The following actions are intentionally phrased as **normalization questions**, not corrections to any implementation:",
        "",
    ]
    for row in rows:
        out.append(f"- **{row['id']}** — {row['m13_3_action']}")

    out += [
        "",
        "## Source registry",
        "",
        "Every crosswalk cell cites one or more stable source IDs below. Repository sources are commit-pinned; published sources use DOI identity. Source-code readings are labeled as implementation inference in the JSON rather than silently promoted to published architectural fact.",
        "",
    ]
    for source_id, source_value in sources.items():
        source = _mapping(source_value, source_id)
        out.append(f"### `{source_id}`")
        out.append("")
        out.append(f"- Identity: {_source_label(source_id, source)}")
        out.append(f"- Evidence type: `{source['evidence_type']}`")
        if source.get("locator"):
            out.append(f"- Locator: {source['locator']}")
        out.append(f"- Role: {source['role']}")
        out.append("")

    out += [
        "## Scope conclusions from M13.2",
        "",
        "The four-way common subset is narrower than any one implementation. Point-neuron LIF behavior, threshold/reset/refractory behavior, static signed synaptic drive, sparse fan-in/fan-out, and synchronous multi-tick recurrence are plausible common comparison targets, but several require explicit transforms. The project deliberately does not claim Loihi/Catalyst parity for dendritic trees, programmable delays, online learning, multicore NoC, management processors, or asynchronous quiescence execution.",
        "",
        "Catalyst must not be treated as one undifferentiated reference model: the pinned CPU simulator and RTL expose different update/configuration surfaces, and the RTL itself contains both a simple subtractive-leak path and an optional CUBA path. M13.3 must therefore name the exact Catalyst boundary used by each normalized behavior.",
        "",
        "The strongest semantic questions handed to M13.3/M13.4 are the current/voltage update ordering, strict `>` versus Catalyst `>=` threshold comparison, refractory-count convention, native weight encoding transforms, and what event-order information can be compared without inventing a global ordering contract.",
        "",
        "## M13.2 pass boundary",
        "",
        "M13.2 is ready to close when this generated document and its machine-readable source agree, all 15 milestone feature classes are present, every one of the four columns is source-backed in every row, and the full project regression suite remains green. No behavioral differential result is required by M13.2 itself.",
        "",
    ]
    return "\n".join(out)
