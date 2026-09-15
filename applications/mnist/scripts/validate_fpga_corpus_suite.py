from __future__ import annotations

import argparse
from pathlib import Path

from mnist_app.fpga_corpus import validate_physical_corpus_suite


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the full MNIST-08 physical corpus against Python golden traces."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--physical-dir", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()

    suite = validate_physical_corpus_suite(
        args.manifest,
        args.physical_dir,
        args.report_dir,
    )
    print(
        "MNIST-08 suite: "
        f"passed={suite['passed']} cases={suite['case_count']} "
        f"ticks={suite['committed_tick_count']} mismatches={suite['mismatch_count']}"
    )
    for profile, summary in suite["profile_summary"].items():
        print(
            f"profile={profile} cases={summary['cases']} "
            f"passed={summary['passed']} mismatches={summary['mismatches']}"
        )
    for reason, summary in suite["selection_reason_summary"].items():
        print(
            f"reason={reason} cases={summary['cases']} "
            f"passed={summary['passed']} mismatches={summary['mismatches']}"
        )
    print(f"suite report: {args.report_dir / 'suite_report.json'}")
    return 0 if suite["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
