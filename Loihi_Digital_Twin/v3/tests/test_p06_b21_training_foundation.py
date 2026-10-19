"""B2.1 width-scaled Train/VALIDATION-only SNN foundation acceptance tests.

Synthetic fixed-seed uint8 data; no training archives, official TEST images,
trained checkpoint, physical KV260 or destructive state/DDR access.
"""
from __future__ import annotations

import hashlib
import json
import os

import pytest
import torch

from loihi_twin_v2.p06_a3_data import TrainingSplit
from loihi_twin_v2.p06_a3_training import (
    HIDDEN_LIF, OUTPUT_LIF, TrainSettings as TrackASettings,
    initialize_model as accepted_initialize,
)
from loihi_twin_v2.p06_b21_training_foundation import (
    B21IntegerSNN, B21Settings, B21_SCHEMA, foundation_manifest,
    require_train_only_split,
)
from loihi_twin_v2.p06_b12_partition import B12Options, compile_synapse_aware
from loihi_twin_v2.p06_b14_monolithic import (
    pixel_schedule_independent, simulate_monolithic,
)
from loihi_twin_v2.p06_b14_differential import run_and_compare


def pixels(seed: int) -> bytes:
    return bytes(((i * 41 + seed * 13) % 256) for i in range(784))


def test_new_width_and_independent_seed_initialization_no_track_a_change():
    s = B21Settings(hidden_neurons=6, seed=20261019)
    a, b = B21IntegerSNN.initialized(s), B21IntegerSNN.initialized(s)
    c = B21IntegerSNN.initialized(B21Settings(hidden_neurons=6, seed=20261020))
    assert a.w_input_hidden.shape == (6, 784)
    assert a.w_hidden_output.shape == (10, 6)
    assert torch.equal(a.w_input_hidden, b.w_input_hidden)
    assert torch.equal(a.w_hidden_output, b.w_hidden_output)
    assert not torch.equal(a.w_input_hidden, c.w_input_hidden)
    assert a.integer_weight_sha256() == b.integer_weight_sha256()
    assert a.integer_weight_sha256() != c.integer_weight_sha256()
    manifest = foundation_manifest(s, a)
    assert manifest["schema"] == B21_SCHEMA
    assert manifest["architecture"] == [784, 6, 10]
    assert manifest["connections_dense"] == (784 + 10) * 6
    assert manifest["checkpoint_frozen"] is False
    assert manifest["official_mnist_test_status"] == "SEALED_NOT_ACCESSED"
    # Existing accepted compact Track A forward still hard-codes 32 hidden;
    # new B2 width must never mutate or monkey-patch that original model.
    old = accepted_initialize(TrackASettings())
    assert old.w_input_hidden.shape == (32, 784)
    assert old.w_hidden_output.shape == (10, 32)


@pytest.mark.parametrize("hidden", (1, 2, 5))
def test_integer_torch_forward_matches_truly_independent_26_tick_source_graph(hidden):
    model = B21IntegerSNN.initialized(B21Settings(hidden_neurons=hidden, seed=20261019))
    graph = model.to_network_spec()
    assert graph.fingerprint == model.to_network_spec().fingerprint
    assert len(graph.input_projections[0].connections) == 784 * hidden
    assert len(graph.projections[0].connections) == hidden * 10
    assert len({c.weight for c in graph.input_projections[0].connections}) > 1
    batch = (pixels(0), pixels(1), bytes([255] * 784), bytes(784))
    x = torch.tensor([list(row) for row in batch], dtype=torch.uint8)
    with torch.no_grad():
        actual = model(x)
    assert actual.shape == (4, 10)
    assert actual.dtype == torch.float64
    for index, row in enumerate(batch):
        schedule = {"pixels": pixel_schedule_independent(row)}
        expected = simulate_monolithic(graph, schedule, readout_population="readout")
        assert tuple(int(v) for v in actual[index]) == expected.readout_spike_counts
        assert expected.predicted_class == int(actual[index].argmax())


def test_b21_production_packer_and_independent_oracle_align_and_do_not_lose_zero_edges():
    model = B21IntegerSNN.initialized(B21Settings(hidden_neurons=3, seed=12))
    with torch.no_grad():
        model.w_input_hidden[0, 0] = 0.0
        model.w_hidden_output[0, 0] = 0.0
        model.w_input_hidden[1, 17] = -100.0
    graph = model.to_network_spec()
    assert any(c.weight == 0 for c in graph.input_projections[0].connections)
    result = compile_synapse_aware(graph, B12Options(readout_population="readout"))
    assert result.compiled.source_fingerprint == graph.fingerprint
    assert result.capacity_audit["logical_core_count"] == 2
    schedule = {"pixels": pixel_schedule_independent(pixels(5))}
    report = run_and_compare(graph, result, schedule, readout_population="readout")
    with torch.no_grad():
        counts = model(torch.tensor([list(pixels(5))], dtype=torch.uint8))[0]
    assert tuple(int(x) for x in counts) == report.reference.readout_spike_counts
    assert report.predicted_class == int(counts.argmax())
    assert report.report()["all_neuron_states_and_inputs_equal"] is True
    assert report.report()["all_spikes_and_NEXT_routes_equal"] is True


