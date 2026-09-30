from __future__ import annotations

import pytest

from loihi_twin_v2 import MappingError, compile_network
from mnist_v2_nxtf.reconstruction import (
    PAPER_EXPANDED_CONNECTION_TARGET,
    PAPER_NEURON_TARGET,
    PAPER_SHARED_WEIGHT_TARGET,
    PAPER_TRAINABLE_PARAMETER_TARGET,
    PROPOSED_FILTERS,
    PROPOSED_METRICS,
    ranked_reconstructions,
    validate_proposed_reconstruction,
)
from mnist_v2_nxtf.structural import (
    P06_STRUCTURAL_COMPARTMENTS_PER_CORE,
    build_structural_network,
    compile_structural_probe,
)


def test_source_bounded_reconstruction_is_deterministic() -> None:
    validate_proposed_reconstruction()
    best = ranked_reconstructions(limit=1)[0]

    assert best.filters == PROPOSED_FILTERS == (14, 20, 12)
    assert best.layer_neurons == (2016, 2000, 192, 10)
    assert best.neuron_count == 4218
    assert best.kernel_weights == 6950
    assert best.bias_count == 56
    assert best.trainable_parameters == 7006
    assert best.expanded_connections == 338880

    # Keep the candidate close to every published aggregate anchor without
    # pretending that any of these tolerances came from the NxTF authors.
    assert abs(best.neuron_count - PAPER_NEURON_TARGET) / PAPER_NEURON_TARGET < 0.06
    assert (
        abs(best.trainable_parameters - PAPER_TRAINABLE_PARAMETER_TARGET)
        / PAPER_TRAINABLE_PARAMETER_TARGET
        < 0.01
    )
    assert (
        abs(best.expanded_connections - PAPER_EXPANDED_CONNECTION_TARGET)
        / PAPER_EXPANDED_CONNECTION_TARGET
        < 0.01
    )
    assert (
        abs(best.kernel_weights - PAPER_SHARED_WEIGHT_TARGET)
        / PAPER_SHARED_WEIGHT_TARGET
        < 0.04
    )


def test_structural_network_matches_reconstruction_counts() -> None:
    network = build_structural_network()

    assert sum(population.size for population in network.populations) == 4218
    assert len(network.populations) == 56
    assert sum(
        len(projection.connections) for projection in network.projections
    ) + sum(
        len(projection.connections) for projection in network.input_projections
    ) == PROPOSED_METRICS.expanded_connections


def test_default_p06_first_fit_exposes_synapse_capacity_pressure() -> None:
    with pytest.raises(MappingError) as caught:
        compile_network(build_structural_network())

    assert caught.value.code == "core_resource_capacity"
    assert caught.value.context["resource"] == "synapse_bytes"
    assert caught.value.context["used"] > caught.value.context["limit"]


def test_capacity_safe_p06_probe_uses_five_logical_cores() -> None:
    assert P06_STRUCTURAL_COMPARTMENTS_PER_CORE == 900

    compiled = compile_structural_probe()
    report = compiled.report()

    assert report["logical_core_count"] == 5
    assert report["placement_count"] == 4218
    assert report["ingress_route_count"] == 2187
    assert report["connection_sharing"]["expanded_connections"] == 338880
    assert report["connection_sharing"]["stored_shared_parameters"] == 64235
    assert report["static_route_estimate"] == {
        "total": 7860,
        "local": 737,
        "remote": 7123,
    }

    expected_usage = (
        (900, 729, 2700, 12120, 2197, 22500),
        (900, 729, 2700, 16336, 3211, 22500),
        (900, 2745, 1210, 82360, 17181, 91584),
        (900, 2016, 729, 101024, 22680, 113400),
        (618, 3828, 521, 95464, 18966, 88896),
    )
    actual_usage = tuple(
        (
            core["usage"]["compartments"],
            core["usage"]["input_axons"],
            core["usage"]["output_routes"],
            core["usage"]["synapse_bytes"],
            core["usage"]["shared_parameters"],
            core["usage"]["expanded_connections"],
        )
        for core in report["cores"]
    )
    assert actual_usage == expected_usage
