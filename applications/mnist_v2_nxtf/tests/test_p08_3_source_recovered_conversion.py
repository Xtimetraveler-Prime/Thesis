from __future__ import annotations

import numpy as np

from loihi_twin_v2 import MappingOptions, compile_network
from mnist_v2_nxtf.conversion import conv_geometries
from mnist_v2_nxtf.source_recovered_conversion import (
    INPUT_INGRESS_MODE,
    SOFTMAX_READOUT_MODE,
    SOFTMAX_READOUT_THRESHOLD,
    build_source_recovered_network,
)
from mnist_v2_nxtf.structural import P06_STRUCTURAL_COMPARTMENTS_PER_CORE


def _synthetic_parameters() -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {
        "input_threshold": np.asarray([2040], dtype=np.int32),
        "conv1_threshold": np.asarray([556], dtype=np.int32),
        "conv2_threshold": np.asarray([512], dtype=np.int32),
        "conv3_threshold": np.asarray([672], dtype=np.int32),
    }
    for geometry in conv_geometries():
        shape = (
            geometry.kernel,
            geometry.kernel,
            geometry.input_channels,
            geometry.output_channels,
        )
        arrays[f"{geometry.name}_kernel_integer"] = np.ones(shape, dtype=np.int16)
        arrays[f"{geometry.name}_bias_integer"] = np.zeros(
            (geometry.output_channels,), dtype=np.int16
        )
    return arrays


def test_source_recovered_network_preserves_graph_and_thresholds() -> None:
    network = build_source_recovered_network(_synthetic_parameters())
    assert sum(population.size for population in network.populations) == 4218
    assert len(network.input_populations) == 1
    assert network.input_populations[0].name == "pixels"

    thresholds: dict[str, set[int]] = {}
    for population in network.populations:
        layer = population.name.split("_c", 1)[0]
        thresholds.setdefault(layer, set()).add(population.compartment.threshold)
    assert thresholds == {
        "conv1": {556},
        "conv2": {512},
        "conv3": {672},
        "conv4": {SOFTMAX_READOUT_THRESHOLD},
    }


def test_source_recovered_graph_still_compiles_to_five_logical_cores() -> None:
    network = build_source_recovered_network(_synthetic_parameters())
    compiled = compile_network(
        network,
        MappingOptions(compartments_per_core=P06_STRUCTURAL_COMPARTMENTS_PER_CORE),
    )
    assert len(compiled.logical_deployment.core_configs) == 5


def test_softmax_and_input_modes_are_explicit() -> None:
    assert SOFTMAX_READOUT_MODE == "final_membrane_voltage_argmax"
    assert SOFTMAX_READOUT_THRESHOLD == 2**17 - 1
    assert INPUT_INGRESS_MODE == "host_bias_encoder_to_external_pixel_spikes"
