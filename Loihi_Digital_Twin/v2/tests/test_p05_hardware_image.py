from __future__ import annotations

import pytest

from loihi_twin_v2 import (
    CompartmentConfig,
    InputAxonBinding,
    LogicalCoreConfig,
    OutputRoute,
    OutputRouteEntry,
    SynapseEntry,
    SynapseTemplate,
)
from loihi_twin_v2.hardware_p05 import (
    P05_CONTEXT_BITS_PER_CORE,
    P05_ESTIMATED_URAM288,
    P05_K26_URAM288_AVAILABLE,
    P05_MAX_RESIDENT_CONTEXTS,
    P05_PHYSICAL_ENGINE_COUNT,
    export_virtualized_hardware_image,
)


def lif() -> CompartmentConfig:
    return CompartmentConfig(
        current_decay=4096,
        voltage_decay=4096,
        threshold=5,
    )


def core(core_id: int, axon_id: int, route_to: tuple[int, int] | None = None) -> LogicalCoreConfig:
    routes = ()
    if route_to is not None:
        routes = (OutputRouteEntry(0, (OutputRoute(*route_to),)),)
    return LogicalCoreConfig(
        core_id=core_id,
        compartments=(lif(),),
        input_axons=(InputAxonBinding(axon_id, 0),),
        synapse_templates=(SynapseTemplate(0, (SynapseEntry(0, 6),)),),
        output_routes=routes,
    )


def test_p05_context_slots_are_separate_from_logical_core_identity():
    image = export_virtualized_hardware_image(
        (
            core(7, 100, route_to=(42, 200)),
            core(42, 200, route_to=(99, 300)),
            core(99, 300, route_to=(7, 100)),
        )
    )

    assert image.physical_engine_count == P05_PHYSICAL_ENGINE_COUNT == 1
    assert image.logical_core_ids == (7, 42, 99)
    assert image.logical_to_context_slot == {7: 0, 42: 1, 99: 2}
    assert [context.context_slot for context in image.contexts] == [0, 1, 2]


def test_p05_full_context_profile_removes_p04_directed_fixture_axon_limit():
    image = export_virtualized_hardware_image(
        (
            core(0, 100, route_to=(1, 100)),
            core(1, 100),
        )
    )

    assert image.contexts[0].image.axon_words[0].index == 100
    assert image.report()["logical_capacity_changed"] is False


def test_p05_metadata_word_keeps_logical_id_and_counts_explicit():
    image = export_virtualized_hardware_image((core(37, 123),))
    context = image.contexts[0]
    word = context.metadata_word(initial_event_count=9)

    assert word & 0x7F == 37
    assert (word >> 7) & 0x7FF == context.image.compartment_count
    assert (word >> 18) & 0xFFFF == context.image.synapse_count
    assert (word >> 34) & 0x1FFF == context.image.route_count
    assert (word >> 47) & 0x1FFF == 9


def test_p05_three_context_uram_plan_leaves_headroom():
    assert P05_MAX_RESIDENT_CONTEXTS == 3
    assert P05_ESTIMATED_URAM288 == 47
    assert P05_ESTIMATED_URAM288 < P05_K26_URAM288_AVAILABLE
    assert P05_CONTEXT_BITS_PER_CORE > 3_375_104


def test_p05_rejects_routes_to_nonresident_logical_core():
    with pytest.raises(ValueError, match="unconfigured logical core"):
        export_virtualized_hardware_image((core(0, 0, route_to=(5, 1)),))


def test_p05_first_profile_rejects_more_than_three_resident_contexts():
    configs = tuple(core(i, i) for i in range(4))
    with pytest.raises(ValueError, match="at most 3 contexts"):
        export_virtualized_hardware_image(configs)
