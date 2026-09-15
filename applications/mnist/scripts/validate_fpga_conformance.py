from __future__ import annotations

import argparse
import json
from pathlib import Path

from mnist_app.fpga_conformance import compare_physical_to_golden
from neuromorphic_twin.fpga_physical_trace import read_physical_fpga_trace_json


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate one MNIST-07 physical FPGA trace against its golden trace."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--case-id", type=int, required=True)
    parser.add_argument("--physical", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    records = payload.get("cases")
    if not isinstance(records, list):
        raise SystemExit("invalid MNIST-07 manifest")
    selected = [record for record in records if record.get("case_id") == args.case_id]
    if len(selected) != 1:
        raise SystemExit(f"invalid MNIST-07 case id: {args.case_id}")
    record = selected[0]

    golden = read_physical_fpga_trace_json(
        args.manifest.parent / record["golden_trace"]
    )
    physical = read_physical_fpga_trace_json(args.physical)
    report = compare_physical_to_golden(
        golden,
        physical,
        expected_prediction=int(record["expected_prediction"]),
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    if not report["passed"]:
        print(
            f"MNIST-07 FAIL: case={args.case_id} "
            f"mismatches={report['mismatch_count']} report={args.report}"
        )
        for mismatch in report["mismatches"][:20]:
            print(
                f"  tick={mismatch['tick']} {mismatch['field']}: "
                f"expected={mismatch['expected']!r} actual={mismatch['actual']!r}"
            )
        return 1

    print(
        f"MNIST-07 PASS: case={args.case_id} prediction={report['physical_prediction']} "
        f"mismatches=0 report={args.report}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
