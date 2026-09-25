from __future__ import annotations

import argparse
import json
from pathlib import Path

from mnist_app.catalyst_divergence import summarize_cases, summarize_cases_compact


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify FPGA-v1/Catalyst MNIST divergences from matched case JSON files."
    )
    parser.add_argument(
        "--result-dir",
        type=Path,
        default=Path("applications/mnist/build/mnist-12/catalyst"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("applications/mnist/build/mnist-12/catalyst/divergence_summary.json"),
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Store only aggregate counts/index lists instead of per-case mismatch vectors.",
    )
    args = parser.parse_args()

    suite_path = args.result_dir / "suite.json"
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    case_files = [
        args.result_dir / f"index{int(case['mnist_test_index']):05d}.json"
        for case in suite["cases"]
    ]
    results = [json.loads(path.read_text(encoding="utf-8")) for path in case_files]
    summary = summarize_cases_compact(results) if args.compact else summarize_cases(results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        "MNIST-12 divergence summary: "
        f"cases={summary['case_count']} "
        f"transport_consistent={summary['transport_consistent_cases']} "
        f"prediction_agreement={summary['prediction_agreement_cases']} "
        f"spike_vector_agreement={summary['graph_spike_vector_agreement_cases']} "
        f"sub_rest_clamp={summary['sub_rest_clamp_cases']} "
        f"exact={summary['exact_cases']} "
        f"other={summary['other_translated_dynamics_cases']} "
        f"compact={args.compact} output={args.output}"
    )
    return 0 if int(summary["transport_inconsistent_cases"]) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
