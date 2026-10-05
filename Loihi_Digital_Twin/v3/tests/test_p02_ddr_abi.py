from __future__ import annotations

import pytest

from loihi_twin_v2 import (
    CompartmentConfig,
    InputAxonBinding,
    LogicalCoreConfig,
    OutputRoute,
    OutputRouteEntry,
    P03_REQUIRED_ARITHMETIC,
    SynapseEntry,
    SynapseTemplate,
    export_paged_hardware_image,
)
from loihi_twin_v2.ddr_abi import (
    P02_DDR_BACKING_REGION_BYTES,
    P02_DDR_BANK_LAYOUT,
    P02_DDR_CONTEXT_STRIDE_BYTES,
    P02_DDR_HEADER_BYTES,
    P02_DDR_PAYLOAD_END,
    P02_DDR_RESERVED_TAIL_BYTES,
    build_initial_ddr_context_record,
    ddr_bank_slice,
    ddr_context_address,
    ddr_context_offset,
    ddr_context_record_fingerprint,
    parse_ddr_context_header,
)


def make_core(core_id: int = 7) -> LogicalCoreConfig:
    return LogicalCoreConfig(
        core_id=core_id,
        compartments=(
            CompartmentConfig(
                current_decay=4096,
                voltage_decay=2048,
                threshold=9,
                bias=-1,
            ),
            CompartmentConfig(
                current_decay=4096,
                voltage_decay=4096,
                threshold=5,
            ),
        ),
        input_axons=(
            InputAxonBinding(axon_id=3, template_id=0, target_offset=0),
            # Keep the maximum sparse axon ID while targeting the same valid\n            # two-compartment template range as the lower axon.\n            InputAxonBinding(axon_id=4095, template_id=0, target_offset=0),
        ),
        synapse_templates=(
            SynapseTemplate(
                template_id=0,
                entries=(
                    SynapseEntry(target_compartment=0, weight=6),
                    SynapseEntry(target_compartment=1, weight=-4),
                ),
            ),
        ),
        output_routes=(
            OutputRouteEntry(
                source_compartment=0,
                routes=(OutputRoute(destination_core=core_id, destination_axon=3),),
            ),
        ),
        arithmetic=P03_REQUIRED_ARITHMETIC,
    )


def backing_context(core_id: int = 7):
    image = export_paged_hardware_image((make_core(core_id),))
    return image.backing_contexts[0]


def test_p02_ddr_layout_is_fixed_512k_and_nonoverlapping():
    assert P02_DDR_HEADER_BYTES == 0x1000
    assert P02_DDR_CONTEXT_STRIDE_BYTES == 0x80000
    assert P02_DDR_PAYLOAD_END == 0x6C000
    assert P02_DDR_RESERVED_TAIL_BYTES == 0x14000
    assert P02_DDR_BACKING_REGION_BYTES == 64 * 1024 * 1024

    assert [bank.name for bank in P02_DDR_BANK_LAYOUT] == [
        "config",
        "state",
        "axon",
        "synapse",
        "route_descriptor",
        "route",
        "event0",
        "event1",
        "trace",
        "packet",
    ]

    previous_end = P02_DDR_HEADER_BYTES
    for bank in P02_DDR_BANK_LAYOUT:
        assert bank.offset == previous_end
        previous_end = bank.end
    assert previous_end == P02_DDR_PAYLOAD_END


def test_p02_ddr_core_address_is_simple_fixed_stride():
    base = 0x4000_0000
    assert ddr_context_offset(0) == 0
    assert ddr_context_offset(1) == 0x80000
    assert ddr_context_offset(127) == 127 * 0x80000
    assert ddr_context_address(base, 7) == base + 7 * 0x80000

    with pytest.raises(ValueError, match="512 KiB aligned"):
        ddr_context_address(base + 0x1000, 0)
    with pytest.raises(ValueError):
        ddr_context_offset(128)


def test_p02_initial_record_densifies_sparse_banks_and_round_trips_header():
    context = backing_context()
    record = build_initial_ddr_context_record(
        context,
        current_event_bank=1,
        event0_words=(3, 4),
        event1_words=(9,),
    )

    assert len(record) == P02_DDR_CONTEXT_STRIDE_BYTES
    header = parse_ddr_context_header(record)
    assert header.logical_core_id == 7
    assert header.current_event_bank == 1
    assert header.compartment_count == 2
    assert header.synapse_count == 2
    assert header.route_count == 1
    assert header.event0_count == 2
    assert header.event1_count == 1
    assert header.packet_count == 0

    image = context.image

    config = record[ddr_bank_slice("config")]
    assert int.from_bytes(config[:16], "little") == image.config_words[0]
    assert int.from_bytes(config[16:32], "little") == image.config_words[1]
    assert set(config[32:]) <= {0}

    axon = record[ddr_bank_slice("axon")]
    assert int.from_bytes(axon[3 * 8 : 4 * 8], "little") == image.axon_words[0].word
    assert int.from_bytes(axon[4095 * 8 : 4096 * 8], "little") == image.axon_words[1].word
    assert int.from_bytes(axon[4 * 8 : 5 * 8], "little") == 0

    event0 = record[ddr_bank_slice("event0")]
    event1 = record[ddr_bank_slice("event1")]
    assert int.from_bytes(event0[0:4], "little") == 3
    assert int.from_bytes(event0[4:8], "little") == 4
    assert int.from_bytes(event1[0:4], "little") == 9

    assert set(record[P02_DDR_PAYLOAD_END:]) <= {0}


def test_p02_record_serialization_is_deterministic_and_fingerprinted():
    context = backing_context()
    a = build_initial_ddr_context_record(context, event0_words=(3,))
    b = build_initial_ddr_context_record(context, event0_words=(3,))
    assert a == b
    assert ddr_context_record_fingerprint(a) == ddr_context_record_fingerprint(b)


def test_p02_record_detects_payload_corruption():
    record = bytearray(build_initial_ddr_context_record(backing_context()))
    state_slice = ddr_bank_slice("state")
    record[state_slice.start] ^= 0x01

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        parse_ddr_context_header(bytes(record))


def test_p02_record_rejects_invalid_event_inputs():
    context = backing_context()
    with pytest.raises(ValueError, match="current_event_bank"):
        build_initial_ddr_context_record(context, current_event_bank=2)
    with pytest.raises(ValueError, match="event count exceeds 4096"):
        build_initial_ddr_context_record(
            context,
            event0_words=tuple(0 for _ in range(4097)),
        )
