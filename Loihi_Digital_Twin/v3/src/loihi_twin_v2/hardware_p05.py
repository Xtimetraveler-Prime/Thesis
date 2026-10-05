"""P05 full-context logical-core virtualization hardware contract.

P05 replaces the resource-scaled P04 validation memories with independently
retained full logical-core contexts.  The first K26 closure target stores three
contexts and services them with one unchanged P03 HLS compute engine.
"""

from __future__ import annotations

from dataclasses import dataclass

from .core import LogicalCoreConfig
from .hardware_p03 import OneCoreHardwareImage, export_one_core_image

P05_PROFILE_NAME = "p05-k26-three-context-one-engine-v1"
P05_PHYSICAL_ENGINE_COUNT = 1
P05_MAX_RESIDENT_CONTEXTS = 3

# P03 retained-image bits per logical core. P05 adds a second full input-event
# buffer so packets generated while one logical core is serviced cannot mutate
# the current-timestep event image of a logical core that has not run yet.
P05_P03_CONTEXT_BITS = 3_375_104
P05_EVENT_BUFFER_BITS_PER_CONTEXT = 4096 * 32
P05_CONTEXT_BITS_PER_CORE = P05_P03_CONTEXT_BITS + P05_EVENT_BUFFER_BITS_PER_CONTEXT
P05_THREE_CONTEXT_BITS = P05_CONTEXT_BITS_PER_CORE * P05_MAX_RESIDENT_CONTEXTS

# Exact first-pass UltraRAM primitive estimate for three contexts using the
# existing P03 bank widths/depths and two event buffers. UltraRAM288 is treated
# as 4096 x 72 for packing estimates. This is an implementation planning number,
# not a logical Loihi capacity.
P05_ESTIMATED_URAM288 = 47
P05_K26_URAM288_AVAILABLE = 64


@dataclass(frozen=True, slots=True)
class LogicalContextImage:
    context_slot: int
    logical_core_id: int
    image: OneCoreHardwareImage

    def metadata_word(self, initial_event_count: int = 0) -> int:
        """Pack the first P05 controller metadata layout into one 64-bit word."""

        if not 0 <= initial_event_count <= 4096:
            raise ValueError("initial_event_count must be in [0, 4096]")
        if self.image.compartment_count > 1024:
            raise ValueError("logical compartment count exceeds P05 metadata width")
        if self.image.synapse_count > 32768:
            raise ValueError("logical synapse count exceeds P05 metadata width")
        if self.image.route_count > 4096:
            raise ValueError("logical route count exceeds P05 metadata width")

        word = 0
        word |= self.logical_core_id & 0x7F
        word |= (self.image.compartment_count & 0x7FF) << 7
        word |= (self.image.synapse_count & 0xFFFF) << 18
        word |= (self.image.route_count & 0x1FFF) << 34
        word |= (initial_event_count & 0x1FFF) << 47
        return word


@dataclass(frozen=True, slots=True)
class VirtualizedHardwareImage:
    profile: str
    physical_engine_count: int
    contexts: tuple[LogicalContextImage, ...]

    @property
    def logical_core_count(self) -> int:
        return len(self.contexts)

    @property
    def logical_core_ids(self) -> tuple[int, ...]:
        return tuple(context.logical_core_id for context in self.contexts)

    @property
    def logical_to_context_slot(self) -> dict[int, int]:
        return {
            context.logical_core_id: context.context_slot
            for context in self.contexts
        }

    def report(self) -> dict[str, object]:
        return {
            "profile": self.profile,
            "logical_core_count": self.logical_core_count,
            "logical_core_ids": list(self.logical_core_ids),
            "physical_engine_count": self.physical_engine_count,
            "resident_context_slots": [context.context_slot for context in self.contexts],
            "context_bits_per_core": P05_CONTEXT_BITS_PER_CORE,
            "resident_context_bits": P05_CONTEXT_BITS_PER_CORE * self.logical_core_count,
            "estimated_uram288_for_three_context_target": P05_ESTIMATED_URAM288,
            "k26_uram288_available": P05_K26_URAM288_AVAILABLE,
            "logical_capacity_changed": False,
        }


def export_virtualized_hardware_image(
    core_configs: tuple[LogicalCoreConfig, ...],
) -> VirtualizedHardwareImage:
    """Pack up to three full logical-core contexts for the first P05 K26 target.

    Context slots are physical retention locations and are intentionally separate
    from logical core IDs. Routes continue to carry logical destination IDs.
    """

    if not core_configs:
        raise ValueError("P05 hardware image requires at least one logical core")
    if len(core_configs) > P05_MAX_RESIDENT_CONTEXTS:
        raise ValueError(
            f"P05 first hardware profile retains at most {P05_MAX_RESIDENT_CONTEXTS} contexts"
        )

    logical_ids = tuple(config.core_id for config in core_configs)
    if len(logical_ids) != len(set(logical_ids)):
        raise ValueError("P05 logical core IDs must be unique")
    configured = set(logical_ids)

    for config in core_configs:
        for route_entry in config.output_routes:
            for route in route_entry.routes:
                if route.destination_core not in configured:
                    raise ValueError(
                        f"P05 route from logical core {config.core_id} targets "
                        f"unconfigured logical core {route.destination_core}"
                    )

    contexts = tuple(
        LogicalContextImage(
            context_slot=slot,
            logical_core_id=config.core_id,
            image=export_one_core_image(config),
        )
        for slot, config in enumerate(core_configs)
    )
    return VirtualizedHardwareImage(
        profile=P05_PROFILE_NAME,
        physical_engine_count=P05_PHYSICAL_ENGINE_COUNT,
        contexts=contexts,
    )
