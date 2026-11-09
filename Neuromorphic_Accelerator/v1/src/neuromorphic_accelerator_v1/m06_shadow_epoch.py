"""M06 SOURCE-ONLY shadow epoch: isolate speculative neural page writes.

In this serialized Python model, a complete shadow bytearray is copied from
canonical state at epoch start. The shadow AXI *behavioral* image may suffer
partial W commits; an unsuccessful epoch is discarded. Only independent
full-trace/final-image verification allows one software-atomic canonical
bytearray replacement. No real DDR copy/swap/atomic marker or PS/PL protocol
has been implemented or verified. A physical implementation needs an owned,
separately allocated shadow region and crash-safe commit record.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .m02_dense_reference import evaluate_dense
from .m02_types import InputCurrent, Network, ReferenceTrace
from .m06_axi_transport import AXIModelImage
from .m06_block_residency import BlockCache, CanonicalImage, Geometry, NoOwnership, ResidencyError
from .m06_paged_replay import PagedRun, replay_with_paging


class EpochError(ResidencyError):
    """A state-transition, provenance, or canonical consistency failure."""


@dataclass(frozen=True)
class EpochReceipt:
    epoch_id: str
    changed_pages: tuple[int, ...]
    canonical_version_after: tuple[int, ...]
    status: str = "SOFTWARE_COMMITTED_NOT_PHYSICAL_DDR"


class ShadowEpoch:
    """Single-threaded/serialized experimental copy-on-write neural epoch.

    No public mutation API to recover a committed/aborted state in place.
    No physical DDR write is issued, ever. All cache and AXI handshakes refer
    to SHADOW logical memory, not the external real canonical location.
    """

    def __init__(self, canonical: CanonicalImage, *, owner: str,
                 epoch_id: str, ready_delay_every: int = 3):
        if (not isinstance(epoch_id, str) or not epoch_id
                or not isinstance(owner, str) or not owner):
            raise ValueError("nonempty owner and epoch identifier required")
        canonical.check_owner(owner)
        if canonical.geometry.page_bytes % 32 or canonical.geometry.max_model_transfer_bytes % 32:
            raise ValueError("shadow AXI transport requires 32-byte pages/chunks")
        self.canonical = canonical
        self.owner = owner
        self.epoch_id = epoch_id
        self._original = canonical.snapshot(owner=owner)
        self._base_versions = tuple(
            canonical.version(page, owner=owner)
            for page in range(canonical.geometry.pages))
        self.shadow = AXIModelImage(
            canonical.geometry,
            emulated_owner=owner,
            initial=self._original,
            logical_bus_base=0,
            ready_delay_every=ready_delay_every)
        self.cache = BlockCache(self.shadow, owner=owner)
        self._status = "PREPARED"
        self._actual: PagedRun | None = None
        self._expected: ReferenceTrace | None = None

    @property
    def status(self) -> str:
        return self._status

    def run(self, network: Network, events: Iterable[InputCurrent], *,
            ticks: int) -> PagedRun:
        if self._status != "PREPARED":
            raise EpochError("epoch run must start from PREPARED only")
        frozen_events = tuple(events)
        try:
            result = replay_with_paging(network, frozen_events, ticks=ticks,
                                        cache=self.cache)
        except (ValueError, ResidencyError, PermissionError):
            self._status = "FAILED_REQUIRES_ABORT"
            raise
        self._actual = result
        self._status = "RAN_UNCOMMITTED"
        return result

    def verify_against_independent_m02(self, net: Network,
                                       events: Iterable[InputCurrent], *,
                                       ticks: int) -> None:
        if self._status != "RAN_UNCOMMITTED" or self._actual is None:
            raise EpochError("cannot approve unrun/failed epoch")
        try:
            expected = evaluate_dense(net, tuple(events), ticks=ticks)
            if expected != self._actual.trace:
                raise EpochError("independent M02 trace differs from paged inference")
            new_shadow = self.shadow.snapshot(owner=self.owner)
            expected_bytes = b"".join(
                voltage.to_bytes(2, "little", signed=True)
                + bytes(self.canonical.geometry.bytes_per_neuron - 2)
                for voltage in expected.voltage_rows[-1])
            if new_shadow != expected_bytes:
                raise EpochError("shadow canonical bytes differ from expected M02 final voltages")
        except (ValueError, ResidencyError, PermissionError):
            self._status = "FAILED_REQUIRES_ABORT"
            raise
        self._expected = expected
        self._status = "VALIDATED_UNCOMMITTED"

    def commit(self) -> EpochReceipt:
        if self._status != "VALIDATED_UNCOMMITTED" or self._expected is None:
            raise EpochError("cannot commit before independent M02+shadow verification")
        # This check + bytearray replacement are serialized software ONLY,
        # not a physical atomic DDR multi-burst transaction.
        try:
            self.canonical.check_owner(self.owner)
            for page, original_ver in enumerate(self._base_versions):
                if self.canonical.version(page, owner=self.owner) != original_ver:
                    raise EpochError("canonical externally changed during speculative epoch")
            if self.canonical.snapshot(owner=self.owner) != self._original:
                raise EpochError("canonical raw contents changed without a version increment")
            new_data = self.shadow.snapshot(owner=self.owner)
            if len(new_data) != len(self._original):
                raise EpochError("incorrect canonical epoch state image size")
        except (ValueError, ResidencyError, PermissionError):
            self._status = "FAILED_REQUIRES_ABORT"
            raise

        pages = []
        width = self.canonical.geometry.page_bytes
        for page in range(self.canonical.geometry.pages):
            at = page * width
            if new_data[at:at+width] != self._original[at:at+width]:
                pages.append(page)
        # No transfer to real DDR: atomic in-memory bytearray assignment in
        # one single-threaded function only. Real commit marker NOT IMPLEMENTED.
        self.canonical._bytes[:] = new_data
        for page in pages:
            self.canonical._version[page] += 1
        self._status = "COMMITTED"
        return EpochReceipt(
            epoch_id=self.epoch_id,
            changed_pages=tuple(pages),
            canonical_version_after=tuple(self.canonical._version),
        )

    def abort(self) -> dict:
        if self._status == "COMMITTED":
            raise EpochError("cannot abort a committed epoch")
        if self._status == "ABORTED":
            raise EpochError("cannot double-abort an epoch")
        prior = self._status
        self._status = "ABORTED"
        return {
            "epoch_id": self.epoch_id,
            "prior_status": prior,
            "shadow_uncertain_pages": sorted(self.shadow.uncertain_pages),
            "canonical_never_written_by_shadow_epoch": True,
            "shadow_discarded": True,
            "physical_ddr": "NOT_ACCESSED",
        }
