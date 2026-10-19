#!/usr/bin/env python3
"""B2.4: materialize OR independently verify one frozen host artifact snapshot.

This utility never opens official TEST and never contacts KV260/JTAG.
Generation replays B2.3's full dense 26-tick canonical TRAIN-derived
validation ordinals (0,1,2) and refuses to overwrite any existing directory.
Default is no-op help: --freeze or --verify required.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from loihi_twin_v2.p06_b24_freeze import freeze_trained_candidate, verify_frozen_directory


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true",
                      help="generate new hash-indexed checkpoint / 27 P02 initial DDR artifacts")
    mode.add_argument("--verify", action="store_true",
                      help="read-only verify all frozen file bytes and P02 header/payload hashes")
    p.add_argument("--candidate-dir", type=Path, help="original B2.2 trained checkpoint")
    p.add_argument("--data-dir", type=Path, help="canonical TRAIN-only MNIST archives")
    p.add_argument("--output-dir", type=Path, required=True,
                   help="new frozen directory or existing directory to verify")
    p.add_argument("--deep", action="store_true",
                   help="with --verify, rehydrate and cross-check B1.2 source, mapper and all 27 P02 records")
    a = p.parse_args()
    if a.freeze:
        if a.candidate_dir is None or a.data_dir is None:
            p.error("--freeze needs --candidate-dir and --data-dir (canonical TRAIN-only)")
        if a.deep:
            p.error("--deep requires --verify, never --freeze")
        result = freeze_trained_candidate(
            a.candidate_dir, a.data_dir, a.output_dir)
        result["operation"] = "FREEZE_NEW_HOST_SNAPSHOT_PENDING_USER_ACCEPTANCE"
        marker = "P06_B24_HOST_FREEZE_MATERIALIZED_PASS=1"
    else:
        result = verify_frozen_directory(a.output_dir, deep=a.deep)
        result["operation"] = "INDEPENDENT_READ_ONLY_FROZEN_BYTE_VERIFICATION"
        marker = "P06_B24_FROZEN_INTEGRITY_PASS=1"
    print(json.dumps(result, sort_keys=True, indent=2))
    print(marker)
    print("P06_B24_OFFICIAL_TEST_STATUS=SEALED")
    print("P06_B24_PHYSICAL_KV260_STATUS=NOT_TESTED")


if __name__ == "__main__":
    main()
