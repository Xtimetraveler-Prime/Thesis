#!/usr/bin/env python3
"""A3.3: independently score exact 128 unique physical validation predictions.

Ten independent A53 launches required: eight primary 16-frame batches
plus cold-start repeats of batches 0 and 7. Numerics and source/labels
are checked BEFORE aggregate scores are disclosed. No canonical t10k
test files are loaded; repeat launches are never double-counted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from loihi_twin_v2.p06_a3_data import load_train_validation
from loihi_twin_v2.p06_a3_training import load_candidate, integer_weights_sha256
from loihi_twin_v2.p06_a4_snapshot import (
    compile_and_check_traces, require_pinned_training_candidate,
)
from loihi_twin_v2.p07_a1_ingress import mapping_from_compiled
from loihi_twin_v2.p07_a2_batch import COMPILED_FINGERPRINT, DDR_SHA256
from loihi_twin_v2.p07_a2_evidence import parse_evidence, compare_to_packed_oracle
from loihi_twin_v2.p07_a3_3_protocol import (
    RUN_IDS, verify_protocol, validate_evidence_log, sha, json_bytes,
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--protocol-dir", type=Path, required=True)
    p.add_argument("--evidence-root", type=Path, required=True)
    p.add_argument("--data-dir", type=Path, default=Path("data/mnist_raw"))
    p.add_argument("--candidate-dir", type=Path, default=Path(
        "artifacts/p06_a3_candidate_seed20261013"))
    p.add_argument("--ddr-file", type=Path, default=Path(
        "artifacts/p06_a4_static_ddr_seed20261013/core0_initial_p02_ddr_512k.bin"))
    p.add_argument("--report", type=Path, help="NEW JSON output; never overwrite")
    args = p.parse_args()
    if args.report is not None and args.report.exists():
        p.error("P07-A3.3 report exists; refuse overwrite")
    if hashlib.sha256(args.ddr_file.read_bytes()).hexdigest() != DDR_SHA256:
        raise ValueError("P07-A3.3 master DDR digest mismatch")
    split = load_train_validation(args.data_dir)
    model, manifest = load_candidate(args.candidate_dir)
    require_pinned_training_candidate(manifest, integer_weights_sha256(model))
    if manifest.get("source_dataset") != split.manifest:
        raise ValueError("P07-A3.3 checkpoint/canonical validation split mismatch")
    image, compiled, traces = compile_and_check_traces(model, ())
    if traces or compiled.fingerprint != COMPILED_FINGERPRINT:
        raise ValueError("P07-A3.3 frozen compiler fingerprint mismatch")
    plan, batches = verify_protocol(args.protocol_dir, split, mapping_from_compiled(compiled))
    if tuple(entry["run_id"] for entry in plan["runs"]) != RUN_IDS:
        raise ValueError("P07-A3.3 fixed physical restart order changed")

    primary = {}
    evidence_hashes = {}
    # First require ALL physical runs and numerical parity BEFORE exposing
    # any classification score. Missing/error attempts cannot be discarded.
    for entry in plan["runs"]:
        run_id = entry["run_id"]
        batch_name = entry["batch_name"]
        b = batches[int(batch_name[-2:])]
        batch_dir = args.protocol_dir / batch_name
        run_dir = args.evidence_root / run_id
        validate_evidence_log(run_dir, batch_dir, b)
        mailbox = (run_dir / "p07_a2_mailbox.bin").read_bytes()
        physical = parse_evidence(mailbox, b.header, b.payload)
        compare_to_packed_oracle(physical, b.header, b.payload,
                                 image, mapping_from_compiled(compiled))
        evidence_hashes[run_id] = sha(mailbox)
        if entry["role"] == "primary":
            primary[run_id] = physical
        else:
            original = args.evidence_root / entry["byte_identical_to"] / "p07_a2_mailbox.bin"
            if mailbox != original.read_bytes():
                raise AssertionError(
                    "P07-A3.3 cold-start repeat differs from primary mailbox: "
                    +run_id
                )
        print("P07_A3_3_PHYSICAL_RUN_EXACT="+run_id)

    if len(primary) != 8 or len(evidence_hashes) != 10:
        raise ValueError("P07-A3.3 incomplete physical run population")

    predictions = []
    confusion = [[0 for _ in range(10)] for _ in range(10)]
    silent = correct = 0
    for index in range(8):
        batch_name = f"batch_{index:02d}"
        batch = batches[index]
        run = primary[batch_name+"_primary"]
        for j, (frame, meta) in enumerate(zip(run.frames, batch.labels["rows"])):
            label, pred = meta["label"], frame.predicted
            correct += int(label == pred)
            silent += int(frame.silent)
            confusion[label][pred] += 1
            predictions.append({
                "frame": 16*index+j, "source_index": meta["source_index"],
                "truth": label, "prediction": pred, "silent": int(frame.silent),
                "image_sha256": meta["pixels_sha256"],
                "counts": list(frame.counts),
                "origin_run": batch_name+"_primary",
            })
    if len(predictions) != 128 or sum(sum(row) for row in confusion) != 128:
        raise AssertionError("P07-A3.3 skipped or duplicated primary validation images")
    report = {
        "schema": plan["schema"]+"-physical-acceptance-v1",
        "scope": "physical TRAIN-derived validation diagnostic, NOT official TEST",
        "selection_rule": plan["selection_rule"],
        "selected_indices_le32_sha256": plan["selected_indices_le32_sha256"],
        "primary_unique_frames": 128, "physical_launches": 10,
        "hardware_frame_executions": 160, "repeat_count": 2,
        "correct": correct, "denominator": 128, "silent": silent,
        "accuracy": correct/128, "confusion": confusion,
        "mailbox_sha256_by_run": evidence_hashes, "frames": predictions,
        "official_mnist_test": "SEALED",
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("xb") as out:
            out.write(json_bytes(report))
    print(f"P07_A3_3_VALIDATION_CORRECT={correct}/128")
    print(f"P07_A3_3_VALIDATION_SILENT={silent}/128")
    print("P07_A3_3_PHYSICAL_LAUNCHES_EXACT=10/10")
    print("P07_A3_3_RESTART_REPEATS_BYTE_EXACT=2/2")
    print("P07_A3_3_PHYSICAL_ORACLE_EXACT=1")
    print("P07_A3_3_OFFICIAL_TEST=SEALED")
    print("P07_A3_3_PHYSICAL_GATE_PASS=1")


if __name__ == "__main__":
    main()
