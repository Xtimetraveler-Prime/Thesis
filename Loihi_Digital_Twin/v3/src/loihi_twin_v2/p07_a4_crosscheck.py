"""Direct FPGA-to-FPGA P07-A3.3 -> A4.2c cross-protocol audit.

Read ACTUAL prior eight P07-A3.3 primary 64KiB JTAG mailboxes and
ACTUAL new A4.2c one-launch 1MiB result journal, require every
26x10 output spike bit/readout/route/event field identical for each
of the exact same first 128 TRAIN-derived validation images. Compare
frame-0 full compartment trace byte-for-byte as an independent
cross-firmware regression.

This is NOT a software oracle, simulation, or official MNIST TEST
accuracy gate. It must accompany, not replace, p07_a4_2_verify.py.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import struct

from .p07_a2_batch import parse_batch
from .p07_a2_evidence import TRACE_SIZE, parse_evidence
from .p07_a4_stream import parse_stream, parse_journal, sha256

SCHEMA_A3 = "p07-a3-3-validation128-restart-v1"
A3_BATCHES = 8
A3_BATCH_SIZE = 16
FRAME_COUNT = 128


@dataclass(frozen=True)
class CrosscheckSummary:
    frames: int
    prior_primary_batches: int
    selected_trace_exact: bool


def _json(path: Path) -> dict:
    raw=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw,dict):raise ValueError("A4.2c malformed evidence JSON: "+str(path))
    return raw


def compare_prior_physical(
    *, a4_stage: Path, a4_journal: Path, a4_trace: Path,
    a3_protocol: Path, a3_evidence: Path,
) -> CrosscheckSummary:
    """Fail closed on omitted, reordered, tampered or nonphysical evidence."""
    meta=_json(a4_stage/"p07_a4_2a_stage_manifest.json")
    if (meta.get("schema")!="p07-a4-2a-persistent-ddr-stage-v1" or
        meta.get("scope")!="TRAIN_DERIVED_VALIDATION_FIRST_128" or
        meta.get("frame_count")!=FRAME_COUNT or
        meta.get("trace_index")!=0 or
        meta.get("official_mnist_test")!="SEALED"):
        raise ValueError("A4.2c crosscheck requires exact preselected 128 TRAIN validation images, trace frame 0")
    paths={
        "descriptor":"p07_a4_descriptor_256.bin",
        "mapping":"p07_a4_mapping_1568.bin",
        "pixels":"p07_a4_pixels_raw.bin",
        "zero_journal_1m":"p07_a4_journal_initial_1m.bin",
    }
    inputs={key:(a4_stage/filename).read_bytes() for key,filename in paths.items()}
    for key,data in inputs.items():
        if sha256(data)!=meta.get("sha256",{}).get(key):
            raise ValueError("A4.2c crosscheck staged A4 source hash changed: "+key)
    stream=parse_stream(inputs["descriptor"],inputs["mapping"],inputs["pixels"])
    results=parse_journal(a4_journal.read_bytes(),stream)
    if len(results)!=FRAME_COUNT:
        raise ValueError("A4.2c crosscheck missing persistent physical image results")
    new_trace=a4_trace.read_bytes()
    if len(new_trace)!=65536 or any(new_trace[TRACE_SIZE:]):
        raise ValueError("A4.2c crosscheck new physical selected trace corrupted")
    a4_ledger=_json(a4_stage/"p07_a4_2a_validation_labels_HOST_ONLY.json")
    if (a4_ledger.get("official_mnist_test")!="SEALED" or
        len(a4_ledger.get("rows",[]))!=FRAME_COUNT or
        len(a4_ledger.get("indices",[]))!=FRAME_COUNT):
        raise ValueError("A4.2c incomplete TRAIN-derived host-only label ledger")
    a3_plan=_json(a3_protocol/"p07_a3_3_protocol.json")
    if (a3_plan.get("schema")!=SCHEMA_A3 or
        a3_plan.get("primary_unique_frames")!=FRAME_COUNT or
        a3_plan.get("primary_batches")!=A3_BATCHES or
        len(a3_plan.get("batches",[]))!=A3_BATCHES or
        a3_plan.get("official_mnist_test")!="SEALED"):
        raise ValueError("A3.3 prior precommitted physical plan changed")
    indices=a3_plan.get("selected_source_indices",[])
    if (indices!=a4_ledger["indices"] or len(indices)!=FRAME_COUNT or
        len(set(indices))!=FRAME_COUNT or
        sha256(b"".join(struct.pack("<I",i) for i in indices))!=
         a3_plan.get("selected_indices_le32_sha256")):
        raise ValueError("A4.2c persistent source order differs from A3.3")
    a3_report=_json(a3_evidence/"p07_a3_3_validation128_report.json")
    if (a3_report.get("selected_indices_le32_sha256")!=
          a3_plan["selected_indices_le32_sha256"] or
        a3_report.get("primary_unique_frames")!=FRAME_COUNT or
        a3_report.get("denominator")!=FRAME_COUNT or
        a3_report.get("physical_launches")!=10 or
        a3_report.get("repeat_count")!=2 or
        a3_report.get("official_mnist_test")!="SEALED" or
        len(a3_report.get("frames",[]))!=FRAME_COUNT or
        not isinstance(a3_report.get("mailbox_sha256_by_run"),dict)):
        raise ValueError("A4.2c prior A3.3 physical acceptance report incomplete")

    for batch_idx in range(A3_BATCHES):
        batch_dir=a3_protocol/f"batch_{batch_idx:02d}"
        batch_info=_json(batch_dir/"p07_a2_manifest.json")
        prior_labels=_json(batch_dir/"p07_a3_3_labels.json")
        header=(batch_dir/"p07_a2_header_64.bin").read_bytes()
        payload=(batch_dir/"p07_a2_ingress_payload.bin").read_bytes()
        expected=a3_plan["batches"][batch_idx]
        if (expected.get("name")!=f"batch_{batch_idx:02d}" or
            expected.get("header_sha256")!=sha256(header) or
            expected.get("payload_sha256")!=sha256(payload) or
            batch_info.get("sha256",{}).get("header")!=sha256(header) or
            batch_info.get("sha256",{}).get("payload")!=sha256(payload) or
            batch_info.get("selected_source_indices")!=indices[16*batch_idx:16*(batch_idx+1)] or
            len(prior_labels.get("rows",[]))!=A3_BATCH_SIZE):
            raise ValueError(f"A4.2c original A3.3 immutable batch_{batch_idx:02d} changed")
        run_id=f"batch_{batch_idx:02d}_primary"
        run_dir=a3_evidence/run_id
        log=(run_dir/"verify.log").read_text(encoding="utf-8")
        if "P07_A2_PHYSICAL_TRACES_EXACT=1" not in log:
            raise ValueError(f"A4.2c A3.3 original physical verifier pass missing: {run_id}")
        old_raw=(run_dir/"p07_a2_mailbox.bin").read_bytes()
        if sha256(old_raw)!=a3_report["mailbox_sha256_by_run"].get(run_id):
            raise ValueError(f"A4.2c original A3.3 physical mailbox digest changed: {run_id}")
        old=parse_evidence(old_raw,header,payload)
        if len(old.frames)!=A3_BATCH_SIZE or old.trace_frame!=0:
            raise ValueError(f"A4.2c original A3.3 trace/frame selection changed: {run_id}")
        prior_records=parse_batch(header,payload)
        for local, (prev,record) in enumerate(zip(old.frames,prior_records)):
            i=batch_idx*A3_BATCH_SIZE+local
            now=results[i]
            previous_label=prior_labels["rows"][local]
            current_label=a4_ledger["rows"][i]
            prior_report=a3_report["frames"][i]
            if (previous_label.get("frame")!=local or
                previous_label.get("source_index")!=indices[i] or
                previous_label.get("pixels_sha256")!=sha256(stream.image(i)) or
                previous_label.get("label")!=current_label.get("label") or
                previous_label.get("ingress_sha256")!=sha256(record) or
                current_label.get("position")!=i or
                current_label.get("source_index")!=indices[i] or
                current_label.get("pixels_sha256")!=sha256(stream.image(i)) or
                prior_report.get("frame")!=i or
                prior_report.get("source_index")!=indices[i] or
                prior_report.get("truth")!=current_label.get("label") or
                prior_report.get("prediction")!=prev.predicted or
                prior_report.get("silent")!=int(prev.silent) or
                prior_report.get("image_sha256")!=sha256(stream.image(i))):
                raise ValueError(f"A4.2c physical dataset/provenance mismatch frame={i}")
            if record!=stream.ingress(i):
                raise AssertionError(f"A4.2c ORIGINAL input P07-A1 record mismatch frame={i}")
            pairs=(
                ("spikes_26x10",prev.output_spikes,now.output_spikes),
                ("counts",prev.counts,now.counts),
                ("predicted",prev.predicted,now.predicted),
                ("silent",prev.silent,now.all_silent),
                ("routes",prev.routed_packets,now.routes),
                ("last_discard",prev.dropped_packets,now.discarded),
                ("external_events",prev.external_event_count,now.external_events),
            )
            for key,left,right in pairs:
                if left!=right:
                    raise AssertionError(
                        f"A4.2c CROSS-DEVICE FIRST mismatch frame={i} field={key} "
                        f"old={left} persistent={right}"
                    )
        if batch_idx==0 and new_trace[:TRACE_SIZE]!=old.trace:
            raise AssertionError("A4.2c selected frame0 full 26x42 trace differs from accepted A3.3 physical trace")

    return CrosscheckSummary(FRAME_COUNT,A3_BATCHES,True)
