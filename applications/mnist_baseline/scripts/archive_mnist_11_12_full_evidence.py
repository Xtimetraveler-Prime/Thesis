from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from mnist_app.matched_bundle import SHARD_MANIFEST_SCHEMA
from mnist_app.matched_summary import write_matched_summary


SCHEMA = "neuromorphic-twin-mnist-11-12-full-evidence-v1"


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
        description="Archive compact 10,000-image MNIST-11/12 matched-reference evidence."
    )
    parser.add_argument("--request-manifest", type=Path, required=True)
    parser.add_argument("--brian-dir", type=Path, required=True)
    parser.add_argument("--catalyst-dir", type=Path, required=True)
    parser.add_argument("--catalyst-divergence", type=Path, required=True)
    parser.add_argument(
        "--accepted-validation",
        type=Path,
        default=Path("applications/mnist/frozen/mnist-v1/accepted_software_validation.json"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("applications/mnist/evidence/mnist-11-12/matched-full-v1"),
    )
    args = parser.parse_args()

    request = _read(args.request_manifest)
    brian_suite = _read(args.brian_dir / "suite.json")
    catalyst_suite = _read(args.catalyst_dir / "suite.json")
    divergence = _read(args.catalyst_divergence)

    if request.get("schema") != SHARD_MANIFEST_SCHEMA:
        raise RuntimeError("full evidence requires the sharded matched-request manifest")
    if int(request.get("case_count", -1)) != 10_000:
        raise RuntimeError("full evidence requires exactly 10,000 request cases")
    expected_indices = tuple(range(10_000))
    brian_indices = _indices(brian_suite)
    catalyst_indices = _indices(catalyst_suite)
    if brian_indices != expected_indices or catalyst_indices != expected_indices:
        raise RuntimeError("full suites must cover MNIST test indices 0..9999 in order")
    if int(brian_suite.get("case_count", -1)) != 10_000:
        raise RuntimeError("Brian full suite case count is not 10,000")
    if int(catalyst_suite.get("case_count", -1)) != 10_000:
        raise RuntimeError("Catalyst full suite case count is not 10,000")
    if int(catalyst_suite["transport_consistent_cases"]) != 10_000:
        raise RuntimeError("Catalyst full suite contains transport-inconsistent cases")
    if int(divergence.get("case_count", -1)) != 10_000:
        raise RuntimeError("Catalyst compact divergence summary case count is not 10,000")
    if int(divergence.get("transport_inconsistent_cases", -1)) != 0:
        raise RuntimeError("Catalyst compact divergence summary contains transport failures")

    target = args.output_root
    if target.exists():
        shutil.rmtree(target)
    (target / "brian2loihi").mkdir(parents=True)
    (target / "catalyst").mkdir(parents=True)

    shutil.copy2(args.request_manifest, target / "request_manifest.json")
    shutil.copy2(args.brian_dir / "suite.json", target / "brian2loihi" / "suite.json")
    shutil.copy2(args.catalyst_dir / "suite.json", target / "catalyst" / "suite.json")
    shutil.copy2(args.catalyst_divergence, target / "catalyst" / "divergence_compact.json")
    for source_dir, target_dir in (
        (args.brian_dir, target / "brian2loihi"),
        (args.catalyst_dir, target / "catalyst"),
    ):
        for name in ("semantic_audit.json", "feasibility_audit.json"):
            source = source_dir / name
            if source.exists():
                shutil.copy2(source, target_dir / name)

    comparison_path = target / "comparison_summary.json"
    write_matched_summary(
        args.accepted_validation,
        target / "brian2loihi" / "suite.json",
        target / "catalyst" / "suite.json",
        comparison_path,
    )
    comparison = _read(comparison_path)

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
        "case_count": 10_000,
        "request_manifest_sha256": _sha256(args.request_manifest),
        "request_indices_sha256": request["indices_sha256"],
        "request_shard_count": int(request["shard_count"]),
        "brian_all_passed": bool(brian_suite["all_passed"]),
        "brian_prediction_agreement_cases": int(brian_suite["prediction_agreement_cases"]),
        "brian_exact_trace_agreement_cases": int(brian_suite["exact_trace_agreement_cases"]),
        "catalyst_transport_consistent_cases": int(catalyst_suite["transport_consistent_cases"]),
        "catalyst_graph_prediction_agreement_cases": int(
            catalyst_suite["graph_prediction_agreement_cases"]
        ),
        "catalyst_graph_spike_vector_agreement_cases": int(
            catalyst_suite["graph_spike_vector_agreement_cases"]
        ),
        "catalyst_sub_rest_clamp_cases": int(divergence["sub_rest_clamp_cases"]),
        "catalyst_other_translated_dynamics_cases": int(
            divergence["other_translated_dynamics_cases"]
        ),
        "project_accuracy": comparison["catalyst_matched_scope"]["project_accuracy_on_scope"],
        "brian2loihi_accuracy": comparison["brian2loihi_matched_scope"][
            "brian2loihi_accuracy_on_scope"
        ],
        "catalyst_graph_accuracy": comparison["catalyst_matched_scope"][
            "graph_accuracy_on_scope"
        ],
        "artifacts": artifacts,
        "note": (
            "Per-image full-test JSON and request shards remain build artifacts. The archive "
            "preserves complete suite case tables, compact divergence indices, request-manifest "
            "hash/provenance, and all thesis-facing aggregate results without committing the "
            "large transient request/result corpus."
        ),
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        f"MNIST-11/12 full evidence archived: cases=10000 "
        f"brian_all_passed={manifest['brian_all_passed']} "
        f"catalyst_transport_consistent={manifest['catalyst_transport_consistent_cases']} "
        f"output={target}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
