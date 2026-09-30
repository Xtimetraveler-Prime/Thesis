from __future__ import annotations

import pytest

from loihi_twin_v2 import MappingError, MappingOptions, compile_network
from loihi_twin_v2.workload_p07 import build_p07_deep_network


def _compiled():
    return compile_network(
        build_p07_deep_network(), MappingOptions(compartments_per_core=4)
    )


def test_p07_six_layers_pack_deterministically_into_three_cores():
    compiled = _compiled()
    assert len(compiled.logical_deployment.core_configs) == 3

    by_population: dict[str, list[tuple[int, int]]] = {}
    for record in compiled.placement:
        by_population.setdefault(record.population, []).append(
            (record.core_id, record.compartment_id)
        )

    assert by_population == {
        "layer0": [(0, 0), (0, 1)],
        "layer1": [(0, 2), (0, 3)],
        "layer2": [(1, 0), (1, 1)],
        "layer3": [(1, 2), (1, 3)],
        "layer4": [(2, 0), (2, 1)],
        "layer5": [(2, 2), (2, 3)],
    }


def test_p07_mapping_exercises_sharing_and_local_remote_traffic():
    report = _compiled().report()
    assert report["logical_core_count"] == 3
    assert report["ingress_route_count"] == 4
    assert report["static_route_estimate"] == {
        "total": 10,
        "local": 6,
        "remote": 4,
    }
    sharing = report["connection_sharing"]
    assert sharing["expanded_connections"] == 28
    assert sharing["stored_shared_parameters"] == 6
    assert sharing["expanded_per_stored_parameter"] == pytest.approx(28 / 6)
    assert [core["usage"]["compartments"] for core in report["cores"]] == [4, 4, 4]


def test_p07_same_network_records_explicit_two_core_capacity_failure():
    with pytest.raises(MappingError) as failure:
        compile_network(
            build_p07_deep_network(),
            MappingOptions(compartments_per_core=4, max_logical_cores=2),
        )
    assert failure.value.code == "logical_core_capacity"
    assert failure.value.context == {"required": 3, "limit": 2}


def test_p07_spike_wave_crosses_six_layers_with_alternating_local_remote_traffic():
    compiled = _compiled()
    chip = compiled.build_chip()
    initial = compiled.external_packets("pixels", (0,), target_timestep=0)

    expected_spikes = (
        {0: (0, 1)},
        {0: (2, 3)},
        {1: (0, 1)},
        {1: (2, 3)},
        {2: (0, 1)},
        {2: (2, 3)},
        {},
    )
    # packet_traffic is a cumulative normalized traffic snapshot.
    expected_cumulative_traffic = (
        (2, 0),
        (2, 2),
        (4, 2),
        (4, 4),
        (6, 4),
        (6, 4),
        (6, 4),
    )

    for timestep in range(7):
        trace = chip.step(initial if timestep == 0 else ())
        actual_spikes = {
            core.logical_core_id: core.spikes_out
            for core in trace.cores
            if core.spikes_out
        }
        assert actual_spikes == expected_spikes[timestep]
        local = sum(row[4] for row in trace.packet_traffic if row[3] == "local")
        remote = sum(row[4] for row in trace.packet_traffic if row[3] == "remote")
        assert (local, remote) == expected_cumulative_traffic[timestep]


def test_p07_forward_reverse_logical_service_order_is_invariant():
    compiled = _compiled()
    initial = compiled.external_packets("pixels", (0, 1), target_timestep=0)
    traces = []
    for order in ((0, 1, 2), (2, 1, 0)):
        chip = compiled.build_chip()
        run = []
        for timestep in range(7):
            trace = chip.step(
                initial if timestep == 0 else (),
                service_order=order,
                reverse_packet_drain=order[0] == 2,
            )
            run.append(trace)
        traces.append(tuple(run))
    assert traces[0] == traces[1]
