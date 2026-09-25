from __future__ import annotations

import argparse
import json
from pathlib import Path

from mnist_app.catalyst_matched import (
    RESULT_SCHEMA,
    catalyst_feasibility_audit,
    run_catalyst_matched_case,
    summarize_suite,
    write_json,
)
from mnist_app.matched_bundle import (
    iter_matched_request_shards,
    read_matched_request_bundle,
)
from mnist_app.matched_reference import load_frozen_matched_workload, semantic_audit_payload


def _iter_cases(bundle: Path | None, shard_manifest: Path | None):
    if bundle is not None:
        yield from read_matched_request_bundle(bundle)
        return
    assert shard_manifest is not None
    for shard in iter_matched_request_shards(shard_manifest):
        yield from shard


def _case_count(bundle: Path | None, shard_manifest: Path | None) -> int:
    source = bundle if bundle is not None else shard_manifest
    assert source is not None
    payload = json.loads(source.read_text(encoding="utf-8"))
    return int(payload["case_count"])


def _load_resumed_result(path: Path, expected_index: int) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != RESULT_SCHEMA:
        raise RuntimeError(f"resume result has unexpected schema: {path}")
    if int(payload.get("mnist_test_index", -1)) != expected_index:
        raise RuntimeError(f"resume result index mismatch: {path}")
    if payload.get("profile") != "native-sparse":
        raise RuntimeError(f"resume result profile mismatch: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run frozen native-sparse MNIST through pinned Catalyst N1 CPU reference paths."
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--bundle",
        type=Path,
        help="Single matched request bundle. Omit with --audit-only.",
    )
    source.add_argument(
        "--shard-manifest",
        type=Path,
        help="Sharded request manifest for large scopes such as the full 10,000-image test.",
    )
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1,
        help="Print routine case progress every N completed cases.",
    )
    parser.add_argument(
        "--print-spike-disagreements",
        action="store_true",
        help="Also print every spike-vector-only project/Catalyst disagreement.",
    )
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
    if not args.audit_only and args.bundle is None and args.shard_manifest is None:
        parser.error("--bundle or --shard-manifest is required unless --audit-only is selected")
    if args.progress_every <= 0:
        parser.error("--progress-every must be positive")

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

    total = _case_count(args.bundle, args.shard_manifest)
    results: list[dict[str, object]] = []
    for position, case in enumerate(
        _iter_cases(args.bundle, args.shard_manifest),
        start=1,
    ):
        path = args.output_dir / f"index{case.mnist_test_index:05d}.json"
        resumed = args.resume and path.exists()
        if resumed:
            result = _load_resumed_result(path, case.mnist_test_index)
        else:
            result = run_catalyst_matched_case(workload, case)
            write_json(result, path)
        results.append(result)

        graph = result["graph_preserving"]
        direct = result["delivered_drive"]
        internal = result["catalyst_internal_control"]
        critical = (
            not bool(result["passed_transport_consistency"])
            or not bool(graph["prediction_agreement_with_project"])
        )
        spike_only = not bool(graph["spike_vector_agreement_with_project"])
        should_print = (
            position == total
            or position % args.progress_every == 0
            or critical
            or (args.print_spike_disagreements and spike_only)
        )
        if should_print:
            print(
                f"MNIST-12 progress={position}/{total} index={case.mnist_test_index} "
                f"label={case.label} project={result['project_prediction']} graph={graph['prediction']} "
                f"direct={direct['prediction']} graph_trace_mismatches="
                f"{graph['voltage_spike_trace']['mismatch_count']} direct_trace_mismatches="
                f"{direct['voltage_spike_trace']['mismatch_count']} catalyst_internal_trace_mismatches="
                f"{internal['voltage_spike_trace']['mismatch_count']} max_abs_direct_current="
                f"{direct['metadata']['max_abs_delivered_current']} spike_vector_agreement="
                f"{graph['spike_vector_agreement_with_project']} transport_consistent="
                f"{result['passed_transport_consistency']} source={'resume' if resumed else 'run'}"
            )
            if critical and graph["voltage_spike_trace"]["first_mismatch"] is not None:
                print(f"  graph_first_mismatch={graph['voltage_spike_trace']['first_mismatch']}")

    if len(results) != total:
        raise RuntimeError(f"matched request source yielded {len(results)} cases; expected {total}")
    suite = summarize_suite(results)
    suite_path = args.output_dir / "suite.json"
    write_json(suite, suite_path)
    print(
        f"MNIST-12 suite: cases={suite['case_count']} "
        f"transport_consistent={suite['transport_consistent_cases']} "
        f"graph_prediction_agreement={suite['graph_prediction_agreement_cases']} "
        f"graph_spike_vector_agreement={suite['graph_spike_vector_agreement_cases']} "
        f"direct_prediction_agreement={suite['delivered_drive_prediction_agreement_cases']}"
    )
    print(f"suite: {suite_path}")
    return 0 if suite["transport_consistent_cases"] == suite["case_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
