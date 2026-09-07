from __future__ import annotations

import argparse
from pathlib import Path

from neuromorphic_twin.fpga_physical_trace import read_physical_fpga_trace_json
from neuromorphic_twin.fpga_single_tick_conformance import (
    build_m12_single_tick_cases,
    compare_m12_single_tick_capture,
    write_m12_single_tick_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate one M12.2 physical case against the independent Python golden result."
    )
    parser.add_argument("--case-id", type=int, required=True)
    parser.add_argument("--physical", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    cases = build_m12_single_tick_cases()
    if not 0 <= args.case_id < len(cases):
        raise SystemExit(f"invalid M12.2 case id: {args.case_id}")
    case = cases[args.case_id]

    artifact = read_physical_fpga_trace_json(args.physical)
    report = compare_m12_single_tick_capture(case, artifact)
    write_m12_single_tick_report(report, args.report)

    if not report.passed:
        print(
            f"M12.2 targeted case FAIL: {case.case_id:02d} {case.name} "
            f"mismatches={len(report.mismatches)}"
        )
        for mismatch in report.mismatches:
            print(
                f"  {mismatch.field}: expected={mismatch.expected!r} "
                f"actual={mismatch.actual!r}"
            )
        return 1

    print(f"M12.2 targeted case PASS: {case.case_id:02d} {case.name} mismatches=0")
    print(f"M12.2 targeted report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
