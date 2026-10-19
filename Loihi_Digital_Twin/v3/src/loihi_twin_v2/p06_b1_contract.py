"""P06-B1.1 opt-in packed-core/DDR capacity audit (no Track A mutation).

This is a feasibility and provenance guard around the accepted compiler, P03
word exporter, P02 DDR ABI, and P08 page materializer. It does NOT partition a
network by synapse pressure, define a scaled streaming ABI, run the KV260, or
claim native Loihi SRAM equivalence.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json

B1_CONTRACT_SCHEMA = "p06-b1.1-packed-multicore-capacity-audit-v1"

# Accepted P05 diagnostic address/deployment boundary: IDs 0..125. P02 and
# Loihi-like logical model expose 128, but the old P05 deployment admits 126.
P05_DIAGNOSTIC_MAX_CORES = 126
MAX_COMPARTMENTS = 1024
MAX_AXONS = 4096
MAX_ROUTES = 4096
MAX_SYN_WORDS = 32768
MAX_LOGICAL_SYNAPSE_BYTES = 128 * 1024
MAX_EVENTS_PER_BANK = 4096
MAX_PACKETS_PER_BANK = 4096
DDR_RECORD_BYTES = 512 * 1024
P05_RESIDENT_SLOTS = 3
P05_HLS_ENGINES = 1


class B1CapacityError(ValueError):
    """A quantified, fail-closed source/packed capacity violation."""

    def __init__(self, name: str, used: int, limit: int, core_id: int | None = None):
        self.name, self.used, self.limit, self.core_id = name, used, limit, core_id
        location = "" if core_id is None else f"core {core_id}: "
        super().__init__(f"{location}{name}: used={used}, limit={limit}")


def _nonnegative_int(label: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


@dataclass(frozen=True, slots=True)
class CorePressure:
    """Source-independent conservative per-tick resource pressure.

    synapse_words counts actually STORED template entries, not expanded
    connections. For the accepted four-byte project accounting model:
      bytes = 4 * (stored entries + template headers + axon bindings).
    Worst-case CURRENT bank demand sums simultaneous external events and
    all possible PRIOR-epoch routed spikes, even if those maxima cannot
    coincide in a particular application.
    """

    compartments: int
    input_axons: int
    route_words: int
    synapse_words: int
    template_headers: int
    external_events_per_tick: int
    routed_events_per_tick: int
    emitted_packets_per_tick: int

    @property
    def synapse_bytes(self) -> int:
        return 4 * (self.synapse_words + self.template_headers + self.input_axons)

    @property
    def current_event_bank_events(self) -> int:
        return self.external_events_per_tick + self.routed_events_per_tick

    def validate(self, *, core_id: int | None = None) -> "CorePressure":
        fields = (
            ("compartments", self.compartments, MAX_COMPARTMENTS),
            ("input_axons", self.input_axons, MAX_AXONS),
            ("route_words", self.route_words, MAX_ROUTES),
            ("synapse_words", self.synapse_words, MAX_SYN_WORDS),
            ("synapse_bytes", self.synapse_bytes, MAX_LOGICAL_SYNAPSE_BYTES),
            ("external_events_per_tick", self.external_events_per_tick, MAX_EVENTS_PER_BANK),
            ("routed_events_per_tick", self.routed_events_per_tick, MAX_EVENTS_PER_BANK),
            ("current_event_bank_events", self.current_event_bank_events, MAX_EVENTS_PER_BANK),
            ("emitted_packets_per_tick", self.emitted_packets_per_tick, MAX_PACKETS_PER_BANK),
        )
        for label, used, maximum in fields:
            _nonnegative_int(label, used)
            if used > maximum:
                raise B1CapacityError(label, used, maximum, core_id)
        _nonnegative_int("template_headers", self.template_headers)
        return self

    def report(self) -> dict[str, int]:
        self.validate()
        return {
            "compartments": self.compartments,
            "input_axons": self.input_axons,
            "route_words": self.route_words,
            "synapse_words": self.synapse_words,
            "template_headers": self.template_headers,
            "logical_synapse_bytes": self.synapse_bytes,
            "worst_external_events": self.external_events_per_tick,
            "worst_routed_events": self.routed_events_per_tick,
            "worst_current_bank_events": self.current_event_bank_events,
            "worst_emitted_packets": self.emitted_packets_per_tick,
        }


def audit_compiled_candidate(compiled: object) -> dict:
    """Audit a *previously compiled* candidate against real P03/P02 images.

    Calls existing accepted exporters rather than inventing a second packer.
    This is the B1.1 foundation for a NEW opt-in synapse-aware B1.2 compiler;
    the accepted P06-A first-fit compiler is never modified here.
    """
    from .compiler import CompiledDeployment
    from .ddr_abi import (
        P02_DDR_BANK_LAYOUT, P02_DDR_CONTEXT_STRIDE_BYTES,
        P02_DDR_PAYLOAD_END, build_initial_ddr_context_record,
        parse_ddr_context_header,
    )
    from .hardware_p03 import P03_MAX_SYNAPSE_ENTRIES
    from .hardware_p08 import export_paged_hardware_image
    from .hardware_p05 import P05_MAX_RESIDENT_CONTEXTS, P05_PHYSICAL_ENGINE_COUNT

    if not isinstance(compiled, CompiledDeployment):
        raise TypeError("requires a genuine P06 CompiledDeployment")
    configs = compiled.logical_deployment.core_configs
    ids = {config.core_id for config in configs}
    if len(configs) > P05_DIAGNOSTIC_MAX_CORES:
        raise B1CapacityError("p05_diagnostic_core_count", len(configs), P05_DIAGNOSTIC_MAX_CORES)
    if any(cid >= P05_DIAGNOSTIC_MAX_CORES for cid in ids):
        raise ValueError("P05 diagnostic core IDs 126/127 are not supported for B1.1")
    if (P02_DDR_CONTEXT_STRIDE_BYTES != DDR_RECORD_BYTES
            or P03_MAX_SYNAPSE_ENTRIES != MAX_SYN_WORDS
            or P05_MAX_RESIDENT_CONTEXTS != P05_RESIDENT_SLOTS
            or P05_PHYSICAL_ENGINE_COUNT != P05_HLS_ENGINES):
        raise ValueError("frozen packed/DDR/physical-engine contract drift")

    external = Counter()
    seen_external = set()
    for route in compiled.ingress_routes:
        key = (route.input_population, route.input_index, route.destination_core)
        if key in seen_external:
            raise ValueError(f"duplicate external logical route {key}")
        seen_external.add(key)
        if route.destination_core not in ids:
            raise ValueError("external route targets missing logical core")
        external[route.destination_core] += 1

    routed = Counter()
    for config in configs:
        for entry in config.output_routes:
            for route in entry.routes:
                if route.destination_core not in ids:
                    raise ValueError("output route targets missing logical core")
                routed[route.destination_core] += 1

    hardware = export_paged_hardware_image(configs)
    layout = [
        {"name": bank.name, "offset": bank.offset,
         "word_bytes": bank.word_bytes, "depth": bank.depth,
         "bytes": bank.size_bytes}
        for bank in P02_DDR_BANK_LAYOUT
    ]
    checked = []
    for context, config in zip(hardware.backing_contexts, configs, strict=True):
        image = context.image
        if config.synapse_cost_model.name != "v2-simple-32bit-entry":
            raise ValueError("B1.1 only audits the accepted four-byte P06 cost model")
        pressure = CorePressure(
            compartments=image.compartment_count,
            input_axons=len(image.axon_words),
            route_words=image.route_count,
            synapse_words=len(image.synapse_words),
            template_headers=len(config.synapse_templates),
            external_events_per_tick=external[config.core_id],
            routed_events_per_tick=routed[config.core_id],
            emitted_packets_per_tick=image.route_count,
        ).validate(core_id=config.core_id)
        if pressure.synapse_bytes != config.resource_usage.synapse_bytes:
            raise ValueError(f"core {config.core_id}: logical/packed synapse accounting disagrees")
        if (pressure.input_axons != len(config.input_axons)
                or pressure.route_words != config.resource_usage.output_routes
                or pressure.synapse_words != image.synapse_count):
            raise ValueError(f"core {config.core_id}: P03 exporter occupancy mismatch")
        record = build_initial_ddr_context_record(context)
        header = parse_ddr_context_header(record, verify_payload=True)
        if (len(record) != DDR_RECORD_BYTES or header.logical_core_id != config.core_id
                or header.compartment_count != pressure.compartments
                or header.synapse_count != pressure.synapse_words
                or header.route_count != pressure.route_words
                or header.event0_count or header.event1_count or header.packet_count
                or any(record[P02_DDR_PAYLOAD_END:])):
            raise ValueError(f"core {config.core_id}: invalid initial 512KiB DDR image")
        checked.append({
            "core_id": config.core_id,
            **pressure.report(),
            "record_bytes": len(record),
            "initial_ddr_sha256": hashlib.sha256(record).hexdigest(),
            "initial_ddr_payload_sha256": header.payload_sha256,
        })

    manifest = {
        "schema": B1_CONTRACT_SCHEMA,
        "source_network_sha256": compiled.source_fingerprint,
        "original_compiled_sha256": compiled.fingerprint,
        "original_compiler_version": compiled.compiler_version,
        "logical_core_count": len(configs),
        "resident_context_slots": hardware.resident_context_count,
        "physical_hls_engines": hardware.physical_engine_count,
        "backing_bytes": len(configs) * DDR_RECORD_BYTES,
        "record_bytes_each": DDR_RECORD_BYTES,
        "ddr_bank_layout": layout,
        "cores": checked,
        "new_b1_partition_algorithm": "NOT_IMPLEMENTED_B1_1",
        "new_scaled_ingress_abi": "NOT_IMPLEMENTED_B1_1",
        "p05_diagnostic_abi_scaled_compatible": False,
        "physical_kv260_execution": "NOT_TESTED",
        "official_mnist_test_access": "NONE",
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest["audit_sha256"] = hashlib.sha256(canonical).hexdigest()
    return manifest
