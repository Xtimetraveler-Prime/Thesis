#!/usr/bin/env python3
"""P06-A4 software snapshot gate for the ACCEPTED trained MNIST candidate.

No official MNIST test data are opened. This writes an ABI-explicit P03 word
snapshot and 26-step software differential traces, NOT a deployable P05 DDR
context or a KV260 bitstream.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from loihi_twin_v2.p06_a4_snapshot import run_a4_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--validation-traces", type=int, default=3)
    args = parser.parse_args()
    manifest = run_a4_snapshot(
        args.candidate_dir, args.data_dir, args.output_dir,
        diagnostic_validation_count=args.validation_traces,
    )
    print("P06_A4_SOFTWARE_SNAPSHOT_PASS=1")
    print("P06_A4_IMAGE=" + json.dumps(manifest["image"], sort_keys=True))
    print("P06_A4_PACKED_STREAMS=" + json.dumps(manifest["packed_word_streams"], sort_keys=True))
    print("P06_A4_PARITY=" + json.dumps(manifest["packet_gate"], sort_keys=True))
    print("P06_A4_OFFICIAL_TEST_STATUS=SEALED")
    print("P06_A4_FPGA_STATUS=NO_PHYSICAL_RUN_NO_DDR_PAGE_IMAGE")
    print("P06_A4_CLOSURE=PENDING_NATIVE_ACCEPTANCE_AND_FINAL_PROTOCOL_FREEZE")


if __name__ == "__main__":
    main()
