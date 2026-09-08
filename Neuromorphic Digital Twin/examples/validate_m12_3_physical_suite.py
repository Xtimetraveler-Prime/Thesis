from __future__ import annotations

import argparse
import json
from pathlib import Path

from neuromorphic_twin.fpga_multitick_conformance import (
    M12_MULTITICK_REPORT_SCHEMA,
    build_m12_multitick_cases,
    compare_m12_multitick_capture,
    write_m12_multitick_report,
)
from neuromorphic_twin.fpga_physical_trace import read_physical_fpga_trace_json


SUITE_REPORT_SCHEMA = "neuromorphic-twin-m12-multitick-suite-report-v1"


def validate_suite(physical_dir: Path, report_dir: Path) -> Path:
    cases = build_m12_multitick_cases()
    report_dir.mkdir(parents=True, exist_ok=True)

    suite_cases: list[dict[str, object]] = []
    mismatch_total = 0
    devices: set[str] = set()
    observed_ticks = 0

    for case in cases:
        physical_path = physical_dir / f"{case.case_id:02d}-{case.name}.physical.json"
        if not physical_path.is_file():
            raise FileNotFoundError(f"missing M12.3 physical artifact: {physical_path}")

        artifact = read_physical_fpga_trace_json(physical_path)
        devices.add(artifact.device)
        observed_ticks += len(artifact.ticks)
        report = compare_m12_multitick_capture(case, artifact)
        report_path = report_dir / f"{case.case_id:02d}-{case.name}.report.json"
        write_m12_multitick_report(report, report_path)
        mismatch_total += len(report.mismatches)

        suite_cases.append(
            {
                "case_id": case.case_id,
                "name": case.name,
                "category": case.category,
                "coverage": list(case.coverage),
                "expected_ticks": case.tick_count,
                "observed_ticks": len(artifact.ticks),
                "physical_artifact": physical_path.name,
                "report": report_path.name,
                "passed": report.passed,
                "mismatch_count": len(report.mismatches),
            }
        )

        if report.passed:
            print(
                f"M12.3 case PASS: {case.case_id:02d} {case.name} "
                f"ticks={case.tick_count}"
            )
        else:
            print(
                f"M12.3 case FAIL: {case.case_id:02d} {case.name} "
                f"ticks={case.tick_count} mismatches={len(report.mismatches)}"
            )
            for mismatch in report.mismatches:
                prefix = "artifact" if mismatch.tick is None else f"tick={mismatch.tick}"
                print(
                    f"  {prefix} {mismatch.field}: expected={mismatch.expected!r} "
                    f"actual={mismatch.actual!r}"
                )

    expected_ticks = sum(case.tick_count for case in cases)
    suite = {
        "schema": SUITE_REPORT_SCHEMA,
        "case_report_schema": M12_MULTITICK_REPORT_SCHEMA,
        "case_count": len(cases),
        "expected_tick_count": expected_ticks,
        "observed_tick_count": observed_ticks,
        "pass_count": sum(1 for case in suite_cases if case["passed"]),
        "fail_count": sum(1 for case in suite_cases if not case["passed"]),
        "mismatch_count": mismatch_total,
        "devices": sorted(devices),
        "cases": suite_cases,
    }
    suite_path = report_dir / "suite_report.json"
    suite_path.write_text(json.dumps(suite, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if mismatch_total or suite["fail_count"] or observed_ticks != expected_ticks:
        raise SystemExit(
            "M12.3 exact physical multi-tick differential FAILED: "
            f"cases={len(cases)} fail={suite['fail_count']} "
            f"ticks={observed_ticks}/{expected_ticks} mismatches={mismatch_total}"
        )

    print(
        "M12.3 exact physical multi-tick differential passed: "
        f"cases={len(cases)} ticks={expected_ticks} mismatches=0 "
        f"devices={','.join(sorted(devices))}"
    )
    return suite_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exact Python-golden versus physical-FPGA M12.3 multi-tick suite."
    )
    parser.add_argument("--physical-dir", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()
    suite_path = validate_suite(args.physical_dir, args.report_dir)
    print(f"M12.3 suite report: {suite_path}")


if __name__ == "__main__":
    main()
