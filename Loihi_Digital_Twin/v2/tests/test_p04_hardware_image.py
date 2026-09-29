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
from loihi_twin_v2.hardware_p03 import P03_REQUIRED_ARITHMETIC
from loihi_twin_v2.hardware_p04 import (
    P04_PHYSICAL_INPUT_AXONS,
    P04_PROFILE_NAME,
    export_two_core_validation_image,
)


def core(core_id: int, axon_id: int, destination_core: int) -> LogicalCoreConfig:
    return LogicalCoreConfig(
        core_id=core_id,
        compartments=(CompartmentConfig(4096, 4096, 5),),
        input_axons=(InputAxonBinding(axon_id, 0),),
        synapse_templates=(SynapseTemplate(0, (SynapseEntry(0, 6),)),),
        output_routes=(
            OutputRouteEntry(0, (OutputRoute(destination_core, axon_id),)),
        ),
        arithmetic=P03_REQUIRED_ARITHMETIC,
    )


def test_p04_two_core_image_reuses_p03_words_without_changing_logical_contract():
    image = export_two_core_validation_image((core(0, 1, 1), core(1, 1, 0)))
    assert image.profile == P04_PROFILE_NAME
    assert image.core0.core_id == 0
    assert image.core1.core_id == 1
    assert image.core0.compartment_count == 1
    assert image.core1.compartment_count == 1
    assert image.core0.route_count == 1
    assert image.core1.route_count == 1


def test_p04_fixture_requires_exact_endpoint_ids_zero_and_one():
    with pytest.raises(ValueError, match="core IDs 0 and 1"):
        export_two_core_validation_image((core(0, 1, 0), core(2, 1, 0)))


def test_p04_fixture_rejects_physical_axon_address_without_redefining_logical_limit():
    high = P04_PHYSICAL_INPUT_AXONS
    config0 = core(0, high, 1)
    config1 = core(1, 1, 0)
    with pytest.raises(ValueError, match="fixture"):
        export_two_core_validation_image((config0, config1))


def test_p04_fixture_rejects_destination_outside_two_instantiated_endpoints():
    config0 = core(0, 1, 2)
    config1 = core(1, 1, 0)
    with pytest.raises(ValueError, match="uninstantiated core"):
        export_two_core_validation_image((config0, config1))
