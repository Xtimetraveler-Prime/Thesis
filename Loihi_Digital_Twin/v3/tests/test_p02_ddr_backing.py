from __future__ import annotations

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
    ddr_bank_slice,
    parse_ddr_context_header,
)
from loihi_twin_v2.ddr_backing import (
    ContextTransferModel,
    DdrBackingStoreModel,
    P02_FULL_PAGE_OUT_BYTES,
    P02_MUTABLE_PAGE_OUT_BYTES,
    P02_PAGE_IN_BYTES,
    PageOutPolicy,
)


def make_core(core_id: int, core_count: int = 5) -> LogicalCoreConfig:
    next_core = (core_id + 1) % core_count
    return LogicalCoreConfig(
        core_id=core_id,
        compartments=(
            CompartmentConfig(
                current_decay=4096,
                voltage_decay=4096,
                threshold=5,
            ),
        ),
        input_axons=(InputAxonBinding(axon_id=10 + core_id, template_id=0),),
        synapse_templates=(
            SynapseTemplate(
                template_id=0,
                entries=(SynapseEntry(target_compartment=0, weight=6),),
            ),
        ),
        output_routes=(
            OutputRouteEntry(
                source_compartment=0,
                routes=(
                    OutputRoute(
                        destination_core=next_core,
                        destination_axon=10 + next_core,
                    ),
                ),
            ),
        ),
        arithmetic=P03_REQUIRED_ARITHMETIC,
    )


def make_backing() -> DdrBackingStoreModel:
    image = export_paged_hardware_image(
        tuple(make_core(core_id) for core_id in range(5))
    )
    return DdrBackingStoreModel(image, backing_base=0x4000_0000)


def test_p02_2_transfer_byte_counts_match_physical_payloads():
    assert P02_PAGE_IN_BYTES == 0x6B000
    assert P02_FULL_PAGE_OUT_BYTES == 0x6B000
    assert P02_MUTABLE_PAGE_OUT_BYTES == 0x1A000


def test_p02_2_backing_store_keeps_logical_id_to_fixed_ddr_address():
    backing = make_backing()

    assert backing.address(0) == 0x4000_0000
    assert backing.address(1) == 0x4008_0000
    assert backing.address(4) == 0x4020_0000


def test_p02_2_page_in_materializes_all_banks_and_runtime_metadata():
    backing = make_backing()
    transfer = ContextTransferModel(backing)

    page_in = transfer.page_in(0, 2)
    resident = transfer.resident(2)

    assert page_in.operation == "page-in"
    assert page_in.logical_core_id == 0
    assert page_in.resident_slot == 2
    assert page_in.bytes_transferred == P02_PAGE_IN_BYTES
    assert transfer.residency == (None, None, 0)
    assert resident.logical_core_id == 0
    assert resident.current_event_bank == 0
    assert resident.compartment_count == 1
    assert resident.event0_count == 0
    assert resident.event1_count == 0
    assert resident.packet_count == 0
    assert set(resident.banks) == {
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
    }


def test_p02_2_mutated_state_and_events_survive_evict_and_reload():
    backing = make_backing()
    transfer = ContextTransferModel(backing)

    transfer.page_in(0, 0)
    original_fingerprint = backing.fingerprint(0)

    state_word = 0x0002_000456_FFFF85
    transfer.write_word(0, "state", 0, state_word)
    transfer.write_word(0, "event1", 0, 0x123)
    transfer.write_word(0, "event1", 1, 0x456)
    transfer.set_runtime_metadata(
        0,
        current_event_bank=1,
        event1_count=2,
        packet_count=0,
    )

    page_out = transfer.page_out(0, policy=PageOutPolicy.MUTABLE_ONLY)
    assert page_out.bytes_transferred == P02_MUTABLE_PAGE_OUT_BYTES
    assert transfer.residency == (None, None, None)
    assert backing.fingerprint(0) != original_fingerprint

    header = parse_ddr_context_header(backing.record(0))
    assert header.current_event_bank == 1
    assert header.event1_count == 2

    transfer.page_in(0, 1)
    assert transfer.read_word(1, "state", 0) == state_word
    assert transfer.read_word(1, "event1", 0) == 0x123
    assert transfer.read_word(1, "event1", 1) == 0x456
    reloaded = transfer.resident(1)
    assert reloaded.current_event_bank == 1
    assert reloaded.event1_count == 2


def test_p02_2_mutable_only_writeback_matches_full_writeback():
    full_backing = make_backing()
    mutable_backing = make_backing()
    full = ContextTransferModel(full_backing)
    mutable = ContextTransferModel(mutable_backing)

    for model in (full, mutable):
        model.page_in(2, 0)
        model.write_word(0, "state", 0, 0x55AA)
        model.write_word(0, "event0", 0, 0x7)
        model.write_word(0, "trace", 0, (1 << 200) | 0x33)
        model.write_word(0, "packet", 0, 0x1234_5678_9ABC_DEF0)
        model.set_runtime_metadata(
            0,
            current_event_bank=0,
            event0_count=1,
            packet_count=1,
        )

    full_out = full.page_out(0, policy=PageOutPolicy.FULL_PAYLOAD)
    mutable_out = mutable.page_out(0, policy=PageOutPolicy.MUTABLE_ONLY)

    assert full_out.bytes_transferred == P02_FULL_PAGE_OUT_BYTES
    assert mutable_out.bytes_transferred == P02_MUTABLE_PAGE_OUT_BYTES
    assert full_backing.record(2) == mutable_backing.record(2)


def test_p02_2_static_banks_are_not_runtime_writable():
    transfer = ContextTransferModel(make_backing())
    transfer.page_in(0, 0)

    for bank in ("config", "axon", "synapse", "route_descriptor", "route"):
        try:
            transfer.write_word(0, bank, 0, 1)
        except ValueError as exc:
            assert "static during execution" in str(exc)
        else:
            raise AssertionError(f"static bank {bank} unexpectedly accepted a write")


def test_p02_2_replace_writes_back_victim_before_loading_new_core():
    backing = make_backing()
    transfer = ContextTransferModel(backing)

    transfer.page_in(0, 0)
    transfer.write_word(0, "state", 0, 0xDEAD)
    old_state_slice = ddr_bank_slice("state")
    assert int.from_bytes(
        backing.record(0)[old_state_slice.start : old_state_slice.start + 8],
        "little",
    ) != 0xDEAD

    page_out, page_in = transfer.replace(
        4,
        0,
        page_out_policy=PageOutPolicy.MUTABLE_ONLY,
    )

    assert page_out is not None
    assert page_out.logical_core_id == 0
    assert page_in.logical_core_id == 4
    assert page_in.evicted_logical_core_id == 0
    assert transfer.residency == (4, None, None)
    assert int.from_bytes(
        backing.record(0)[old_state_slice.start : old_state_slice.start + 8],
        "little",
    ) == 0xDEAD


def test_p02_2_page_in_requires_explicit_eviction_of_occupied_slot():
    transfer = ContextTransferModel(make_backing())
    transfer.page_in(0, 0)

    try:
        transfer.page_in(1, 0)
    except ValueError as exc:
        assert "page it out first" in str(exc)
    else:
        raise AssertionError("occupied resident slot accepted page-in")
