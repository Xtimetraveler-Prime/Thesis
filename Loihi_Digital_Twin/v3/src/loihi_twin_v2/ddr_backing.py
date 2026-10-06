"""P02.2 software model for DDR-backed resident-context transfers.

The K26 DDR ABI is defined in :mod:`ddr_abi`.  This module models the boundary
that P02.3 hardware must implement: complete logical contexts are authoritative
in DDR, while at most three resident slots contain the ten P05 payload banks
plus the small runtime metadata required to interpret them.

No physical AXI latency is claimed here.  Transfer byte counts are exact for the
selected bank set and are intended to make later hardware measurements explicit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .ddr_abi import (
    P02_DDR_BANK_LAYOUT,
    P02_DDR_CONTEXT_STRIDE_BYTES,
    build_initial_ddr_context_record,
    ddr_bank_slice,
    ddr_context_address,
    ddr_context_record_fingerprint,
    parse_ddr_context_header,
    refresh_ddr_context_runtime_header,
)
from .hardware_p05 import P05_MAX_RESIDENT_CONTEXTS
from .hardware_p08 import PagedHardwareImage


P02_PAGE_IN_BANKS = tuple(bank.name for bank in P02_DDR_BANK_LAYOUT)
P02_MUTABLE_BANKS = ("state", "event0", "event1", "trace", "packet")
P02_STATIC_BANKS = tuple(
    bank.name for bank in P02_DDR_BANK_LAYOUT if bank.name not in P02_MUTABLE_BANKS
)
P02_PAGE_IN_BYTES = sum(bank.size_bytes for bank in P02_DDR_BANK_LAYOUT)
P02_FULL_PAGE_OUT_BYTES = P02_PAGE_IN_BYTES
P02_MUTABLE_PAGE_OUT_BYTES = sum(
    bank.size_bytes for bank in P02_DDR_BANK_LAYOUT
    if bank.name in P02_MUTABLE_BANKS
)


class PageOutPolicy(str, Enum):
    FULL_PAYLOAD = "full-payload"
    MUTABLE_ONLY = "mutable-only"


@dataclass(frozen=True, slots=True)
class PageTransfer:
    operation: str
    logical_core_id: int
    resident_slot: int
    banks: tuple[str, ...]
    bytes_transferred: int
    evicted_logical_core_id: int | None = None


@dataclass(slots=True)
class ResidentContext:
    logical_core_id: int
    current_event_bank: int
    compartment_count: int
    synapse_count: int
    route_count: int
    event0_count: int
    event1_count: int
    packet_count: int
    banks: dict[str, bytearray]
    dirty: bool = False

    def bank(self, name: str) -> bytearray:
        try:
            return self.banks[name]
        except KeyError as exc:
            raise KeyError(f"unknown resident bank {name!r}") from exc


class DdrBackingStoreModel:
    """Sparse software model of the fixed-address 64 MiB DDR backing region."""

    def __init__(
        self,
        hardware_image: PagedHardwareImage,
        *,
        backing_base: int = 0,
    ) -> None:
        # Validate alignment using the accepted address helper.
        ddr_context_address(backing_base, 0)
        self.backing_base = backing_base
        self.logical_core_ids = hardware_image.logical_core_ids
        self._records: dict[int, bytes] = {
            context.logical_core_id: build_initial_ddr_context_record(context)
            for context in hardware_image.backing_contexts
        }

    def has_core(self, logical_core_id: int) -> bool:
        return logical_core_id in self._records

    def address(self, logical_core_id: int) -> int:
        if logical_core_id not in self._records:
            raise KeyError(f"logical core {logical_core_id} is not in the DDR deployment")
        return ddr_context_address(self.backing_base, logical_core_id)

    def record(self, logical_core_id: int) -> bytes:
        try:
            return self._records[logical_core_id]
        except KeyError as exc:
            raise KeyError(
                f"logical core {logical_core_id} is not in the DDR deployment"
            ) from exc

    def replace_record(self, logical_core_id: int, record: bytes) -> None:
        if logical_core_id not in self._records:
            raise KeyError(f"logical core {logical_core_id} is not in the DDR deployment")
        header = parse_ddr_context_header(record)
        if header.logical_core_id != logical_core_id:
            raise ValueError(
                "DDR record logical_core_id does not match backing-store destination"
            )
        self._records[logical_core_id] = record

    def fingerprint(self, logical_core_id: int) -> str:
        return ddr_context_record_fingerprint(self.record(logical_core_id))


class ContextTransferModel:
    """Reference page-in/page-out behavior for the three accepted resident slots."""

    def __init__(
        self,
        backing: DdrBackingStoreModel,
        *,
        resident_slot_count: int = P05_MAX_RESIDENT_CONTEXTS,
    ) -> None:
        if not 1 <= resident_slot_count <= P05_MAX_RESIDENT_CONTEXTS:
            raise ValueError(
                f"resident_slot_count must be in [1, {P05_MAX_RESIDENT_CONTEXTS}]"
            )
        self.backing = backing
        self.resident_slot_count = resident_slot_count
        self._slots: list[ResidentContext | None] = [None] * resident_slot_count
        self.history: list[PageTransfer] = []

    @property
    def residency(self) -> tuple[int | None, ...]:
        return tuple(
            None if context is None else context.logical_core_id
            for context in self._slots
        )

    def _require_slot(self, resident_slot: int) -> None:
        if isinstance(resident_slot, bool) or not isinstance(resident_slot, int):
            raise TypeError("resident_slot must be an int")
        if not 0 <= resident_slot < self.resident_slot_count:
            raise ValueError(
                f"resident_slot must be in [0, {self.resident_slot_count})"
            )

    def resident(self, resident_slot: int) -> ResidentContext:
        self._require_slot(resident_slot)
        context = self._slots[resident_slot]
        if context is None:
            raise ValueError(f"resident slot {resident_slot} is empty")
        return context

    @staticmethod
    def _transfer_bytes(bank_names: tuple[str, ...]) -> int:
        wanted = set(bank_names)
        return sum(
            bank.size_bytes for bank in P02_DDR_BANK_LAYOUT if bank.name in wanted
        )

    def page_in(self, logical_core_id: int, resident_slot: int) -> PageTransfer:
        self._require_slot(resident_slot)
        occupied = self._slots[resident_slot]
        if occupied is not None:
            raise ValueError(
                f"resident slot {resident_slot} already contains logical core "
                f"{occupied.logical_core_id}; page it out first"
            )

        record = self.backing.record(logical_core_id)
        header = parse_ddr_context_header(record)
        banks = {
            name: bytearray(record[ddr_bank_slice(name)])
            for name in P02_PAGE_IN_BANKS
        }
        self._slots[resident_slot] = ResidentContext(
            logical_core_id=logical_core_id,
            current_event_bank=header.current_event_bank,
            compartment_count=header.compartment_count,
            synapse_count=header.synapse_count,
            route_count=header.route_count,
            event0_count=header.event0_count,
            event1_count=header.event1_count,
            packet_count=header.packet_count,
            banks=banks,
            dirty=False,
        )
        transfer = PageTransfer(
            operation="page-in",
            logical_core_id=logical_core_id,
            resident_slot=resident_slot,
            banks=P02_PAGE_IN_BANKS,
            bytes_transferred=self._transfer_bytes(P02_PAGE_IN_BANKS),
        )
        self.history.append(transfer)
        return transfer

    def write_word(
        self,
        resident_slot: int,
        bank_name: str,
        index: int,
        word: int,
    ) -> None:
        context = self.resident(resident_slot)
        if bank_name not in P02_MUTABLE_BANKS:
            raise ValueError(f"bank {bank_name!r} is static during execution")

        bank_layout = next(
            (bank for bank in P02_DDR_BANK_LAYOUT if bank.name == bank_name),
            None,
        )
        if bank_layout is None:
            raise KeyError(f"unknown resident bank {bank_name!r}")
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("index must be an int")
        if not 0 <= index < bank_layout.depth:
            raise ValueError(f"{bank_name} index exceeds bank depth")
        if isinstance(word, bool) or not isinstance(word, int):
            raise TypeError("word must be an int")
        if not 0 <= word < (1 << (bank_layout.word_bytes * 8)):
            raise ValueError(f"word does not fit {bank_layout.word_bytes * 8} bits")

        start = index * bank_layout.word_bytes
        context.bank(bank_name)[start : start + bank_layout.word_bytes] = word.to_bytes(
            bank_layout.word_bytes, "little"
        )
        context.dirty = True

    def read_word(self, resident_slot: int, bank_name: str, index: int) -> int:
        context = self.resident(resident_slot)
        bank_layout = next(
            (bank for bank in P02_DDR_BANK_LAYOUT if bank.name == bank_name),
            None,
        )
        if bank_layout is None:
            raise KeyError(f"unknown resident bank {bank_name!r}")
        if not 0 <= index < bank_layout.depth:
            raise ValueError(f"{bank_name} index exceeds bank depth")
        start = index * bank_layout.word_bytes
        return int.from_bytes(
            context.bank(bank_name)[start : start + bank_layout.word_bytes],
            "little",
        )

    def set_runtime_metadata(
        self,
        resident_slot: int,
        *,
        current_event_bank: int | None = None,
        event0_count: int | None = None,
        event1_count: int | None = None,
        packet_count: int | None = None,
    ) -> None:
        context = self.resident(resident_slot)
        if current_event_bank is not None:
            if current_event_bank not in (0, 1):
                raise ValueError("current_event_bank must be 0 or 1")
            context.current_event_bank = current_event_bank
        for name, value in (
            ("event0_count", event0_count),
            ("event1_count", event1_count),
            ("packet_count", packet_count),
        ):
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an int")
            if not 0 <= value <= 4096:
                raise ValueError(f"{name} must be in [0, 4096]")
            setattr(context, name, value)
        context.dirty = True

    def page_out(
        self,
        resident_slot: int,
        *,
        policy: PageOutPolicy = PageOutPolicy.FULL_PAYLOAD,
    ) -> PageTransfer:
        context = self.resident(resident_slot)
        record = bytearray(self.backing.record(context.logical_core_id))

        bank_names = (
            P02_PAGE_IN_BANKS
            if policy is PageOutPolicy.FULL_PAYLOAD
            else P02_MUTABLE_BANKS
        )
        for name in bank_names:
            target = ddr_bank_slice(name)
            resident_bank = context.bank(name)
            if len(resident_bank) != target.stop - target.start:
                raise ValueError(f"resident bank {name!r} size mismatch")
            record[target] = resident_bank

        refreshed = refresh_ddr_context_runtime_header(
            record,
            current_event_bank=context.current_event_bank,
            event0_count=context.event0_count,
            event1_count=context.event1_count,
            packet_count=context.packet_count,
        )
        self.backing.replace_record(context.logical_core_id, refreshed)

        transfer = PageTransfer(
            operation="page-out",
            logical_core_id=context.logical_core_id,
            resident_slot=resident_slot,
            banks=bank_names,
            bytes_transferred=self._transfer_bytes(bank_names),
        )
        self.history.append(transfer)
        self._slots[resident_slot] = None
        return transfer

    def replace(
        self,
        logical_core_id: int,
        resident_slot: int,
        *,
        page_out_policy: PageOutPolicy = PageOutPolicy.FULL_PAYLOAD,
    ) -> tuple[PageTransfer | None, PageTransfer]:
        self._require_slot(resident_slot)
        previous = self._slots[resident_slot]
        page_out_transfer = None
        if previous is not None:
            page_out_transfer = self.page_out(
                resident_slot,
                policy=page_out_policy,
            )
        page_in_transfer = self.page_in(logical_core_id, resident_slot)
        if page_out_transfer is not None:
            page_in_transfer = PageTransfer(
                operation=page_in_transfer.operation,
                logical_core_id=page_in_transfer.logical_core_id,
                resident_slot=page_in_transfer.resident_slot,
                banks=page_in_transfer.banks,
                bytes_transferred=page_in_transfer.bytes_transferred,
                evicted_logical_core_id=previous.logical_core_id,
            )
            self.history[-1] = page_in_transfer
        return page_out_transfer, page_in_transfer
