"""Strict precommitted first1024 TRAIN-derived validation physical evidence gate.

No official TEST data or JTAG actions. This uses original XSDB logs and
six preserved binary staging readbacks from each actual KV260 launch,
checks all 1024 per-frame CRC-protected 26x10-bit hardware outputs via the
P07A4R01 decoder, and compares complete 1MiB/64KiB binary artifacts
across independent user-rebooted launches. The heavy independent frozen
neural P03 packed oracle is run by scripts/p07_a4_2_verify.py and MUST
be attested in the immutable physical verify.log for each run.
"""
from __future__ import annotations

import json
from pathlib import Path

from .p07_a4_restart import _read_run, ELF_SHA256, XSA_SHA256
from .p07_a4_stream import parse_stream, sha256
from .p07_a4_validation import (
    FRAME_COUNT, TRACE_FRAME, SCOPE, indices_le32_sha256,
)

STAGE_FILES={
    "descriptor":"p07_a4_descriptor_256.bin",
    "mapping":"p07_a4_mapping_1568.bin",
    "pixels":"p07_a4_pixels_raw.bin",
    "zero_journal_1m":"p07_a4_journal_initial_1m.bin",
}


def stage_1024(path: Path):
    meta=json.loads((path/"p07_a4_2a_stage_manifest.json").read_text())
    if (meta.get("schema")!="p07-a4-2a-persistent-ddr-stage-v1" or
        meta.get("scope")!=SCOPE or meta.get("frame_count")!=FRAME_COUNT or
        meta.get("trace_index")!=TRACE_FRAME or
        meta.get("official_mnist_test")!="SEALED" or
        meta.get("physical_hardware")!="NOT_RUN"):
        raise ValueError("A4.2c requires fixed first1024 TRAIN-only source and last-image trace")
    raw={key:(path/name).read_bytes() for key,name in STAGE_FILES.items()}
    for key,buffer in raw.items():
        if sha256(buffer)!=meta.get("sha256",{}).get(key):
            raise ValueError("A4.2c first1024 stage SHA256 changed: "+key)
    stream=parse_stream(raw["descriptor"],raw["mapping"],raw["pixels"])
    if stream.image_count!=FRAME_COUNT or stream.trace_index!=TRACE_FRAME:
        raise ValueError("A4.2c first1024 immutable descriptor/sample selection changed")
    ledger=json.loads((path/"p07_a4_2a_validation_labels_HOST_ONLY.json").read_text())
    indices=ledger.get("indices")
    rows=ledger.get("rows")
    if (ledger.get("scope")!=SCOPE or ledger.get("official_mnist_test")!="SEALED" or
        ledger.get("source")!="canonical TRAIN-only IDX" or
        not isinstance(indices,list) or not isinstance(rows,list) or
        len(indices)!=FRAME_COUNT or len(rows)!=FRAME_COUNT or
        len(set(indices))!=FRAME_COUNT or
        any(type(index) is not int or not 0 <= index < 60000 for index in indices) or
        ledger.get("selected_indices_le32_sha256")!=indices_le32_sha256(tuple(indices))):
        raise ValueError("A4.2c first1024 TRAIN source index ledger/order invalid")
    for i,row in enumerate(rows):
        pixel=stream.image(i)
        if (row.get("position")!=i or row.get("source_index")!=indices[i] or
            type(row.get("label")) is not int or not 0<=row["label"]<=9 or
            row.get("pixels_sha256")!=sha256(pixel)):
            raise ValueError(f"A4.2c validation1024 source pixel/label provenance invalid at {i}")
    return meta,stream,ledger


def verify_1024(*, stage: Path, primary: Path,
                repeat: Path | None = None) -> dict:
    """Read-only admission for independent physical 1024 primary/cold repeat."""
    meta,stream,ledger=stage_1024(stage)
    first=_read_run(stage,primary,stream,expected_frames=FRAME_COUNT)
    if first.complete_frames!=FRAME_COUNT:
        raise ValueError("A4.2c primary did not physically complete 1024 image results")
    result={
        "schema":"p07-a4-2c-1024-long-persistent-cold-repeat-v1",
        "scope":SCOPE,"official_mnist_test":"SEALED",
        "selected_source_indices_le32_sha256":ledger["selected_indices_le32_sha256"],
        "unique_train_validation_images":FRAME_COUNT,
        "frozen_elf_sha256":ELF_SHA256,"frozen_xsa_sha256":XSA_SHA256,
        "descriptor_sha256":meta["sha256"]["descriptor"],
        "pixel_stream_sha256":meta["sha256"]["pixels"],
        "selected_trace_image":TRACE_FRAME,
        "primary":first.__dict__,
        "status":"PRIMARY_ACCEPTED_REPEAT_NOT_RUN",
        "operator_reboot_attestation":"required before independent cold restart; not cryptographically proven",
    }
    if repeat is None:return result
    if repeat.resolve()==primary.resolve():
        raise ValueError("A4.2c larger repeat must use a NEW independent evidence directory")
    second=_read_run(stage,repeat,stream,expected_frames=FRAME_COUNT)
    if second.complete_frames!=FRAME_COUNT:
        raise ValueError("A4.2c second launch missing completed images")
    if second.bit_sha256!=first.bit_sha256 or second.ltx_sha256!=first.ltx_sha256:
        raise ValueError("A4.2c larger repeat bitstream differs from primary")
    if ((primary/"p07_a4_journal_1m.bin").read_bytes() !=
        (repeat/"p07_a4_journal_1m.bin").read_bytes()):
        raise AssertionError("A4.2c 1024 full 1MiB physical journal differs across independent boots")
    if ((primary/"p07_a4_trace_64k.bin").read_bytes() !=
        (repeat/"p07_a4_trace_64k.bin").read_bytes()):
        raise AssertionError("A4.2c 1024 selected last-image full 64KiB physical trace differs")
    result.update(
        repeat=second.__dict__,physical_launches=2,
        physical_frame_executions=2*FRAME_COUNT,
        full_journal_1m_byte_exact=True,selected_trace_64k_byte_exact=True,
        status="PRIMARY_AND_COLD_REPEAT_VERIFIED_PENDING_PHYSICAL_FAILURE_TEST",
    )
    return result
