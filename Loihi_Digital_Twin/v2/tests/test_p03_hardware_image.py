from __future__ import annotations

import pytest

from loihi_twin_v2 import (
    ArithmeticConfig,
    CompartmentConfig,
    CompartmentState,
    InputAxonBinding,
    LogicalCoreConfig,
    OutputRoute,
    OutputRouteEntry,
    OverflowMode,
    SynapseEntry,
    SynapseTemplate,
)
from loihi_twin_v2.hardware_p03 import (
    P03_REQUIRED_ARITHMETIC,
    export_one_core_image,
    pack_compartment_config,
    pack_compartment_state,
    pack_output_packet,
    unpack_axon_word,
    unpack_compartment_config,
    unpack_compartment_state,
    unpack_output_packet,
    unpack_route_descriptor,
    unpack_route_word,
    unpack_synapse_word,
)
from loihi_twin_v2.packet import SpikePacket


def compartment(threshold: int = 5) -> CompartmentConfig:
    return CompartmentConfig(
        current_decay=4096,
        voltage_decay=2048,
        threshold=threshold,
        bias=-2,
        reset_voltage=-1,
        refractory_ticks=3,
    )


def test_p03_config_and_state_words_round_trip_signed_fields():
    cfg = compartment()
    packed_cfg = pack_compartment_config(cfg)
    assert unpack_compartment_config(packed_cfg) == {
        "current_decay": 4096,
        "voltage_decay": 2048,
        "threshold": 5,
        "bias": -2,
        "reset_voltage": -1,
        "refractory_ticks": 3,
    }

    state = CompartmentState(current=-123, voltage=456, refractory_remaining=2)
    assert unpack_compartment_state(pack_compartment_state(state)) == state


def test_p03_export_preserves_shared_template_storage():
    config = LogicalCoreConfig(
        core_id=7,
        compartments=(compartment(), compartment(100), compartment(3)),
        input_axons=(
            InputAxonBinding(axon_id=10, template_id=4, target_offset=0),
            InputAxonBinding(axon_id=11, template_id=4, target_offset=1),
        ),
        synapse_templates=(
            SynapseTemplate(
                template_id=4,
                entries=(SynapseEntry(0, 6), SynapseEntry(1, -4)),
            ),
        ),
        output_routes=(
            OutputRouteEntry(
                source_compartment=0,
                routes=(OutputRoute(1, 3), OutputRoute(2, 4)),
            ),
        ),
        arithmetic=P03_REQUIRED_ARITHMETIC,
    )

    image = export_one_core_image(config)
    assert image.core_id == 7
    assert image.compartment_count == 3
    assert image.synapse_count == 2
    assert len(image.synapse_words) == 2
    assert len(image.axon_words) == 2

    axon0 = unpack_axon_word(image.axon_words[0].word)
    axon1 = unpack_axon_word(image.axon_words[1].word)
    assert (axon0["synapse_start"], axon0["synapse_count"]) == (0, 2)
    assert (axon1["synapse_start"], axon1["synapse_count"]) == (0, 2)
    assert axon0["target_offset"] == 0
    assert axon1["target_offset"] == 1

    first_synapse = unpack_synapse_word(image.synapse_words[0])
    second_synapse = unpack_synapse_word(image.synapse_words[1])
    assert first_synapse["weight"] == 6
    assert second_synapse["weight"] == -4

    route_desc = unpack_route_descriptor(image.route_descriptor_words[0].word)
    assert route_desc["route_start"] == 0
    assert route_desc["route_count"] == 2
    assert unpack_route_word(image.route_words[0]) == {
        "destination_core": 1,
        "destination_axon": 3,
    }
    assert unpack_route_word(image.route_words[1]) == {
        "destination_core": 2,
        "destination_axon": 4,
    }


def test_p03_export_rejects_unbounded_python_arithmetic_profile():
    config = LogicalCoreConfig(
        core_id=0,
        compartments=(compartment(),),
        arithmetic=ArithmeticConfig(),
    )
    with pytest.raises(ValueError, match="24-bit saturating"):
        export_one_core_image(config)


def test_p03_output_packet_round_trip_matches_normalized_fields():
    packet = SpikePacket(
        target_timestep=17,
        destination_core=127,
        destination_axon=4095,
        source_core=3,
        source_compartment=1023,
        source_timestep=16,
    )
    decoded = unpack_output_packet(pack_output_packet(packet))
    assert decoded == {
        "destination_core": 127,
        "destination_axon": 4095,
        "source_compartment": 1023,
        "target_timestep": 17,
        "valid": True,
    }


def test_p03_initial_state_count_must_match_compartments():
    config = LogicalCoreConfig(
        core_id=0,
        compartments=(compartment(), compartment()),
        arithmetic=ArithmeticConfig(state_bits=24, overflow=OverflowMode.SATURATE),
    )
    with pytest.raises(ValueError, match="initial_states"):
        export_one_core_image(config, (CompartmentState(),))
