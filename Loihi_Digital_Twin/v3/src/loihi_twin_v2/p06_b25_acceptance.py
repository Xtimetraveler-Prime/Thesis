"""P06-B2.5 read-only host-software acceptance and P07-B handoff gate.

Consumes the *existing* local B2.4 freeze with all 33 SHA-indexed assets.
Reuses B2.4 integrity validation (optionally deep) and pins both the
canonical-content digest and original pretty-printed manifest-file SHA256
from the user's native verification. No changes to frozen files, Track A,
MNIST datasets, or hardware. Passing this tool is a P06 HOST-SOFTWARE GO,
NOT a P07-B physical execution or official-MNIST-TEST GO.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .p06_b24_freeze import (
    B24_MANIFEST_NAME, B24_SCHEMA, B24_PROTOCOL_NAME,
    PINNED_B23_FRAMES, PINNED_B23_SOURCE_SHA256,
    PINNED_B23_DEPLOYMENT_SHA256, PINNED_B23_CAPACITY_SHA256,
    PINNED_B22_WEIGHTS_SHA256, PINNED_B22_INTEGER_SHA256,
    sha256_file, verify_frozen_directory,
)

B25_SCHEMA = "p06-b2.5-host-software-acceptance-p07b-readiness-v1"

# Two DIFFERENT hash domains, recorded from the user's original B2.4 run.
PINNED_B24_CANONICAL_MANIFEST_SHA256 = "d01ccd2d5a85b22f81580cd7800933642e19d1a43e8a2f38eac1f6c4d83cab90"
PINNED_B24_MANIFEST_FILE_SHA256 = "d71e2827a81ab1f00ef1e89446540ac04b7d7b34d89b30d46cd6e4ff013c7a63"

EXPECTED_VALIDATION_ORDINALS = (0, 1, 2)
EXPECTED_DDR_CORES = 27
EXPECTED_DDR_RECORD_BYTES = 524288
EXPECTED_DDR_TOTAL_BYTES = 14155776
EXPECTED_FULL_DENSE_CONNECTIONS = 794000


class B25AcceptanceError(ValueError):
    """Rejects source drift, missing provenance or false physical claims."""


def _require_equal(name: str, actual: object, expected: object) -> None:
    if actual != expected:
        raise B25AcceptanceError(f"B2.5 {name} mismatch: {actual!r} != {expected!r}")


def review_freeze_documents(
    manifest: dict, protocol: dict, b23: dict, packed_document: dict,
    *, canonical_hash: str, file_hash: str, verified: dict,
) -> dict:
    """Pure policy checks, testable without creating a fake frozen checkpoint.

    A real B2.5 acceptance must use assess_frozen_handoff so checks are
    preceded by the actual B2.4 SHA/P02 payload/deployment verification.
    """
    if not all(isinstance(x, dict) for x in
               (manifest, protocol, b23, packed_document, verified)):
        raise B25AcceptanceError("B2.5 documents must be mappings")
    _require_equal("freeze schema", manifest.get("schema"), B24_SCHEMA)
    _require_equal("freeze status", manifest.get("status"),
                   "HOST_FROZEN_CANDIDATE_PENDING_NATIVE_ACCEPTANCE")
    _require_equal("freeze bytes SHA", file_hash, PINNED_B24_MANIFEST_FILE_SHA256)
    _require_equal("freeze content SHA", canonical_hash, PINNED_B24_CANONICAL_MANIFEST_SHA256)
    _require_equal("freeze content SHA in file", manifest.get("manifest_sha256"), canonical_hash)
    _require_equal("verified source SHA", verified.get("manifest_sha256"), canonical_hash)
    _require_equal("frozen image count", verified.get("cores_checked"), EXPECTED_DDR_CORES)
    _require_equal("frozen assets", verified.get("files_checked"), 33)
    _require_equal("frozen P02 payload bytes", verified.get("total_initial_ddr_bytes"),
                   EXPECTED_DDR_TOTAL_BYTES)
    _require_equal("official TEST sealed", verified.get("official_mnist_test_status"),
                   "SEALED_NOT_ACCESSED")
    _require_equal("physical KV260 status", verified.get("physical_kv260_execution"), "NOT_TESTED")
    _require_equal("manifest architecture", manifest.get("architecture"), [784, 1000, 10])
    _require_equal("manifest physical", manifest.get("physical_kv260_execution"), "NOT_TESTED")
    _require_equal("host freeze materialized", manifest.get("checkpoint_frozen"), True)
    _require_equal("B2.4 native marker stays original false",
                   manifest.get("user_native_B2_4_accepted"), False)
    _require_equal("trained checkpoint", manifest.get("weights_file_sha256"),
                   PINNED_B22_WEIGHTS_SHA256)
    _require_equal("signed24 integer weights", manifest.get("effective_integer_weights_sha256"),
                   PINNED_B22_INTEGER_SHA256)
    _require_equal("source network SHA", manifest.get("source_network_sha256"),
                   PINNED_B23_SOURCE_SHA256)
    _require_equal("deployment SHA", manifest.get("deployment_sha256"),
                   PINNED_B23_DEPLOYMENT_SHA256)
    _require_equal("B1.1 capacity SHA", manifest.get("capacity_audit_sha256"),
                   PINNED_B23_CAPACITY_SHA256)
    _require_equal("manifest record count", manifest.get("core_count"), EXPECTED_DDR_CORES)
    _require_equal("backing size", manifest.get("backing_bytes"), EXPECTED_DDR_TOTAL_BYTES)
    records = manifest.get("ddr_context_sha256")
    if (not isinstance(records, list) or len(records) != EXPECTED_DDR_CORES
            or any(not isinstance(x, str) or len(x) != 64 for x in records)
            or len(set(records)) != EXPECTED_DDR_CORES):
        raise B25AcceptanceError("missing/reused P02 per-core SHA256 evidence")
    _require_equal("fixed validation ordinals", manifest.get("B2_3_parity_validation_ordinals"),
                   list(EXPECTED_VALIDATION_ORDINALS))
    val = manifest.get("validation_provenance")
    if not isinstance(val, dict):
        raise B25AcceptanceError("missing TRAIN-derived validation provenance")
    for name, expected in (
        ("best_epoch", 6),
        ("TRAIN_derived_validation_count", 10000),
        ("TRAIN_derived_validation_accuracy", 0.9708),
        ("all_silent_validation_count", 0),
    ):
        _require_equal(name, val.get(name), expected)
    _require_equal("trained source in numerical report",
                   b23.get("trained_source_network_sha256"), PINNED_B23_SOURCE_SHA256)
    _require_equal("B2.3 validated frame count", b23.get("validation_frame_count"), 3)
    frames = b23.get("validation_frames")
    if not isinstance(frames, list) or len(frames) != 3:
        raise B25AcceptanceError("B2.3 must contain exactly three preset validation frames")
    for frame, (ordinal, canonical_idx, image_sha, mono_sha, partitioned_sha) in zip(
        frames, PINNED_B23_FRAMES, strict=True,
    ):
        for key, expected in (
            ("validation_ordinal", ordinal), ("canonical_train_idx", canonical_idx),
            ("image_sha256", image_sha), ("monolithic_trace_sha256", mono_sha),
            ("partitioned_trace_sha256", partitioned_sha),
            ("all_26_ticks_full_neuron_parity", True),
        ):
            _require_equal(f"validation ordinal {ordinal} {key}", frame.get(key), expected)
    _require_equal("official TEST protocol version", protocol.get("schema"),
                   "p06-b2.4-sealed-mnist-official-test-protocol-v1")
    _require_equal("official TEST count", protocol.get("test_count"), 10000)
    _require_equal("official TEST seal", protocol.get("current_unseal_status"),
                   "SEALED_NOT_ACCESSED")
    _require_equal("official TEST model selection prohibited",
                   protocol.get("no_model_selection_after_unseal"), True)
    _require_equal("full official TEST prerequisite", protocol.get("test_population"),
                   "canonical MNIST official 10000 TEST images in original IDX order")
    _require_equal("official TEST physical status", protocol.get("board_27_core_run"), "NOT_TESTED")

    original = packed_document.get("manifest")
    if not isinstance(original, dict):
        raise B25AcceptanceError("missing B1.2 native serialized compiler manifest")
    cap = original.get("capacity_audit")
    if not isinstance(cap, dict):
        raise B25AcceptanceError("B1.2 packed capacity audit missing")
    for name, expected in (
        ("source_fingerprint", PINNED_B23_SOURCE_SHA256),
        ("deployment_fingerprint", PINNED_B23_DEPLOYMENT_SHA256),
    ):
        _require_equal("compiler " + name, original.get(name), expected)
    _require_equal("B1.1 checked capacity SHA", cap.get("audit_sha256"),
                   PINNED_B23_CAPACITY_SHA256)
    _require_equal("packed logical cores", cap.get("logical_core_count"), EXPECTED_DDR_CORES)
    _require_equal("packed DDR backing", cap.get("backing_bytes"), EXPECTED_DDR_TOTAL_BYTES)
    _require_equal("three P05 resident slots", cap.get("resident_context_slots"), 3)
    _require_equal("one P05 physical engine", cap.get("physical_hls_engines"), 1)
    _require_equal("no FPGA scaled physical evidence", cap.get("physical_kv260_execution"), "NOT_TESTED")
    cores = cap.get("cores")
    if (not isinstance(cores, list) or len(cores) != EXPECTED_DDR_CORES
            or {r["core_id"] for r in cores} != set(range(EXPECTED_DDR_CORES))):
        raise B25AcceptanceError("B1.1 per-core occupancy list incomplete")
    limits = {
        "compartments": 1024, "input_axons": 4096,
        "route_words": 4096, "synapse_words": 32768,
        "logical_synapse_bytes": 131072,
        "worst_external_events": 4096, "worst_routed_events": 4096,
        "worst_current_bank_events": 4096, "worst_emitted_packets": 4096,
    }
    for core in cores:
        cid = core["core_id"]
        for name, limit in limits.items():
            used = core.get(name)
            if type(used) is not int or not 0 <= used <= limit:
                raise B25AcceptanceError(
                    f"core {cid}: B1.1 {name} outside accepted physical packing budget")
        if (core.get("record_bytes") != EXPECTED_DDR_RECORD_BYTES
                or core.get("initial_ddr_sha256") != records[cid]
                or core["worst_current_bank_events"]
                   != core["worst_external_events"] + core["worst_routed_events"]):
            raise B25AcceptanceError(f"core {cid}: P02 record SHA/event-budget identity changed")
    return {
        "architecture": [784, 1000, 10],
        "connections_full_dense": EXPECTED_FULL_DENSE_CONNECTIONS,
        "best_epoch": val["best_epoch"],
        "train_derived_validation_count": val["TRAIN_derived_validation_count"],
        "train_derived_validation_accuracy": val["TRAIN_derived_validation_accuracy"],
        "all_silent_validation_count": val["all_silent_validation_count"],
        "three_26_tick_validation_frames_verified": [r["validation_ordinal"] for r in frames],
        "logical_cores": 27,
        "initial_27core_ddr_backing_bytes": EXPECTED_DDR_TOTAL_BYTES,
        "maximum_per_core_logical_synapse_bytes": max(c["logical_synapse_bytes"] for c in cores),
        "maximum_per_core_current_bank_events": max(c["worst_current_bank_events"] for c in cores),
        "physical_resident_context_slots": 3,
        "physical_hls_engine_count": 1,
    }


def assess_frozen_handoff(
    frozen_dir: str | Path, *, deep: bool = False,
) -> dict:
    """Read-only B2 software acceptance; physical run remains explicitly blocked."""
    root = Path(frozen_dir)
    frozen = verify_frozen_directory(root, deep=deep)
    manifest_path = root / B24_MANIFEST_NAME
    file_sha = sha256_file(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    protocol = json.loads((root / B24_PROTOCOL_NAME).read_text(encoding="utf-8"))
    b23 = json.loads((root / "b23_validation_parity.json").read_text(encoding="utf-8"))
    packed = json.loads((root / "packed_deployment.json").read_text(encoding="utf-8"))
    details = review_freeze_documents(
        manifest, protocol, b23, packed,
        canonical_hash=frozen["manifest_sha256"], file_hash=file_sha,
        verified=frozen,
    )
    return {
        "schema": B25_SCHEMA,
        "B2_5_native_user_accepted": False,
        "software_phase": "HOST_SOFTWARE_EXIT_EVIDENCE_COMPLETE_PENDING_B2_5_NATIVE_GATE",
        "B2_4_user_native_verification_attested": True,
        "full_snapshot_file_sha256": file_sha,
        "full_snapshot_canonical_manifest_sha256": frozen["manifest_sha256"],
        "snapshot_assets_verified": frozen["files_checked"],
        "independent_B12_DDR_regeneration_checked": bool(deep),
        "source": details,
        "host_go_for_p07b_design_and_planning": True,
        "go_for_p07b_scaled_physical_execution": False,
        "go_for_official_mnist_test_unseal": False,
        "blocking_P07B_deliverables": [
            "pin operator-approved physical KV260 memory-region/DDR owner map, A53 and fabric firmware revisions",
            "implement and byte-validate P06B13I1/P06B13R1 scaled multi-core ingress and next-epoch route parser in A53/PL (not the original P05 single-axon ABI)",
            "implement deterministic 27 logical-core backing ownership, 3 resident contexts and single physical HLS engine including 26-tick RESET and last mutable writeback",
            "prove a physical barrier/next-epoch packet protocol: ordering, overflow checks, one-tick delay and no cross-image stale state",
            "measure actual physical read/write page traffic, PL/PS execution latency and energy with traceable instrumentation (not B1.5 projections)",
            "verify board-vs-host complete 26-tick signed24 state/spike/readout equality on predeclared TRAIN-derived validation frames",
            "obtain separate user P07-B physical acceptance and freeze run IDs before any official TEST unseal",
        ],
        "official_TEST_protocol": {
            "population": protocol["test_population"],
            "count": protocol["test_count"],
            "status": "SEALED_NOT_ACCESSED",
            "threshold_for_unseal": "not before independently accepted P07-B hardware parity and frozen measurement run",
        },
        "physical_kv260_execution": "NOT_TESTED",
        "physical_page_traffic_measured": False,
        "runtime_mutable_ddr_captured": False,
        "no_frozen_files_modified": True,
    }
