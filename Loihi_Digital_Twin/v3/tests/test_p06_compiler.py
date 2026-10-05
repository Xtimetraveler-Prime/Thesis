from __future__ import annotations

import pytest

from loihi_twin_v2 import (
    CompartmentConfig,
    CompiledDeployment,
    CoreCapacity,
    InputPopulationSpec,
    InputProjectionSpec,
    MappingError,
    MappingOptions,
    NetworkSpec,
    PopulationSpec,
    ProjectionConnection,
    ProjectionSpec,
    compile_network,
    export_compiled_fpga_image,
)


def lif(threshold: int = 5) -> CompartmentConfig:
    return CompartmentConfig(
        current_decay=4096,
        voltage_decay=4096,
        threshold=threshold,
    )


def connection(source: int, destination: int, weight: int = 6) -> ProjectionConnection:
    return ProjectionConnection(source, destination, weight)


def test_p06_network_and_compiled_deployment_round_trip_are_fingerprinted():
    network = NetworkSpec(
        populations=(PopulationSpec("neurons", 2, lif()),),
        input_populations=(InputPopulationSpec("stimulus", 1),),
        input_projections=(
            InputProjectionSpec(
                "stimulus_to_neurons",
                "stimulus",
                "neurons",
                (connection(0, 0), connection(0, 1)),
            ),
        ),
    )

    reloaded_network = NetworkSpec.from_json(network.to_json())
    assert reloaded_network.fingerprint == network.fingerprint

    compiled = compile_network(network)
    reloaded = CompiledDeployment.from_json(compiled.to_json())
    assert reloaded.fingerprint == compiled.fingerprint
    assert reloaded.logical_deployment.fingerprint == compiled.logical_deployment.fingerprint
    assert reloaded.report() == compiled.report()


def test_p06_mapping_is_deterministic_across_equivalent_input_orderings():
    populations_a = (
        PopulationSpec("a_source", 2, lif()),
        PopulationSpec("b_destination", 2, lif()),
    )
    projection_connections = (connection(1, 1, 4), connection(0, 0, 3))
    network_a = NetworkSpec(
        populations=populations_a,
        projections=(
            ProjectionSpec(
                "projection",
                "a_source",
                "b_destination",
                projection_connections,
            ),
        ),
    )
    network_b = NetworkSpec(
        populations=tuple(reversed(populations_a)),
        projections=(
            ProjectionSpec(
                "projection",
                "a_source",
                "b_destination",
                tuple(reversed(projection_connections)),
            ),
        ),
    )

    compiled_a = compile_network(network_a)
    compiled_b = compile_network(network_b)

    assert network_a.fingerprint == network_b.fingerprint
    assert compiled_a.fingerprint == compiled_b.fingerprint
    assert compiled_a.logical_deployment.fingerprint == compiled_b.logical_deployment.fingerprint
    assert compiled_a.placement == compiled_b.placement


def test_p06_population_partitioning_is_deterministic_and_can_split_a_population():
    compiled = compile_network(
        NetworkSpec(populations=(PopulationSpec("layer", 5, lif()),)),
        MappingOptions(compartments_per_core=2),
    )

    assert len(compiled.logical_deployment.core_configs) == 3
    assert [(p.neuron_index, p.core_id, p.compartment_id) for p in compiled.placement] == [
        (0, 0, 0),
        (1, 0, 1),
        (2, 1, 0),
        (3, 1, 1),
        (4, 2, 0),
    ]
    assert [len(core.compartments) for core in compiled.logical_deployment.core_configs] == [2, 2, 1]


def test_p06_relative_fanout_patterns_share_one_synapse_template():
    network = NetworkSpec(
        populations=(
            PopulationSpec("a_source", 2, lif()),
            PopulationSpec("b_destination", 4, lif()),
        ),
        projections=(
            ProjectionSpec(
                "shared_pattern",
                "a_source",
                "b_destination",
                (
                    connection(0, 0, 3),
                    connection(0, 1, 4),
                    connection(1, 2, 3),
                    connection(1, 3, 4),
                ),
            ),
        ),
    )

    compiled = compile_network(network)
    core = compiled.logical_deployment.core_configs[0]

    assert len(core.synapse_templates) == 1
    assert len(core.synapse_templates[0].entries) == 2
    assert len(core.input_axons) == 2
    assert [binding.target_offset for binding in core.input_axons] == [2, 4]
    assert core.resource_usage.expanded_connections == 4
    assert core.resource_usage.shared_parameters == 2
    assert compiled.report()["connection_sharing"]["expanded_per_stored_parameter"] == 2.0


def test_p06_external_ingress_and_compiled_python_execution_use_same_mapping():
    network = NetworkSpec(
        populations=(
            PopulationSpec("a_source", 1, lif()),
            PopulationSpec("b_destination", 1, lif()),
        ),
        projections=(
            ProjectionSpec(
                "source_to_destination",
                "a_source",
                "b_destination",
                (connection(0, 0, 6),),
            ),
        ),
        input_populations=(InputPopulationSpec("stimulus", 1),),
        input_projections=(
            InputProjectionSpec(
                "stimulus_to_source",
                "stimulus",
                "a_source",
                (connection(0, 0, 6),),
            ),
        ),
    )
    compiled = compile_network(network)
    chip = compiled.build_chip()

    t0 = chip.step(compiled.external_packets("stimulus", (0,), target_timestep=0))
    source = next(core for core in t0.cores if core.logical_core_id == 0)
    assert source.spikes_out == (0,)
    assert len(source.packets_out) == 1

    t1 = chip.step()
    destination = next(core for core in t1.cores if core.logical_core_id == 0)
    assert destination.spikes_out == (1,)


def test_p06_capacity_failure_reports_core_resource_and_limit():
    network = NetworkSpec(
        populations=(
            PopulationSpec("a_source", 2, lif()),
            PopulationSpec("b_destination", 1, lif()),
        ),
        projections=(
            ProjectionSpec(
                "fanin",
                "a_source",
                "b_destination",
                (connection(0, 0), connection(1, 0)),
            ),
        ),
    )
    options = MappingOptions(
        capacity=CoreCapacity(
            compartments=1024,
            input_axons=1,
            output_routes=4096,
            synapse_bytes=128 * 1024,
        )
    )

    with pytest.raises(MappingError) as excinfo:
        compile_network(network, options)

    assert excinfo.value.code == "core_resource_capacity"
    assert excinfo.value.context["core_id"] == 0
    assert excinfo.value.context["resource"] == "input_axons"
    assert excinfo.value.context["used"] == 2
    assert excinfo.value.context["limit"] == 1


def test_p06_same_compiled_artifact_exports_to_p05_full_context_fpga_image():
    compiled = compile_network(
        NetworkSpec(populations=(PopulationSpec("three", 3, lif()),)),
        MappingOptions(compartments_per_core=1),
    )

    fpga = export_compiled_fpga_image(compiled)

    assert fpga.compiled_deployment_fingerprint == compiled.fingerprint
    assert fpga.source_fingerprint == compiled.source_fingerprint
    assert fpga.logical_core_count == 3
    assert fpga.logical_to_context_slot == {0: 0, 1: 1, 2: 2}
    assert fpga.report()["logical_capacity_changed"] is False


def test_p06_fpga_export_rejects_more_than_three_currently_resident_contexts():
    compiled = compile_network(
        NetworkSpec(populations=(PopulationSpec("four", 4, lif()),)),
        MappingOptions(compartments_per_core=1),
    )

    with pytest.raises(ValueError, match="resident P05 FPGA context count"):
        export_compiled_fpga_image(compiled)
