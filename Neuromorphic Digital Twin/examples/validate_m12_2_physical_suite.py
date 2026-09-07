from __future__ import annotations

import argparse
import json
from pathlib import Path

from neuromorphic_twin.fpga_physical_trace import read_physical_fpga_trace_json
from neuromorphic_twin.fpga_single_tick_conformance import (
    M12_SINGLE_TICK_REPORT_SCHEMA,
    build_m12_single_tick_cases,
    compare_m12_single_tick_capture,
    write_m12_single_tick_report,
)


SUITE_REPORT_SCHEMA = "neuromorphic-twin-m12-single-tick-suite-report-v1"


def validate_suite(physical_dir: Path, report_dir: Path) -> Path:
    cases = build_m12_single_tick_cases()
    report_dir.mkdir(parents=True, exist_ok=True)

    suite_cases: list[dict[str, object]] = []
    mismatch_total = 0
    devices: set[str] = set()

    for case in cases:
        physical_path = physical_dir / f"{case.case_id:02d}-{case.name}.physical.json"
        if not physical_path.is_file():
            raise FileNotFoundError(f"missing M12.2 physical artifact: {physical_path}")

        artifact = read_physical_fpga_trace_json(physical_path)
        devices.add(artifact.device)
        report = compare_m12_single_tick_capture(case, artifact)
        report_path = report_dir / f"{case.case_id:02d}-{case.name}.report.json"
        write_m12_single_tick_report(report, report_path)
        mismatch_total += len(report.mismatches)

        suite_cases.append(
            {
                "case_id": case.case_id,
                "name": case.name,
                "category": case.category,
                "coverage": list(case.coverage),
                "physical_artifact": physical_path.name,
                "report": report_path.name,
                "passed": report.passed,
                "mismatch_count": len(report.mismatches),
            }
        )

        if report.passed:
            print(f"M12.2 case PASS: {case.case_id:02d} {case.name}")
        else:
            print(
                f"M12.2 case FAIL: {case.case_id:02d} {case.name} "
                f"mismatches={len(report.mismatches)}"
            )
            for mismatch in report.mismatches:
                print(
                    f"  {mismatch.field}: expected={mismatch.expected!r} "
                    f"actual={mismatch.actual!r}"
                )

    suite = {
        "schema": SUITE_REPORT_SCHEMA,
        "case_report_schema": M12_SINGLE_TICK_REPORT_SCHEMA,
        "case_count": len(cases),
        "pass_count": sum(1 for case in suite_cases if case["passed"]),
        "fail_count": sum(1 for case in suite_cases if not case["passed"]),
        "mismatch_count": mismatch_total,
        "devices": sorted(devices),
        "cases": suite_cases,
    }
    suite_path = report_dir / "suite_report.json"
    suite_path.write_text(json.dumps(suite, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if mismatch_total or suite["fail_count"]:
        raise SystemExit(
            "M12.2 exact physical single-tick differential FAILED: "
            f"cases={len(cases)} fail={suite['fail_count']} mismatches={mismatch_total}"
        )

    print(
        "M12.2 exact physical single-tick differential passed: "
        f"cases={len(cases)} mismatches=0 devices={','.join(sorted(devices))}"
    )
    return suite_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exact Python-golden versus physical-FPGA M12.2 single-tick suite."
    )
    parser.add_argument("--physical-dir", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()
    suite_path = validate_suite(args.physical_dir, args.report_dir)
    print(f"M12.2 suite report: {suite_path}")


if __name__ == "__main__":
    main()