def test_manually_calculated_25_inputs_and_one_drain_next_epoch_spikes():
    model = B21IntegerSNN(hidden_neurons=3)
    with torch.no_grad():
        model.w_input_hidden[0, 0] = 40.0
        model.w_hidden_output[0, 0] = 12.0
    image = bytes([255] + [0] * 783)
    with torch.no_grad():
        counts = model(torch.tensor([list(image)], dtype=torch.uint8))[0]
    assert tuple(int(v) for v in counts) == (25,) + (0,) * 9
    source = model.to_network_spec()
    oracle = simulate_monolithic(
        source, {"pixels": pixel_schedule_independent(image)},
        readout_population="readout")
    assert oracle.ticks[0].spikes == (("hidden", 0),)
    assert oracle.ticks[0].readout_counts == (0,) * 10
    assert oracle.ticks[1].readout_counts == (1,) + (0,) * 9
    assert oracle.ticks[25].spikes == (("readout", 0),)
    assert oracle.readout_spike_counts == (25,) + (0,) * 9


def test_width_32_agrees_exactly_with_frozen_track_a_integer_forward():
    settings = B21Settings(hidden_neurons=32, seed=83)
    scaled = B21IntegerSNN.initialized(settings)
    old = accepted_initialize(TrackASettings(seed=83))
    with torch.no_grad():
        old.w_input_hidden.copy_(scaled.w_input_hidden)
        old.w_hidden_output.copy_(scaled.w_hidden_output)
        image = torch.tensor([list(pixels(14))], dtype=torch.uint8)
        assert torch.equal(scaled(image), old(image))


def test_training_gradient_is_finite_through_reused_unchanged_ste_kernel():
    model = B21IntegerSNN.initialized(B21Settings(hidden_neurons=4, seed=93))
    model.train()
    x = torch.tensor([list(pixels(1)), list(pixels(2))], dtype=torch.uint8)
    scores = model(x)
    loss = torch.nn.functional.cross_entropy(scores * 2.0, torch.tensor([1, 8]))
    assert torch.isfinite(loss)
    loss.backward()
    assert model.w_input_hidden.grad is not None
    assert model.w_hidden_output.grad is not None
    assert bool(torch.isfinite(model.w_input_hidden.grad).all())
    assert bool(torch.isfinite(model.w_hidden_output.grad).all())


def test_signed24_nonfinite_and_uint8_contract_fail_closed():
    model = B21IntegerSNN.initialized(B21Settings(hidden_neurons=2))
    with pytest.raises((ValueError, TypeError), match="uint8"):
        model(torch.zeros((1, 784), dtype=torch.float32))
    with pytest.raises(ValueError, match="784"):
        model(torch.zeros((1, 783), dtype=torch.uint8))
    with pytest.raises(ValueError, match="empty"):
        model(torch.zeros((0, 784), dtype=torch.uint8))
    with torch.no_grad():
        model.w_hidden_output[0, 0] = float("nan")
    with pytest.raises(ValueError, match="nonfinite"):
        model.to_network_spec()
    with torch.no_grad():
        model.w_hidden_output[0, 0] = float((1 << 23))
    with pytest.raises(ValueError, match="signed24"):
        model.to_network_spec()


def test_train_split_gate_refuses_synthetic_or_unverified_canonical_claim():
    empty = TrainingSplit(images=b"", labels=b"", train_indices=(),
                          validation_indices=(),
                          manifest={"schema": "synthetic-idx-test-not-benchmark"})
    with pytest.raises(ValueError, match="canonical"):
        require_train_only_split(empty)
    # No need to allocate ~47 MiB of fake pixels: manifest's UNSEALED
    # official-test claim must be rejected before data-size admission.
    forged = TrainingSplit(
        images=b"", labels=b"",
        train_indices=tuple(range(50000)),
        validation_indices=tuple(range(50000, 60000)),
        manifest={
            "schema": "p06-a3-mnist-train50000-val10000-seeded-v1",
            "image_count": 60000, "train_count": 50000,
            "validation_count": 10000, "split_seed": 20261013,
            "official_test_set": "opened", "archives": {},
        },
    )
    with pytest.raises(ValueError, match="official-test"):
        require_train_only_split(forged)
    with pytest.raises(TypeError):
        require_train_only_split(object())


@pytest.mark.parametrize("width", (0, 1001, True))
def test_width_rejection(width):
    with pytest.raises(ValueError, match="hidden_neurons"):
        B21Settings(hidden_neurons=width)


@pytest.mark.skipif(os.environ.get("P06_B21_1000_SHAPE") != "1",
                    reason="optional 1000-neuron state/graph allocation; no training or MNIST")
def test_opt_in_full_1000_hidden_dense_graph_export_and_packing():
    settings = B21Settings(hidden_neurons=1000)
    model = B21IntegerSNN.initialized(settings)
    assert model.w_input_hidden.shape == (1000, 784)
    assert model.w_hidden_output.shape == (10, 1000)
    source = model.to_network_spec()
    assert len(source.input_projections[0].connections) == 784000
    assert len(source.projections[0].connections) == 10000
    assert source.fingerprint == model.to_network_spec().fingerprint
    packed = compile_synapse_aware(source, B12Options(readout_population="readout"))
    assert packed.capacity_audit["logical_core_count"] <= 126
    assert packed.capacity_audit["backing_bytes"] <= 126 * 524288
    assert packed.capacity_audit["cores"][-1]["compartments"] == 10
    assert max(core["logical_synapse_bytes"] for core in packed.capacity_audit["cores"]) <= 131072
    assert all(core["worst_current_bank_events"] <= 4096
               for core in packed.capacity_audit["cores"])
    assert packed.compiled.source_fingerprint == source.fingerprint
