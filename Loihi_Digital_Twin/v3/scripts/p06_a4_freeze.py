#!/usr/bin/env python3
"""P06-A4.2 static DDR freeze gate; DOES NOT RUN THE KV260.

Validates exact user-reported P03 stream SHA256/lengths + accepted
checkpoint, compiles trained weights, serializes 512KiB P02.1 core
record, parses header/digest, verifies every static/mutable bank.
Neither this file nor its output provides the P07 A53 multi-axon event
streaming ABI or official MNIST test evaluation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from loihi_twin_v2.p06_a4_freeze import freeze_static_ddr


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = freeze_static_ddr(
        args.candidate_dir, args.snapshot_dir, args.output_dir
    )
    print("P06_A4_STATIC_DDR_FREEZE_PASS=1", flush=True)
    print("P06_A4_DDR_SHA256=" + result["ddr_file_sha256"], flush=True)
    print("P06_A4_DDR_META=" + json.dumps(result["ddr_abi"], sort_keys=True), flush=True)
    print("P06_A4_NATIVE_TEST_STATUS=STATIC_HOST_IMAGE_ONLY")
    print("P06_A4_OFFICIAL_TEST_STATUS=SEALED")
    print("P06_A4_P07_A53_INPUT_STREAMING=NOT_IMPLEMENTED")


if __name__ == "__main__":
    main()
