from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from mnist_app.brian2loihi_matched import (
    RESULT_SCHEMA,
    run_brian2loihi_matched_case,
    summarize_suite,
    write_case_result,
)
from mnist_app.matched_bundle import (
    iter_matched_request_shards,
    read_matched_request_bundle,
)
from mnist_app.matched_reference import (
    load_frozen_matched_workload,
    semantic_audit_payload,
)


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
        description="Run the frozen native-sparse MNIST workload against pinned Brian2Loihi."
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
        help="Print routine case progress every N completed cases; mismatches always print.",
    )
    parser.add_argument(
        "--frozen-root",
        type=Path,
        default=Path("applications/mnist/frozen/mnist-v1"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("applications/mnist/build/mnist-11/brian2loihi"),
    )
    args = parser.parse_args()
    if not args.audit_only and args.bundle is None and args.shard_manifest is None:
        parser.error("--bundle or --shard-manifest is required unless --audit-only is selected")
    if args.progress_every <= 0:
        parser.error("--progress-every must be positive")

    workload = load_frozen_matched_workload(args.frozen_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    audit_path = args.output_dir / "semantic_audit.json"
    audit_path.write_text(
        json.dumps(semantic_audit_payload(workload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "MNIST-11 semantic preflight: profile=native-sparse neurons=10 axons=784 "
        f"synapses={len(workload.synapses)} threshold={workload.configs[0].threshold} "
        f"sat24_bound={workload.conservative_abs_voltage_bound:.1f} audit={audit_path}"
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
            result = run_brian2loihi_matched_case(workload, case)
            write_case_result(result, path)
        results.append(result)

        should_print = (
            position == total
            or position % args.progress_every == 0
            or not bool(result["passed"])
        )
        if should_print:
            trace = result["trace_comparison"]
            print(
                f"MNIST-11 progress={position}/{total} index={case.mnist_test_index} "
                f"label={case.label} project={result['project_prediction']} "
                f"brian={result['brian2loihi_prediction']} "
                f"trace_mismatches={trace['mismatch_count']} "
                f"weight_mismatches={result['effective_weight_mismatch_count']} "
                f"passed={result['passed']} source={'resume' if resumed else 'run'}"
            )

    if len(results) != total:
        raise RuntimeError(f"matched request source yielded {len(results)} cases; expected {total}")
    suite = summarize_suite(results)
    suite_path = args.output_dir / "suite.json"
    suite_path.write_text(json.dumps(suite, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"MNIST-11 suite: cases={suite['case_count']} passed={suite['passed_cases']} "
        f"prediction_agreement={suite['prediction_agreement_cases']} "
        f"spike_vector_agreement={suite['spike_count_vector_agreement_cases']} "
        f"exact_trace={suite['exact_trace_agreement_cases']} all_passed={suite['all_passed']}"
    )
    print(f"suite: {suite_path}")
    return 0 if suite["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
