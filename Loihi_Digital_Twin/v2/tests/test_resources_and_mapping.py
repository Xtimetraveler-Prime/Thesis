from __future__ import annotations

import pytest

from loihi_twin_v2 import (
    CompartmentConfig,
    Deployment,
    InputAxonBinding,
    LogicalChip,
    LogicalCoreConfig,
    OutputRoute,
    OutputRouteEntry,
    ResourceCapacityError,
    SpikePacket,
    SynapseEntry,
    SynapseTemplate,
)


def quiet_compartment() -> CompartmentConfig:
    return CompartmentConfig(4096, 4096, 1000)


def test_t7_rejects_compartment_capacity_overflow_with_named_resource():
    with pytest.raises(ResourceCapacityError) as exc:
        LogicalCoreConfig(
            core_id=0,
            compartments=tuple(quiet_compartment() for _ in range(1025)),
        )
    assert exc.value.resource == "compartments"


def test_t7_rejects_input_axon_capacity_overflow_with_named_resource():
    template = SynapseTemplate(0, (SynapseEntry(0, 1),))
    with pytest.raises(ResourceCapacityError) as exc:
        LogicalCoreConfig(
            core_id=0,
            compartments=(quiet_compartment(),),
            input_axons=tuple(InputAxonBinding(i, 0) for i in range(4097)),
            synapse_templates=(template,),
        )
    assert exc.value.resource == "input_axons"


def test_t7_rejects_output_route_capacity_overflow_with_named_resource():
    with pytest.raises(ResourceCapacityError) as exc:
        LogicalCoreConfig(
            core_id=0,
            compartments=(quiet_compartment(),),
            output_routes=(
                OutputRouteEntry(
                    0,
                    tuple(OutputRoute(1, 0) for _ in range(4097)),
                ),
            ),
        )
    assert exc.value.resource == "output_routes"


def test_t7_rejects_synapse_memory_capacity_overflow_with_named_resource():
    oversized = SynapseTemplate(
        0,
        tuple(SynapseEntry(0, 1) for _ in range(33000)),
    )
    with pytest.raises(ResourceCapacityError) as exc:
        LogicalCoreConfig(
            core_id=0,
            compartments=(quiet_compartment(),),
            input_axons=(InputAxonBinding(0, 0),),
            synapse_templates=(oversized,),
        )
    assert exc.value.resource == "synapse_bytes"


def _sharing_configs(shared: bool) -> LogicalCoreConfig:
    entries = (SynapseEntry(0, 2), SynapseEntry(1, 3))
    if shared:
        templates = (SynapseTemplate(0, entries),)
        bindings = (InputAxonBinding(0, 0), InputAxonBinding(1, 0))
    else:
        templates = (SynapseTemplate(0, entries), SynapseTemplate(1, entries))
        bindings = (InputAxonBinding(0, 0), InputAxonBinding(1, 1))
    return LogicalCoreConfig(
        core_id=0,
        compartments=(quiet_compartment(), quiet_compartment()),
        input_axons=bindings,
        synapse_templates=templates,
    )


def test_t8_shared_template_reduces_storage_without_changing_expanded_effects():
    shared = _sharing_configs(True)
    discrete = _sharing_configs(False)

    assert shared.resource_usage.expanded_connections == discrete.resource_usage.expanded_connections == 4
    assert shared.resource_usage.shared_parameters == 2
    assert discrete.resource_usage.shared_parameters == 4
    assert shared.resource_usage.synapse_bytes < discrete.resource_usage.synapse_bytes

    packets = (SpikePacket(0, 0, 0), SpikePacket(0, 0, 1))
    shared_trace = LogicalChip((shared,)).step(packets)
    discrete_trace = LogicalChip((discrete,)).step(packets)
    shared_state = tuple(x.state for x in shared_trace.cores[0].compartment_state_after)
    discrete_state = tuple(x.state for x in discrete_trace.cores[0].compartment_state_after)
    assert shared_state == discrete_state
    assert shared_state[0].voltage == 4
    assert shared_state[1].voltage == 6


def test_deployment_manifest_is_deterministic_and_core_order_independent():
    core0 = LogicalCoreConfig(core_id=0, compartments=(quiet_compartment(),))
    core1 = LogicalCoreConfig(core_id=1, compartments=(quiet_compartment(),))
    a = Deployment((core0, core1))
    b = Deployment((core1, core0))

    assert a.fingerprint == b.fingerprint
    assert a.manifest() == b.manifest()
    assert a.manifest()["logical_core_count"] == 2
    assert a.manifest()["cores"][0]["core_id"] == 0
