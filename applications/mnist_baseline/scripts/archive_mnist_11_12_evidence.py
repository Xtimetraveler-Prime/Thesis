from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from mnist_app.matched_summary import write_matched_summary


SCHEMA = "neuromorphic-twin-mnist-11-12-evidence-archive-v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _indices(suite: dict[str, object]) -> tuple[int, ...]:
    return tuple(int(case["mnist_test_index"]) for case in suite["cases"])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and archive compact MNIST-11/12 matched-reference evidence."
    )
    parser.add_argument("--scope", choices=("anchor", "corpus", "full"), required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument(
        "--brian-dir",
        type=Path,
        default=Path("applications/mnist/build/mnist-11/brian2loihi"),
    )
    parser.add_argument(
        "--catalyst-dir",
        type=Path,
        default=Path("applications/mnist/build/mnist-12/catalyst"),
    )
    parser.add_argument(
        "--accepted-validation",
        type=Path,
        default=Path("applications/mnist/frozen/mnist-v1/accepted_software_validation.json"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("applications/mnist/evidence/mnist-11-12"),
    )
    args = parser.parse_args()

    bundle = _read(args.bundle)
    brian_suite = _read(args.brian_dir / "suite.json")
    catalyst_suite = _read(args.catalyst_dir / "suite.json")
    bundle_indices = tuple(int(case["mnist_test_index"]) for case in bundle["cases"])
    brian_indices = _indices(brian_suite)
    catalyst_indices = _indices(catalyst_suite)
    if bundle_indices != brian_indices or bundle_indices != catalyst_indices:
        raise RuntimeError(
            "bundle/Brian/Catalyst index scopes differ; refusing to archive mixed evidence"
        )
    if int(bundle["case_count"]) != len(bundle_indices):
        raise RuntimeError("bundle case count is inconsistent")
    if int(brian_suite["case_count"]) != len(bundle_indices):
        raise RuntimeError("Brian suite case count is inconsistent")
    if int(catalyst_suite["case_count"]) != len(bundle_indices):
        raise RuntimeError("Catalyst suite case count is inconsistent")
    if int(catalyst_suite["transport_consistent_cases"]) != len(bundle_indices):
        raise RuntimeError("Catalyst transport consistency is not complete; archive rejected")

    expected_counts = {"anchor": 2, "corpus": 30, "full": 10_000}
    if len(bundle_indices) != expected_counts[args.scope]:
        raise RuntimeError(
            f"scope {args.scope!r} requires {expected_counts[args.scope]} cases; got {len(bundle_indices)}"
        )

    target = args.output_root / f"matched-{args.scope}-v1"
    if target.exists():
        shutil.rmtree(target)
    (target / "brian2loihi").mkdir(parents=True)
    (target / "catalyst").mkdir(parents=True)

    shutil.copy2(args.bundle, target / "request_bundle.json")
    shutil.copy2(args.brian_dir / "suite.json", target / "brian2loihi" / "suite.json")
    brian_audit = args.brian_dir / "semantic_audit.json"
    if brian_audit.exists():
        shutil.copy2(brian_audit, target / "brian2loihi" / "semantic_audit.json")

    shutil.copy2(args.catalyst_dir / "suite.json", target / "catalyst" / "suite.json")
    for optional_name in ("semantic_audit.json", "feasibility_audit.json", "divergence_summary.json"):
        source = args.catalyst_dir / optional_name
        if source.exists():
            shutil.copy2(source, target / "catalyst" / optional_name)

    for index in bundle_indices:
        name = f"index{index:05d}.json"
        brian_case = args.brian_dir / name
        catalyst_case = args.catalyst_dir / name
        if not brian_case.exists() or not catalyst_case.exists():
            raise RuntimeError(f"missing matched case evidence for MNIST index {index}")
        shutil.copy2(brian_case, target / "brian2loihi" / name)
        shutil.copy2(catalyst_case, target / "catalyst" / name)

    summary_path = target / "comparison_summary.json"
    write_matched_summary(
        args.accepted_validation,
        target / "brian2loihi" / "suite.json",
        target / "catalyst" / "suite.json",
        summary_path,
    )

    artifacts = []
    for path in sorted(p for p in target.rglob("*") if p.is_file() and p.name != "manifest.json"):
        artifacts.append(
            {
                "path": path.relative_to(target).as_posix(),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
        )

    manifest = {
        "schema": SCHEMA,
        "scope": args.scope,
        "case_count": len(bundle_indices),
        "mnist_test_indices": list(bundle_indices),
        "brian_all_passed": bool(brian_suite["all_passed"]),
        "brian_prediction_agreement_cases": int(brian_suite["prediction_agreement_cases"]),
        "brian_exact_trace_agreement_cases": int(brian_suite["exact_trace_agreement_cases"]),
        "catalyst_transport_consistent_cases": int(catalyst_suite["transport_consistent_cases"]),
        "catalyst_graph_prediction_agreement_cases": int(
            catalyst_suite["graph_prediction_agreement_cases"]
        ),
        "artifacts": artifacts,
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        f"MNIST-11/12 evidence archived: scope={args.scope} cases={len(bundle_indices)} "
        f"brian_all_passed={manifest['brian_all_passed']} "
        f"catalyst_transport_consistent={manifest['catalyst_transport_consistent_cases']} "
        f"output={target}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
