from __future__ import annotations

import argparse
import json
from pathlib import Path

from mnist_app.fpga_conformance import compare_physical_to_golden
from neuromorphic_twin.fpga_physical_trace import read_physical_fpga_trace_json


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate both MNIST-07 physical FPGA traces against golden traces."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--physical-dir", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()

    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    records = payload.get("cases")
    if not isinstance(records, list) or len(records) != 2:
        raise SystemExit("MNIST-07 manifest must contain exactly two cases")

    args.report_dir.mkdir(parents=True, exist_ok=True)
    reports: list[dict[str, object]] = []
    for record in records:
        case_id = int(record["case_id"])
        name = str(record["name"])
        golden = read_physical_fpga_trace_json(
            args.manifest.parent / str(record["golden_trace"])
        )
        physical_path = args.physical_dir / f"{case_id:02d}-{name}.physical.json"
        physical = read_physical_fpga_trace_json(physical_path)
        report = compare_physical_to_golden(
            golden,
            physical,
            expected_prediction=int(record["expected_prediction"]),
        )
        report["case_id"] = case_id
        report["profile"] = record["profile"]
        report_path = args.report_dir / f"{case_id:02d}-{name}.report.json"
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        reports.append(report)
        status = "PASS" if report["passed"] else "FAIL"
        print(
            f"MNIST-07 {status}: case={case_id} profile={record['profile']} "
            f"prediction={report['physical_prediction']} "
            f"mismatches={report['mismatch_count']}"
        )

    passed = all(bool(report["passed"]) for report in reports)
    suite = {
        "schema": "neuromorphic-twin-mnist-fpga-conformance-suite-v1",
        "passed": passed,
        "case_count": len(reports),
        "mismatch_count": sum(int(report["mismatch_count"]) for report in reports),
        "cases": reports,
    }
    suite_path = args.report_dir / "suite_report.json"
    suite_path.write_text(
        json.dumps(suite, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"MNIST-07 suite report: {suite_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
