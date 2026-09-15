from __future__ import annotations

import argparse
import json
from pathlib import Path

from mnist_app.catalyst_matched import (
    catalyst_feasibility_audit,
    run_catalyst_matched_case,
    summarize_suite,
    write_json,
)
from mnist_app.matched_bundle import read_matched_request_bundle
from mnist_app.matched_reference import load_frozen_matched_workload, semantic_audit_payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run frozen native-sparse MNIST through pinned Catalyst N1 CPU reference paths."
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        help="Matched request bundle. Omit with --audit-only.",
    )
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument(
        "--frozen-root",
        type=Path,
        default=Path("applications/mnist/frozen/mnist-v1"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("applications/mnist/build/mnist-12/catalyst"),
    )
    args = parser.parse_args()
    if not args.audit_only and args.bundle is None:
        parser.error("--bundle is required unless --audit-only is selected")

    workload = load_frozen_matched_workload(args.frozen_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    audit = catalyst_feasibility_audit(workload)
    write_json(audit, args.output_dir / "feasibility_audit.json")
    write_json(semantic_audit_payload(workload), args.output_dir / "semantic_audit.json")
    print(
        "MNIST-12 feasibility: "
        f"generic_cpu_graph_fit={audit['generic_cpu_reference']['graph_preserving_single_core_fit']} "
        f"k26_graph_fit={audit['pinned_k26_wrapper']['graph_preserving_fit']} "
        f"physical_source_supported={audit['pinned_k26_wrapper']['physical_programming_source_supported']}"
    )
    if args.audit_only:
        return 0

    cases = read_matched_request_bundle(args.bundle)
    results: list[dict[str, object]] = []
    for case in cases:
        result = run_catalyst_matched_case(workload, case)
        results.append(result)
        write_json(result, args.output_dir / f"index{case.mnist_test_index:05d}.json")
        graph = result["graph_preserving"]
        direct = result["delivered_drive"]
        print(
            f"MNIST-12 case index={case.mnist_test_index} label={case.label} "
            f"project={result['project_prediction']} graph={graph['prediction']} "
            f"direct={direct['prediction']} graph_trace_mismatches="
            f"{graph['voltage_spike_trace']['mismatch_count']} direct_trace_mismatches="
            f"{direct['voltage_spike_trace']['mismatch_count']} transport_consistent="
            f"{result['passed_transport_consistency']}"
        )

    suite = summarize_suite(results)
    suite_path = args.output_dir / "suite.json"
    write_json(suite, suite_path)
    print(
        f"MNIST-12 suite: cases={suite['case_count']} "
        f"transport_consistent={suite['transport_consistent_cases']} "
        f"graph_prediction_agreement={suite['graph_prediction_agreement_cases']} "
        f"direct_prediction_agreement={suite['delivered_drive_prediction_agreement_cases']}"
    )
    print(f"suite: {suite_path}")
    # Project-vs-Catalyst disagreement is evidence, not a harness failure.  Exit
    # nonzero only when the two independently constructed Catalyst transport
    # views disagree, which indicates the matched adapter itself needs review.
    return 0 if suite["transport_consistent_cases"] == suite["case_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
