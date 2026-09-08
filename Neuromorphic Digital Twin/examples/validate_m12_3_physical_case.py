from __future__ import annotations

import argparse
from pathlib import Path

from neuromorphic_twin.fpga_multitick_conformance import (
    build_m12_multitick_cases,
    compare_m12_multitick_capture,
    write_m12_multitick_report,
)
from neuromorphic_twin.fpga_physical_trace import read_physical_fpga_trace_json


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate one M12.3 physical multi-tick case against Python golden ticks."
    )
    parser.add_argument("--case-id", type=int, required=True)
    parser.add_argument("--physical", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    cases = build_m12_multitick_cases()
    if not 0 <= args.case_id < len(cases):
        raise SystemExit(f"invalid M12.3 case id: {args.case_id}")
    case = cases[args.case_id]

    artifact = read_physical_fpga_trace_json(args.physical)
    report = compare_m12_multitick_capture(case, artifact)
    write_m12_multitick_report(report, args.report)

    if not report.passed:
        print(
            f"M12.3 targeted case FAIL: {case.case_id:02d} {case.name} "
            f"ticks={case.tick_count} mismatches={len(report.mismatches)}"
        )
        for mismatch in report.mismatches:
            prefix = "artifact" if mismatch.tick is None else f"tick={mismatch.tick}"
            print(
                f"  {prefix} {mismatch.field}: expected={mismatch.expected!r} "
                f"actual={mismatch.actual!r}"
            )
        return 1

    print(
        f"M12.3 targeted case PASS: {case.case_id:02d} {case.name} "
        f"ticks={case.tick_count} mismatches=0"
    )
    print(f"M12.3 targeted report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
