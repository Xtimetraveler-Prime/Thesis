#!/usr/bin/env python3
"""Independent native A4.2a offline stage verifier, never accesses MNIST TEST.

Validates every byte of A4.2a descriptor, mapping, raw uint8 stream and
the complete initial 1MiB progress/result journal; reconstructs
accepted P07-A1 ingress on representative exact frame indices.
No torch, Vitis, FPGA, board or download required.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from loihi_twin_v2.p07_a1_ingress import decode_ingress
from loihi_twin_v2.p07_a4_stream import (
    parse_stream, initial_journal, sha256,
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage-dir", required=True, type=Path)
    args = p.parse_args()
    directory = args.stage_dir
    files = {
        "descriptor": "p07_a4_descriptor_256.bin",
        "mapping": "p07_a4_mapping_1568.bin",
        "pixels": "p07_a4_pixels_raw.bin",
        "zero_journal_1m": "p07_a4_journal_initial_1m.bin",
    }
    raw = {name:(directory / path).read_bytes() for name,path in files.items()}
    manifest = json.loads((directory/"p07_a4_2a_stage_manifest.json").read_text())
    if (manifest.get("schema") != "p07-a4-2a-persistent-ddr-stage-v1" or
            manifest.get("official_mnist_test") != "SEALED" or
            manifest.get("physical_hardware") != "NOT_RUN" or
            manifest.get("scope") not in (
                "SYNTHETIC_BLACK","SYNTHETIC_WHITE","SYNTHETIC_RAMP",
                "TRAIN_DERIVED_VALIDATION_FIRST_16",
                "TRAIN_DERIVED_VALIDATION_FIRST_128")):
        raise ValueError("A4.2a stage origin/phase/TEST seal invalid")
    for key, data in raw.items():
        if sha256(data) != manifest.get("sha256",{}).get(key):
            raise ValueError("A4.2a stage file SHA256 mismatch: "+files[key])
    stream = parse_stream(raw["descriptor"],raw["mapping"],raw["pixels"])
    if (stream.image_count != manifest.get("frame_count") or
            stream.trace_index != manifest.get("trace_index") or
            raw["zero_journal_1m"] != initial_journal(stream)):
        raise ValueError("A4.2a initial mailbox/descriptors inconsistent")
    sample_indices = sorted(set((0,stream.image_count//2,stream.image_count-1,
                                 stream.trace_index)))
    for index in sample_indices:
        decoded = decode_ingress(stream.ingress(index))
        if decoded.pixels != stream.image(index) or decoded.pixel_to_axon != stream.mapping:
            raise AssertionError("A4.2a accepted P07-A1 image/mapping parity failure")
    if manifest["scope"].startswith("TRAIN_DERIVED_VALIDATION"):
        ledger = json.loads(
            (directory/"p07_a4_2a_validation_labels_HOST_ONLY.json").read_text())
        if (ledger.get("official_mnist_test") != "SEALED" or
                len(ledger.get("indices", [])) != stream.image_count or
                len(ledger.get("rows", [])) != stream.image_count):
            raise ValueError("A4.2a incomplete host-only validation provenance")
        for index,row in enumerate(ledger["rows"]):
            if (row.get("position") != index or
                    row.get("source_index") != ledger["indices"][index] or
                    row.get("pixels_sha256") != sha256(stream.image(index)) or
                    type(row.get("label")) is not int or not 0 <= row["label"] <= 9):
                raise ValueError("A4.2a source image/label ledger inconsistency")
    print("P07_A4_2A_FRAME_COUNT="+str(stream.image_count))
    print("P07_A4_2A_RAW_PIXEL_BYTES="+str(len(stream.images)))
    print("P07_A4_2A_INPUT_DESCRIPTOR_CRC_PASS=1")
    print("P07_A4_2A_1M_JOURNAL_INIT_EXACT=1")
    print("P07_A4_2A_ACCEPTED_A1_INGRESS_EQUIVALENCE=1")
    print("P07_A4_2A_STAGING_CHECK_PASS=1")
    print("P07_A4_OFFICIAL_TEST=SEALED")


if __name__ == "__main__":
    main()
