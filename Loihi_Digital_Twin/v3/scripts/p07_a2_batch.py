#!/usr/bin/env python3
"""Prepare immutable, versioned A53 batch from accepted P07-A1 records.

The frozen 512KiB master DDR image is STAGED separately (not rewritten).
Never download or unseal official MNIST TEST data in this script.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from loihi_twin_v2.p07_a2_batch import write_batch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, action="append", required=True,
                        help="Existing 2480-byte P07-A1 record; repeat up to 16")
    parser.add_argument("--trace-frame", type=int, default=0)
    parser.add_argument("--out", type=Path, required=True,
                        help="Fresh output directory, refuse existing path")
    args = parser.parse_args()
    result = write_batch(tuple(args.record), args.out, trace_frame=args.trace_frame)
    print("P07_A2_BATCH_SHA256=" + result["sha256"]["header"])
    print("P07_A2_PAYLOAD_SHA256=" + result["sha256"]["payload"])
    print("P07_A2_FRAME_COUNT=" + str(result["frame_count"]))
    print("P07_A2_DDR_SHA256=" + result["ddr_sha256"])
    print("P07_A2_TEST_STATUS=SEALED")
    print("P07_A2_BOARD_STATUS=NOT_RUN")
    print("P07_A2_BATCH_HOST_PASS=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
