from __future__ import annotations

import argparse
from pathlib import Path

from mnist_app.fpga_corpus import validate_physical_corpus_suite
from mnist_app.fpga_corpus_reporting import format_suite_summary


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
