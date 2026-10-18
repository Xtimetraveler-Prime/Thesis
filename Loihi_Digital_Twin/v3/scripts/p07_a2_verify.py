#!/usr/bin/env python3
"""Compare an independently captured 64KiB KV260 mailbox against P06 oracle.

This script never opens official MNIST TEST. Any incomplete physical
execution is a failure, not synthetic/native FPGA accuracy.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from loihi_twin_v2.p06_a3_training import load_candidate, integer_weights_sha256
from loihi_twin_v2.p06_a4_snapshot import (
    compile_and_check_traces, require_pinned_training_candidate,
)
from loihi_twin_v2.p07_a1_ingress import mapping_from_compiled
from loihi_twin_v2.p07_a2_batch import COMPILED_FINGERPRINT, DDR_SHA256
from loihi_twin_v2.p07_a2_evidence import (
    compare_to_packed_oracle, parse_evidence,
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mailbox", type=Path, required=True)
    ap.add_argument("--batch-dir", type=Path, required=True)
    ap.add_argument("--candidate-dir", type=Path,
                    default=Path("artifacts/p06_a3_candidate_seed20261013"))
    ap.add_argument("--ddr-file", type=Path,
                    default=Path("artifacts/p06_a4_static_ddr_seed20261013/core0_initial_p02_ddr_512k.bin"))
    args = ap.parse_args()

    if hashlib.sha256(args.ddr_file.read_bytes()).hexdigest() != DDR_SHA256:
        raise ValueError("frozen local DDR identity mismatch")
    header = (args.batch_dir / "p07_a2_header_64.bin").read_bytes()
    payload = (args.batch_dir / "p07_a2_ingress_payload.bin").read_bytes()
    evidence = parse_evidence(args.mailbox.read_bytes(), header, payload)

    model, candidate = load_candidate(args.candidate_dir)
    require_pinned_training_candidate(candidate, integer_weights_sha256(model))
    image, compiled, traces = compile_and_check_traces(model, ())
    if traces or compiled.fingerprint != COMPILED_FINGERPRINT:
        raise ValueError("trained compiler/packed image differs from frozen P07-A1 source")
    mapping = mapping_from_compiled(compiled)
    compare_to_packed_oracle(evidence, header, payload, image, mapping)

    for index, frame in enumerate(evidence.frames):
        print(f"P07_A2_FRAME={index} class={frame.predicted} counts={frame.counts} "
              f"silent={int(frame.silent)} routed={frame.routed_packets} "
              f"last_discard={frame.dropped_packets}")
    print("P07_A2_PHYSICAL_TRACES_EXACT=1")
    print("P07_A2_OFFICIAL_TEST=SEALED")


if __name__ == "__main__":
    main()
