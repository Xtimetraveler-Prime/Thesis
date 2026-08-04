"""Run directed encoded-weight comparisons against Brian2Loihi."""

from __future__ import annotations

import argparse
from pathlib import Path

from neuromorphic_twin.comparison import (
    BackendUnavailableError,
    write_report_json,
    write_trace_json,
)
from neuromorphic_twin.comparison.weight_conformance import (
    build_weight_conformance_cases,
    format_weight_suite_report,
    run_weight_conformance_suite,
    weight_case_output_name,
    write_weight_suite_report_json,
)


def _select_cases(names: list[str]):
    available = build_weight_conformance_cases()
    if not names:
        return available

    by_name = {case.name: case for case in available}
    unknown = sorted(set(names) - set(by_name))
    if unknown:
        raise SystemExit(
            f"Unknown case(s): {', '.join(unknown)}. Use --list to inspect names."
        )
    return tuple(by_name[name] for name in names)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        help="run one named case; may be supplied multiple times",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list encoded-weight cases and exit",
    )
    parser.add_argument(
        "--output",
        default="comparison_output/weights",
        help="root directory for suite and per-case JSON artifacts",
    )
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="stop after the first FAIL or ERROR",
    )
    parser.add_argument(
        "--max-mismatches",
        type=int,
        default=5,
        help="maximum mismatch lines shown for each failed case",
    )
    args = parser.parse_args()

    all_cases = build_weight_conformance_cases()
    if args.list:
        for case in all_cases:
            fmt = case.encoding.weight_format
            print(
                f"{case.name:<42} "
                f"mantissa={case.encoding.requested_mantissa:>4} "
                f"exp={fmt.exponent:>2} bits={fmt.num_weight_bits} "
                f"mode={fmt.sign_mode.value:<10} "
                f"{case.description}"
            )
        return 0

    selected = _select_cases(args.case)
    try:
        suite = run_weight_conformance_suite(
            selected,
            stop_on_failure=args.stop_on_failure,
        )
    except BackendUnavailableError as exc:
        print(exc)
        return 2

    print(
        format_weight_suite_report(
            suite,
            max_mismatches_per_case=args.max_mismatches,
        )
    )

    output_root = Path(args.output)
    for result in suite.results:
        case_dir = output_root / weight_case_output_name(result.case.name)
        if result.reference is not None:
            write_trace_json(
                result.reference.trace,
                case_dir / "brian2loihi_trace.json",
            )
        if result.candidate is not None:
            write_trace_json(
                result.candidate.trace,
                case_dir / "python_trace.json",
            )
        if result.report is not None:
            write_report_json(
                result.report,
                case_dir / "comparison_report.json",
            )

    write_weight_suite_report_json(
        suite,
        output_root / "suite_report.json",
    )
    print(f"Wrote suite artifacts to {output_root.resolve()}")
    return 0 if suite.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
