"""P06-A4.2 immutable candidate/packed-word audit and P02 512KiB DDR seed.

This is a STATIC logical-core record generated with the EXISTING accepted
P02.1 DDR ABI. It is NOT a P05 diagnostic workload, not a full MNIST
event-streaming application, and not a physical FPGA inference result.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from .ddr_abi import (
    P02_DDR_CONTEXT_STRIDE_BYTES, build_initial_ddr_context_record,
    ddr_bank_slice, parse_ddr_context_header,
)
from .hardware_p08 import BackingLogicalContextImage
from .p06_a3_training import integer_weights_sha256, load_candidate
from .p06_a4_snapshot import (
    FREEZE_SCHEMA, PINNED_CHECKPOINT_SHA256,
    PINNED_INTEGER_WEIGHTS_SHA256, PINNED_TRAIN_INDICES_SHA256,
    PINNED_VALIDATION_INDICES_SHA256, compile_and_check_traces,
    packed_word_snapshot, require_pinned_training_candidate,
)
from .p06_input_contract import ENCODER_PROFILE, READOUT_PROFILE

A4_FREEZE_SCHEMA = "p06-a4-p02-ddr-static-seed-v1"
EXPECTED_STREAMS = {
    "axon_index_le16_word_le64.bin": (8160, "bfec16a76eab97afd5d208e7c1dfd9e6f75ce9f3ff6f1a8f194d52a998d1de72"),
    "compartment_config_le128.bin": (672, "a3b520f46a65cc8ee7c1f616337d535d20b6d4f7200ababcd271d1eac1381b5a"),
    "compartment_state_le64.bin": (336, "52a3e0804d93dc525ec3c67ef8ac5b01756ecf0513e36f3c19435e4c82cb5d29"),
    "route_descriptor_index_le16_word_le32.bin": (192, "56769029563e60e87d68082e3a11977ec56cf267291ab42893a5f4721edb3510"),
    "route_words_le32.bin": (128, "0caaba89a0927126aaee06fff208c07c41f380ed9c4f18bb5cf2ccea6ae4a806"),
    "synapses_le64.bin": (203264, "d83b4e401cae33f92a2cba7c53f2f681453f88395b65d503c2c590f6c60e31d7"),
}
EXPECTED_IMAGE = {
    "axon_bindings": 816, "compartments": 42, "logical_core_id": 0,
    "profile": "p03-k26-one-core-sat24-v1-compat",
    "route_descriptors": 32, "route_words": 32, "synapse_words": 25408,
}
DDRBIN = "core0_initial_p02_ddr_512k.bin"
FROZEN_MANIFEST = "p06_a4_static_ddr_freeze_manifest.json"


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def audit_snapshot(snapshot_dir: str | Path) -> dict:
    """Reject any missing, modified, substituted or unverified P03 stream."""
    folder = Path(snapshot_dir)
    path = folder / "a4_software_snapshot_manifest.json"
    raw_manifest = path.read_bytes()
    manifest = json.loads(raw_manifest)
    if manifest.get("schema") != FREEZE_SCHEMA:
        raise ValueError("wrong P06-A4.1 software snapshot schema")
    if manifest.get("status") != "SOFTWARE_WORD_SNAPSHOT / PHYSICAL_GATE_NOT_RUN":
        raise ValueError("unexpected software-snapshot status")
    if manifest.get("accepted_training_candidate_sha256") != PINNED_CHECKPOINT_SHA256:
        raise ValueError("A4 snapshot checkpoint hash does not match frozen candidate")
    if manifest.get("accepted_integer_weights_sha256") != PINNED_INTEGER_WEIGHTS_SHA256:
        raise ValueError("A4 snapshot integer weight hash does not match frozen candidate")
    if manifest.get("training_best_epoch") != 8 or manifest.get("training_best_validation_accuracy") != 0.9439:
        raise ValueError("A4 snapshot validation selection changed")
    if manifest.get("training_validation_go_floor") != 0.60:
        raise ValueError("predeclared 60% validation GO threshold changed")
    dataset = manifest.get("canonical_dataset_manifest", {})
    if dataset.get("train_indices_le32_sha256") != PINNED_TRAIN_INDICES_SHA256:
        raise ValueError("training split hash mismatch")
    if dataset.get("validation_indices_le32_sha256") != PINNED_VALIDATION_INDICES_SHA256:
        raise ValueError("validation split hash mismatch")
    if dataset.get("official_test_set") != "sealed: no t10k archives opened":
        raise ValueError("official test set status changed")
    if manifest.get("encoder") != ENCODER_PROFILE or manifest.get("readout") != READOUT_PROFILE:
        raise ValueError("encoder/readout freeze mismatch")
    if manifest.get("total_timesteps") != 26 or manifest.get("reset_per_image") is not True:
        raise ValueError("26-step reset contract changed")
    if manifest.get("image") != EXPECTED_IMAGE:
        raise ValueError("P03 packed image resource identity does not match native result")
    parity = manifest.get("packet_gate", {})
    if (parity.get("frames"), parity.get("timesteps_per_frame"), parity.get("status")) != (
        5, 26, "ALL_TRACES_EXACTLY_EQUAL"
    ):
        raise ValueError("missing accepted five-frame four-way parity gate")
    if manifest.get("official_test_status") != "SEALED / NOT OPENED":
        raise ValueError("official test status not sealed")
    if manifest.get("hardware_status") != "NO PHYSICAL FPGA TEST / NO A53 DDR PAGE IMAGE":
        raise ValueError("unexpected hardware evidence status")
    streams = manifest.get("packed_word_streams", {})
    if set(streams) != set(EXPECTED_STREAMS):
        raise ValueError("missing or extra P03 frozen word streams")
    for name, (length, expected_sha) in EXPECTED_STREAMS.items():
        blob = (folder / name).read_bytes()
        if len(blob) != length or _hash(blob) != expected_sha:
            raise ValueError("frozen P03 stream bytes or SHA256 mismatch: " + name)
        if streams[name] != {"bytes": length, "sha256": expected_sha}:
            raise ValueError("snapshot manifest stream metadata mismatch: " + name)
    trace_blob = (folder / "diagnostic_traces.json").read_bytes()
    if _hash(trace_blob) != manifest.get("diagnostic_traces_sha256"):
        raise ValueError("diagnostic trace SHA256 mismatch")
    traces = json.loads(trace_blob)
    if not isinstance(traces, list) or len(traces) != 5:
        raise ValueError("expected five diagnostic frames")
    for i, item in enumerate(traces):
        if len(item.get("timesteps", [])) != 26:
            raise ValueError(f"diagnostic frame {i} wrong timestep count")
        if len(item.get("output_counts", [])) != 10:
            raise ValueError(f"diagnostic frame {i} wrong readout width")
        if item["timesteps"][-1].get("tick") != 25:
            raise ValueError(f"diagnostic frame {i} lacks drain tick")
    return {"manifest": manifest, "manifest_sha256": _hash(raw_manifest)}


def _verify_ddr_matches_p03_words(record: bytes, image) -> None:
    """Check P02 context banks against P03 snapshot values independently."""
    def byte_stream(values, width):
        return b"".join(v.to_bytes(width, "little", signed=False) for v in values)

    dense = (
        ("config", image.config_words, 16),
        ("state", image.state_words, 8),
        ("synapse", image.synapse_words, 8),
        ("route", image.route_words, 4),
    )
    for name, words, width in dense:
        raw = record[ddr_bank_slice(name)]
        data = byte_stream(words, width)
        if not raw.startswith(data) or any(raw[len(data):]):
            raise AssertionError("static DDR bank mismatch/nonzero tail: " + name)
    for name, entries, width in (
        ("axon", image.axon_words, 8),
        ("route_descriptor", image.route_descriptor_words, 4),
    ):
        raw = record[ddr_bank_slice(name)]
        known = {entry.index: entry.word for entry in entries}
        for index in range(len(raw) // width):
            actual = int.from_bytes(raw[index * width : (index + 1) * width], "little")
            if actual != known.get(index, 0):
                raise AssertionError(f"static DDR {name} sparse index {index} mismatch")
    for name in ("event0", "event1", "trace", "packet"):
        if any(record[ddr_bank_slice(name)]):
            raise AssertionError("nonzero initial DDR mutable bank: " + name)


def freeze_static_ddr(
    candidate_dir: str | Path, snapshot_dir: str | Path, output_dir: str | Path
) -> dict:
    """Verify and produce a byte-exact 512KiB static P02 record.

    No new training, MNIST official test access, or runtime event stream.
    """
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError("static DDR freeze output exists; refuse overwrite")
    checked = audit_snapshot(snapshot_dir)
    model, manifest = load_candidate(candidate_dir)
    require_pinned_training_candidate(manifest, integer_weights_sha256(model))
    if manifest["source_dataset"] != checked["manifest"]["canonical_dataset_manifest"]:
        raise ValueError("trained checkpoint/snapshot dataset provenance mismatch")
    image, compiled, no_traces = compile_and_check_traces(model, ())
    if no_traces:
        raise AssertionError("unexpected trace during static DDR layout stage")
    streams = packed_word_snapshot(image)
    for name, data in streams.items():
        if (len(data), _hash(data)) != EXPECTED_STREAMS[name]:
            raise AssertionError("DDR source compiler did not reproduce accepted P03 word bank " + name)
    if compiled.fingerprint != checked["manifest"]["deployment_fingerprint"]:
        raise AssertionError("compiled deployment fingerprint differs from accepted P03 snapshot")
    if compiled.source_fingerprint != checked["manifest"]["network_fingerprint"]:
        raise AssertionError("compiled network fingerprint differs from accepted P03 snapshot")
    record = build_initial_ddr_context_record(
        BackingLogicalContextImage(logical_core_id=image.core_id, image=image)
    )
    if len(record) != P02_DDR_CONTEXT_STRIDE_BYTES:
        raise AssertionError("expected 512KiB DDR context record")
    header = parse_ddr_context_header(record, verify_payload=True)
    if (header.logical_core_id, header.compartment_count, header.synapse_count, header.route_count) != (
        0, 42, 25408, 32
    ):
        raise AssertionError("P02 DDR header metadata mismatch")
    if (header.current_event_bank, header.event0_count, header.event1_count, header.packet_count) != (0, 0, 0, 0):
        raise AssertionError("DDR context must start with empty event/packet banks")
    _verify_ddr_matches_p03_words(record, image)
    summary = {
        "schema": A4_FREEZE_SCHEMA,
        "state": "STATIC_DDR_INITIAL_CONTEXT_FROZEN / P07_SOFTWARE_AND_BOARD_UNVERIFIED",
        "checkpoint_sha256": PINNED_CHECKPOINT_SHA256,
        "effective_integer_weights_sha256": PINNED_INTEGER_WEIGHTS_SHA256,
        "source_a4_snapshot_manifest_sha256": checked["manifest_sha256"],
        "source_a4_p03_streams": checked["manifest"]["packed_word_streams"],
        "source_compiler_fingerprint": compiled.fingerprint,
        "source_network_fingerprint": compiled.source_fingerprint,
        "encoder": ENCODER_PROFILE, "readout": READOUT_PROFILE,
        "ticks": 26, "reset_each_image": True,
        "trained_validation_accuracy": 0.9439,
        "trained_validation_sample_count": 10000,
        "predeclared_validation_accuracy_floor": 0.60,
        "official_mnist_test": "SEALED / NEVER LOADED",
        "ddr_abi": {"magic": "LTV3CTX1", "version": 1,
                    "size_bytes": len(record), "logical_core_id": 0,
                    "event0_count": 0, "event1_count": 0,
                    "payload_sha256": header.payload_sha256},
        "ddr_file": DDRBIN,
        "ddr_file_sha256": _hash(record),
        "byte_exact_bank_comparison": "PASS",
        "inference_parity": "5 frames x 26 steps x four accepted host engines EXACT",
        "boundary": "NOT a P05 diagnostic header/payload; P07 multi-axon A53 streaming and physical FPGA remain TODO",
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / DDRBIN).write_bytes(record)
    (output / FROZEN_MANIFEST).write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return summary
