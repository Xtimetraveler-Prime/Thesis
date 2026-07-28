"""Compare two previously exported trace JSON files.

This path is useful when Brian2Loihi, an RTL simulator, and the main Python
model live in different environments or on different machines.
"""

import argparse

from neuromorphic_twin.comparison import (
    compare_traces,
    format_report,
    read_trace_json,
    write_report_json,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", help="reference trace JSON")
    parser.add_argument("candidate", help="candidate trace JSON")
    parser.add_argument(
        "--report",
        default="comparison_output/saved_trace_report.json",
        help="path for the machine-readable comparison report",
    )
    args = parser.parse_args()

    reference = read_trace_json(args.reference)
    candidate = read_trace_json(args.candidate)
    report = compare_traces(reference, candidate)
    print(format_report(report))
    write_report_json(report, args.report)
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
