#!/usr/bin/env python3
"""P07-A4.2a: NEW persistent DDR preflight for synthetic/validation only.

Absolutely NO access to canonical MNIST t10k TEST archives. This is a
candidate input/DDR staging layout for native tests, NOT a physical
firmware/FPGA demonstration. Accepted P07-A2/P03/P05 files unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from loihi_twin_v2.ddr_abi import parse_ddr_context_header
from loihi_twin_v2.p06_a3_training import load_candidate, integer_weights_sha256
from loihi_twin_v2.p06_a4_snapshot import (
    compile_and_check_traces, require_pinned_training_candidate,
)
from loihi_twin_v2.p07_a1_ingress import mapping_from_compiled
from loihi_twin_v2.p07_a2_batch import COMPILED_FINGERPRINT, DDR_SHA256
from loihi_twin_v2.p07_a4_stream import (
    make_stream, parse_stream, initial_journal, sha256,
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--synthetic", choices=("black", "white", "ramp"))
    source.add_argument("--validation-first", type=int, choices=(16,128),
                        help="first 16 or 128 canonical TRAIN-derived validation images")
    p.add_argument("--count", type=int, default=16,
                   help="SYNTHETIC repeat count 1..10000; forbidden with validation")
    p.add_argument("--trace-index", type=int, default=0)
    p.add_argument("--data-dir", type=Path, default=Path("data/mnist_raw"))
    p.add_argument("--candidate-dir", type=Path, default=Path(
        "artifacts/p06_a3_candidate_seed20261013"))
    p.add_argument("--ddr-file", type=Path, default=Path(
        "artifacts/p06_a4_static_ddr_seed20261013/core0_initial_p02_ddr_512k.bin"))
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        p.error("P07-A4.2a destination exists; refuse overwrite of artifacts/evidence")
    if args.validation_first is not None and args.count != 16:
        p.error("--count only applies to --synthetic")
    if args.synthetic is not None and not 1 <= args.count <= 10000:
        p.error("--count must be in [1,10000]")

    master = args.ddr_file.read_bytes()
    if hashlib.sha256(master).hexdigest() != DDR_SHA256:
        raise ValueError("P07-A4.2a DDR master immutable SHA mismatch")
    hdr = parse_ddr_context_header(master, verify_payload=True)
    if (hdr.logical_core_id, hdr.compartment_count,
        hdr.synapse_count, hdr.route_count) != (0,42,25408,32):
        raise ValueError("P07-A4.2a immutable master neural header mismatch")
    model, candidate = load_candidate(args.candidate_dir)
    require_pinned_training_candidate(candidate, integer_weights_sha256(model))
    image, compiled, traces = compile_and_check_traces(model, ())
    if traces or image.core_id != 0 or compiled.fingerprint != COMPILED_FINGERPRINT:
        raise ValueError("P07-A4.2a compiled Track A checkpoint identity changed")
    mapping = mapping_from_compiled(compiled)

    ledger = None
    if args.validation_first is None:
        pix = {
            "black": bytes(784),
            "white": bytes([255])*784,
            "ramp": bytes(i%256 for i in range(784)),
        }[args.synthetic]
        images = pix*args.count
        scope = "SYNTHETIC_"+args.synthetic.upper()
    else:
        from loihi_twin_v2.p06_a3_data import load_train_validation
        from loihi_twin_v2.p07_a3_3_protocol import select_frames
        split = load_train_validation(args.data_dir)
        if split.manifest != candidate.get("source_dataset"):
            raise ValueError("P07-A4.2a frozen training split differs from checkpoint")
        frames = select_frames(split)[:args.validation_first]
        images = b"".join(f.pixels for f in frames)
        scope = "TRAIN_DERIVED_VALIDATION_FIRST_"+str(args.validation_first)
        ledger = {
            "scope": scope, "source": "canonical TRAIN-only IDX",
            "indices": [f.source_index for f in frames],
            "rows": [
                {"position": i,"source_index": f.source_index,
                 "label": f.label, "pixels_sha256":sha256(f.pixels)}
                for i,f in enumerate(frames)
            ],
            "source_dataset_sha256":sha256(json.dumps(
                split.manifest,sort_keys=True,separators=(",",":")).encode()),
            "official_mnist_test": "SEALED",
        }
    stream = make_stream(images,mapping,trace_index=args.trace_index)
    assert parse_stream(stream.header,stream.mapping_bytes,stream.images)==stream
    journal = initial_journal(stream)
    manifest = {
        "schema": "p07-a4-2a-persistent-ddr-stage-v1",
        "scope": scope, "frame_count": stream.image_count,
        "trace_index": stream.trace_index, "image_stride_bytes": 784,
        "mapping_source":"frozen compile_network mapping_from_compiled",
        "ddr_sha256":DDR_SHA256, "compiled_fingerprint": COMPILED_FINGERPRINT,
        "sha256": {
            "descriptor":sha256(stream.header),
            "mapping":sha256(stream.mapping_bytes),
            "pixels":sha256(stream.images),
            "zero_journal_1m":sha256(journal),
        },
        "official_mnist_test":"SEALED",
        "physical_hardware":"NOT_RUN",
    }
    output = args.out
    output.mkdir(parents=True,exist_ok=False)
    (output/"p07_a4_descriptor_256.bin").write_bytes(stream.header)
    (output/"p07_a4_mapping_1568.bin").write_bytes(stream.mapping_bytes)
    (output/"p07_a4_pixels_raw.bin").write_bytes(stream.images)
    (output/"p07_a4_journal_initial_1m.bin").write_bytes(journal)
    (output/"p07_a4_2a_stage_manifest.json").write_text(
        json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    if ledger is not None:
        (output/"p07_a4_2a_validation_labels_HOST_ONLY.json").write_text(
            json.dumps(ledger,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("P07_A4_2A_STREAM_FRAMES="+str(stream.image_count))
    print("P07_A4_2A_STREAM_BYTES="+str(len(stream.images)))
    print("P07_A4_2A_DESCRIPTOR_SHA256="+sha256(stream.header))
    print("P07_A4_2A_RAW_PIXEL_SHA256="+sha256(stream.images))
    print("P07_A4_2A_INPUT_ABI_HOST_PASS=1")
    print("P07_A4_2A_A53_FIRMWARE=NOT_YET_BUILT")
    print("P07_A4_2A_KV260_STATUS=NOT_RUN")
    print("P07_A4_OFFICIAL_TEST=SEALED")
    print("P07_A4_2A_OUTPUT_DIR="+str(output.resolve()))


if __name__ == "__main__":
    main()
