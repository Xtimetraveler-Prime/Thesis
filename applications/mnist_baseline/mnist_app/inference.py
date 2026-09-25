"""Golden-model inference for exported MNIST deployments."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import (
    DEFAULT_PROFILE,
    OUTPUT_NEURONS,
    PRESENTATION_TICKS,
    MnistProfile,
    get_profile,
)
from .encoding import count_events, encode_event_schedule


@dataclass(frozen=True, slots=True)
class DeploymentRuntime:
    core: object
    profile: MnistProfile
    row_lengths: tuple[int, ...]
    manifest: dict[str, object]


@dataclass(frozen=True, slots=True)
class InferenceResult:
    prediction: int
    spike_counts: tuple[int, ...]
    total_input_events: int
    events_per_tick: tuple[int, ...]
    synaptic_visits: int | None
    predictions_by_tick: tuple[int, ...]
    no_spike: bool
    tied_winners: int


def load_deployment(manifest_path: str | Path) -> DeploymentRuntime:
    """Instantiate the existing FPGA-v1 Python golden core from an export."""

    from neuromorphic_twin import (
        FPGA_CORE_ARITHMETIC_V1,
        NeuronConfig,
        NeuromorphicCore,
        read_weight_storage_json,
    )

    manifest_path = Path(manifest_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "neuromorphic-twin-mnist-deployment-v2":
        raise ValueError("unsupported MNIST deployment schema")

    profile = get_profile(payload["profile"])
    configs = tuple(NeuronConfig(**row) for row in payload["neuron_configs"])
    if len(configs) != OUTPUT_NEURONS:
        raise ValueError("deployment must contain ten output neuron configs")

    storage_path = manifest_path.parent / payload["weight_storage"]
    storage = read_weight_storage_json(storage_path)
    if storage.axon_count != profile.input_axons:
        raise ValueError("deployment axon rows do not match declared profile")
    if storage.synapse_count > profile.max_synapses:
        raise ValueError("deployment synapses exceed declared profile")
    row_lengths = tuple(
        storage.axon_row_pointers[i + 1] - storage.axon_row_pointers[i]
        for i in range(storage.axon_count)
    )

    core = NeuromorphicCore(
        configs,
        storage.decode_synapses(),
        arithmetic=FPGA_CORE_ARITHMETIC_V1,
    )
    return DeploymentRuntime(
        core=core,
        profile=profile,
        row_lengths=row_lengths,
        manifest=payload,
    )


def load_core_from_deployment(manifest_path: str | Path):
    """Compatibility wrapper returning only the instantiated core."""

    return load_deployment(manifest_path).core


def infer_image(
    core,
    image: np.ndarray,
    *,
    profile: str | MnistProfile = DEFAULT_PROFILE,
    row_lengths: tuple[int, ...] | None = None,
) -> InferenceResult:
    """Reset one core, present one image, and decode output spike counts."""

    selected = get_profile(profile)
    if row_lengths is not None and len(row_lengths) != selected.input_axons:
        raise ValueError("row_lengths must contain one entry per input axon")

    schedule = encode_event_schedule(image, profile=selected)
    core.reset()
    spike_counts = np.zeros(OUTPUT_NEURONS, dtype=np.int64)
    predictions_by_tick: list[int] = []
    synaptic_visits = 0 if row_lengths is not None else None

    for tick_events in schedule:
        if row_lengths is not None:
            synaptic_visits += sum(row_lengths[axon] for axon in tick_events)
        trace = core.step(tick_events)
        for spike in trace.spikes:
            spike_counts[spike.neuron_id] += 1
        predictions_by_tick.append(int(np.argmax(spike_counts)))

    prediction = int(np.argmax(spike_counts))
    winning_count = int(spike_counts[prediction])
    tied_winners = int(np.count_nonzero(spike_counts == winning_count))
    return InferenceResult(
        prediction=prediction,
        spike_counts=tuple(int(value) for value in spike_counts),
        total_input_events=count_events(schedule),
        events_per_tick=tuple(len(events) for events in schedule),
        synaptic_visits=synaptic_visits,
        predictions_by_tick=tuple(predictions_by_tick),
        no_spike=winning_count == 0,
        tied_winners=tied_winners,
    )


def evaluate_dataset(
    core,
    images: np.ndarray,
    labels: np.ndarray,
    *,
    profile: str | MnistProfile = DEFAULT_PROFILE,
    row_lengths: tuple[int, ...] | None = None,
) -> dict[str, object]:
    """Evaluate a finite corpus through the actual project golden model."""

    selected = get_profile(profile)
    labels = np.asarray(labels, dtype=np.int64)
    if len(images) != len(labels):
        raise ValueError("images and labels must have the same length")

    confusion = np.zeros((10, 10), dtype=np.int64)
    predictions = np.zeros(len(labels), dtype=np.int64)
    correct_by_tick = np.zeros(PRESENTATION_TICKS, dtype=np.int64)
    correct = 0
    total_events = 0
    total_output_spikes = 0
    total_synaptic_visits = 0
    no_spike_count = 0
    tie_count = 0

    for sample_id, (image, label) in enumerate(zip(images, labels, strict=True)):
        result = infer_image(
            core,
            image,
            profile=selected,
            row_lengths=row_lengths,
        )
        predictions[sample_id] = result.prediction
        confusion[int(label), result.prediction] += 1
        correct += int(result.prediction == int(label))
        correct_by_tick += np.asarray(result.predictions_by_tick) == int(label)
        total_events += result.total_input_events
        total_output_spikes += sum(result.spike_counts)
        if result.synaptic_visits is not None:
            total_synaptic_visits += result.synaptic_visits
        no_spike_count += int(result.no_spike)
        tie_count += int(result.tied_winners > 1)

    incorrect = np.where(predictions != labels)[0]
    count = len(labels)
    return {
        "profile": selected.name,
        "images": count,
        "accuracy": correct / count if count else 0.0,
        "accuracy_by_tick": (
            (correct_by_tick / count).tolist()
            if count
            else [0.0] * PRESENTATION_TICKS
        ),
        "mean_input_events": total_events / count if count else 0.0,
        "mean_output_spikes": total_output_spikes / count if count else 0.0,
        "mean_synaptic_visits": (
            total_synaptic_visits / count
            if count and row_lengths is not None
            else None
        ),
        "no_spike_images": no_spike_count,
        "tied_winner_images": tie_count,
        "predictions": predictions.tolist(),
        "incorrect_indices": incorrect.tolist(),
        "confusion_matrix": confusion.tolist(),
        "presentation_ticks": PRESENTATION_TICKS,
    }
