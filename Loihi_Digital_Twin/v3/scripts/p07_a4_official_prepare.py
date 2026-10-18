#!/usr/bin/env python3
"""Locked persistent full10000 OFFICIAL MNIST TEST source preparation.

--review is safe, does not open any t10k file, no downloads.
Any official access requires EXACT user --i-accept-unseal and separate
--i-accept-one-trace-policy, plus read-only acceptance of actual
KV260 physical descriptor-fault evidence BEFORE accessing t10k.
Never scores predictions; labels are HOST ONLY and never sent to board.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from loihi_twin_v2.p07_a4_protocol import (
    TEST_FILES, download_canonical_official_test,load_canonical_official_test,
)
from loihi_twin_v2.p07_a4_fault import verify_physical_fault
from loihi_twin_v2.p07_a4_official import (
    TRACE_INDEX,STAGE_SCHEMA,write_official_stage,check_official_stage,
)
from loihi_twin_v2.p07_a2_batch import DDR_SHA256, COMPILED_FINGERPRINT


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--review",action="store_true",
                      help="SAFE: never access canonical TEST")
    mode.add_argument("--prepare",action="store_true",
                      help="EXPLICIT official TEST unseal after physical-fault acceptance")
    p.add_argument("--i-accept-unseal",action="store_true")
    p.add_argument("--i-accept-one-trace-policy",action="store_true",
                   help="accept ONE 26x42 full trace for image9999; all 10000 still get 26x10 output history")
    p.add_argument("--download-test",action="store_true",
                   help="explicit download pinned official TEST archives; only with --prepare")
    p.add_argument("--fault-stage-dir",type=Path)
    p.add_argument("--fault-evidence-dir",type=Path)
    p.add_argument("--test-data-dir",type=Path,default=Path("data/mnist_official_test_raw"))
    p.add_argument("--candidate-dir",type=Path,default=Path(
        "artifacts/p06_a3_candidate_seed20261013"))
    p.add_argument("--ddr-file",type=Path,default=Path(
        "artifacts/p06_a4_static_ddr_seed20261013/core0_initial_p02_ddr_512k.bin"))
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    if args.review:
        if args.download_test or args.out is not None:
            p.error("--review may NOT download, stage or open official TEST files")
        print("P07_A4_OFFICIAL_TEST=SEALED")
        print("P07_A4_3_PROTOCOL="+STAGE_SCHEMA)
        print("P07_A4_3_FULL_ORIGINAL_IDX_ORDER_IMAGES=10000")
        print("P07_A4_3_SELECTED_FULL_TRACE_IMAGE="+str(TRACE_INDEX))
        print("P07_A4_3_FULL_OUTPUT_SPIKE_HISTORIES=10000")
        print("P07_A4_3_REQUIRES_PHYSICAL_FAULT_GATE=1")
        for name,md5 in TEST_FILES.values():
            print(f"P07_A4_3_CANONICAL_ARCHIVE={name} MD5={md5}")
        print("P07_A4_3_SEALED_REVIEW_PASS=1")
        return
    if (not args.i_accept_unseal or not args.i_accept_one_trace_policy or
        args.out is None or args.fault_stage_dir is None or
        args.fault_evidence_dir is None):
        p.error("official TEST remains sealed until user accepts unseal, "
                "one-trace observability and supplies accepted physical fault evidence")
    if args.out.exists():
        p.error("refuse overwrite: original official full10000 DDR stage exists")

    # Do not even touch canonical test archives before actual physical
    # negative experiment is fully accepted.
    report=verify_physical_fault(stage=args.fault_stage_dir,
                                 evidence=args.fault_evidence_dir)
    if report["status_word"]!="0xDEAD0001" or report["complete_frames"]!=0:
        raise ValueError("official TEST unseal denied: physical pre-dispatch fail-closed not accepted")
    print("P07_A4_3_PREVIOUS_PHYSICAL_FAULT_GATE_PASS=1")

    # Check frozen model and DDR against the already accepted model
    # BEFORE downloading or loading official test.
    from loihi_twin_v2.ddr_abi import parse_ddr_context_header
    from loihi_twin_v2.p06_a3_training import load_candidate,integer_weights_sha256
    from loihi_twin_v2.p06_a4_snapshot import (
        compile_and_check_traces,require_pinned_training_candidate,
    )
    from loihi_twin_v2.p07_a1_ingress import mapping_from_compiled
    master=args.ddr_file.read_bytes()
    if hashlib.sha256(master).hexdigest()!=DDR_SHA256:
        raise ValueError("official TEST unseal refused: immutable master SHA differs")
    hdr=parse_ddr_context_header(master,verify_payload=True)
    if (hdr.logical_core_id,hdr.compartment_count,
        hdr.synapse_count,hdr.route_count)!=(0,42,25408,32):
        raise ValueError("official TEST unseal refused: neural core context changed")
    model,candidate=load_candidate(args.candidate_dir)
    require_pinned_training_candidate(candidate,integer_weights_sha256(model))
    image,compiled,traces=compile_and_check_traces(model,())
    if traces or image.core_id!=0 or compiled.fingerprint!=COMPILED_FINGERPRINT:
        raise ValueError("official TEST unseal refused: trained checkpoint drift")
    mapping=mapping_from_compiled(compiled)
    if args.download_test:
        download_canonical_official_test(args.test_data_dir)
    official=load_canonical_official_test(args.test_data_dir)
    write_official_stage(args.out,official,mapping)
    stream,meta,ledger=check_official_stage(args.out,official)
    if stream.image_count!=10000 or len(ledger["rows"])!=10000:
        raise AssertionError("official TEST original-order full denominator corrupted")
    print("P07_A4_3_CANONICAL_ARCHIVE_MD5_IDX_PASS=1")
    print("P07_A4_3_SOURCE_10000_ORIGINAL_ORDER_PASS=1")
    print("P07_A4_3_SELECTED_FULL_TRACE_IMAGE=9999")
    print("P07_A4_3_LABELS_HOST_ONLY=1")
    print("P07_A4_3_STAGING_SELF_CHECK_PASS=1")
    print("P07_A4_3_OFFICIAL_TEST=UNSEALED_NOT_SCORED")
    print("P07_A4_3_KV260=NOT_RUN")
    print("P07_A4_3_STAGE_DIR="+str(args.out.resolve()))


if __name__=="__main__":
    main()
