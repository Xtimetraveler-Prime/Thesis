#!/usr/bin/env python3
"""P07-A3: validation-only board accuracy AFTER strict frozen oracle agreement.

Fails closed on physical/runtime mismatch or image/label/source mismatch.
This CLI reads canonical TRAIN-only MNIST IDX via strict split loader.
Never opens the official t10k test set.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from loihi_twin_v2.p06_a3_data import load_train_validation
from loihi_twin_v2.p06_a3_training import load_candidate, integer_weights_sha256
from loihi_twin_v2.p06_a4_snapshot import (
    compile_and_check_traces, require_pinned_training_candidate,
)
from loihi_twin_v2.p07_a1_ingress import mapping_from_compiled
from loihi_twin_v2.p07_a2_batch import COMPILED_FINGERPRINT, DDR_SHA256
from loihi_twin_v2.p07_a2_evidence import compare_to_packed_oracle, parse_evidence
from loihi_twin_v2.p07_a3_validation import verify_validation_provenance


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mailbox", type=Path, required=True)
    parser.add_argument("--batch-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=Path("data/mnist_raw"))
    parser.add_argument("--candidate-dir", type=Path, default=Path(
        "artifacts/p06_a3_candidate_seed20261013"))
    parser.add_argument("--ddr-file", type=Path, default=Path(
        "artifacts/p06_a4_static_ddr_seed20261013/core0_initial_p02_ddr_512k.bin"))
    args = parser.parse_args()
    if hashlib.sha256(args.ddr_file.read_bytes()).hexdigest() != DDR_SHA256:
        raise ValueError("P07-A3 frozen DDR image mismatch")
    split = load_train_validation(args.data_dir)
    header, payload, ledger = verify_validation_provenance(args.batch_dir, split)
    model, candidate = load_candidate(args.candidate_dir)
    require_pinned_training_candidate(candidate, integer_weights_sha256(model))
    if candidate.get("source_dataset") != split.manifest:
        raise ValueError("P07-A3 candidate source dataset differs")
    image, compiled, traces = compile_and_check_traces(model, ())
    if traces or compiled.fingerprint != COMPILED_FINGERPRINT:
        raise ValueError("P07-A3 model compiler drift")
    physical = parse_evidence(args.mailbox.read_bytes(), header, payload)
    # Mandatory order: zero numerical divergences before scoring any labels.
    compare_to_packed_oracle(physical, header, payload, image, mapping_from_compiled(compiled))
    correct = silent = 0
    confusion = [[0]*10 for _ in range(10)]
    for n, (frame, row) in enumerate(zip(physical.frames, ledger["rows"])):
        truth, pred = row["label"], frame.predicted
        confusion[truth][pred] += 1
        correct += int(pred == truth)
        silent += int(frame.silent)
        print(f"P07_A3_VALIDATION_FRAME={n} source_index={row['source_index']} "
              f"truth={truth} prediction={pred} silent={int(frame.silent)}")
    print("P07_A3_PHYSICAL_VALIDATION_EXACT=1")
    print(f"P07_A3_VALIDATION_ACCURACY={correct}/{len(physical.frames)}")
    print(f"P07_A3_VALIDATION_SILENT={silent}/{len(physical.frames)}")
    for truth, counts in enumerate(confusion):
        print(f"P07_A3_CONFUSION_TRUTH_{truth}="+",".join(str(x) for x in counts))
    print("P07_A3_OFFICIAL_TEST=SEALED")
    print("P07_A3_PHYSICAL_GATE_PASS=1")


if __name__ == "__main__":
    main()
