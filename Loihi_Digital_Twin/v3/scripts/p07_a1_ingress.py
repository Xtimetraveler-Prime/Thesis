#!/usr/bin/env python3
"""P07-A1 native preflight: frozen trained checkpoint + DDR -> one ingress.

Consumes existing immutable local artifacts. Does not regenerate DDR, access
official MNIST TEST, modify RTL/P05, or claim physical FPGA inference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from loihi_twin_v2.ddr_abi import P02_DDR_CONTEXT_STRIDE_BYTES, parse_ddr_context_header
from loihi_twin_v2.p06_a3_training import load_candidate, integer_weights_sha256
from loihi_twin_v2.p06_a4_snapshot import (
    compile_and_check_traces, require_pinned_training_candidate,
)
from loihi_twin_v2.p06_input_contract import ENCODER_PROFILE, READOUT_PROFILE
from loihi_twin_v2.p07_a1_ingress import (
    decode_ingress, encode_compiled_ingress, ingress_sha256,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate-dir",
        type=Path, default=Path("artifacts/p06_a3_candidate_seed20261013"),
    )
    parser.add_argument(
        "--ddr-file", type=Path,
        default=Path("artifacts/p06_a4_static_ddr_seed20261013/core0_initial_p02_ddr_512k.bin"),
    )
    parser.add_argument(
        "--ddr-manifest", type=Path,
        default=Path("artifacts/p06_a4_static_ddr_seed20261013/p06_a4_static_ddr_freeze_manifest.json"),
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--raw-image", type=Path, help="Exactly 784 raw bytes; not official TEST")
    input_group.add_argument("--synthetic", choices=("black", "white", "ramp"))
    parser.add_argument("--out", type=Path, required=True, help="NEW filename; never overwrite")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("destination exists; refuse to overwrite an accepted artifact")

    ddr = args.ddr_file.read_bytes()
    if len(ddr) != P02_DDR_CONTEXT_STRIDE_BYTES:
        raise ValueError("wrong frozen static P02 context size")
    header = parse_ddr_context_header(ddr, verify_payload=True)
    if (header.logical_core_id != 0 or header.current_event_bank != 0 or
            header.event0_count or header.event1_count or header.packet_count or
            (header.compartment_count, header.synapse_count, header.route_count) !=
            (42, 25408, 32)):
        raise ValueError("DDR context differs from frozen P06 Track A initial image")
    ddr_sha = hashlib.sha256(ddr).hexdigest()
    freeze = json.loads(args.ddr_manifest.read_text(encoding="utf-8"))
    if freeze.get("ddr_file_sha256") != ddr_sha:
        raise ValueError("local P06-A4.2 DDR manifest SHA256 does not match real binary")
    if (freeze.get("encoder"), freeze.get("readout"), freeze.get("ticks")) != (
            ENCODER_PROFILE, READOUT_PROFILE, 26):
        raise ValueError("P06-A4.2 frozen event/readout semantics mismatch")

    model, candidate_manifest = load_candidate(args.candidate_dir)
    require_pinned_training_candidate(candidate_manifest, integer_weights_sha256(model))
    image, compiled, traces = compile_and_check_traces(model, ())
    if traces or image.core_id != 0:
        raise ValueError("unexpected compiler traces or core ID")
    if compiled.fingerprint != freeze.get("source_compiler_fingerprint"):
        raise ValueError("P07 compiled deployment differs from frozen DDR source")
    if compiled.source_fingerprint != freeze.get("source_network_fingerprint"):
        raise ValueError("P07 source network fingerprint differs from frozen DDR")

    if args.raw_image is not None:
        pixels = args.raw_image.read_bytes()
    else:
        pixels = {
            "black": bytes(784),
            "white": bytes([255]) * 784,
            "ramp": bytes(i % 256 for i in range(784)),
        }[args.synthetic]
    record = encode_compiled_ingress(pixels, compiled, ddr_sha256=ddr_sha)
    decoded = decode_ingress(record)
    events = tuple(decoded.event_axons(tick) for tick in range(26))
    if len(events[-1]) != 0:
        raise AssertionError("drain timestep generated external events")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("xb") as out:
        out.write(record)
    print(f"P07_A1_DDR_SHA256={ddr_sha}")
    print(f"P07_A1_COMPILED_FINGERPRINT={compiled.fingerprint}")
    print(f"P07_A1_INGRESS_SHA256={ingress_sha256(record)}")
    print(f"P07_A1_INPUT_EVENTS={sum(map(len, events))}")
    print("P07_A1_26_TICKS=25_INPUT_PLUS_1_DRAIN")
    print("P07_A1_HOST_RECORD_PASS=1")
    print("P07_A1_KV260_STATUS=NOT_RUN")


if __name__ == "__main__":
    main()
