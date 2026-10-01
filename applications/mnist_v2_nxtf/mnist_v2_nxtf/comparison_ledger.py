"""P08.5.1 machine-readable NxTF/project comparison ledger.

The ledger is deliberately classification-first: every quantity is assigned a
comparison boundary before P08.5 writes thesis-facing conclusions.  This keeps
published native-Loihi measurements, source-bounded reconstruction, and
project-specific FPGA measurements from being collapsed into one misleading
performance table.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

LEDGER_SCHEMA = "p08-nxtf-comparison-ledger-v1"
LEDGER_STATUS = "P08_5_1_COMPARISON_LEDGER_REVIEW_PENDING"
LEDGER_JSON = "p08_5_comparison_ledger.json"
LEDGER_MARKDOWN = "p08_5_comparison_table.md"

DIRECTLY_COMPARABLE = "DIRECTLY_COMPARABLE"
COMPARABLE_WITH_RECONSTRUCTION_CAVEAT = "COMPARABLE_WITH_RECONSTRUCTION_CAVEAT"
CONTEXT_ONLY = "CONTEXT_ONLY"
PROJECT_SPECIFIC = "PROJECT_SPECIFIC"
NOT_COMPARABLE = "NOT_COMPARABLE"

COMPARISON_CLASSES = {
    DIRECTLY_COMPARABLE,
    COMPARABLE_WITH_RECONSTRUCTION_CAVEAT,
    CONTEXT_ONLY,
    PROJECT_SPECIFIC,
    NOT_COMPARABLE,
}

SOURCED_EXACT = "SOURCED_EXACT"
SOURCED_APPROXIMATE = "SOURCED_APPROXIMATE"
SOURCED_STYLE_OR_RANGE = "SOURCED_STYLE_OR_RANGE"
PROJECT_MEASURED = "PROJECT_MEASURED"
PROJECT_RECONSTRUCTION = "PROJECT_RECONSTRUCTION"
DERIVED_FROM_ACCEPTED_MEASUREMENT = "DERIVED_FROM_ACCEPTED_MEASUREMENT"
NOT_AVAILABLE = "NOT_AVAILABLE"

FIDELITY_CLASSES = {
    SOURCED_EXACT,
    SOURCED_APPROXIMATE,
    SOURCED_STYLE_OR_RANGE,
    PROJECT_MEASURED,
    PROJECT_RECONSTRUCTION,
    DERIVED_FROM_ACCEPTED_MEASUREMENT,
    NOT_AVAILABLE,
}

ACCEPTED_IDENTITIES = {
    "ann_semantic_weights": "e5c07133b8d534d29596cbde9d637db695942dfb224a82c2533f59a17f1c74ce",
    "parameters": "9169939821201e4764813dbb17e254b796cd952e4707315eb61ecd0e0082926e",
    "network": "6e47dc0c37d2f05828f0a0231406c7df8e4bf83652300fde0df1a0b8f9d83f13",
    "compiled": "5dc7c9af692ca375283ede186b81d135bd1c76708b114cc64e3f99c085cd856b",
    "p08_4_2_trace": "a81844443b6e5f6c278167a4aafc46dcfd74f7df5498179312b1fc39edba09d6",
    "bitstream_sha256": "3538b8f7a23dbd923c77471cb533cd844af548c0d50d7679cd40844f465e8f83",
    "probes_sha256": "e32376f31486b96b070b0b12c6131d7bed067e0dd05e0461b029baf3eeea6936",
}


def _side(value: Any, *, fidelity: str, evidence: str, qualifier: str | None = None) -> dict[str, Any]:
    return {
        "value": value,
        "fidelity": fidelity,
        "evidence": evidence,
        "qualifier": qualifier,
    }


def _row(
    metric_id: str,
    label: str,
    unit: str,
    *,
    nxtf: dict[str, Any],
    project: dict[str, Any],
    comparison_class: str,
    allow_numeric_delta: bool,
    note: str,
) -> dict[str, Any]:
    return {
        "id": metric_id,
        "label": label,
        "unit": unit,
        "nxtf": nxtf,
        "project": project,
        "comparison_class": comparison_class,
        "allow_numeric_delta": allow_numeric_delta,
        "note": note,
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        "nxtf_paper": {
            "kind": "primary_reference",
            "citation": (
                "B. Rueckauer et al., 'NxTF: An API and Compiler for Deep Spiking "
                "Neural Networks on Intel Loihi,' ACM JETC 18(3), 2022, "
                "doi:10.1145/3501770, arXiv:2101.04261."
            ),
            "project_record": "Loihi_Digital_Twin/v2/docs/P08_MNIST_COMPARISON_CONTRACT.md",
        },
        "nxtf_source_audit": {
            "kind": "project_source_audit",
            "citation": "Project audit of paper, public NxTF tutorial, and SNN-Toolbox evidence.",
            "project_record": "Loihi_Digital_Twin/v2/docs/P08_NXTF_SOURCE_AUDIT.md",
        },
        "p08_1_reconstruction": {
            "kind": "accepted_project_reconstruction",
            "citation": "Accepted P08.1 source-bounded topology/resource reconstruction.",
            "project_record": "Loihi_Digital_Twin/v2/docs/P08_NXTF_RECONSTRUCTION.md",
        },
        "p08_2_acceptance": {
            "kind": "accepted_project_measurement",
            "citation": "Accepted P08.2 mapping/paging boundary.",
            "project_record": "Loihi_Digital_Twin/v2/docs/P08_2_ACCEPTANCE.md",
        },
        "p08_3_acceptance": {
            "kind": "accepted_project_measurement",
            "citation": "Accepted P08.3 training and source-recovered conversion result.",
            "project_record": "Loihi_Digital_Twin/v2/docs/P08_3_ACCEPTANCE.md",
        },
        "p08_4_acceptance": {
            "kind": "accepted_project_measurement",
            "citation": "Accepted P08.4 official-test and K26 conformance result.",
            "project_record": "Loihi_Digital_Twin/v2/docs/P08_4_ACCEPTANCE.md",
        },
        "p08_4_3b_acceptance": {
            "kind": "accepted_project_measurement",
            "citation": "Accepted representative physical MNIST deep-dispatch result.",
            "project_record": "Loihi_Digital_Twin/v2/docs/P08_4_3B_ACCEPTANCE.md",
        },
    }


def _rows() -> list[dict[str, Any]]:
    na_nxtf = lambda evidence="nxtf_paper": _side(None, fidelity=NOT_AVAILABLE, evidence=evidence)
    na_project = lambda evidence="p08_4_acceptance": _side(None, fidelity=NOT_AVAILABLE, evidence=evidence)

    return [
        _row(
            "dataset",
            "Dataset",
            "name",
            nxtf=_side("MNIST 28x28", fidelity=SOURCED_EXACT, evidence="nxtf_paper"),
            project=_side("MNIST 28x28", fidelity=PROJECT_MEASURED, evidence="p08_4_acceptance"),
            comparison_class=DIRECTLY_COMPARABLE,
            allow_numeric_delta=False,
            note="Same benchmark dataset and ten-class digit-recognition task.",
        ),
        _row(
            "class_count",
            "Output classes",
            "classes",
            nxtf=_side(10, fidelity=SOURCED_EXACT, evidence="nxtf_paper"),
            project=_side(10, fidelity=PROJECT_RECONSTRUCTION, evidence="p08_1_reconstruction"),
            comparison_class=DIRECTLY_COMPARABLE,
            allow_numeric_delta=True,
            note="Same ten MNIST classes.",
        ),
        _row(
            "network_family",
            "Network family",
            "description",
            nxtf=_side("four-layer CNN", fidelity=SOURCED_EXACT, evidence="nxtf_paper"),
            project=_side("four-layer all-convolutional CNN", fidelity=PROJECT_RECONSTRUCTION, evidence="p08_1_reconstruction"),
            comparison_class=COMPARABLE_WITH_RECONSTRUCTION_CAVEAT,
            allow_numeric_delta=False,
            note="Layer family matches; exact unpublished paper dimensions were not recovered.",
        ),
        _row(
            "algorithmic_timesteps",
            "Primary inference horizon",
            "timesteps/sample",
            nxtf=_side(100, fidelity=SOURCED_EXACT, evidence="nxtf_paper"),
            project=_side(100, fidelity=PROJECT_MEASURED, evidence="p08_4_acceptance"),
            comparison_class=DIRECTLY_COMPARABLE,
            allow_numeric_delta=True,
            note="Same algorithmic horizon; raw FPGA clock cycles remain a separate quantity.",
        ),
        _row(
            "ann_test_error",
            "ANN official-test classification error",
            "fraction",
            nxtf=_side(0.0074, fidelity=SOURCED_EXACT, evidence="nxtf_paper"),
            project=_side(0.0126, fidelity=PROJECT_MEASURED, evidence="p08_4_acceptance"),
            comparison_class=COMPARABLE_WITH_RECONSTRUCTION_CAVEAT,
            allow_numeric_delta=True,
            note="Same MNIST error metric, but the project topology/checkpoint is a source-bounded reconstruction rather than the unpublished exact paper model.",
        ),
        _row(
            "snn_test_error",
            "Converted-SNN official-test classification error",
            "fraction",
            nxtf=_side(0.0079, fidelity=SOURCED_EXACT, evidence="nxtf_paper"),
            project=_side(0.0176, fidelity=PROJECT_MEASURED, evidence="p08_4_acceptance"),
            comparison_class=COMPARABLE_WITH_RECONSTRUCTION_CAVEAT,
            allow_numeric_delta=True,
            note="Same MNIST error metric at 100 timesteps, with different exact topology/compiler/neuron implementation boundaries.",
        ),
        _row(
            "ann_to_snn_error_increase",
            "ANN-to-SNN error increase",
            "fraction",
            nxtf=_side(0.0005, fidelity=DERIVED_FROM_ACCEPTED_MEASUREMENT, evidence="nxtf_paper", qualifier="0.79% - 0.74%"),
            project=_side(0.0050, fidelity=DERIVED_FROM_ACCEPTED_MEASUREMENT, evidence="p08_4_acceptance", qualifier="1.76% - 1.26%"),
            comparison_class=COMPARABLE_WITH_RECONSTRUCTION_CAVEAT,
            allow_numeric_delta=True,
            note="Useful conversion-loss comparison, but not evidence that conversion alone explains the cross-system accuracy gap.",
        ),
        _row(
            "neuron_count",
            "Neuron/compartment count",
            "neurons",
            nxtf=_side(4000, fidelity=SOURCED_APPROXIMATE, evidence="nxtf_paper", qualifier="paper reports approximately 4k"),
            project=_side(4218, fidelity=PROJECT_RECONSTRUCTION, evidence="p08_1_reconstruction"),
            comparison_class=COMPARABLE_WITH_RECONSTRUCTION_CAVEAT,
            allow_numeric_delta=False,
            note="Scale comparison only because the published value is approximate and the exact paper topology is unrecovered.",
        ),
        _row(
            "trainable_parameters",
            "Trainable parameters",
            "parameters",
            nxtf=_side(7000, fidelity=SOURCED_APPROXIMATE, evidence="nxtf_paper", qualifier="paper reports approximately 7k"),
            project=_side(7006, fidelity=PROJECT_RECONSTRUCTION, evidence="p08_1_reconstruction"),
            comparison_class=COMPARABLE_WITH_RECONSTRUCTION_CAVEAT,
            allow_numeric_delta=False,
            note="Scale comparison only; the paper table value is approximate.",
        ),
        _row(
            "expanded_connections",
            "Expanded/discrete convolutional connections",
            "connections",
            nxtf=_side(341000, fidelity=SOURCED_APPROXIMATE, evidence="nxtf_paper", qualifier="paper reports 341k"),
            project=_side(338880, fidelity=PROJECT_RECONSTRUCTION, evidence="p08_1_reconstruction"),
            comparison_class=COMPARABLE_WITH_RECONSTRUCTION_CAVEAT,
            allow_numeric_delta=False,
            note="Comparable graph-scale quantity, but the paper value is rounded and the exact graph differs.",
        ),
        _row(
            "shared_weight_accounting",
            "Stored/shared convolution parameters",
            "stored entries",
            nxtf=_side(6746, fidelity=SOURCED_EXACT, evidence="nxtf_paper"),
            project=_side(64235, fidelity=PROJECT_MEASURED, evidence="p08_2_acceptance", qualifier="P06 stored shared-parameter accounting"),
            comparison_class=CONTEXT_ONLY,
            allow_numeric_delta=False,
            note="Do not ratio these values: NxTF connection sharing/native Loihi packing and P06 template/accounting semantics are different representations.",
        ),
        _row(
            "mapped_core_count",
            "Mapped neuromorphic core count",
            "cores",
            nxtf=_side(14, fidelity=SOURCED_EXACT, evidence="nxtf_paper", qualifier="Loihi neurocores"),
            project=_side(5, fidelity=PROJECT_MEASURED, evidence="p08_2_acceptance", qualifier="P06 logical cores"),
            comparison_class=CONTEXT_ONLY,
            allow_numeric_delta=False,
            note="The native NxTF compiler and P06 mapper/storage models differ; five project logical cores must not be interpreted as five native Loihi cores.",
        ),
        _row(
            "resident_context_count",
            "Resident FPGA context slots",
            "contexts",
            nxtf=na_nxtf(),
            project=_side(3, fidelity=PROJECT_MEASURED, evidence="p08_4_acceptance"),
            comparison_class=PROJECT_SPECIFIC,
            allow_numeric_delta=False,
            note="Physical K26 residency/cache quantity, not a native-Loihi mapping quantity.",
        ),
        _row(
            "physical_engine_count",
            "Physical FPGA compute engines",
            "engines",
            nxtf=na_nxtf(),
            project=_side(1, fidelity=PROJECT_MEASURED, evidence="p08_4_acceptance"),
            comparison_class=PROJECT_SPECIFIC,
            allow_numeric_delta=False,
            note="FPGA time-multiplexing quantity with no direct NxTF Table-2 counterpart.",
        ),
        _row(
            "representative_forward_page_loads",
            "Representative full-inference forward page loads",
            "loads/sample",
            nxtf=na_nxtf(),
            project=_side(497, fidelity=PROJECT_MEASURED, evidence="p08_4_acceptance", qualifier="official-test index 0, forward service order"),
            comparison_class=PROJECT_SPECIFIC,
            allow_numeric_delta=False,
            note="Implementation-level paging observation for the project deployment.",
        ),
        _row(
            "representative_internal_packet_traffic",
            "Representative internal packet traffic",
            "packets/sample",
            nxtf=na_nxtf(),
            project=_side(17910, fidelity=PROJECT_MEASURED, evidence="p08_4_acceptance", qualifier="official-test index 0"),
            comparison_class=PROJECT_SPECIFIC,
            allow_numeric_delta=False,
            note="Normalized project packet traffic; the paper does not publish an equivalent count.",
        ),
        _row(
            "fpga_pl_clock",
            "Requested K26 programmable-logic clock",
            "MHz",
            nxtf=na_nxtf(),
            project=_side(100.0, fidelity=PROJECT_MEASURED, evidence="p08_4_acceptance"),
            comparison_class=PROJECT_SPECIFIC,
            allow_numeric_delta=False,
            note="Synchronous FPGA implementation clock, not an algorithmic timestep rate or native-Loihi clock comparison.",
        ),
        _row(
            "representative_physical_dispatch_cycles",
            "Representative physical deep-core dispatch",
            "PL cycles/dispatch",
            nxtf=na_nxtf(),
            project=_side(3865, fidelity=PROJECT_MEASURED, evidence="p08_4_3b_acceptance", qualifier="logical core 4 at timestep 99"),
            comparison_class=PROJECT_SPECIFIC,
            allow_numeric_delta=False,
            note="One physical HLS dispatch only; it is not full-sample inference latency.",
        ),
        _row(
            "representative_physical_dispatch_time",
            "Derived representative deep-core dispatch time",
            "microseconds/dispatch",
            nxtf=na_nxtf(),
            project=_side(38.65, fidelity=DERIVED_FROM_ACCEPTED_MEASUREMENT, evidence="p08_4_3b_acceptance", qualifier="3865 cycles / 100 MHz"),
            comparison_class=PROJECT_SPECIFIC,
            allow_numeric_delta=False,
            note="Derived from the accepted single-dispatch observation; explicitly not end-to-end sample latency.",
        ),
        _row(
            "fpga_uram",
            "K26 UltraRAM utilization",
            "URAM288 primitives",
            nxtf=na_nxtf(),
            project=_side(47, fidelity=PROJECT_MEASURED, evidence="p08_4_acceptance"),
            comparison_class=PROJECT_SPECIFIC,
            allow_numeric_delta=False,
            note="FPGA implementation resource, not comparable to Loihi neurocore occupancy.",
        ),
        _row(
            "fpga_setup_slack",
            "K26 routed worst setup slack",
            "ns",
            nxtf=na_nxtf(),
            project=_side(0.734, fidelity=PROJECT_MEASURED, evidence="p08_4_acceptance"),
            comparison_class=PROJECT_SPECIFIC,
            allow_numeric_delta=False,
            note="Timing-closure evidence for the requested 100 MHz FPGA implementation.",
        ),
        _row(
            "native_loihi_energy",
            "Native-Loihi energy per sample",
            "mJ/sample",
            nxtf=_side(0.66, fidelity=SOURCED_EXACT, evidence="nxtf_paper"),
            project=na_project(),
            comparison_class=NOT_COMPARABLE,
            allow_numeric_delta=False,
            note="Published context only. P08 has no equivalent workload-specific K26 physical energy measurement.",
        ),
        _row(
            "native_loihi_latency",
            "Native-Loihi wall-clock latency per sample",
            "ms/sample",
            nxtf=_side(6.65, fidelity=SOURCED_EXACT, evidence="nxtf_paper"),
            project=na_project(),
            comparison_class=NOT_COMPARABLE,
            allow_numeric_delta=False,
            note="Published context only. Debug/JTAG-controlled representative FPGA dispatch timing is not an end-to-end equivalent.",
        ),
        _row(
            "physical_conformance_scope",
            "Physical K26 conformance scope",
            "description",
            nxtf=na_nxtf(),
            project=_side(
                "representative logical-core-4 page replacement and timestep-99 dispatch; exact 618 state/trace words and output evidence",
                fidelity=PROJECT_MEASURED,
                evidence="p08_4_3b_acceptance",
            ),
            comparison_class=PROJECT_SPECIFIC,
            allow_numeric_delta=False,
            note="Full 100-timestep paging is proven by P08.4.2 software conformance, not by an end-to-end JTAG replay.",
        ),
    ]


def _fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_ledger() -> dict[str, Any]:
    ledger: dict[str, Any] = {
        "schema": LEDGER_SCHEMA,
        "status": LEDGER_STATUS,
        "purpose": "classification-first bounded comparison of published NxTF and accepted FPGA-v2 P08 results",
        "accepted_identities": dict(ACCEPTED_IDENTITIES),
        "comparison_classes": sorted(COMPARISON_CLASSES),
        "fidelity_classes": sorted(FIDELITY_CLASSES),
        "sources": _sources(),
        "rows": _rows(),
        "guardrails": {
            "native_loihi_energy_is_direct_fpga_comparison": False,
            "native_loihi_latency_is_direct_fpga_comparison": False,
            "shared_weight_counts_use_same_storage_model": False,
            "mapped_core_counts_use_same_compiler_model": False,
            "representative_dispatch_cycles_are_full_sample_latency": False,
            "full_100_timestep_inference_physically_replayed_over_jtag": False,
            "post_test_model_or_conversion_selection": False,
        },
    }
    validate_ledger(ledger)
    ledger["ledger_fingerprint"] = _fingerprint(ledger)
    return ledger


def validate_ledger(ledger: dict[str, Any]) -> None:
    if ledger.get("schema") != LEDGER_SCHEMA:
        raise ValueError("comparison ledger schema drifted")
    if ledger.get("status") != LEDGER_STATUS:
        raise ValueError("comparison ledger status drifted")
    if ledger.get("accepted_identities") != ACCEPTED_IDENTITIES:
        raise ValueError("accepted P08 identities drifted")

    sources = ledger.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise ValueError("comparison ledger requires a source registry")

    rows = ledger.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("comparison ledger requires rows")
    ids = [row.get("id") for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("comparison ledger metric IDs must be unique")

    for row in rows:
        metric_id = row.get("id")
        comparison_class = row.get("comparison_class")
        if comparison_class not in COMPARISON_CLASSES:
            raise ValueError(f"{metric_id}: unknown comparison class {comparison_class!r}")
        if not isinstance(row.get("allow_numeric_delta"), bool):
            raise ValueError(f"{metric_id}: allow_numeric_delta must be boolean")
        if not row.get("note"):
            raise ValueError(f"{metric_id}: comparison note is required")
        for side_name in ("nxtf", "project"):
            side = row.get(side_name)
            if not isinstance(side, dict):
                raise ValueError(f"{metric_id}: missing {side_name} side")
            if side.get("fidelity") not in FIDELITY_CLASSES:
                raise ValueError(f"{metric_id}: invalid {side_name} fidelity")
            if side.get("evidence") not in sources:
                raise ValueError(f"{metric_id}: unknown {side_name} evidence source")

        if comparison_class in {CONTEXT_ONLY, PROJECT_SPECIFIC, NOT_COMPARABLE} and row["allow_numeric_delta"]:
            raise ValueError(f"{metric_id}: incompatible metric class may not enable numeric delta")
        if comparison_class == NOT_COMPARABLE and row["project"]["value"] is not None:
            raise ValueError(f"{metric_id}: NOT_COMPARABLE row must not invent a project counterpart")
        if comparison_class == PROJECT_SPECIFIC and row["nxtf"]["value"] is not None:
            raise ValueError(f"{metric_id}: PROJECT_SPECIFIC row must not invent an NxTF counterpart")

    by_id = {row["id"]: row for row in rows}
    required_guarded = {
        "native_loihi_energy": NOT_COMPARABLE,
        "native_loihi_latency": NOT_COMPARABLE,
        "shared_weight_accounting": CONTEXT_ONLY,
        "mapped_core_count": CONTEXT_ONLY,
        "representative_physical_dispatch_cycles": PROJECT_SPECIFIC,
    }
    for metric_id, expected_class in required_guarded.items():
        if by_id.get(metric_id, {}).get("comparison_class") != expected_class:
            raise ValueError(f"{metric_id}: comparison guardrail drifted")

    guardrails = ledger.get("guardrails")
    if not isinstance(guardrails, dict) or any(value is not False for value in guardrails.values()):
        raise ValueError("all P08.5.1 overclaim guardrails must remain false")


def _safe_delta(row: dict[str, Any]) -> float | int | None:
    if not row["allow_numeric_delta"]:
        return None
    left = row["nxtf"]["value"]
    right = row["project"]["value"]
    if isinstance(left, bool) or isinstance(right, bool):
        return None
    if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
        return None
    return right - left


def _display_value(side: dict[str, Any]) -> str:
    value = side["value"]
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def render_markdown(ledger: dict[str, Any]) -> str:
    validate_ledger({key: value for key, value in ledger.items() if key != "ledger_fingerprint"})
    lines = [
        "# P08.5 NxTF Comparison Ledger",
        "",
        "Generated from the classification-first P08.5.1 ledger. Numeric deltas appear only where the ledger explicitly permits them; their presence does not remove reconstruction caveats.",
        "",
        "| Metric | NxTF | Project | Unit | Comparison class | Safe delta (project - NxTF) |",
        "|---|---:|---:|---|---|---:|",
    ]
    for row in ledger["rows"]:
        delta = _safe_delta(row)
        delta_text = "—" if delta is None else f"{delta:.6g}"
        lines.append(
            "| "
            + " | ".join(
                [
                    row["label"].replace("|", "\\|"),
                    _display_value(row["nxtf"]).replace("|", "\\|"),
                    _display_value(row["project"]).replace("|", "\\|"),
                    row["unit"].replace("|", "\\|"),
                    row["comparison_class"],
                    delta_text,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- Native-Loihi energy and latency remain published context only; no direct K26 counterpart is claimed.",
            "- NxTF shared-weight count and P06 stored-template count use different representations and are not ratioed.",
            "- NxTF Loihi-neurocore count and P06 logical-core count use different compiler/resource models and are contextual only.",
            "- The 3,865-cycle K26 observation is one representative deep-core dispatch, not end-to-end sample latency.",
            "- Complete 100-timestep paging is proven in P08.4.2 software conformance; P08.4.3b is representative physical dispatch conformance.",
            "- No model or conversion selection follows the official-test results.",
            "",
            f"Ledger fingerprint: `{ledger['ledger_fingerprint']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_ledger(output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    ledger = build_ledger()
    (output / LEDGER_JSON).write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / LEDGER_MARKDOWN).write_text(render_markdown(ledger), encoding="utf-8")
    return ledger


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate and validate the P08.5.1 NxTF comparison ledger")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    ledger = write_ledger(args.output_dir)
    counts = Counter(row["comparison_class"] for row in ledger["rows"])
    print(
        "PASS: P08.5.1 ledger "
        f"rows={len(ledger['rows'])} fingerprint={ledger['ledger_fingerprint']}"
    )
    print(
        "PASS: P08.5.1 classifications "
        + " ".join(f"{name}={counts.get(name, 0)}" for name in sorted(COMPARISON_CLASSES))
    )
    for metric_id in ("ann_test_error", "snn_test_error", "ann_to_snn_error_increase"):
        row = next(row for row in ledger["rows"] if row["id"] == metric_id)
        print(
            "PASS: P08.5.1 safe delta "
            f"metric={metric_id} delta={_safe_delta(row):.6f} class={row['comparison_class']}"
        )
    print(
        "PASS: P08.5.1 guardrails "
        "energy_direct=false latency_direct=false shared_weight_ratio=false "
        "core_count_ratio=false dispatch_is_sample_latency=false full_jtag_replay=false post_test_tuning=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
