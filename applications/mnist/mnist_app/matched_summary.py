"""Assemble matched MNIST external-reference results without mixing scopes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping


SUMMARY_SCHEMA = "neuromorphic-twin-mnist-matched-comparison-summary-v1"


def _read(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _case_indices(suite: Mapping[str, object]) -> tuple[int, ...]:
    return tuple(int(case["mnist_test_index"]) for case in suite["cases"])


def build_matched_summary(
    accepted_validation_path: str | Path,
    brian_suite_path: str | Path,
    catalyst_suite_path: str | Path,
) -> dict[str, object]:
    accepted = _read(accepted_validation_path)
    brian = _read(brian_suite_path)
    catalyst = _read(catalyst_suite_path)
    if brian.get("schema") != "neuromorphic-twin-mnist-11-brian2loihi-suite-v1":
        raise ValueError("unexpected MNIST-11 suite schema")
    if catalyst.get("schema") != "neuromorphic-twin-mnist-12-catalyst-suite-v1":
        raise ValueError("unexpected MNIST-12 suite schema")
    brian_indices = _case_indices(brian)
    catalyst_indices = _case_indices(catalyst)
    if brian_indices != catalyst_indices:
        raise ValueError(
            "refusing to combine Brian/Catalyst suites with different MNIST index/order scopes"
        )
    case_count = len(brian_indices)
    if case_count == 0:
        raise ValueError("matched comparison requires at least one case")

    brian_cases = list(brian["cases"])
    catalyst_cases = list(catalyst["cases"])
    for brian_case, catalyst_case in zip(brian_cases, catalyst_cases, strict=True):
        if int(brian_case["label"]) != int(catalyst_case["label"]):
            raise ValueError("Brian/Catalyst labels differ on the matched scope")
        if int(brian_case["project_prediction"]) != int(catalyst_case["project_prediction"]):
            raise ValueError("Brian/Catalyst project predictions differ on the matched scope")

    catalyst_project_correct = sum(
        int(case["project_prediction"]) == int(case["label"])
        for case in catalyst_cases
    )
    catalyst_graph_correct = sum(
        int(case["graph_prediction"]) == int(case["label"])
        for case in catalyst_cases
    )
    catalyst_direct_correct = sum(
        int(case["delivered_drive_prediction"]) == int(case["label"])
        for case in catalyst_cases
    )
    native = accepted["profiles"]["native-sparse"]["summary"]

    return {
        "schema": SUMMARY_SCHEMA,
        "profile": "native-sparse",
        "matched_scope": {
            "case_count": case_count,
            "mnist_test_indices": list(brian_indices),
        },
        "project_full_test_context": {
            "corpus": accepted["corpus"],
            "images": int(native["images"]),
            "golden_accuracy": float(native["golden_accuracy"]),
            "stored_synapses": int(native["deployment_stored_synapses"]),
            "evidence_label": "PROJECT FULL-TEST GOLDEN CONTEXT",
        },
        "brian2loihi_matched_scope": {
            "case_count": case_count,
            "prediction_agreement_cases": int(brian["prediction_agreement_cases"]),
            "spike_count_vector_agreement_cases": int(
                brian["spike_count_vector_agreement_cases"]
            ),
            "exact_trace_agreement_cases": int(brian["exact_trace_agreement_cases"]),
            "project_accuracy_on_scope": float(brian["project_accuracy_on_scope"]),
            "brian2loihi_accuracy_on_scope": float(
                brian["brian2loihi_accuracy_on_scope"]
            ),
            "evidence_label": "MATCHED GRAPH + MATCHED/EXPLICITLY-EQUIVALENT DYNAMICS",
        },
        "catalyst_matched_scope": {
            "case_count": case_count,
            "transport_consistent_cases": int(catalyst["transport_consistent_cases"]),
            "graph_prediction_agreement_cases": int(
                catalyst["graph_prediction_agreement_cases"]
            ),
            "graph_spike_vector_agreement_cases": int(
                catalyst["graph_spike_vector_agreement_cases"]
            ),
            "delivered_drive_prediction_agreement_cases": int(
                catalyst["delivered_drive_prediction_agreement_cases"]
            ),
            "delivered_drive_spike_vector_agreement_cases": int(
                catalyst["delivered_drive_spike_vector_agreement_cases"]
            ),
            "project_accuracy_on_scope": catalyst_project_correct / case_count,
            "graph_accuracy_on_scope": catalyst_graph_correct / case_count,
            "delivered_drive_accuracy_on_scope": catalyst_direct_correct / case_count,
            "evidence_label": "MATCHED EFFECTIVE GRAPH / DELIVERED DRIVE + TRANSLATED DYNAMICS",
        },
        "hardware_boundary": {
            "fpga_v1": "physical K26 application behavior/timing already accepted in MNIST-07..10",
            "brian2loihi": "software emulator only; no hardware latency/energy claim",
            "catalyst": "generic CPU matched experiment supported; pinned M13.5 K26 graph-preserving MNIST blocked by 512-neuron wrapper and missing board integration",
            "published_loihi": "retain MNIST-10 NxTF row as UNMATCHED LITERATURE REFERENCE only",
        },
    }


def write_matched_summary(
    accepted_validation_path: str | Path,
    brian_suite_path: str | Path,
    catalyst_suite_path: str | Path,
    output_path: str | Path,
) -> Path:
    payload = build_matched_summary(
        accepted_validation_path, brian_suite_path, catalyst_suite_path
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target
