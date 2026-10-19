"""B2.3 read-only trained checkpoint -> B1.2 packed audit and B1.4 numerical gate.

Never edits weights or uses MNIST TEST. Full 794k-edge packing is performed
once; each selected validation image executes 26 ticks independently against
both original source-graph LIF oracle and mapped logical cores.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import torch

from .p06_a3_data import load_train_validation
from .p06_b22_training import load_candidate, require_pinned_train_validation
from .p06_b12_partition import B12Options, compile_synapse_aware
from .p06_b14_monolithic import pixel_schedule_independent
from .p06_b14_differential import run_and_compare

B23_SCHEMA = "p06-b2.3-trained-quantized-packed-numerical-audit-v1"
PINNED_B22_WEIGHTS_SHA256 = "93e43915b38cf3c815a125bbab2788e45209f0ccd024d098b25b82a0a8cd0957"
PINNED_B22_INTEGER_SHA256 = "4a20357fc5e77465380c1600e7e82cda515bbafc233fb9e3a1205bca9d00d8b0"


class B23AuditError(ValueError):
    pass


@dataclass(frozen=True)
class B23AuditedCandidate:
    manifest: dict
    network_sha256: str
    deployment_sha256: str
    capacity_audit_sha256: str
    core_count: int
    backing_bytes: int
    worst_current_events: int
    validated_frames: tuple[dict, ...]

    def report(self) -> dict:
        return {
            "schema": B23_SCHEMA,
            "candidate_best_epoch": self.manifest["best_epoch"],
            "candidate_validation_accuracy_train_derived": self.manifest["best_validation"]["accuracy"],
            "candidate_validation_count": self.manifest["best_validation"]["count"],
            "weights_file_sha256": self.manifest["weights_file_sha256"],
            "effective_integer_weights_sha256": self.manifest["effective_integer_weights_sha256"],
            "trained_source_network_sha256": self.network_sha256,
            "compiled_deployment_sha256": self.deployment_sha256,
            "capacity_audit_sha256": self.capacity_audit_sha256,
            "core_count": self.core_count,
            "initial_ddr_backing_bytes": self.backing_bytes,
            "worst_current_events": self.worst_current_events,
            "validation_frames": list(self.validated_frames),
            "validation_frame_count": len(self.validated_frames),
            "full_dense_26_tick_numerics_executed_for_selected_frames": bool(self.validated_frames),
            "checkpoint_frozen": False,
            "B2_4_freeze_accepted": False,
            "official_mnist_test_status": "SEALED_NOT_ACCESSED",
            "physical_kv260_execution": "NOT_TESTED",
        }


def audit_candidate(
    candidate_dir: str | Path, *,
    data_dir: str | Path | None = None,
    validation_ordinals: tuple[int, ...] = (),
) -> B23AuditedCandidate:
    """Pin exact user-attested B2.2 model, audit dense packing and optional frames.

    Validation ordinal 0 means the first image in the deterministic frozen
    validation split, NOT the first raw MNIST IDX image. No labels from TEST.
    """
    model, manifest = load_candidate(candidate_dir)
    if (manifest["weights_file_sha256"] != PINNED_B22_WEIGHTS_SHA256
            or manifest["effective_integer_weights_sha256"] != PINNED_B22_INTEGER_SHA256):
        raise B23AuditError("B2.3 requires exact user-accepted B2.2 checkpoint/integer hashes")
    if (manifest["architecture"] != [784, 1000, 10] or manifest["best_epoch"] != 6
            or manifest["best_validation"]["count"] != 10000
            or manifest["best_validation"]["accuracy"] != 0.9708
            or manifest["best_validation"]["all_silent_count"] != 0
            or manifest["candidate_go"] is not True):
        raise B23AuditError("B2.3 trained topology/validation provenance differs from accepted candidate")
    if (type(validation_ordinals) is not tuple
            or any(type(i) is not int or i < 0 or i >= 10000 for i in validation_ordinals)
            or tuple(sorted(set(validation_ordinals))) != validation_ordinals):
        raise B23AuditError("validation ordinals must be distinct sorted indices in [0,10000)")
    if validation_ordinals and data_dir is None:
        raise B23AuditError("validation parity requires original canonical TRAIN-only data-dir")
    model.eval()
    graph = model.to_network_spec()
    packed = compile_synapse_aware(graph, B12Options(readout_population="readout"))
    audit = packed.capacity_audit
    if audit["logical_core_count"] != 27 or audit["backing_bytes"] != 27 * 524288:
        raise B23AuditError("trained dense graph changed B1.2 27-core backing geometry")
    if any(row["logical_synapse_bytes"] > 131072
           or row["worst_current_bank_events"] > 4096
           for row in audit["cores"]):
        raise B23AuditError("trained graph exceeds B1.1 packed/core event capacity")

    frames = []
    if validation_ordinals:
        split = load_train_validation(data_dir, strict=True)
        require_pinned_train_validation(split)
        for ordinal in validation_ordinals:
            original_idx = split.validation_indices[ordinal]
            raw = split.images[original_idx * 784:(original_idx + 1) * 784]
            label = int(split.labels[original_idx])
            schedule = {"pixels": pixel_schedule_independent(raw)}
            comparison = run_and_compare(graph, packed, schedule, readout_population="readout")
            with torch.no_grad():
                forward = model(torch.tensor([list(raw)], dtype=torch.uint8))[0]
            torch_counts = tuple(int(value) for value in forward)
            if comparison.readout_spike_counts != torch_counts:
                raise B23AuditError(
                    f"validation ordinal {ordinal} integer-forward versus B1.4 oracle differs: "
                    f"tensor={torch_counts}, scalar={comparison.readout_spike_counts}")
            frames.append({
                "validation_ordinal": ordinal,
                "canonical_train_idx": original_idx,
                "image_sha256": hashlib.sha256(raw).hexdigest(),
                "label": label,
                "predicted_class": comparison.predicted_class,
                "readout_spike_counts": list(comparison.readout_spike_counts),
                "monolithic_trace_sha256": comparison.reference.trace_sha256,
                "partitioned_trace_sha256": comparison.output_trace_sha256,
                "all_26_ticks_full_neuron_parity": comparison.semantic_ticks_compared == 26,
            })
    return B23AuditedCandidate(
        manifest=manifest, network_sha256=graph.fingerprint,
        deployment_sha256=packed.compiled.fingerprint,
        capacity_audit_sha256=audit["audit_sha256"],
        core_count=audit["logical_core_count"], backing_bytes=audit["backing_bytes"],
        worst_current_events=max(c["worst_current_bank_events"] for c in audit["cores"]),
        validated_frames=tuple(frames),
    )
