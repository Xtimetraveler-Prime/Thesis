from __future__ import annotations

import argparse
from pathlib import Path

from mnist_app.fpga_corpus import validate_physical_corpus_suite


def format_suite_summary(suite: dict[str, object]) -> tuple[str, ...]:
    """Format the stable MNIST-08 suite schema for console reporting."""

    lines = [
        "MNIST-08 suite: "
        f"passed={suite['passed']} cases={suite['case_count']} "
        f"ticks={suite['tick_count']} mismatches={suite['mismatch_count']}"
    ]
    for profile, summary in suite["profiles"].items():
        lines.append(
            f"profile={profile} cases={summary['cases']} "
            f"passed={summary['passed']} mismatches={summary['mismatches']}"
        )
    for reason, summary in suite["selection_reasons"].items():
        lines.append(
            f"reason={reason} cases={summary['cases']} "
            f"passed={summary['passed']} mismatches={summary['mismatches']}"
        )
    return tuple(lines)


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
    for line in format_suite_summary(suite):
        print(line)
    print(f"suite report: {args.report_dir / 'suite_report.json'}")
    return 0 if suite["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
