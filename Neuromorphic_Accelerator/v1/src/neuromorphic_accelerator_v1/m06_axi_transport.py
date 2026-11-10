"""M06 SOFTWARE-ONLY AXI4 256->128 aligned INCR transport contract and page image.

These are independent behavioral Python models, NOT AMD SmartConnect logic,
vendor simulation, tested physical DDR, or proof about USER/ID sidebands.
A lost write response or interrupted in-flight W transfer can leave PARTIAL
canonical memory bytes: poison the page/cache and require explicit recovery.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib

from .m06_block_residency import (
    CanonicalImage, Geometry, NoOwnership, ResidencyError, checked_int,
)

UPSTREAM_BYTES = 32  # four DMA MM2S/S2MM AXI-MM 256-bit masters
DOWNSTREAM_BYTES = 16  # K26 HP0 AXI-MM PS endpoint 128-bit
AXI_BOUNDARY = 4096
AXI_MAX_BEATS = 256
AXI_ADDR_LIMIT = 2**32


class AXIModelError(ResidencyError):
    """Unsupported AXI envelope or simulated transport fault."""


@dataclass(frozen=True)
class AXIBurst:
    """Logical, not physically owned, 256-bit AXI4 address descriptor."""
    address: int
    upstream_beats: int
    upstream_id: int = 1
    bytes_total: int = 0

    def __post_init__(self) -> None:
        checked_int("burst address", self.address, 0, AXI_ADDR_LIMIT - 1)
        checked_int("upstream beats", self.upstream_beats, 1, AXI_MAX_BEATS)
        checked_int("upstream ID", self.upstream_id, 0, 65535)
        if self.address % UPSTREAM_BYTES:
            raise ValueError("256-bit AXI burst must start at 32-byte aligned address")
        if (self.address // AXI_BOUNDARY !=
                (self.address + UPSTREAM_BYTES*self.upstream_beats-1) // AXI_BOUNDARY):
            raise ValueError("AXI4 INCR burst must not cross 4KiB")
        if self.address + UPSTREAM_BYTES*self.upstream_beats > AXI_ADDR_LIMIT:
            raise ValueError("32-bit address overflow")
        if self.bytes_total not in (0, UPSTREAM_BYTES*self.upstream_beats):
            raise ValueError("upstream AXI burst byte count inconsistent")

    @property
    def nbytes(self) -> int:
        return self.upstream_beats * UPSTREAM_BYTES

    @property
    def upstream_len(self) -> int:
        return self.upstream_beats-1

    @property
    def upstream_size(self) -> int:
        return 5  # 2^5 bytes = 256b

    @property
    def downstream_len(self) -> int:
        return self.upstream_beats*2-1  # <= 255 if upstream<=128

    @property
    def downstream_size(self) -> int:
        return 4  # 2^4 bytes = 128b


def plan_aligned_incr(address: int, length: int, *, max_bytes: int = 256,
                      axid: int = 1) -> tuple[AXIBurst, ...]:
    """Partition full-width upstream DMA 256b beats at 4KiB and 128b AXI max.

    Both sides get <=256 AXI4 beats. Downsize doubles the beat count, so
    one upstream segment cannot exceed 128 beats (4096 bytes). Explicit
    max_bytes further bounds each *modeled* burst. This does not guarantee
    true SmartConnect conversion.
    """
    checked_int("start address", address, 0, AXI_ADDR_LIMIT - 1)
    checked_int("byte count", length, 1, AXI_ADDR_LIMIT)
    checked_int("max modeled transaction bytes", max_bytes, UPSTREAM_BYTES, AXI_MAX_BEATS*UPSTREAM_BYTES)
    checked_int("AXI id", axid, 0, 65535)
    if address % UPSTREAM_BYTES or length % UPSTREAM_BYTES or max_bytes % UPSTREAM_BYTES:
        raise ValueError("only 32-byte aligned full-width DMA INCR requests supported")
    if address + length > AXI_ADDR_LIMIT:
        raise ValueError("modeled AXI transfer beyond 32-bit address range")
    output: list[AXIBurst] = []
    consumed = 0
    while consumed < length:
        at = address + consumed
        to_4k = AXI_BOUNDARY - at % AXI_BOUNDARY
        size = min(length-consumed, to_4k,
                   AXI_MAX_BEATS*DOWNSTREAM_BYTES, max_bytes)
        if size == 0 or size % UPSTREAM_BYTES:
            raise ValueError("aligned AXI planner cannot form legal INCR burst")
        burst = AXIBurst(at, size // UPSTREAM_BYTES, upstream_id=axid,
                         bytes_total=size)
        if burst.downstream_len > 255:
            raise ValueError("128-bit downstream AXI LEN overflow")
        output.append(burst)
        consumed += size
    return tuple(output)


def split_256_to_128(up_data: bytes, up_strb: int) -> tuple[tuple[bytes, int], tuple[bytes, int]]:
    if type(up_data) is not bytes or len(up_data) != UPSTREAM_BYTES:
        raise ValueError("upstream WDATA must be exactly 32 bytes")
    checked_int("upstream WSTRB", up_strb, 0, (1 << UPSTREAM_BYTES)-1)
    return ((up_data[:DOWNSTREAM_BYTES], up_strb & 0xffff),
            (up_data[DOWNSTREAM_BYTES:], up_strb >> 16))


def join_128_to_256(low: bytes, high: bytes) -> bytes:
    if (type(low) is not bytes or type(high) is not bytes
            or len(low) != DOWNSTREAM_BYTES or len(high) != DOWNSTREAM_BYTES):
        raise ValueError("128-bit low/high RDATA halves required")
    return low + high


@dataclass(frozen=True)
class AXIFault:
    """One-shot source-model injection, never a fabricated vendor fault."""
    direction: str  # READ or WRITE
    kind: str  # RRESP, BRESP, READY_TIMEOUT, RESPONSE_LOST
    burst: int = 0
    beat: int = 0

    def __post_init__(self) -> None:
        if self.direction not in ("READ", "WRITE"):
            raise ValueError("bad fault direction")
        if self.kind not in ("RRESP", "BRESP", "READY_TIMEOUT", "RESPONSE_LOST"):
            raise ValueError("bad simulated fault kind")
        checked_int("fault burst", self.burst, 0, 10**6)
        checked_int("fault beat", self.beat, 0, 10**6)
        if self.kind == "RRESP" and self.direction != "READ":
            raise ValueError("RRESP fault applies only to reads")
        if self.kind in ("BRESP", "RESPONSE_LOST") and self.direction != "WRITE":
            raise ValueError("B/uncertain-write fault applies only to writes")


class AXIModelImage(CanonicalImage):
    """Software-owned canonical image with modeled 256->128 AXI transactions.

    Each upstream 256b beat is split into lower/upper 128b downstream
    handshakes; reads are reconstructed in original byte order. The model
    records per-channel ready/valid handshakes, stalls, and byte/strobe
    witnesses. This model deliberately serializes all AXI channels and
    transfers; it does NOT simulate arbitration, concurrency or real timing.

    Physical AXI writes are not page-atomic: a fault during W or missing B
    can leave a partially modified block. Quarantine is sticky even if a
    new cache object tries to attach to the same image.
    """

    def __init__(self, geometry: Geometry, *, emulated_owner: str,
                 initial: bytes | None = None, logical_bus_base: int = 0,
                 ready_delay_every: int = 3, cycle_watchdog: int = 1000,
                 axid: int = 1):
        super().__init__(geometry, emulated_owner=emulated_owner, initial=initial)
        checked_int("logical bus base", logical_bus_base, 0, AXI_ADDR_LIMIT-1)
        checked_int("ready delay cadence", ready_delay_every, 0, 1000)
        checked_int("per-handshake watchdog", cycle_watchdog, 1, 100000)
        checked_int("AXI ID", axid, 0, 65535)
        if (self.geometry.page_bytes % UPSTREAM_BYTES or
                self.geometry.max_model_transfer_bytes % UPSTREAM_BYTES or
                logical_bus_base % UPSTREAM_BYTES):
            raise ValueError("AXI model requires 32-byte aligned page, chunk and base")
        if logical_bus_base + geometry.image_bytes > AXI_ADDR_LIMIT:
            raise ValueError("logical AXI region outside 32-bit address space")
        self.logical_bus_base = logical_bus_base
        self.axid = axid
        self.ready_delay_every = ready_delay_every
        self.cycle_watchdog = cycle_watchdog
        self._cycle = 0
        self._fault_axi: AXIFault | None = None
        self.uncertain_pages: set[int] = set()
        self.handshakes: dict[str, int] = {}
        self.stalls: dict[str, int] = {}
        self.burst_log: list[dict] = []
        self.channel_trace: list[dict] = []  # full sampled cycles, host-only

    def inject_axi_fault_once(self, fault: AXIFault) -> None:
        if type(fault) is not AXIFault or self._fault_axi is not None:
            raise ValueError("one explicit pending AXI fault at a time")
        self._fault_axi = fault

    def _get_fault(self, direction: str, burst_index: int, kind: str,
                   beat_index: int = 0) -> bool:
        wanted = AXIFault(direction, kind, burst_index, beat_index)
        if self._fault_axi == wanted:
            self._fault_axi = None
            return True
        return False

    def _handshake(self, channel: str, payload: bytes, *, timeout: bool = False) -> None:
        """One held VALID/payload until READY handshake, with watchdog."""
        if channel not in ("U_AW", "U_W", "U_B", "U_AR", "U_R",
                           "D_AW", "D_W", "D_B", "D_AR", "D_R"):
            raise ValueError("unknown explicitly modeled AXI channel")
        if type(payload) is not bytes:
            raise ValueError("AXI payload must be immutable bytes")
        digest = hashlib.sha256(payload).hexdigest()
        for trial in range(self.cycle_watchdog):
            self._cycle += 1
            # A deterministic forced delay on selected clock slots. This is
            # synthetic backpressure, not an AXI timing claim.
            ready = not timeout and (
                self.ready_delay_every == 0
                or self._cycle % self.ready_delay_every != 0)
            self.channel_trace.append({
                "cycle": self._cycle, "channel": channel,
                "valid": True, "ready": ready,
                "payload_sha256": digest,
            })
            if ready:
                self.handshakes[channel] = self.handshakes.get(channel, 0)+1
                return
            self.stalls[channel] = self.stalls.get(channel, 0)+1
        raise AXIModelError(f"{channel} stalled beyond simulated watchdog")

    def _checked_page(self, page: int, owner: str) -> int:
        self.check_owner(owner)
        start = self.geometry.offset_for_page(page)
        if page in self.uncertain_pages:
            raise AXIModelError("canonical page uncertain after interrupted AXI write")
        return start

    def version(self, page: int, *, owner: str) -> int:
        self._checked_page(page, owner)
        return super().version(page, owner=owner)

    def read_block(self, page: int, *, owner: str) -> tuple[bytes, int, int]:
        start = self._checked_page(page, owner)
        plan = plan_aligned_incr(
            self.logical_bus_base + start, self.geometry.page_bytes,
            max_bytes=self.geometry.max_model_transfer_bytes, axid=self.axid)
        buffer = bytearray()
        for idx, burst in enumerate(plan):
            self._handshake("U_AR", f"{burst.address}:{burst.upstream_len}:5".encode())
            self._handshake("D_AR", f"{burst.address}:{burst.downstream_len}:4".encode())
            for beat in range(burst.upstream_beats):
                low_pos = start + (burst.address-(self.logical_bus_base+start)) + 32*beat
                low = bytes(self._bytes[low_pos:low_pos+16])
                high = bytes(self._bytes[low_pos+16:low_pos+32])
                for half, d in enumerate((low, high)):
                    if self._get_fault("READ", idx, "RRESP", beat*2+half):
                        raise AXIModelError("simulated downstream RRESP SLVERR")
                    if self._get_fault("READ", idx, "READY_TIMEOUT", beat*2+half):
                        self._handshake("D_R", d, timeout=True)
                    else:
                        self._handshake("D_R", d)
                joined = join_128_to_256(low, high)
                self._handshake("U_R", joined)
                buffer.extend(joined)
            self.burst_log.append({
                "direction": "READ", "address": burst.address,
                "upstream_beats": burst.upstream_beats,
                "downstream_beats": 2*burst.upstream_beats,
                "upstream_len": burst.upstream_len, "downstream_len": burst.downstream_len,
                "upstream_size": burst.upstream_size, "downstream_size": burst.downstream_size,
                "upstream_id": burst.upstream_id,
                "read_payload_sha256": hashlib.sha256(buffer[-burst.nbytes:]).hexdigest(),
                "status": "MODEL_OK_NOT_VENDOR_VERIFIED",
            })
        if len(buffer) != self.geometry.page_bytes:
            raise AXIModelError("read-block byte count lost")
        return bytes(buffer), self._version[page], len(plan)

    def write_block(self, page: int, data: bytes, *,
                    expected_version: int, owner: str) -> tuple[int, int]:
        start = self._checked_page(page, owner)
        if type(data) is not bytes or len(data) != self.geometry.page_bytes:
            raise ValueError("AXI page write requires entire page bytes")
        if type(expected_version) is not int or expected_version != self._version[page]:
            raise AXIModelError("stale canonical page version on AXI write")
        plan = plan_aligned_incr(
            self.logical_bus_base + start, self.geometry.page_bytes,
            max_bytes=self.geometry.max_model_transfer_bytes, axid=self.axid)
        offset = 0
        try:
            for idx, burst in enumerate(plan):
                self._handshake("U_AW", f"{burst.address}:{burst.upstream_len}:5".encode())
                self._handshake("D_AW", f"{burst.address}:{burst.downstream_len}:4".encode())
                for beat in range(burst.upstream_beats):
                    up = data[offset:offset+32]
                    offset += 32
                    self._handshake("U_W", up + b"\xff"*4)
                    for half, (part, strobe) in enumerate(split_256_to_128(
                            up, 0xffffffff)):
                        if self._get_fault("WRITE", idx, "READY_TIMEOUT", beat*2+half):
                            self._handshake("D_W", part, timeout=True)
                        else:
                            self._handshake("D_W", part + strobe.to_bytes(2, "little"))
                        # Only accepted 128-bit W beats change canonical
                        # bytes; interruption can therefore be mid-page.
                        at = start + offset - 32 + half*16
                        for lane in range(16):
                            if strobe & (1 << lane):
                                self._bytes[at+lane] = part[lane]
                self._handshake("D_B", b"OKAY")
                if self._get_fault("WRITE", idx, "BRESP", 0):
                    raise AXIModelError("simulated downstream BRESP SLVERR")
                if self._get_fault("WRITE", idx, "RESPONSE_LOST", 0):
                    self._handshake("U_B", b"NO_ACK", timeout=True)
                self._handshake("U_B", b"OKAY")
                self.burst_log.append({
                    "direction": "WRITE", "address": burst.address,
                    "upstream_beats": burst.upstream_beats,
                    "downstream_beats": 2*burst.upstream_beats,
                    "upstream_len": burst.upstream_len,
                    "downstream_len": burst.downstream_len,
                    "upstream_size": burst.upstream_size,
                    "downstream_size": burst.downstream_size,
                    "upstream_id": burst.upstream_id,
                    "written_payload_sha256": hashlib.sha256(
                        data[offset-burst.nbytes:offset]).hexdigest(),
                    "status": "MODEL_OK_NOT_VENDOR_VERIFIED",
                })
        except (AXIModelError, ResidencyError):
            self.uncertain_pages.add(page)
            raise
        self._version[page] += 1
        return self._version[page], len(plan)

    def snapshot(self, *, owner: str) -> bytes:
        self.check_owner(owner)
        if self.uncertain_pages:
            raise AXIModelError("snapshot forbidden: AXI write may have partially committed")
        return super().snapshot(owner=owner)

    def diagnostic_after_fault(self, *, owner: str) -> dict:
        """Do not advertise uncertain bytes as authoritative canonical state."""
        self.check_owner(owner)
        return {
            "uncertain_pages": sorted(self.uncertain_pages),
            "writes_not_page_atomic": True,
            "full_canonical_snapshot_trustworthy": not bool(self.uncertain_pages),
            "model_direction": "HOST_SYNTHETIC_ONLY",
            "physical_axi_or_ddr": "NOT_PROVEN",
            "channel_handshakes": dict(self.handshakes),
            "channel_stalls": dict(self.stalls),
            "completed_bursts": len(self.burst_log),
        }
