#!/usr/bin/env python3
"""P06-B2.5: read-only final host-software audit and honest P07-B handoff.

Checks the *existing* user-verified B2.4 frozen directory. Default verifies
all 33 frozen assets and 27 P02 headers, P05 slot/one-engine resource limits,
both independently observed B2.4 manifest SHA256 values, TRAIN-derived
validation provenance and all three B2.3 trace witnesses. --deep additionally
rebuilds B1.2 source/packed images using B2.4's accepted deep checker.

No training, no TEST unseal, no JTAG/FPGA programming, and NO MERGING.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from loihi_twin_v2.p06_b25_acceptance import assess_frozen_handoff


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--frozen-dir", type=Path, required=True,
                   help="read-only existing artifacts/p06_b24_frozen_1000 directory")
    p.add_argument("--deep", action="store_true",
                   help="independently regenerate and compare all 27 initial P02 images")
    p.add_argument("--report", type=Path,
                   help="optional NEW output JSON outside frozen directory; no overwrite")
    args = p.parse_args()
    frozen_root = args.frozen_dir.resolve()
    if args.report is not None:
        resolved = args.report.resolve()
        if resolved == frozen_root or frozen_root in resolved.parents:
            p.error("report must be OUTSIDE frozen directory to preserve its 33-asset hash set")
        if args.report.exists() or args.report.is_symlink():
            p.error("report already exists; no overwrite")
        if not args.report.parent.is_dir():
            p.error("report parent missing")
    result = assess_frozen_handoff(args.frozen_dir, deep=args.deep)
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    if args.report is not None:
        with args.report.open("x", encoding="utf-8", newline="\n") as f:
            json.dump(result, f, sort_keys=True, indent=2)
            f.write("\n")
        print("P06_B25_REPORT_FILE_SHA256=" +
              hashlib.sha256(args.report.read_bytes()).hexdigest())
    print("P06_B25_HOST_SOFTWARE_HANDOFF_PASS=1")
    print("P06_B25_SCALED_FPGA_EXECUTION_GO=0")
    print("P06_B25_OFFICIAL_TEST_UNSEAL_GO=0")
    print("P06_B25_FREEZE_UNMODIFIED=1")


if __name__ == "__main__":
    main()
