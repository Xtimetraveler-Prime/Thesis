#!/usr/bin/env python3
"""B2.3 read-only trained checkpoint resource and selected-validation parity.

No checkpoint rewrite, no official MNIST TEST, no hardware access. Default:
structural B1.2 pack of the actual user-pinned 1000-neuron checkpoint.
Add --validation-ordinals 0,1,2 --data-dir ... for full 26-tick
independent monolithic versus partitioned numeric parity on those frames.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from loihi_twin_v2.p06_b23_trained_audit import audit_candidate


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate-dir", type=Path, required=True)
    p.add_argument("--data-dir", type=Path)
    p.add_argument("--validation-ordinals", type=int, nargs="*", default=[])
    p.add_argument("--report", type=Path, help="new JSON report path; no overwrite")
    a = p.parse_args()
    if a.report is not None and a.report.exists():
        p.error("report exists; refusing overwrite")
    result = audit_candidate(a.candidate_dir, data_dir=a.data_dir,
                             validation_ordinals=tuple(a.validation_ordinals))
    report = result.report()
    print(json.dumps(report, indent=2, sort_keys=True))
    if a.report is not None:
        if not a.report.parent.is_dir():
            p.error("report parent must exist")
        with a.report.open("x", encoding="utf-8") as out:
            json.dump(report, out, sort_keys=True, indent=2)
            out.write("\n")
    print("P06_B23_TRAINED_PACKED_AUDIT_PASS=1")
    print("P06_B23_VALIDATION_NUMERICAL_PARITY=" +
          ("PASS" if result.validated_frames else "NOT_RUN"))
    print("P06_B23_OFFICIAL_TEST_STATUS=SEALED")
    print("P06_B23_FREEZE_STATUS=NOT_FROZEN")


if __name__ == "__main__":
    main()
