"""P08 host-paged hardware-image contract for deployments larger than P05.

The physical K26 shell still retains at most three complete P05 context slots and
uses one P03-compatible HLS engine. P08 adds a host/backing image containing all
logical cores. Any subset of up to three logical contexts can be materialized
into the resident slots without changing logical IDs or route destinations.
"""

from __future__ import annotations

from dataclasses import dataclass

from .compiler import CompiledDeployment
from .core import LogicalCoreConfig
from .hardware_p03 import OneCoreHardwareImage, export_one_core_image
from .hardware_p05 import (
    LogicalContextImage,
    P05_CONTEXT_BITS_PER_CORE,
    P05_MAX_RESIDENT_CONTEXTS,
    P05_PHYSICAL_ENGINE_COUNT,
)


P08_PAGED_FPGA_PROFILE_NAME = "p08-host-paged-p05-context-v1"
P08_RESIDENT_CONTEXT_COUNT = P05_MAX_RESIDENT_CONTEXTS


@dataclass(frozen=True, slots=True)
class BackingLogicalContextImage:
    """One full logical context retained in host/backing storage."""

    logical_core_id: int
    image: OneCoreHardwareImage

    def metadata_word(self, initial_event_count: int = 0) -> int:
        # Reuse the accepted P05 metadata layout. Context slot is intentionally
        # supplied only when the backing image is materialized as a resident page.
        return LogicalContextImage(
            context_slot=0,
            logical_core_id=self.logical_core_id,
            image=self.image,
        ).metadata_word(initial_event_count=initial_event_count)


@dataclass(frozen=True, slots=True)
class ResidentPageImage:
    """A concrete set of logical contexts loaded into P05 resident slots."""

    contexts: tuple[LogicalContextImage, ...]

    @property
    def logical_core_ids(self) -> tuple[int, ...]:
        return tuple(context.logical_core_id for context in self.contexts)

    @property
    def logical_to_context_slot(self) -> dict[int, int]:
        return {
            context.logical_core_id: context.context_slot
            for context in self.contexts
        }


@dataclass(frozen=True, slots=True)
class PagedHardwareImage:
    profile: str
    physical_engine_count: int
    resident_context_count: int
    backing_contexts: tuple[BackingLogicalContextImage, ...]
    initial_resident_core_ids: tuple[int, ...]

    @property
    def logical_core_count(self) -> int:
        return len(self.backing_contexts)

    @property
    def logical_core_ids(self) -> tuple[int, ...]:
        return tuple(context.logical_core_id for context in self.backing_contexts)

    @property
    def requires_paging(self) -> bool:
        return self.logical_core_count > self.resident_context_count

    @property
    def backing_by_logical_core(self) -> dict[int, BackingLogicalContextImage]:
        return {
            context.logical_core_id: context
            for context in self.backing_contexts
        }

    def resident_page(self, logical_core_ids: tuple[int, ...]) -> ResidentPageImage:
        """Materialize up to three backing contexts into physical slot order."""

        if not logical_core_ids:
            raise ValueError("resident page must contain at least one logical core")
        if len(logical_core_ids) > self.resident_context_count:
            raise ValueError("resident page exceeds physical context-slot count")
        if len(logical_core_ids) != len(set(logical_core_ids)):
            raise ValueError("resident page logical core IDs must be unique")

        backing = self.backing_by_logical_core
        unknown = set(logical_core_ids) - set(backing)
        if unknown:
            raise ValueError(f"resident page contains unknown logical cores {sorted(unknown)}")

        return ResidentPageImage(
            contexts=tuple(
                LogicalContextImage(
                    context_slot=slot,
                    logical_core_id=logical_core_id,
                    image=backing[logical_core_id].image,
                )
                for slot, logical_core_id in enumerate(logical_core_ids)
            )
        )

    def initial_page(self) -> ResidentPageImage:
        return self.resident_page(self.initial_resident_core_ids)

    def report(self) -> dict[str, object]:
        return {
            "profile": self.profile,
            "logical_core_count": self.logical_core_count,
            "logical_core_ids": list(self.logical_core_ids),
            "backing_context_count": self.logical_core_count,
            "resident_context_count": self.resident_context_count,
            "initial_resident_core_ids": list(self.initial_resident_core_ids),
            "physical_engine_count": self.physical_engine_count,
            "requires_paging": self.requires_paging,
            "context_bits_per_resident_slot": P05_CONTEXT_BITS_PER_CORE,
            "resident_context_bits": self.resident_context_count * P05_CONTEXT_BITS_PER_CORE,
            "logical_capacity_changed": False,
        }


