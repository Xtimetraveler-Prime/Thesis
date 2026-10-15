"""P06-A4.1 trained checkpoint -> P03 word snapshot + differential trace gate.

Consumes the exact user-trained P06-A3 checkpoint. Never loads official
MNIST test archives. The word dumps below preserve packed P03 values,
but are NOT the P05 512 KiB DDR record, A53 input streaming protocol, or
a physical FPGA experiment. P07 must create/validate that separate ABI.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import struct

import torch

from .compiler import MappingOptions, compile_network
from .hardware_p03 import export_one_core_image
from .p06_a3_data import load_train_validation
from .p06_a3_training import load_candidate, integer_weights_sha256
from .p06_compact_inference import infer_image
from .p06_input_contract import (
    ENCODER_PROFILE, READOUT_PROFILE, pixel_spikes, event_schedule_sha256,
)
from .p06_packed_replay import replay_p03_image
from .p06_train_export import compact_to_compiler_spec

FREEZE_SCHEMA = "p06-a4-trained-p03-software-word-freeze-candidate-v1"
# Identifies the first accepted training trial from the user's printed
# manifest. These cannot be silently replaced by a retrained checkpoint.
PINNED_CHECKPOINT_SHA256 = "0b0e8a2a9be3ceb19f206f8f55bfd8e73b52e7c2e39f271d7696c39fc9b6fd88"
PINNED_INTEGER_WEIGHTS_SHA256 = "1396f93d21f03b7cff6580ed9cc3176ce40a7afaf53254643120174572b9fe0b"
PINNED_TRAIN_INDICES_SHA256 = "1cbcb0b2bf481958d6c917ea6d70fa44a20839406f0c824540f8e691edfdd851"
PINNED_VALIDATION_INDICES_SHA256 = "3b9520013f30742c3818f55024ea39e3e0632113c487c589fdfbb73c7d274831"
PINNED_BEST_VALIDATION = 0.9439
PINNED_BEST_EPOCH = 8


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require_pinned_training_candidate(manifest: dict, effective_sha: str) -> None:
    """Require exact project-trained checkpoint identity; fail closed."""
    if manifest.get("candidate_go") is not True:
        raise ValueError("training candidate failed predeclared validation GO gate")
    if manifest.get("weights_file_sha256") != PINNED_CHECKPOINT_SHA256:
        raise ValueError("wrong or replaced training checkpoint SHA256")
    if effective_sha != PINNED_INTEGER_WEIGHTS_SHA256:
        raise ValueError("wrong or replaced effective integer weights SHA256")
    if manifest.get("exported_integer_weights_sha256") != effective_sha:
        raise ValueError("checkpoint manifest integer weight SHA256 mismatch")
    if manifest.get("best_epoch") != PINNED_BEST_EPOCH:
        raise ValueError("candidate selected a different epoch")
    if manifest.get("best_validation", {}).get("accuracy") != PINNED_BEST_VALIDATION:
        raise ValueError("candidate validation accuracy differs from accepted result")
    source = manifest.get("source_dataset", {})
    if source.get("train_indices_le32_sha256") != PINNED_TRAIN_INDICES_SHA256:
        raise ValueError("training index fingerprint changed")
    if source.get("validation_indices_le32_sha256") != PINNED_VALIDATION_INDICES_SHA256:
        raise ValueError("validation index fingerprint changed")
    if manifest.get("official_mnist_test_status") != "SEALED / NOT READ":
        raise ValueError("official MNIST test partition must remain sealed")
    if manifest.get("input_encoder") != ENCODER_PROFILE or manifest.get("readout") != READOUT_PROFILE:
        raise ValueError("encoder/readout contract changed")


def _word_stream(values, byte_width: int) -> bytes:
    if byte_width not in (2, 4, 8, 16):
        raise ValueError("unsupported word width")
    return b"".join(int(v).to_bytes(byte_width, "little", signed=False) for v in values)


def packed_word_snapshot(image) -> dict[str, bytes]:
    """Serialize actual packed P03 words, *without* inventing a DDR page ABI.

    Sparse axon/route descriptors are explicit indexed records. Word order
    and LE widths are declared, so identical images create identical hashes.
    """
    return {
        "compartment_config_le128.bin": _word_stream(image.config_words, 16),
        "compartment_state_le64.bin": _word_stream(image.state_words, 8),
        "synapses_le64.bin": _word_stream(image.synapse_words, 8),
        "axon_index_le16_word_le64.bin": b"".join(
            _word_stream((record.index,), 2) + _word_stream((record.word,), 8)
            for record in image.axon_words
        ),
        "route_descriptor_index_le16_word_le32.bin": b"".join(
            _word_stream((record.index,), 2) + _word_stream((record.word,), 4)
            for record in image.route_descriptor_words
        ),
        "route_words_le32.bin": _word_stream(image.route_words, 4),
    }


def _assert_equal(left, right, description: str) -> None:
    if left != right:
        raise AssertionError(f"P06-A4 first divergence: {description}")


def verify_frame(model, compiled, image, pixel_to_axon, pixels: bytes) -> dict:
    """Four-way exact 26-tick check on one trace: Torch/dense/packed/chip."""
    network = model.to_integer_network()
    dense = infer_image(network, pixels)
    packed = replay_p03_image(image, pixel_to_axon, pixels)
    with torch.no_grad():
        torch_counts = tuple(int(v) for v in model(torch.tensor([list(pixels)], dtype=torch.uint8))[0].tolist())
    _assert_equal(torch_counts, dense.output_counts, "Torch vs dense output counts")
    _assert_equal(packed.output_counts, dense.output_counts, "packed vs dense output counts")
    _assert_equal(packed.predicted_class, dense.predicted_class, "packed vs dense prediction")
    chip = compiled.build_chip()  # fresh state and queued events per sample
    tick_summaries = []
    for tick, expected in enumerate(dense.traces):
        actual = packed.ticks[tick]
        core = chip.step(compiled.external_packets(
            "pixels", pixel_spikes(pixels, tick), target_timestep=tick,
        )).cores[0]
        prefix = f"tick={tick}"
        _assert_equal(
            actual.accumulators,
            expected.hidden_synaptic_inputs + expected.output_synaptic_inputs,
            prefix + " packed vs dense accumulators",
        )
        _assert_equal(
            actual.states_after,
            expected.hidden_after + expected.output_after,
            prefix + " packed vs dense state",
        )
        expected_spikes = expected.hidden_spikes + tuple(32 + v for v in expected.output_spikes)
        _assert_equal(actual.fired_compartments, expected_spikes, prefix + " packed vs dense spikes")
        _assert_equal(actual.fired_compartments, core.spikes_out, prefix + " chip vs packed spikes")
        core_state = tuple(
            (s.state.current, s.state.voltage, s.state.refractory_remaining)
            for s in core.compartment_state_after
        )
        packed_state = tuple((s.current, s.voltage, s.refractory_remaining) for s in actual.states_after)
        _assert_equal(core_state, packed_state, prefix + " chip vs packed state")
        _assert_equal(
            sorted(p.destination_axon for p in core.packets_out),
            sorted(actual.next_packet_axons), prefix + " chip vs packed packet destinations",
        )
        _assert_equal(actual.output_counts, expected.output_spike_counts, prefix + " output spike counts")
        tick_summaries.append({
            "tick": tick,
            "external_events": len(expected.external_pixel_indices),
            "hidden_spikes": list(expected.hidden_spikes),
            "output_spikes": list(expected.output_spikes),
            "output_spike_counts": list(expected.output_spike_counts),
            "received_hidden_spikes": list(expected.received_hidden_spikes),
        })
    _assert_equal(len(tick_summaries), 26, "26-step readout window")
    return {
        "pixel_sha256": _sha(pixels), "event_schedule_sha256": event_schedule_sha256(pixels),
        "predicted_class": dense.predicted_class,
        "output_counts": list(dense.output_counts),
        "dropped_boundary_hidden_spikes": list(dense.dropped_boundary_hidden_spikes),
        "timesteps": tick_summaries,
    }


def compile_and_check_traces(model, frames: tuple[tuple[str, bytes], ...]):
    """Build and verify original first-fit 1-core packed image, fail closed."""
    network = model.to_integer_network()
    source = compact_to_compiler_spec(network)
    compiled = compile_network(source, MappingOptions(max_logical_cores=1))
    configs = compiled.logical_deployment.core_configs
    if len(configs) != 1:
        raise ValueError("trained compact checkpoint must compile to one logical core")
    packed_image = export_one_core_image(configs[0])
    if packed_image.core_id != 0 or packed_image.compartment_count != 42:
        raise ValueError("trained compact P03 image has wrong logical core/compartment count")
    if len(compiled.placement) != 42 or len(compiled.ingress_routes) != 784:
        raise ValueError("compiled trained network placement or ingress count changed")
    if packed_image.synapse_count > 32768 or packed_image.route_count > 4096:
        raise ValueError("trained hardware-image capacity exceeded")
    if len(packed_image.axon_words) > 4096 or len(packed_image.config_words) != 42:
        raise ValueError("packed neuron/axon resource capacity exceeded")
    routes = tuple(sorted(compiled.ingress_routes, key=lambda x: x.input_index))
    if tuple(x.input_index for x in routes) != tuple(range(784)):
        raise ValueError("trained ingress map is incomplete or duplicated")
    if any(x.destination_core != packed_image.core_id for x in routes):
        raise ValueError("trained input ingress escapes compact core")
    pixel_to_axon = tuple(x.destination_axon for x in routes)
    if len(set(pixel_to_axon)) != 784:
        raise ValueError("trained pixel axons are not distinct")
    reports = []
    for label, pixels in frames:
        if len(pixels) != 784:
            raise ValueError("diagnostic frame must have 784 uint8 pixel bytes")
        reports.append({"frame": label, **verify_frame(
            model, compiled, packed_image, pixel_to_axon, pixels,
        )})
    return packed_image, compiled, tuple(reports)


def run_a4_snapshot(
    candidate_dir: str | Path, data_dir: str | Path, output_dir: str | Path,
    *, diagnostic_validation_count: int = 3,
) -> dict:
    """Produce software word snapshot ONLY once every numerical gate passes."""
    if type(diagnostic_validation_count) is not int or not 1 <= diagnostic_validation_count <= 16:
        raise ValueError("diagnostic_validation_count must be in [1,16]")
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError("A4 snapshot output already exists; refusing overwrite")
    model, trained_manifest = load_candidate(candidate_dir)
    require_pinned_training_candidate(trained_manifest, integer_weights_sha256(model))
    split = load_train_validation(data_dir)
    if split.manifest != trained_manifest["source_dataset"]:
        raise ValueError("current MNIST training archive/split differs from checkpoint provenance")
    if split.manifest.get("official_test_set") != "sealed: no t10k archives opened":
        raise ValueError("official test provenance changed")
    frames = [
        ("synthetic-black", bytes(784)),
        ("synthetic-white", bytes([255] * 784)),
    ]
    for j, source_index in enumerate(split.validation_indices[:diagnostic_validation_count]):
        pos = source_index * 784
        frames.append((f"validation-diagnostic-{j}-source-index-{source_index}",
                       split.images[pos : pos + 784]))
    image, compiled, checked_traces = compile_and_check_traces(model, tuple(frames))
    streams = packed_word_snapshot(image)
    meta = {
        "schema": FREEZE_SCHEMA, "status": "SOFTWARE_WORD_SNAPSHOT / PHYSICAL_GATE_NOT_RUN",
        "accepted_training_candidate_sha256": trained_manifest["weights_file_sha256"],
        "accepted_integer_weights_sha256": integer_weights_sha256(model),
        "training_best_epoch": trained_manifest["best_epoch"],
        "training_best_validation_accuracy": trained_manifest["best_validation"]["accuracy"],
        "training_validation_go_floor": trained_manifest["validation_go_floor_predeclared"],
        "canonical_dataset_manifest": split.manifest,
        "encoder": ENCODER_PROFILE, "readout": READOUT_PROFILE,
        "total_timesteps": 26, "reset_per_image": True,
        "software_compiler_version": compiled.compiler_version,
        "network_fingerprint": compiled.source_fingerprint,
        "deployment_fingerprint": compiled.fingerprint,
        "deployment_resource_report": compiled.report(),
        "image": {
            "profile": image.profile, "logical_core_id": image.core_id,
            "compartments": image.compartment_count, "axon_bindings": len(image.axon_words),
            "synapse_words": image.synapse_count, "route_words": image.route_count,
            "route_descriptors": len(image.route_descriptor_words),
        },
        "packed_word_streams": {
            name: {"bytes": len(data), "sha256": _sha(data)} for name, data in streams.items()
        },
        "packet_gate": {
            "software_engines_compared": [
                "P06-A2 integer dense oracle", "PyTorch integer forward",
                "independent P03 word decoder/replay", "accepted LogicalChip",
            ],
            "frames": len(checked_traces), "timesteps_per_frame": 26,
            "status": "ALL_TRACES_EXACTLY_EQUAL",
        },
        "official_test_status": "SEALED / NOT OPENED",
        "hardware_status": "NO PHYSICAL FPGA TEST / NO A53 DDR PAGE IMAGE",
        "p06_a4_exit": "PENDING_NATIVE_ACCEPTANCE_AND_FINAL_PROTOCOL_FREEZE",
    }
    # Create output only after complete compilation and all comparisons pass.
    output.mkdir(parents=True, exist_ok=False)
    for filename, data in streams.items():
        (output / filename).write_bytes(data)
    trace_json = json.dumps(checked_traces, sort_keys=True, indent=2) + "\n"
    (output / "diagnostic_traces.json").write_text(trace_json, encoding="utf-8")
    meta["diagnostic_traces_sha256"] = _sha(trace_json.encode())
    (output / "a4_software_snapshot_manifest.json").write_text(
        json.dumps(meta, sort_keys=True, indent=2) + "\n", encoding="utf-8",
    )
    return meta
