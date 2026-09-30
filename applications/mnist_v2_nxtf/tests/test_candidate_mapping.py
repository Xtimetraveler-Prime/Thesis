from __future__ import annotations

import numpy as np

from loihi_twin_v2 import MappingError, MappingOptions, compile_network, export_compiled_fpga_image
from mnist_v2_nxtf import (
    TOTAL_SPIKING_NEURONS,
    TOTAL_TRAINABLE_WEIGHTS,
    build_network,
    make_mapping_probe_model,
    topology_report,
)
from mnist_v2_nxtf.data import encode_binary_spikes, stratified_train_validation_indices


def _compiled():
    return compile_network(build_network(make_mapping_probe_model()))


def test_p08_candidate_shape_and_parameter_contract():
    assert TOTAL_SPIKING_NEURONS == 2474
    assert TOTAL_TRAINABLE_WEIGHTS == 7597
    assert topology_report() == {
        "conv1_neurons": 1728,
        "conv2_neurons": 726,
        "dense_hidden_neurons": 10,
        "output_neurons": 10,
        "total_spiking_neurons": 2474,
        "trainable_weights": 7597,
    }


def test_p08_candidate_maps_to_accepted_three_context_boundary():
    compiled = _compiled()
    report = compiled.report()
    fpga = export_compiled_fpga_image(compiled).report()
    assert report["logical_core_count"] == 3
    assert fpga["logical_core_count"] == 3
    assert fpga["physical_engine_count"] == 1
    assert fpga["logical_capacity_changed"] is False
    assert [core["usage"]["compartments"] for core in report["cores"]] == [1024, 1024, 426]


def test_p08_candidate_mapping_pressure_is_frozen():
    report = _compiled().report()
    assert report["static_route_estimate"] == {
        "total": 2410,
        "local": 416,
        "remote": 1994,
    }
    assert report["connection_sharing"]["expanded_connections"] == 70162
    assert report["connection_sharing"]["stored_shared_parameters"] == 7705
    assert report["connection_sharing"]["expanded_per_stored_parameter"] == 70162 / 7705
    assert [core["usage"] for core in report["cores"]] == [
        {
            "compartments": 1024,
            "input_axons": 514,
            "output_routes": 1069,
            "synapse_bytes": 13680,
            "shared_parameters": 2800,
            "expanded_connections": 25600,
        },
        {
            "compartments": 1024,
            "input_axons": 1134,
            "output_routes": 925,
            "synapse_bytes": 19152,
            "shared_parameters": 3473,
            "expanded_connections": 26240,
        },
        {
            "compartments": 426,
            "input_axons": 1663,
            "output_routes": 416,
            "synapse_bytes": 12972,
            "shared_parameters": 1432,
            "expanded_connections": 18322,
        },
    ]


def test_p08_candidate_records_two_core_policy_failure():
    network = build_network(make_mapping_probe_model())
    try:
        compile_network(network, MappingOptions(max_logical_cores=2))
    except MappingError as exc:
        assert exc.code == "logical_core_capacity"
        assert exc.context == {"required": 3, "limit": 2}
    else:  # pragma: no cover - defensive
        raise AssertionError("candidate unexpectedly fit a two-core mapper policy")


def test_p08_split_is_stratified_and_deterministic():
    labels = np.repeat(np.arange(10, dtype=np.int64), 6000)
    train_a, val_a = stratified_train_validation_indices(labels)
    train_b, val_b = stratified_train_validation_indices(labels)
    assert np.array_equal(train_a, train_b)
    assert np.array_equal(val_a, val_b)
    assert len(train_a) == 55000
    assert len(val_a) == 5000
    assert np.bincount(labels[val_a], minlength=10).tolist() == [500] * 10


def test_p08_rate_encoding_is_deterministic_and_exact_count():
    image = np.zeros((28, 28), dtype=np.uint8)
    image[0, 0] = 255
    image[0, 1] = 128
    spikes = encode_binary_spikes(image, timesteps=100)
    assert spikes.shape == (1, 100, 784)
    assert int(spikes[0, :, 0].sum()) == 100
    assert int(spikes[0, :, 1].sum()) == 50
    assert np.array_equal(spikes, encode_binary_spikes(image, timesteps=100))
