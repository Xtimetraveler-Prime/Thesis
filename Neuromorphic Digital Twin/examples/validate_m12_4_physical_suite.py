from __future__ import annotations

import argparse
import json
from pathlib import Path

from neuromorphic_twin.fpga_broad_regression import (
    M12_BROAD_CORPUS_SCHEMA,
    M12_BROAD_GENERATOR_VERSION,
    build_m12_broad_cases,
    compare_m12_broad_capture,
    write_m12_broad_report,
)
from neuromorphic_twin.fpga_physical_trace import read_physical_fpga_trace_json


SUITE_REPORT_SCHEMA = "neuromorphic-twin-m12-broad-physical-suite-report-v1"


def validate_suite(physical_dir: Path, report_dir: Path) -> Path:
    cases = build_m12_broad_cases()
    report_dir.mkdir(parents=True, exist_ok=True)

    suite_cases: list[dict[str, object]] = []
    mismatch_total = 0
    observed_ticks = 0
    devices: set[str] = set()

    for case in cases:
        physical_path = physical_dir / f"{case.case_id:02d}-{case.name}.physical.json"
        if not physical_path.is_file():
            raise FileNotFoundError(f"missing M12.4 physical artifact: {physical_path}")

        artifact = read_physical_fpga_trace_json(physical_path)
        report = compare_m12_broad_capture(case, artifact)
        report_path = report_dir / f"{case.case_id:02d}-{case.name}.report.json"
        write_m12_broad_report(report, report_path)

        devices.add(artifact.device)
        observed_ticks += len(artifact.ticks)
        mismatch_total += len(report.mismatches)
        suite_cases.append(
            {
                "case_id": case.case_id,
                "name": case.name,
                "source_kind": case.source_kind,
                "seed": f"0x{case.seed:016x}",
                "generator_version": case.generator_version,
                "configuration_sha256": case.configuration_sha256,
                "expected_ticks": case.tick_count,
                "observed_ticks": len(artifact.ticks),
                "golden_artifact": f"{case.case_id:02d}-{case.name}.golden.json",
                "physical_artifact": physical_path.name,
                "report": report_path.name,
                "passed": report.passed,
                "mismatch_count": len(report.mismatches),
            }
        )

        if report.passed:
            print(
                f"M12.4 case PASS: {case.case_id:02d} {case.name} "
                f"kind={case.source_kind} ticks={case.tick_count} "
                f"seed=0x{case.seed:016x} config={case.configuration_sha256[:12]}"
            )
        else:
            print(
                f"M12.4 case FAIL: {case.case_id:02d} {case.name} "
                f"kind={case.source_kind} ticks={case.tick_count} "
                f"seed=0x{case.seed:016x} config={case.configuration_sha256} "
                f"mismatches={len(report.mismatches)}"
            )
            for mismatch in report.mismatches:
                prefix = "artifact" if mismatch.tick is None else f"tick={mismatch.tick}"
                print(
                    f"  {prefix} {mismatch.field}: expected={mismatch.expected!r} "
                    f"actual={mismatch.actual!r}"
                )

    expected_ticks = sum(case.tick_count for case in cases)
    fail_count = sum(1 for entry in suite_cases if not entry["passed"])
    suite = {
        "schema": SUITE_REPORT_SCHEMA,
        "corpus_schema": M12_BROAD_CORPUS_SCHEMA,
        "generator_version": M12_BROAD_GENERATOR_VERSION,
        "case_count": len(cases),
        "seeded_case_count": sum(case.source_kind == "seeded" for case in cases),
        "stress_case_count": sum(case.source_kind == "stress" for case in cases),
        "expected_tick_count": expected_ticks,
        "observed_tick_count": observed_ticks,
        "pass_count": len(cases) - fail_count,
        "fail_count": fail_count,
        "mismatch_count": mismatch_total,
        "devices": sorted(devices),
        "retained_regression_anchors": {
            "m12_2_directed_cases": 16,
            "m12_3_directed_cases": 10,
            "m12_3_directed_ticks": 40,
        },
        "cases": suite_cases,
    }
    suite_path = report_dir / "suite_report.json"
    suite_path.write_text(json.dumps(suite, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if mismatch_total or fail_count or observed_ticks != expected_ticks:
        raise SystemExit(
            "M12.4 exact broad physical differential FAILED: "
            f"cases={len(cases)} fail={fail_count} ticks={observed_ticks}/{expected_ticks} "
            f"mismatches={mismatch_total}"
        )

    print(
        "M12.4 exact broad physical differential passed: "
        f"cases={len(cases)} ticks={expected_ticks} mismatches=0 "
        f"devices={','.join(sorted(devices))}"
    )
    print(f"M12.4 suite report: {suite_path}")
    return suite_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exact Python-golden versus physical-FPGA M12.4 broad deterministic suite."
    )
    parser.add_argument("--physical-dir", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()
    validate_suite(args.physical_dir, args.report_dir)


if __name__ == "__main__":
    main()