@dataclass(frozen=True, slots=True)
class PagedCompiledFpgaImage:
    profile: str
    compiled_deployment_fingerprint: str
    source_fingerprint: str
    hardware_image: PagedHardwareImage

    @property
    def logical_core_count(self) -> int:
        return self.hardware_image.logical_core_count

    def report(self) -> dict[str, object]:
        return {
            "profile": self.profile,
            "compiled_deployment_fingerprint": self.compiled_deployment_fingerprint,
            "source_fingerprint": self.source_fingerprint,
            "logical_core_count": self.logical_core_count,
            "resident_context_count": self.hardware_image.resident_context_count,
            "physical_engine_count": self.hardware_image.physical_engine_count,
            "requires_paging": self.hardware_image.requires_paging,
            "hardware": self.hardware_image.report(),
            "logical_capacity_changed": False,
        }


def _validate_route_targets(core_configs: tuple[LogicalCoreConfig, ...]) -> None:
    configured = {config.core_id: config for config in core_configs}
    for config in core_configs:
        for route_entry in config.output_routes:
            for route in route_entry.routes:
                destination = configured.get(route.destination_core)
                if destination is None:
                    raise ValueError(
                        f"P08 route from logical core {config.core_id} targets "
                        f"unconfigured logical core {route.destination_core}"
                    )
                destination_axons = {binding.axon_id for binding in destination.input_axons}
                if route.destination_axon not in destination_axons:
                    raise ValueError(
                        f"P08 route from logical core {config.core_id} targets missing "
                        f"axon {route.destination_axon} on logical core {route.destination_core}"
                    )


def export_paged_hardware_image(
    core_configs: tuple[LogicalCoreConfig, ...],
    *,
    resident_context_count: int = P08_RESIDENT_CONTEXT_COUNT,
) -> PagedHardwareImage:
    """Export any valid logical deployment into host backing plus P05 slots.

    Unlike :func:`export_virtualized_hardware_image`, routes may target logical
    cores that are not on the same resident page. P08 host routing preserves the
    packet's logical destination ID and appends the event to that logical core's
    backing next-event image before the next algorithmic timestep.
    """

    if not core_configs:
        raise ValueError("P08 paged hardware image requires at least one logical core")
    if not 1 <= resident_context_count <= P05_MAX_RESIDENT_CONTEXTS:
        raise ValueError(
            f"resident_context_count must be in [1, {P05_MAX_RESIDENT_CONTEXTS}]"
        )

    logical_ids = tuple(config.core_id for config in core_configs)
    if len(logical_ids) != len(set(logical_ids)):
        raise ValueError("P08 logical core IDs must be unique")
    _validate_route_targets(core_configs)

    ordered = tuple(sorted(core_configs, key=lambda config: config.core_id))
    backing = tuple(
        BackingLogicalContextImage(
            logical_core_id=config.core_id,
            image=export_one_core_image(config),
        )
        for config in ordered
    )
    effective_resident_count = min(resident_context_count, len(backing))
    initial = tuple(context.logical_core_id for context in backing[:effective_resident_count])

    return PagedHardwareImage(
        profile=P08_PAGED_FPGA_PROFILE_NAME,
        physical_engine_count=P05_PHYSICAL_ENGINE_COUNT,
        resident_context_count=effective_resident_count,
        backing_contexts=backing,
        initial_resident_core_ids=initial,
    )


def export_paged_compiled_fpga_image(
    compiled: CompiledDeployment,
) -> PagedCompiledFpgaImage:
    """Export a P06 deployment without imposing the three-resident-core limit."""

    hardware = export_paged_hardware_image(compiled.logical_deployment.core_configs)
    return PagedCompiledFpgaImage(
        profile=P08_PAGED_FPGA_PROFILE_NAME,
        compiled_deployment_fingerprint=compiled.fingerprint,
        source_fingerprint=compiled.source_fingerprint,
        hardware_image=hardware,
    )
