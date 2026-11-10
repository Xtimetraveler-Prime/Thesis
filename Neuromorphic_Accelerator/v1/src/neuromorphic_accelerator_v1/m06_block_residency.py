"""M06 initial SOURCE-ONLY block residency and canonical-state correctness model.

M01 approved a configurable whole-block cache (option B) as the initial
baseline. Here DDR is a *local bytearray*: no physical address, DMA, PS,
AXI, Linux memory ownership, timing, energy, or bitstream is implied.

Never expose a stale/partially transferred page as valid. A failed or
revoked transfer leaves a sticky poisoned cache; no continuing operation
can quietly overwrite canonical state after failure.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Literal


class ResidencyError(RuntimeError):
    """Transaction or coherency violation; a affected cache stays poisoned."""


class NoOwnership(PermissionError):
    """An emulated owner lease is absent or has been revoked."""


def checked_int(name: str, value: object, lo: int, hi: int) -> int:
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError(f"{name} must be an integer within [{lo}, {hi}]")
    return value


@dataclass(frozen=True)
class Geometry:
    logical_neurons: int = 4096
    bytes_per_neuron: int = 16
    neurons_per_block: int = 16
    resident_budget_bytes: int = 2048
    max_model_transfer_bytes: int = 256

    def validate(self) -> None:
        for name in ("logical_neurons", "bytes_per_neuron", "neurons_per_block",
                     "resident_budget_bytes", "max_model_transfer_bytes"):
            checked_int(name, getattr(self, name), 1, 2**32)
        if self.logical_neurons % self.neurons_per_block:
            raise ValueError("canonical neuron count must consist of full blocks")
        if self.page_bytes > self.resident_budget_bytes:
            raise ValueError("on-chip data budget must hold at least one complete block")
        if self.image_bytes >= 2**32:
            # Address is a logical byte OFFSET, not an approved physical DDR
            # base. Strictly below 2^32 matches original AXI DMA addr32.
            raise ValueError("modeled 32-bit DMA window cannot address canonical image")
        if self.max_model_transfer_bytes > self.page_bytes:
            raise ValueError("model transfer bound cannot exceed page width")

    @property
    def page_bytes(self) -> int:
        return self.bytes_per_neuron * self.neurons_per_block

    @property
    def image_bytes(self) -> int:
        return self.logical_neurons * self.bytes_per_neuron

    @property
    def pages(self) -> int:
        return self.logical_neurons // self.neurons_per_block

    @property
    def slots(self) -> int:
        return self.resident_budget_bytes // self.page_bytes

    def page_for_neuron(self, neuron: int) -> int:
        checked_int("logical neuron", neuron, 0, self.logical_neurons - 1)
        return neuron // self.neurons_per_block

    def offset_for_page(self, page: int) -> int:
        checked_int("logical block", page, 0, self.pages - 1)
        return page * self.page_bytes


class CanonicalImage:
    """Emulated canonical image with one explicit exclusive SOFTWARE owner.

    Read/write transfers are staged chunk by chunk, but the image's per-block
    write is atomic on completion. An injected chunk fault never partially
    modifies canonical bytes. Versions detect lost updates from another actor.
    No real physical ownership can be inferred from this token.
    """

    def __init__(self, geometry: Geometry, *, emulated_owner: str, initial: bytes | None = None):
        geometry.validate()
        if not isinstance(emulated_owner, str) or not emulated_owner:
            raise ValueError("nonempty EMULATED owner identity required")
        if initial is not None and (type(initial) is not bytes or
                                    len(initial) != geometry.image_bytes):
            raise ValueError("canonical starting byte count incorrect")
        self.geometry = geometry
        self._bytes = bytearray(initial if initial is not None
                                else bytes(geometry.image_bytes))
        self._owner = emulated_owner
        self._version = [0] * geometry.pages
        self._fault: tuple[str, int] | None = None

    def check_owner(self, token: str) -> None:
        if token != self._owner or not self._owner:
            raise NoOwnership("emulated canonical-image ownership not held")

    def revoke(self) -> None:
        self._owner = ""

    def inject_once(self, op: Literal["read", "write"], *, chunk: int) -> None:
        if op not in ("read", "write"):
            raise ValueError("injection operation must be read or write")
        checked_int("fault chunk", chunk, 0, 10**9)
        self._fault = (op, chunk)

    def _chunk(self, op: str, chunk: int) -> None:
        if self._fault == (op, chunk):
            self._fault = None
            raise ResidencyError(f"emulated {op} transfer interrupted at chunk {chunk}")

    def version(self, page: int, *, owner: str) -> int:
        self.check_owner(owner)
        self.geometry.offset_for_page(page)
        return self._version[page]

    def read_block(self, page: int, *, owner: str) -> tuple[bytes, int, int]:
        self.check_owner(owner)
        start = self.geometry.offset_for_page(page)
        collected = bytearray()
        transfer = self.geometry.max_model_transfer_bytes
        for chunk, pos in enumerate(range(0, self.geometry.page_bytes, transfer)):
            self._chunk("read", chunk)
            n = min(transfer, self.geometry.page_bytes - pos)
            collected += self._bytes[start + pos:start + pos + n]
        return bytes(collected), self._version[page], chunk + 1

    def write_block(self, page: int, data: bytes, *,
                    expected_version: int, owner: str) -> tuple[int, int]:
        self.check_owner(owner)
        start = self.geometry.offset_for_page(page)
        if type(data) is not bytes or len(data) != self.geometry.page_bytes:
            raise ValueError("wrong full-block canonical write width")
        if type(expected_version) is not int or self._version[page] != expected_version:
            raise ResidencyError("stale canonical page version; no lost-update overwrite")
        staged = bytearray()
        transfer = self.geometry.max_model_transfer_bytes
        for chunk, pos in enumerate(range(0, self.geometry.page_bytes, transfer)):
            self._chunk("write", chunk)
            staged += data[pos:pos + transfer]
        self._bytes[start:start + self.geometry.page_bytes] = staged
        self._version[page] += 1
        return self._version[page], chunk + 1

    def snapshot(self, *, owner: str) -> bytes:
        self.check_owner(owner)
        return bytes(self._bytes)

    def external_edit_for_negative_test(self, page: int, data: bytes) -> None:
        """Explicit test-only simulated competing writer, NOT an authorized API."""
        start = self.geometry.offset_for_page(page)
        if type(data) is not bytes or len(data) != self.geometry.page_bytes:
            raise ValueError("competing write must cover a full modeled page")
        self._bytes[start:start + self.geometry.page_bytes] = data
        self._version[page] += 1


@dataclass
class ResidentBlock:
    data: bytearray
    canonical_version: int
    dirty: bool = False


@dataclass
class CacheCounters:
    accesses: int = 0
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    dirty_evictions: int = 0
    read_bytes: int = 0
    write_bytes: int = 0
    read_transactions: int = 0
    write_transactions: int = 0

    def validate(self) -> None:
        if self.hits + self.misses != self.accesses:
            raise ResidencyError("cache counters must partition each admitted access")


class BlockCache:
    """Bounded model of M01 option B with exact dirty eviction and flush.

    Only one synchronous transfer may be serviced at a time. Real AXI
    concurrency, reordering, burst timing, retry and ownership are FUTURE M06
    work; they cannot be inferred from this Python model.
    """

    def __init__(self, store: CanonicalImage, *, owner: str):
        store.check_owner(owner)
        self.store = store
        self.geometry = store.geometry
        self.owner = owner
        self.counters = CacheCounters()
        self._resident: OrderedDict[int, ResidentBlock] = OrderedDict()
        self._poisoned = False
        self._transfer_active = False

    @property
    def poisoned(self) -> bool:
        return self._poisoned

    @property
    def resident_pages(self) -> tuple[int, ...]:
        return tuple(self._resident)

    @property
    def dirty_pages(self) -> tuple[int, ...]:
        return tuple(p for p, r in self._resident.items() if r.dirty)

    def _ensure_safe(self) -> None:
        if self._poisoned:
            raise ResidencyError("cache is poisoned; investigate/abort dirty state")
        try:
            self.store.check_owner(self.owner)
        except NoOwnership:
            self._poisoned = True
            raise

    def _io(self, method: str, *args, **kwargs):
        if self._transfer_active:
            self._poisoned = True
            raise ResidencyError("overlapping/double page-transfer service")
        self._transfer_active = True
        try:
            reply = getattr(self.store, method)(*args, **kwargs)
            if method in ("read_block", "write_block") and (
                    type(reply) is not tuple or
                    len(reply) != (3 if method == "read_block" else 2)):
                raise ResidencyError("invalid backing transfer acknowledgment tuple")
            return reply
        except (NoOwnership, ResidencyError):
            self._poisoned = True
            raise
        except (TypeError, ValueError) as exc:
            self._poisoned = True
            raise ResidencyError("malformed backing transfer metadata") from exc
        finally:
            self._transfer_active = False

    def _access(self, neuron: int) -> ResidentBlock:
        self._ensure_safe()
        page = self.geometry.page_for_neuron(neuron)
        if page in self._resident:
            record = self._resident[page]
            # Fail closed on unexpected canonical-image mutation even if the
            # block is resident (stale cache-hit exposure is unacceptable).
            observed = self._io("version", page, owner=self.owner)
            if type(observed) is not int or observed != record.canonical_version:
                self._poisoned = True
                raise ResidencyError("stale or malformed canonical page generation on cache hit")
            self.counters.hits += 1
            self._resident.move_to_end(page)
        else:
            if len(self._resident) >= self.geometry.slots:
                victim, record = next(iter(self._resident.items()))
                if record.dirty:
                    version, transactions = self._io(
                        "write_block", victim, bytes(record.data),
                        expected_version=record.canonical_version, owner=self.owner)
                    if (type(version) is not int or
                            version != record.canonical_version + 1 or
                            type(transactions) is not int or transactions < 1):
                        self._poisoned = True
                        raise ResidencyError("invalid backing-store dirty-eviction acknowledgment")
                    record.canonical_version = version
                    record.dirty = False
                    self.counters.dirty_evictions += 1
                    self.counters.write_bytes += self.geometry.page_bytes
                    self.counters.write_transactions += transactions
                del self._resident[victim]
                self.counters.evictions += 1
            data, version, transactions = self._io("read_block", page, owner=self.owner)
            if (type(data) is not bytes or len(data) != self.geometry.page_bytes or
                    type(version) is not int or version < 0 or
                    type(transactions) is not int or transactions < 1):
                self._poisoned = True
                raise ResidencyError("invalid backing-store page width, generation or read acknowledgment")
            self._resident[page] = ResidentBlock(bytearray(data), version)
            self.counters.misses += 1
            self.counters.read_bytes += self.geometry.page_bytes
            self.counters.read_transactions += transactions
        self.counters.accesses += 1
        self.counters.validate()
        if len(self._resident) > self.geometry.slots:
            raise ResidencyError("on-chip resident data-budget violation")
        return self._resident[page]

    def read(self, neuron: int) -> bytes:
        page = self._access(neuron)
        offset = (neuron % self.geometry.neurons_per_block) * self.geometry.bytes_per_neuron
        return bytes(page.data[offset:offset + self.geometry.bytes_per_neuron])

    def write(self, neuron: int, data: bytes) -> None:
        self._ensure_safe()
        if type(data) is not bytes or len(data) != self.geometry.bytes_per_neuron:
            raise ValueError("logical neuron state write must be one exact record")
        block = self._access(neuron)
        offset = (neuron % self.geometry.neurons_per_block) * self.geometry.bytes_per_neuron
        block.data[offset:offset + self.geometry.bytes_per_neuron] = data
        block.dirty = True

    def flush(self) -> None:
        self._ensure_safe()
        for page in list(self._resident):
            record = self._resident[page]
            # No silent clean if the canonical image was replaced externally.
            observed = self._io("version", page, owner=self.owner)
            if type(observed) is not int or observed != record.canonical_version:
                self._poisoned = True
                raise ResidencyError("stale or malformed version before dirty flush")
            if record.dirty:
                version, tx = self._io("write_block", page, bytes(record.data),
                                       expected_version=record.canonical_version,
                                       owner=self.owner)
                if (type(version) is not int or version != record.canonical_version+1 or
                        type(tx) is not int or tx < 1):
                    self._poisoned = True
                    raise ResidencyError("invalid backing-store flush acknowledgment")
                record.canonical_version = version
                record.dirty = False
                self.counters.write_bytes += self.geometry.page_bytes
                self.counters.write_transactions += tx

    def abandon_after_fault(self) -> dict:
        """Diagnostic-only record; NEVER claim all dirty states were written."""
        return {
            "poisoned": self._poisoned,
            "resident": self.resident_pages,
            "dirty_uncommitted": self.dirty_pages,
            "canonical_image_not_guaranteed_current": bool(self.dirty_pages),
            "physical_board": "NOT_AUTHORIZED",
        }
