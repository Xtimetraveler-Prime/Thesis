#!/usr/bin/env python3
"""P07-A4: pre-unseal protocol review and explicitly guarded TEST preparation.

--review only reports the already-frozen protocol; it NEVER opens TEST.
--download-test and --prepare are an IRREVERSIBLE EXPLICIT TEST UNSEAL
and require --i-accept-unseal with the user's informed decision that the
full 10,000-image protocol entails 625 separate JTAG/A53 launches.
No official TEST scoring occurs in this program.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from loihi_twin_v2.ddr_abi import parse_ddr_context_header
from loihi_twin_v2.p07_a2_batch import COMPILED_FINGERPRINT, DDR_SHA256
from loihi_twin_v2.p07_a4_protocol import (
    TEST_FILES, FRAME_COUNT, BATCH_COUNT, SCHEMA,
    download_canonical_official_test, immutable_plan,
    load_canonical_official_test, write_plan,
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    modes = p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--review", action="store_true",
                       help="safe pre-unseal review: NO MNIST TEST data access")
    modes.add_argument("--download-test", action="store_true",
                       help="EXPLICIT official TEST unseal / canonical archive download")
    modes.add_argument("--prepare", action="store_true",
                       help="EXPLICIT official TEST unseal / generate 625 locked batches")
    p.add_argument("--i-accept-unseal", action="store_true",
                   help="required for --download-test or --prepare")
    p.add_argument("--test-data-dir", type=Path, default=Path("data/mnist_official_test_raw"))
    p.add_argument("--candidate-dir", type=Path,
                   default=Path("artifacts/p06_a3_candidate_seed20261013"))
    p.add_argument("--ddr-file", type=Path, default=Path(
        "artifacts/p06_a4_static_ddr_seed20261013/core0_initial_p02_ddr_512k.bin"))
    p.add_argument("--out", type=Path, help="new prepared 625-batch output directory")
    args = p.parse_args()
    if args.review:
        print("P07_A4_PROTOCOL="+SCHEMA)
        print("P07_A4_OFFICIAL_DENOMINATOR="+str(FRAME_COUNT))
        print("P07_A4_PHYSICAL_BATCHES="+str(BATCH_COUNT))
        print("P07_A4_FRAMES_PER_BATCH=16")
        print("P07_A4_MODE=FULL_CANONICAL_ORIGINAL_IDX_ORDER")
        for _, (name, md5) in TEST_FILES.items():
            print(f"P07_A4_REQUIRED_TEST_ARCHIVE={name} MD5={md5}")
        print("P07_A4_TEST_STATUS=SEALED_NOT_OPENED")
        print("P07_A4_RUN_BUDGET=625_INDEPENDENT_JTAG_A53_LAUNCHES")
        print("P07_A4_REVIEW_PASS=1")
        return

    if not args.i_accept_unseal:
        p.error(
            "official TEST access denied until user knowingly supplies "
            "--i-accept-unseal AFTER precommitting the full 10000/625-run protocol"
        )
    if args.download_test:
        if args.out is not None:
            p.error("--download-test does not take --out")
        download_canonical_official_test(args.test_data_dir)
        official = load_canonical_official_test(args.test_data_dir)
        for name, info in official.manifest["archives"].items():
            print(f"P07_A4_OFFICIAL_{name.upper()}_SHA256={info['compressed_sha256']}")
            print(f"P07_A4_OFFICIAL_{name.upper()}_IDX_SHA256={info['decoded_idx_sha256']}")
        print("P07_A4_OFFICIAL_TEST_UNSEALED_PROVENANCE_PASS=1")
        print("P07_A4_KV260_OFFICIAL_TEST=NOT_RUN")
        return

    # Keep --review and --download-test independent of torch. These
    # preflight/explicit provenance modes are valuable in minimal CI
    # environments and must not have a hidden checkpoint dependency.
    from loihi_twin_v2.p06_a3_training import load_candidate, integer_weights_sha256
    from loihi_twin_v2.p06_a4_snapshot import (
        compile_and_check_traces, require_pinned_training_candidate,
    )
    from loihi_twin_v2.p07_a1_ingress import mapping_from_compiled

    if args.out is None:
        p.error("--prepare requires a NEW --out directory")
    if args.out.exists():
        p.error("P07-A4 immutable official TEST bundle already exists; refuse overwrite")
    # Confirm immutable physical baseline BEFORE assembling TEST inputs.
    ddr = args.ddr_file.read_bytes()
    if hashlib.sha256(ddr).hexdigest() != DDR_SHA256:
        raise ValueError("wrong frozen P07-A4 full DDR file SHA256")
    header = parse_ddr_context_header(ddr, verify_payload=True)
    if (header.logical_core_id, header.compartment_count,
            header.synapse_count, header.route_count) != (0, 42, 25408, 32):
        raise ValueError("wrong frozen Track A P02 DDR context")
    model, candidate = load_candidate(args.candidate_dir)
    require_pinned_training_candidate(candidate, integer_weights_sha256(model))
    image, compiled, traces = compile_and_check_traces(model, ())
    if traces or image.core_id != 0 or compiled.fingerprint != COMPILED_FINGERPRINT:
        raise ValueError("frozen Track A model/compiler drift")
    official = load_canonical_official_test(args.test_data_dir)
    plan, batches = immutable_plan(official, mapping_from_compiled(compiled))
    write_plan(args.out, plan, batches)
    print("P07_A4_TEST_ARCHIVE_MD5_AND_IDX_PASS=1")
    print("P07_A4_FULL_TEST_CORPUS=10000")
    print("P07_A4_PHYSICAL_BATCHES=625")
    print("P07_A4_PREPARED_CANONICAL_ORIGINAL_ORDER=1")
    print("P07_A4_OFFICIAL_TEST_STATUS=UNSEALED_NOT_SCORED")
    print("P07_A4_BOARD_STATUS=NOT_RUN")
    print("P07_A4_PREPARE_HOST_PASS=1")
    print("P07_A4_CORPUS_DIR="+str(args.out.resolve()))


if __name__ == "__main__":
    main()
