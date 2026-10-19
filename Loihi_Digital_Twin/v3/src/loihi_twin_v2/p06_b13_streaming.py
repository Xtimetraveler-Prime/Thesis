"""P06-B1.3 opt-in, host-only multi-core ingress/route streaming contract.

NEVER interpret these new bytes as accepted P05 diagnostic/P07-A1 firmware
payloads. B1.3 is a versioned *candidate* wire contract, requiring independent
new PS firmware work and hardware acceptance in P07-B.

P06-A encoded 25 input + one drain epoch, P06-B1.2 placement, genuine P03
axon/route tables and B1.1 image SHA binding are preserved unmodified.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import struct
import zlib

from .compiler import CompiledDeployment
from .p06_b12_partition import B12Result, B12_COMPILER_VERSION
from .p06_b1_contract import MAX_EVENTS_PER_BANK, MAX_PACKETS_PER_BANK, P05_DIAGNOSTIC_MAX_CORES
from .p06_input_contract import INPUT_CHANNELS, INPUT_TICKS, TOTAL_TICKS, pixel_spikes
from .packet import PacketClass, SpikePacket

B13_SCHEMA = "p06-b1.3-multicore-streaming-v1"
B13_WIRE_VERSION = 1
B13_INGRESS_MAGIC = b"P06B13I1"
B13_PACKETS_MAGIC = b"P06B13R1"
B13_HEADER_BYTES = 128
B13_ROUTE_ENTRY_BYTES = 6    # <HHH: source_input_index, destination_core, destination_axon
B13_PACKET_ENTRY_BYTES = 12  # <IHHHH: target_tick, source_core, source_comp, dest_core, dest_axon
B13_INPUT_PIXELS_BYTES = INPUT_CHANNELS
B13_MAX_ROUTES = INPUT_CHANNELS * P05_DIAGNOSTIC_MAX_CORES
_HEADER = "<8s14I"
_ROUTE = "<HHH"
_PACKET = "<IHHHH"
_HEADER_CRC_OFFSET = 52  # 8 byte magic + 11th integer index
_ZERO_SHA = "00" * 32


class B13StreamError(ValueError):
    """Host-side rejected transport frame or lossy logical packet transaction."""


def _unsigned(value: int, *, name: str, limit: int) -> int:
    if type(value) is not int or not 0 <= value <= limit:
        raise B13StreamError(f"{name} must be an integer in [0, {limit}]")
    return value


def _sha_bytes(hexdigest: str, *, name: str) -> bytes:
    if type(hexdigest) is not str or len(hexdigest) != 64:
        raise B13StreamError(f"{name} must be 64 hexadecimal characters")
    try:
        digest = bytes.fromhex(hexdigest)
    except ValueError as exc:
        raise B13StreamError(f"{name} is not hexadecimal") from exc
    if len(digest) != 32 or not any(digest):
        raise B13StreamError(f"{name} cannot be zero/invalid")
    return digest


def _pack_frame(magic: bytes, info: tuple[int, ...], fingerprint: str,
                audit_sha: str, payload: bytes) -> bytes:
    if len(info) != 14:
        raise AssertionError("14 uint32 header fields required")
    values = list(info)
    values[10] = zlib.crc32(payload)
    values[11] = 0
    header = bytearray(
        struct.pack(_HEADER, magic, *values)
        + _sha_bytes(fingerprint, name="deployment SHA256")
        + _sha_bytes(audit_sha, name="B1.1 capacity audit SHA256")
    )
    if len(header) != B13_HEADER_BYTES:
        raise AssertionError("unexpected header byte width")
    struct.pack_into("<I", header, _HEADER_CRC_OFFSET, zlib.crc32(header))
    return bytes(header) + payload


def _unpack_frame(raw: bytes, *, magic: bytes, fingerprint: str,
                  audit_sha: str) -> tuple[tuple[int, ...], bytes]:
    if not isinstance(raw, bytes) or len(raw) < B13_HEADER_BYTES:
        raise B13StreamError("truncated or missing B1.3 stream header")
    header = bytearray(raw[:B13_HEADER_BYTES])
    actual_magic, *words = struct.unpack_from(_HEADER, header)
    if actual_magic != magic or words[0] != B13_WIRE_VERSION or words[1] != B13_HEADER_BYTES:
        raise B13StreamError("wrong B1.3 magic, version, or header length")
    if any(words[i] for i in (12, 13)):
        raise B13StreamError("B1.3 reserved flags/words must be zero")
    if header[64:96] != _sha_bytes(fingerprint, name="deployment SHA256"):
        raise B13StreamError("deployment SHA256 does not match the B1.2 compiled mapping")
    if header[96:128] != _sha_bytes(audit_sha, name="B1.1 capacity audit SHA256"):
        raise B13StreamError("capacity audit SHA256 does not match actual packed images")
    observed_crc = words[11]
    struct.pack_into("<I", header, _HEADER_CRC_OFFSET, 0)
    if zlib.crc32(header) != observed_crc:
        raise B13StreamError("B1.3 header CRC32 mismatch")
    payload = raw[B13_HEADER_BYTES:]
    if words[2] != len(payload):
        raise B13StreamError("B1.3 payload length mismatch")
    if zlib.crc32(payload) != words[10]:
        raise B13StreamError("B1.3 payload CRC32 mismatch")
    return tuple(words), payload


@dataclass(frozen=True, slots=True)
class IngressEnvelope:
    pixels: bytes
    routes: tuple[tuple[int, int, int], ...]
    deployment_sha256: str
    capacity_audit_sha256: str

    @property
    def image_sha256(self) -> str:
        return hashlib.sha256(self.pixels).hexdigest()

    def events(self, tick: int) -> tuple[SpikePacket, ...]:
        """Pixel-order primary, destination-core secondary; duplicates preserved."""
        active = set(pixel_spikes(self.pixels, tick))
        return tuple(SpikePacket(target_timestep=tick, destination_core=core,
                                 destination_axon=axon)
                     for pixel, core, axon in self.routes if pixel in active)


def _ingress_routes(result: B12Result) -> tuple[tuple[int, int, int], ...]:
    compiled = _require_deployment(result)
    ids = {core.core_id for core in compiled.logical_deployment.core_configs}
    axons = {core.core_id: {a.axon_id for a in core.input_axons}
             for core in compiled.logical_deployment.core_configs}
    valid = []
    source_core = set()
    present = set()
    for route in compiled.ingress_routes:
        if route.input_population != "pixels":
            raise B13StreamError("B1.3 MNIST stream only supports pixels input population")
        _unsigned(route.input_index, name="source pixel", limit=INPUT_CHANNELS - 1)
        if route.destination_core not in ids or route.destination_axon not in axons[route.destination_core]:
            raise B13StreamError("ingress route references missing core/axon")
        if not 0 <= route.destination_axon < 4096:
            raise B13StreamError("ingress route axon ID exceeds 12-bit table")
        pair = (route.input_index, route.destination_core)
        if pair in source_core:
            raise B13StreamError("multiple axons for same pixel and destination core")
        source_core.add(pair)
        present.add(route.input_index)
        valid.append((route.input_index, route.destination_core, route.destination_axon))
    if present != set(range(INPUT_CHANNELS)):
        raise B13StreamError("B1.3 dense image contract requires all 784 pixels mapped")
    if len(valid) > B13_MAX_ROUTES:
        raise B13StreamError("total image route count exceeds 784×126")
    by_core = Counter(core for _src, core, _axon in valid)
    if any(count > MAX_EVENTS_PER_BANK for count in by_core.values()):
        raise B13StreamError("all-255 external fanout exceeds destination event bank")
    return tuple(sorted(valid))


def _require_deployment(result: B12Result) -> CompiledDeployment:
    if not isinstance(result, B12Result) or result.compiled.compiler_version != B12_COMPILER_VERSION:
        raise B13StreamError("B1.3 requires versioned B1.2 compiled deployment")
    compiled = result.compiled
    if result.capacity_audit.get("original_compiled_sha256") != compiled.fingerprint:
        raise B13StreamError("B1.1 packed audit fingerprint does not match deployment")
    _sha_bytes(result.capacity_audit.get("audit_sha256"), name="capacity audit SHA256")
    cores = compiled.logical_deployment.core_configs
    if not 1 <= len(cores) <= P05_DIAGNOSTIC_MAX_CORES:
        raise B13StreamError("B1.3 P05-planning logical core count invalid")
    if {core.core_id for core in cores} != set(range(len(cores))):
        raise B13StreamError("B1.3 expects contiguous physical-addressable logical core IDs")
    return compiled


def encode_ingress_frame(result: B12Result, pixels: bytes) -> bytes:
    """Standalone new v1 binary image+replication map; no old P05 firmware write."""
    if type(pixels) is not bytes or len(pixels) != INPUT_CHANNELS:
        raise B13StreamError("image must contain exactly 784 raw uint8 bytes")
    routes = _ingress_routes(result)
    stream = b"".join(struct.pack(_ROUTE, *r) for r in routes) + pixels
    sizes = (
        B13_WIRE_VERSION, B13_HEADER_BYTES, len(stream), len(routes),
        result.capacity_audit["logical_core_count"], INPUT_CHANNELS, INPUT_TICKS,
        TOTAL_TICKS, B13_ROUTE_ENTRY_BYTES, B13_INPUT_PIXELS_BYTES,
        0, 0, 0, 0,
    )
    return _pack_frame(B13_INGRESS_MAGIC, sizes, result.compiled.fingerprint,
                       result.capacity_audit["audit_sha256"], stream)


def decode_ingress_frame(raw: bytes, result: B12Result) -> IngressEnvelope:
    """Complete fail-closed decoding against REAL compiled destination routes."""
    expected = _ingress_routes(result)
    fields, payload = _unpack_frame(
        raw, magic=B13_INGRESS_MAGIC,
        fingerprint=result.compiled.fingerprint,
        audit_sha=result.capacity_audit["audit_sha256"])
    (_version, _header, byte_count, route_count, core_count, channels,
     input_ticks, total_ticks, route_bytes, image_bytes, *_rest) = fields
    if (
        core_count != result.capacity_audit["logical_core_count"]
        or channels != INPUT_CHANNELS or input_ticks != INPUT_TICKS
        or total_ticks != TOTAL_TICKS or route_bytes != B13_ROUTE_ENTRY_BYTES
        or image_bytes != INPUT_CHANNELS or route_count != len(expected)
        or byte_count != route_count * B13_ROUTE_ENTRY_BYTES + INPUT_CHANNELS
    ):
        raise B13StreamError("B1.3 ingress dimensions/route count mismatch")
    got = tuple(struct.iter_unpack(_ROUTE, payload[:route_count * B13_ROUTE_ENTRY_BYTES]))
    if got != expected:
        raise B13StreamError("B1.3 ingress routes differ from signed B1.2 compiled mapping")
    return IngressEnvelope(payload[-INPUT_CHANNELS:], got, result.compiled.fingerprint,
                           result.capacity_audit["audit_sha256"])


def _output_routes(compiled: CompiledDeployment) -> tuple[dict[tuple[int, int], tuple[tuple[int, int], ...]],
                                                             set[tuple[int, int]]]:
    routes = {}
    axons = {(core.core_id, binding.axon_id)
             for core in compiled.logical_deployment.core_configs for binding in core.input_axons}
    for core in compiled.logical_deployment.core_configs:
        for entry in core.output_routes:
            origin = (core.core_id, entry.source_compartment)
            if origin in routes:
                raise B13StreamError("duplicate output route descriptor source compartment")
            targets = tuple(sorted((r.destination_core, r.destination_axon) for r in entry.routes))
            if len(targets) != len(set(targets)) or not set(targets) <= axons:
                raise B13StreamError("invalid or duplicate source output routes")
            routes[origin] = targets
    return routes, axons


def _validate_packet_set(packets: tuple[SpikePacket, ...], tick: int,
                         compiled: CompiledDeployment) -> tuple[SpikePacket, ...]:
    """Require complete deterministic fanout per firing origin, no packet loss."""
    _unsigned(tick, name="emitted epoch", limit=(1 << 32) - 2)
    routes, _axons = _output_routes(compiled)
    origins: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    source_count = Counter()
    target_count = Counter()
    for packet in packets:
        if not isinstance(packet, SpikePacket) or packet.packet_class != PacketClass.SPIKE:
            raise B13StreamError("only normalized spike packets are allowed")
        if packet.source_core is None or packet.source_compartment is None:
            raise B13StreamError("routed spike must include source core and compartment")
        if packet.source_timestep != tick or packet.target_timestep != tick + 1:
            raise B13StreamError("routed spike must target NEXT epoch")
        origin = (packet.source_core, packet.source_compartment)
        target = (packet.destination_core, packet.destination_axon)
        if origin not in routes or target not in routes[origin]:
            raise B13StreamError("routed packet not present in accepted P03 output route table")
        origins[origin].append(target)
        source_count[packet.source_core] += 1
        target_count[packet.destination_core] += 1
    for origin, emitted in origins.items():
        if tuple(sorted(emitted)) != routes[origin]:
            raise B13StreamError("incomplete, duplicate, or lossy multi-destination packet fanout")
    for core, count in source_count.items():
        if count > MAX_PACKETS_PER_BANK:
            raise B13StreamError(f"source core {core} output packet bank overflow: {count}>4096")
    for core, count in target_count.items():
        if count > MAX_EVENTS_PER_BANK:
            raise B13StreamError(f"destination core {core} NEXT event bank overflow: {count}>4096")
    return tuple(sorted(packets, key=lambda p: p.logical_key))


def encode_packet_frame(result: B12Result, packets: tuple[SpikePacket, ...],
                        *, emitted_timestep: int) -> bytes:
    compiled = _require_deployment(result)
    normalized = _validate_packet_set(packets, emitted_timestep, compiled)
    payload = b"".join(struct.pack(
        _PACKET, p.target_timestep, p.source_core, p.source_compartment,
        p.destination_core, p.destination_axon,
    ) for p in normalized)
    fields = (
        B13_WIRE_VERSION, B13_HEADER_BYTES, len(payload), emitted_timestep,
        len(normalized), len(compiled.logical_deployment.core_configs),
        B13_PACKET_ENTRY_BYTES, MAX_PACKETS_PER_BANK, 0, 0, 0, 0, 0, 0,
    )
    return _pack_frame(B13_PACKETS_MAGIC, fields, compiled.fingerprint,
                       result.capacity_audit["audit_sha256"], payload)


def decode_packet_frame(raw: bytes, result: B12Result,
                        *, emitted_timestep: int) -> tuple[SpikePacket, ...]:
    compiled = _require_deployment(result)
    fields, payload = _unpack_frame(
        raw, magic=B13_PACKETS_MAGIC, fingerprint=compiled.fingerprint,
        audit_sha=result.capacity_audit["audit_sha256"])
    (_v, _h, byte_count, tick, count, core_count, entry_bytes,
     per_core_limit, reserved_a, reserved_b, *_rest) = fields
    if count > core_count * MAX_PACKETS_PER_BANK:
        raise B13StreamError("B1.3 frame exceeds aggregate physical packet-bank envelope")
    if (tick != emitted_timestep or core_count != len(compiled.logical_deployment.core_configs)
            or entry_bytes != B13_PACKET_ENTRY_BYTES or per_core_limit != MAX_PACKETS_PER_BANK
            or reserved_a or reserved_b or byte_count != count * B13_PACKET_ENTRY_BYTES):
        raise B13StreamError("B1.3 packet frame dimensions or emitted epoch mismatch")
    decoded = tuple(SpikePacket(target_timestep=target_tick,
                                source_core=source_core, source_compartment=source_comp,
                                destination_core=dest_core, destination_axon=dest_axon,
                                source_timestep=tick)
                    for target_tick, source_core, source_comp, dest_core, dest_axon
                    in struct.iter_unpack(_PACKET, payload))
    if tuple(sorted(decoded, key=lambda p: p.logical_key)) != decoded:
        raise B13StreamError("noncanonical B1.3 packet frame order")
    return _validate_packet_set(decoded, tick, compiled)


@dataclass(frozen=True, slots=True)
class EpochReceipt:
    """Counts under two-bank CURRENT/NEXT semantics, not hardware telemetry."""

    tick: int
    current_bank: int
    external_packets: int
    routed_current_packets: int
    new_routed_next_packets: int
    current_events_by_core: tuple[int, ...]
    next_events_by_core: tuple[int, ...]
    emitted_packets_by_core: tuple[int, ...]
    current_packets: tuple[SpikePacket, ...]
    emitted_next_packets: tuple[SpikePacket, ...]


class StreamingEpochGuard:
    """Transactional host-side epoch planner for a B1.3 ingress/packet stream.

    Instantiate from decoded and bound v1 ingress bytes, never a guessed axon
    table. Each successful step advances exactly one global tick; on any error
    the internal epoch and pending NEXT packets remain unchanged. This is an
    executable contract, NOT a 3-slot physical scheduler or a firmware driver.
    """

    def __init__(self, result: B12Result, ingress_bytes: bytes):
        self._compiled = _require_deployment(result)
        self._result = result
        self.ingress = decode_ingress_frame(ingress_bytes, result)
        self.current_tick = 0
        self._pending: tuple[SpikePacket, ...] = ()
        self._core_count = len(self._compiled.logical_deployment.core_configs)

    def step(
        self, packet_frame: bytes, *,
        source_spikes: tuple[tuple[int, int], ...] | None = None,
    ) -> EpochReceipt:
        """Commit one epoch only after all packet, bank and optional spike checks.

        source_spikes is the genuine trace-level set of emitting compartments
        per core, when available. Without it an entirely missing source group
        cannot be distinguished from a silent neuron using packets alone.
        """
        tick = self.current_tick
        if tick >= TOTAL_TICKS:
            raise B13StreamError("26-tick inference already completed; reset for new image")
        emitted = decode_packet_frame(packet_frame, self._result, emitted_timestep=tick)
        if source_spikes is not None:
            routes, _ = _output_routes(self._compiled)
            available = {(core.core_id, neuron)
                         for core in self._compiled.logical_deployment.core_configs
                         for neuron in range(len(core.compartments))}
            if (not isinstance(source_spikes, tuple)
                    or any(not isinstance(origin, tuple) or len(origin) != 2
                           or type(origin[0]) is not int or type(origin[1]) is not int
                           for origin in source_spikes)
                    or len(set(source_spikes)) != len(source_spikes)
                    or not set(source_spikes) <= available):
                raise B13StreamError("invalid or duplicate source spike provenance")
            expected_origins = {origin for origin in source_spikes if routes.get(origin)}
            received_origins = {(p.source_core, p.source_compartment) for p in emitted}
            if expected_origins != received_origins:
                raise B13StreamError("source spike provenance detects missing or spurious packet fanout")
        incoming = self.ingress.events(tick)
        current = tuple(sorted((*incoming, *self._pending), key=lambda p: p.logical_key))
        current_counts = Counter(p.destination_core for p in current)
        next_counts = Counter(p.destination_core for p in emitted)
        emitted_counts = Counter(p.source_core for p in emitted)
        for core_id in range(self._core_count):
            if current_counts[core_id] > MAX_EVENTS_PER_BANK:
                raise B13StreamError(
                    f"core {core_id} CURRENT event bank overflow at tick {tick}: "
                    f"{current_counts[core_id]}>{MAX_EVENTS_PER_BANK}")
            if next_counts[core_id] > MAX_EVENTS_PER_BANK:
                raise B13StreamError(f"core {core_id} NEXT event bank overflow")
            if emitted_counts[core_id] > MAX_PACKETS_PER_BANK:
                raise B13StreamError(f"core {core_id} emitted packet bank overflow")
        if tick == TOTAL_TICKS - 1 and emitted:
            raise B13StreamError("final drain tick cannot drop NEXT packets from ongoing inference")
        if any(p.target_timestep != tick for p in current):
            raise B13StreamError("CURRENT packets assigned wrong consumption epoch")
        receipt = EpochReceipt(
            tick=tick, current_bank=tick % 2,
            external_packets=len(incoming),
            routed_current_packets=len(self._pending),
            new_routed_next_packets=len(emitted),
            current_events_by_core=tuple(current_counts[c] for c in range(self._core_count)),
            next_events_by_core=tuple(next_counts[c] for c in range(self._core_count)),
            emitted_packets_by_core=tuple(emitted_counts[c] for c in range(self._core_count)),
            current_packets=current, emitted_next_packets=emitted,
        )
        self._pending = emitted
        self.current_tick += 1
        return receipt

    def static_worst_case(self) -> dict:
        """Conservative all-255 external + full prior-route fanout budget."""
        by_core_external = Counter(core for _pixel, core, _axon in self.ingress.routes)
        neural = Counter()
        emitted = Counter()
        for core in self._compiled.logical_deployment.core_configs:
            for entry in core.output_routes:
                for route in entry.routes:
                    neural[route.destination_core] += 1
                    emitted[core.core_id] += 1
        counts = tuple(by_core_external[i] + neural[i] for i in range(self._core_count))
        if any(value > MAX_EVENTS_PER_BANK for value in counts):
            raise B13StreamError("worst-case all-255 CURRENT core bank overflow")
        if any(emitted[i] > MAX_PACKETS_PER_BANK for i in range(self._core_count)):
            raise B13StreamError("worst-case source output packet overflow")
        return {
            "schema": B13_SCHEMA,
            "ingress_routes": len(self.ingress.routes),
            "logical_cores": self._core_count,
            "all_255_input_tick_external_events": len(self.ingress.routes),
            "all_255_over_25_ticks_external_events": len(self.ingress.routes) * INPUT_TICKS,
            "max_core_current_bank_events": max(counts),
            "max_core_emitted_packets": max(emitted.values(), default=0),
            "external_per_core": [by_core_external[i] for i in range(self._core_count)],
            "prior_routed_per_core": [neural[i] for i in range(self._core_count)],
            "current_worst_per_core": list(counts),
            "full_ddr_image_bytes_each": 524288,
            "p05_diagnostic_stream_compatible": False,
            "physical_execution": "NOT_TESTED",
        }
